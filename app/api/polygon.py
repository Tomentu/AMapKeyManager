from flask import Blueprint, request, jsonify, current_app, send_from_directory
from app.services.polygon_crawler import PolygonCrawler
from app.models.polygon_task import PolygonTask
from app.core.database import db
import os
import logging

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

        task = PolygonCrawler.create_task(
            task_id=data['task_id'],
            name=data['name'],
            polygon=data['polygon']
        )

        return jsonify({
            'task_id': task.task_id,
            'name': task.name,
            'status': task.status
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@polygon_bp.route('/tasks', methods=['GET'])
def list_tasks():
    """获取任务列表"""
    try:
        tasks = PolygonTask.query.order_by(PolygonTask.created_at.desc()).all()
        return jsonify([{
            'task_id': task.task_id,
            'name': task.name,
            'status': task.status,
            'current_type': task.current_type,
            'current_page': task.current_page,
            'progress': task.progress,
            'created_at': task.created_at.isoformat(),
            'updated_at': task.updated_at.isoformat()
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