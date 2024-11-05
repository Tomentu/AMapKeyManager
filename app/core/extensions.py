from flask_sqlalchemy import SQLAlchemy
from app.services.task_executor import TaskExecutor


task_executor = TaskExecutor()

def init_extensions(app):
    """初始化扩展"""
    # 其他扩展的初始化...
    
    # 最后初始化任务执行器
    with app.app_context():
        global task_executor
        task_executor = TaskExecutor()