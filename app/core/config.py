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
        'weight5': '060401|060402|060403|060404|060405|060406|060407|060408|060409|060413|060414|060415|141201|150104|150200',
        'weight4_商场': '060100|060101|060102',
        'weight4_超级&综合市场': '060400|060411|060700',
        'weight4_商务住宅': '120201|120203|120300|120302',
        'weight4_科教&交通': '141206|150400',
        'weight3_咖啡厅': '050500|050501|050502|050503|050504',
        'weight3_快餐厅': '050300|050301|050302|050303',
        'weight3_餐饮other':'050600|050700|050800|050900',
        'weight3_综合市场': '060701|060703|060704|060705|060706',
        'weight3_购物other':'060000|060103',
        'weight3_学校': '141200|141202|141203|141204', 
        'weight3_传媒&科研&培训机构': '141100|141101|141102|141103|141104|141105|141300|141400',
        'weight3_科教other':'140100|140200|140300|140400|140500|140600|140700|140800',
        'weight3_住宿other':'120303|100200|100201|100000',
        'weight3_宾馆酒店': '100100|100101|100102|100103|100104|100105',
        'weight3_other':'150500|170000|170100|980100',
        'weight2_体育休闲服务': '080101|080102|080103|080104|080105|080108|080110|080111|080112|080113|080118|080119|080300|080301|080302|080303|080304|080305|080306|080307|080308|080600|080601|080602|080603',
        'weight2_购物服务': '060200|060201|060202|060300|060301|060302|060303|060304|060305|060306|060307|060308|060900|060901|060902|060903|060904|060905|060906|060907',      
        'weight2_商业街': '061000|061001',
        'weight1_生活服务': '070400|070401|070500|071100|071300|071400|071500|071600|071800|072101',
        'weight1_金融保险服务': '160100|160101|160102|160103|160104|160105|160106|160107|160108|160109|160110|160111|160112|160113|160114|160115|160117|160118|160119|160120|160121|160122|160123|160124|160125|160126|160127|160128|160129|160130|160131|160132|160133|160134|160135|160136|160137|160138|160139|160140|160141|160142|160143|160144|160145|160146|160147|160148|160149|160150|160151|160152|160200|160400|160401|160402|160403|160404|160405|160406|160407|160408',
        'weight1_中餐厅': '050100|050101|050102|050103|050104|050105|050106|050107|050108|050109|050110|050111|050112|050113|050114|050115|050116|050117|050118|050119|050120|050121|050122|050123',
        'weight1_外国餐厅': '050200|050201|050202|050203|050204|050205|050206|050207|050208|050209|050210|050211|050212|050213|050214|050215|050216|050217',
        'weight1_快餐厅': '050304|050305|050306|050307|050308|050309|050310|050311',
        'weight1_餐饮other':'050000|050400',
        'weight12_other': '110000|110200|190700|141205|190500',
  }