from datetime import datetime, timedelta
from app.core.database import db
import json
import pytz

# 获取东八区时区
tz = pytz.timezone('Asia/Shanghai')

def get_current_time():
    """获取当前东八区时间"""
    return datetime.utcnow() + timedelta(hours=8)

class PolygonTask(db.Model):
    """多边形POI任务"""
    __tablename__ = 'polygon_tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(50), unique=True)     # 自定义任务ID
    name = db.Column(db.String(100))                    # 任务名称
    polygon = db.Column(db.Text)                        # 多边形坐标
    priority = db.Column(db.Integer, default=0)         # 任务优先级(0-9)，数字越小优先级越高
    
    # 任务状态
    status = db.Column(db.String(20), default='pending')  # pending, running, completed, failed
    current_type = db.Column(db.String(50))              # 当前正在爬取的POI类型
    current_page = db.Column(db.Integer, default=1)      # 当前页码
    
    # 进度记录 (使用Text存储JSON)
    progress_data = db.Column(db.Text, default='{}')     # 各类型的进度数据
    
    # 结果文件
    result_file = db.Column(db.String(200))             # CSV文件路径
    
    # 时间记录
    created_at = db.Column(db.DateTime, default=get_current_time)
    updated_at = db.Column(db.DateTime, default=get_current_time)

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

    def is_stalled(self, timeout_minutes=5):
        """检查任务是否已停滞"""
        if self.status != 'running':
            return False
            
        if not self.updated_at:
            return True
            
        # 直接获取东八区当前时间
        tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(tz).replace(tzinfo=None)  # 转换为naive datetime
        
        # 计算时间差（数据库中已经是东八区时间）
        stall_time = now - self.updated_at
        timeout = timedelta(minutes=timeout_minutes)
        
        return stall_time > timeout