from datetime import datetime
from app.core.database import db
import json

class PolygonTask(db.Model):
    """多边形POI任务"""
    __tablename__ = 'polygon_tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(50), unique=True)     # 自定义任务ID
    name = db.Column(db.String(100))                    # 任务名称
    polygon = db.Column(db.Text)                        # 多边形坐标
    
    # 任务状态
    status = db.Column(db.String(20), default='pending')  # pending, running, completed, failed
    current_type = db.Column(db.String(50))              # 当前正在爬取的POI类型
    current_page = db.Column(db.Integer, default=1)      # 当前页码
    
    # 进度记录 (使用Text存储JSON)
    progress_data = db.Column(db.Text, default='{}')     # 各类型的进度数据
    
    # 结果文件
    result_file = db.Column(db.String(200))             # CSV文件路径
    
    # 时间记录
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def progress(self):
        """获取进度数据"""
        try:
            return json.loads(self.progress_data)
        except:
            return {}
            
    @progress.setter
    def progress(self, value):
        """设置进度数据"""
        self.progress_data = json.dumps(value, ensure_ascii=False)

    @property
    def total_progress(self):
        """计算总体进度百分比"""
        progress = self.progress
        total_pages = sum(type_data['total_pages'] for type_data in progress.values())
        processed_pages = sum(type_data['processed_pages'] for type_data in progress.values())
        if total_pages == 0:
            return 0
        return round(processed_pages / total_pages * 100, 2)