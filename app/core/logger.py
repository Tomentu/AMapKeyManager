import os
import logging
from logging.handlers import RotatingFileHandler
from app.core.config import Config

# 创建全局logger实例
logger = logging.getLogger('amap_proxy')

def setup_logger(app):
    """配置日志系统"""
    global logger
    
    # 避免重复配置
    if logger.handlers:
        return logger
        
    # 强制设置为DEBUG级别
    logger.setLevel(logging.DEBUG)
    
    # 创建控制台处理器并设置为DEBUG
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    
    # 创建logs目录
    log_dir = os.path.dirname(Config.LOG_FILE)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 设置日志级别
    log_level = getattr(logging, Config.LOG_LEVEL.upper())
    
    # 创建格式化器
    formatter = logging.Formatter(Config.LOG_FORMAT)
    
    # 创建文件处理器
    file_handler = RotatingFileHandler(
        Config.LOG_FILE,
        maxBytes=Config.LOG_MAX_BYTES,
        backupCount=Config.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    
    # 配置全局logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.propagate = False
    
    # 配置Flask应用日志
    app.logger.setLevel(log_level)
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    
    # 配置其他日志
    for log_name in ['sqlalchemy.engine', 'werkzeug']:
        log = logging.getLogger(log_name)
        log.setLevel(log_level)
        log.addHandler(file_handler)
        log.addHandler(console_handler)
        log.propagate = False
    
    # 设置SQLAlchemy日志级别为WARNING或更高
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    
    return logger

# 设置基本配置，在setup_logger调用前也能使用
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)