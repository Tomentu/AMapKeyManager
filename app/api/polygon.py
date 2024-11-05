from flask import Blueprint, request, jsonify, current_app, send_from_directory
from app.services.polygon_crawler import PolygonCrawler
from app.models.polygon_task import PolygonTask
from app.core.database import db
import os
import logging
from app.services.task_executor import TaskExecutor

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
    """获取任务列表"""
    try:
        tasks = PolygonTask.query.order_by(PolygonTask.id.desc()).all()
        return jsonify([{
            'task_id': task.task_id,
            'name': task.name,
            'status': 'stalled' if task.is_stalled() else task.status,
            'current_type': task.current_type,
            'current_page': task.current_page,
            'progress': task.progress,
            'created_at': task.created_at.isoformat(),
            'updated_at': task.updated_at.isoformat(),
            'priority': task.priority
        } for task in tasks])

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

@polygon_bp.route('/tasks/stop-all', methods=['POST'])
def stop_all_tasks():
    """停止所有任务"""
    try:
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