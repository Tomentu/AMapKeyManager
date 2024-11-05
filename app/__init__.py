from flask import Flask, jsonify, request
from app.core.config import Config
from app.core.database import db
from app.core.logger import setup_logger, logger
from app.api.proxy import proxy_bp
from app.api.admin import admin_bp
from app.api.polygon import polygon_bp


def create_app(config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # 初始化组件
    db.init_app(app)
    setup_logger(app)
    
    # 注册蓝图
    app.register_blueprint(proxy_bp, url_prefix='/amap')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(polygon_bp, url_prefix='/api/polygon')
    
    # 全局错误处理
    @app.errorhandler(404)
    def handle_404(e):
        logger.warning(f'404 Not Found: {request.url}')
        return jsonify({
            'status': '0',
            'info': 'Not Found',
            'message': '请求的接口不存在',
            'path': request.path
        }), 404

    @app.errorhandler(500)
    def handle_500(e):
        logger.error(f'500 Server Error: {str(e)}')
        logger.error(f'Request URL: {request.url}')
        logger.error(f'Request Method: {request.method}')
        logger.error(f'Request Args: {dict(request.args)}')
        return jsonify({
            'status': '0',
            'info': 'Internal Server Error',
            'message': '服务器内部错误'
        }), 500

    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.error(f"Unhandled exception: {str(e)}")
        return jsonify({
            'status': '0',
            'info': 'Server Error',
            'message': '服务器异常'
        }), 500

    with app.app_context():
        # 确保所有模型表都存在
        db.create_all()
        
        # 导入模型以触发自动创建
        from app.models.api_key import APIKey
        from app.models.polygon_task import PolygonTask

    return app 