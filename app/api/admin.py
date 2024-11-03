from flask import Blueprint, request, jsonify, render_template
from app.models.api_key import APIKey
from app.core.database import db
import logging

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/')
def admin_page():
    """管理页面"""
    return render_template('admin/keys.html')

@admin_bp.route('/keys', methods=['GET'])
def list_keys():
    """获取所有key的状态"""
    keys = APIKey.query.all()
    return jsonify([{
        'id': key.id,
        'key': key.masked_key,
        'is_active': key.is_active,
        'description': key.description,
        'last_reset': key.last_reset.isoformat() if key.last_reset else None,
        'search_usage': {
            'keyword': {
                'used': key.keyword_search_used,
                'limit': key.SEARCH_LIMITS['keyword'],
                'qps': key.QPS_LIMITS['keyword']
            },
            'around': {
                'used': key.around_search_used,
                'limit': key.SEARCH_LIMITS['around'],
                'qps': key.QPS_LIMITS['around']
            },
            'polygon': {
                'used': key.polygon_search_used,
                'limit': key.SEARCH_LIMITS['polygon'],
                'qps': key.QPS_LIMITS['polygon']
            }
        }
    } for key in keys])

@admin_bp.route('/keys', methods=['POST'])
def add_key():
    """添加新key"""
    try:
        data = request.get_json()
        key = APIKey(
            key=data.get('key'),
            description=data.get('description'),
            is_active=True
        )
        db.session.add(key)
        db.session.commit()
        return jsonify({
            'id': key.id,
            'key': key.masked_key,
            'is_active': key.is_active,
            'description': key.description,
            'search_usage': {
                'keyword': {
                    'used': key.keyword_search_used,
                    'limit': key.SEARCH_LIMITS['keyword'],
                    'qps': key.QPS_LIMITS['keyword']
                },
                'around': {
                    'used': key.around_search_used,
                    'limit': key.SEARCH_LIMITS['around'],
                    'qps': key.QPS_LIMITS['around']
                },
                'polygon': {
                    'used': key.polygon_search_used,
                    'limit': key.SEARCH_LIMITS['polygon'],
                    'qps': key.QPS_LIMITS['polygon']
                }
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/keys/<int:key_id>', methods=['PUT'])
def update_key(key_id):
    """更新key信息"""
    try:
        key = APIKey.query.get_or_404(key_id)
        data = request.get_json()
        
        if 'is_active' in data:
            key.is_active = data['is_active']
        if 'description' in data:
            key.description = data['description']
            
        db.session.commit()
        return jsonify({
            'message': 'Key updated successfully',
            'key': {
                'id': key.id,
                'key': key.masked_key,
                'is_active': key.is_active,
                'description': key.description,
                'search_usage': {
                    'keyword': {
                        'used': key.keyword_search_used,
                        'limit': key.SEARCH_LIMITS['keyword'],
                        'qps': key.QPS_LIMITS['keyword']
                    },
                    'around': {
                        'used': key.around_search_used,
                        'limit': key.SEARCH_LIMITS['around'],
                        'qps': key.QPS_LIMITS['around']
                    },
                    'polygon': {
                        'used': key.polygon_search_used,
                        'limit': key.SEARCH_LIMITS['polygon'],
                        'qps': key.QPS_LIMITS['polygon']
                    }
                }
            }
        })
    except Exception as e:
        logger.error(f"Failed to update key: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/keys/<int:key_id>', methods=['DELETE'])
def delete_key(key_id):
    """删除key"""
    try:
        key = APIKey.query.get_or_404(key_id)
        db.session.delete(key)
        db.session.commit()
        return jsonify({'message': 'Key deleted successfully'})
    except Exception as e:
        logger.error(f"Failed to delete key: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500