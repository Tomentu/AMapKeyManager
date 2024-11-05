from flask_sqlalchemy import SQLAlchemy
from app.services.task_executor import TaskExecutor

# 创建扩展实例

# 直接创建 TaskExecutor 实例
task_executor = TaskExecutor()

def init_extensions(app):
    """初始化扩展"""
    # 不需要重新创建 TaskExecutor 实例
    pass