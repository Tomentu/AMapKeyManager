from flask import Flask, jsonify, request
from app.core.config import Config
from app.core.database import db
from app.core.logger import setup_logger, logger
from app.core.extensions import init_extensions
from app.api.proxy import proxy_bp
from app.api.admin import admin_bp
from app.api.polygon import polygon_bp
from app.api.health import health_bp


def create_app(config=None):
    app = Flask(__name__)
    
    # 1. 加载默认配置
    app.config.from_object(Config)
    
    # 2. 加载额外配置（如果有）
    if config:
        app.config.update(config)
    
    # 3. 按顺序初始化核心组件
    db.init_app(app)
    setup_logger(app)
    
    with app.app_context():
        # 4. 确保数据库表存在
        db.create_all()
        
        # 5. 导入模型以触发自动创建
        from app.models.api_key import APIKey
        from app.models.polygon_task import PolygonTask
        
        # 6. 初始化扩展（包括任务执行器）
        init_extensions(app)
    
    # 7. 注册蓝图
    app.register_blueprint(proxy_bp, url_prefix='/amap')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(polygon_bp, url_prefix='/api/polygon')
    app.register_blueprint(health_bp, url_prefix='/health')

    
    # 8. 全局错误处理
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
        logger.error(f"Unhandled exception: {str(e)}")
        return jsonify({
            'status': '0',
            'info': 'Server Error',
            'message': '服务器异常'
        }), 500

    return app 