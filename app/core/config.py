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
    
    # POI类型配置

    POI_TYPES = {
        '交通设施服务': '150104|150200|150400|150500',
        '风景名胜': '110000|110200',
        '住宿服务': '100000|100100|100101|100102|100103|100104|100105|100200|100201',
        # 商务住宅
        '商务住宅': '120000|120100|120200|120201|120202|120203|120300',
        # 生活服务
        '生活服务': '070000|070100|070200|070300|070400|070500|070600|070700|070800|070900|071000|071100|071200|071300|071400',
        # 体育休闲
        '体育休闲': '080000|080100|080200|080300|080400|080500|080600',
        # 医疗保健
        '医疗保健': '090000|090100|090200|090300|090400|090500|090600',
        # 餐饮服务
        '餐饮服务': '050000|050100|050200|050300|050400|050500|050600|050700|050800',
        # 购物服务
        '购物服务': '060000|060100|060200|060300|060400|060500|060600|060700|060800|060900',
        # 科教文化
        '科教文化': '140000|140100|140200|140300|140400|140500|140600|140700|140800',
        # 公司企业
        '公司企业': '170000|170100|170200|170300',
        # 金融保险
        '金融保险': '160000|160100|160200|160300|160400',
        # 政府机构
        '政府机构': '130000|130100|130200|130300|130400',
        # 汽车服务
        '汽车服务': '030000|030100|030200|030300|030400|030500|030600|030700|030800|030900|031000|031100|031200',
        # 汽车销售
        '汽车销售': '040000|040100|040200|040300|040400|040500',
    }