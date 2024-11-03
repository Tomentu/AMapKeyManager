from datetime import datetime
from sqlalchemy.ext.hybrid import hybrid_property
from app import db

class APIKey(db.Model):
    """API密钥模型"""
    __tablename__ = 'api_keys'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    description = db.Column(db.String(200))
    last_reset = db.Column(db.DateTime)
    
    # 搜索服务的使用次数
    keyword_search_used = db.Column(db.Integer, default=0)
    around_search_used = db.Column(db.Integer, default=0)
    polygon_search_used = db.Column(db.Integer, default=0)
    
    # 搜索服务的每日限额
    SEARCH_LIMITS = {
        'keyword': 100,    # 关键字搜索限额
        'around': 100,     # 周边搜索限额
        'polygon': 100     # 多边形搜索限额
    }
    
    # 每个服务的QPS限制
    QPS_LIMITS = {
        'keyword': 3,      # 关键字搜索QPS
        'around': 3,       # 周边搜索QPS
        'polygon': 3       # 多边形搜索QPS
    }

    @hybrid_property
    def masked_key(self):
        """返回遮罩后的key"""
        if not self.key:
            return None
        return f"{self.key[:6]}{'*' * 8}{self.key[-4:]}"

    @classmethod
    def init_table(cls):
        """初始化数据表"""
        if not db.engine.dialect.has_table(db.engine, cls.__tablename__):
            cls.__table__.create(db.engine)
            db.session.commit()
            print(f"Created table: {cls.__tablename__}")
    
    def increment_usage(self, search_type: str) -> bool:
        """增加指定搜索服务的使用次数
        
        Args:
            search_type: 搜索类型 (keyword/around/polygon)
            
        Returns:
            bool: 是否成功增加
        """
        try:
            if search_type == 'keyword':
                self.keyword_search_used += 1
            elif search_type == 'around':
                self.around_search_used += 1
            elif search_type == 'polygon':
                self.polygon_search_used += 1
            else:
                return False
                
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            return False

