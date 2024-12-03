from flask import Blueprint, request, jsonify, current_app, send_from_directory
from app.services.polygon_crawler import PolygonCrawler
from app.models.polygon_task import PolygonTask
from app.core.database import db
import os
import logging
from app.services.task_executor import TaskExecutor
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

polygon_bp = Blueprint('polygon', __name__)

@polygon_bp.route('/tasks', methods=['POST'])
def create_task():
    """创建新的多边形POI爬取任务"""
    try:
        data = request.get_json()
        if not data or 'task_id' not in data or 'name' not in data or 'polygon' not in data:
            return jsonify({
                'error': 'Missing required fields: task_id, name, polygon'
            }), 400

        # 检查task_id是否已存在
        if PolygonTask.query.filter_by(task_id=data['task_id']).first():
            return jsonify({
                'error': 'Task ID already exists'
            }), 400

        # 获取优先级，默认为0
        priority = data.get('priority', 999)

        task = PolygonCrawler.create_task(
            task_id=data['task_id'],
            name=data['name'],
            polygon=data['polygon'],
            priority=priority
        )

        return jsonify({
            'task_id': task.task_id,
            'name': task.name,
            'status': task.status,
            'priority': task.priority
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@polygon_bp.route('/tasks', methods=['GET'])
def list_tasks():
    """获取任务列表，支持状态筛选和分页，已完成降序，未完成升序"""
    try:
        # 获取查询参数
        status = request.args.get('status', 'all')  # all, completed, incomplete
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        # 构建基础查询
        query = PolygonTask.query

        # 根据状态筛选并设置对应的排序方式
        if status == 'completed':
            # 已完成任务按id降序
            query = query.filter_by(status='completed')\
                        .order_by(PolygonTask.id.desc())
        elif status == 'incomplete':
            # 未完成任务按id升序
            query = query.filter(PolygonTask.status != 'completed')\
                        .order_by(PolygonTask.id.asc())
        else:
            # 默认情况：先显示未完成的（升序），再显示已完成的（降序）
            incomplete = query.filter(PolygonTask.status != 'completed')\
                            .order_by(PolygonTask.id.asc())
            completed = query.filter_by(status='completed')\
                           .order_by(PolygonTask.id.asc())
            query = incomplete.union(completed)     

        # 添加分页
        paginated_tasks = query.paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            'tasks': [{
                'task_id': task.task_id,
                'name': task.name,
                'status': 'stalled' if task.is_stalled() else task.status,
                'current_type': task.current_type,
                'current_page': task.current_page,
                'progress': task.progress,
                'created_at': task.created_at.isoformat(),
                'updated_at': task.updated_at.isoformat(),
                'priority': task.priority
            } for task in paginated_tasks.items],
            'pagination': {
                'total': paginated_tasks.total,
                'pages': paginated_tasks.pages,
                'current_page': paginated_tasks.page,
                'per_page': paginated_tasks.per_page,
                'has_next': paginated_tasks.has_next,
                'has_prev': paginated_tasks.has_prev
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@polygon_bp.route('/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    """获取任务详情"""
    try:
        task = PolygonTask.query.filter_by(task_id=str(task_id)).first()
        if not task:
            return jsonify({'error': f'Task not found: {task_id}'}), 404
            
        return jsonify({
            'task_id': task.task_id,
            'name': task.name,
            'status': task.status,
            'current_type': task.current_type,
            'current_page': task.current_page,
            'polygon': task.polygon,
            'result_file': task.result_file,
            'created_at': task.created_at.isoformat(),
            'updated_at': task.updated_at.isoformat()
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@polygon_bp.route('/tasks/<int:task_id>/result', methods=['GET'])
def download_result(task_id):
    """下载任务结果"""
    try:
        task = PolygonTask.query.filter_by(task_id=str(task_id)).first()
        if not task:
            return jsonify({'error': f'Task not found: {task_id}'}), 404
            
        if not task.result_file:
            return jsonify({'error': 'No result file available'}), 404

        # 获取results目录路径
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # app目录
        results_dir = os.path.join(current_dir, 'results')  # app/results

        return send_from_directory(
            results_dir,
            task.result_file,
            as_attachment=True
        )

    except Exception as e:
        logger.error(f"Download failed: {str(e)}")
        return jsonify({'error': str(e)}), 500

@polygon_bp.route('/tasks/<string:task_id>/resume', methods=['POST'])
def resume_task(task_id):
    """恢复任务执行"""
    try:
        PolygonCrawler.resume_task(task_id)
        task = PolygonTask.query.filter_by(task_id=task_id).first()
        
        return jsonify({
            'task_id': task.task_id,
            'name': task.name,
            'status': task.status,
            'message': 'Task resumed successfully'
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500 

@polygon_bp.route('/tasks/<string:task_id>/priority', methods=['PUT'])
def update_priority(task_id):
    """更新任务优先级"""
    try:
        data = request.get_json()
        if 'priority' not in data:
            return jsonify({'error': 'Missing priority field'}), 400

        task = PolygonTask.query.filter_by(task_id=task_id).first()
        if not task:
            return jsonify({'error': 'Task not found'}), 404

        if task.status == 'running' and not task.is_stalled():
            return jsonify({'error': 'Cannot update priority of running task'}), 400

        task.priority = data['priority']
        db.session.commit()

        return jsonify({
            'task_id': task.task_id,
            'priority': task.priority
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500 

@polygon_bp.route('/tasks/resume-batch', methods=['POST'])
def resume_tasks_batch():
    """批量恢复任务"""
    try:
        data = request.get_json()
        limit = data.get('limit', 5)  # 默认恢复5个任务
        
        # 验证参数
        try:
            limit = int(limit)
            if limit <= 0:
                return jsonify({'error': 'Limit must be positive integer'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid limit value'}), 400
            
        # 执行批量恢复
        resumed_tasks = PolygonCrawler.resume_tasks(limit)
        
        return jsonify({
            'message': f'Successfully resumed {len(resumed_tasks)} tasks',
            'resumed_tasks': resumed_tasks
        })

    except Exception as e:
        logger.error(f"Batch resume failed: {str(e)}")
        return jsonify({'error': str(e)}), 500


@polygon_bp.route('/tasks/start', methods=['POST'])
def start_task():
    """启动任务"""
    PolygonCrawler.start_background_check()
    return jsonify({'message': 'Task started'}), 200

@polygon_bp.route('/tasks/stop-all', methods=['POST'])
def stop_all_tasks():
    """停止所有任务"""
    try:

        #取消所有等待任务
        PolygonTask.query.filter(PolygonTask.status == 'waiting').update({'status': 'pending'})
        db.session.commit()
        
        # 停止所有任务
        executor = TaskExecutor()
        stopped_tasks = executor.stop_all_tasks()
        
        # 更新数据库中任务的状态
        for task_id in stopped_tasks:
            task = PolygonTask.query.filter_by(task_id=task_id).first()
            if task:
                task.status = 'pending'
        db.session.commit()
        
        return jsonify({
            'message': f'Successfully stopped {len(stopped_tasks)} tasks',
            'stopped_tasks': stopped_tasks
        })

    except Exception as e:
        logger.error(f"Stop all tasks failed: {str(e)}")
        return jsonify({'error': str(e)}), 500

@polygon_bp.route('/tasks/completed-by-date', methods=['GET'])
def list_completed_tasks_by_date():
    """获取指定日期完成的任务列表（不分页）"""
    try:
        # 获取日期参数，默认为今天
        date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))

        try:
            # 解析日期
            target_date = datetime.strptime(date_str, '%Y-%m-%d')
            # 设置日期范围（当天0点到次日0点）
            start_time = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = start_time + timedelta(days=1)
        except ValueError:
            return jsonify({'error': '日期格式无效，请使用YYYY-MM-DD格式'}), 400

        # 查询指定日期完成的所有任务
        tasks = PolygonTask.query\
            .filter_by(status='completed')\
            .filter(PolygonTask.updated_at >= start_time)\
            .filter(PolygonTask.updated_at < end_time)\
            .order_by(PolygonTask.id.desc())\
            .all()

        return jsonify({
            'date': date_str,
            'tasks': [{
                'task_id': task.task_id,
                'name': task.name,
                'status': task.status,
                'current_type': task.current_type,
                'current_page': task.current_page,
                'polygon': task.polygon,
                'created_at': task.created_at.isoformat(),
                'updated_at': task.updated_at.isoformat(),
                'priority': task.priority
            } for task in tasks],
            'statistics': {
                'total_completed': len(tasks),
                'date_range': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat()
                }
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500