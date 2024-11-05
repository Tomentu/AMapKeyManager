import os
from datetime import timedelta
from dotenv import load_dotenv
from urllib.parse import quote_plus

# 加载 .env 文件
load_dotenv()

class Config:
    """应用配置类"""
    
    # 基础配置
    ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = ENV == 'development'
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-please-change')
    
    # 数据库配置
    DB_USER = os.getenv('DB_USER')
    DB_PASS = os.getenv('DB_PASS')
    DB_HOST = os.getenv('DB_HOST')
    DB_PORT = os.getenv('DB_PORT')
    DB_NAME = os.getenv('DB_NAME')
    
    # 数据库URI
    SQLALCHEMY_DATABASE_URI = (
        f'mysql+pymysql://{DB_USER}:{quote_plus(DB_PASS)}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_POOL_SIZE = int(os.getenv('SQLALCHEMY_POOL_SIZE', '10'))
    SQLALCHEMY_MAX_OVERFLOW = int(os.getenv('SQLALCHEMY_MAX_OVERFLOW', '20'))
    SQLALCHEMY_ECHO = os.getenv('SQLALCHEMY_ECHO', 'false').lower() == 'true'
    
    # API代理配置
    AMAP_BASE_URL = os.getenv('AMAP_BASE_URL')
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT'))
    
    # 代理配置
    CUSTOM_PROXY_URL = os.getenv('CUSTOM_PROXY_URL', 'http://localhost:5000/amap')
    PROXY_ENABLED = os.getenv('PROXY_ENABLED', 'false').lower() == 'true'
    HTTP_PROXY = os.getenv('HTTP_PROXY')
    HTTPS_PROXY = os.getenv('HTTPS_PROXY')
    
    # 日志配置
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'app.log')
    LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', '10485760'))  # 10MB
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))
    
    # 管理员配置
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
    
    # 时区配置
    TIMEZONE = os.getenv('TIMEZONE', 'Asia/Shanghai')
    KEY_RESET_HOUR = int(os.getenv('KEY_RESET_HOUR', '1'))