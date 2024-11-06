from flask import Blueprint, jsonify
from app.models.polygon_task import PolygonTask
from datetime import datetime
from app.services.polygon_crawler import PolygonCrawler
from app.services.key_manager import KeyManager

health_bp = Blueprint('health', __name__)

@health_bp.route('/', methods=['GET'])
def health_check():
    """系统健康状态检查"""
    try:
        return jsonify({
            'status': 'healthy',
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500 