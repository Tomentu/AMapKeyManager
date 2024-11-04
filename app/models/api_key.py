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
    
    # 自定义限额（如果为None则使用默认限额）
    keyword_search_limit = db.Column(db.Integer, nullable=True)
    around_search_limit = db.Column(db.Integer, nullable=True)
    polygon_search_limit = db.Column(db.Integer, nullable=True)
    
    keyword_qps_limit = db.Column(db.Integer, nullable=True)
    around_qps_limit = db.Column(db.Integer, nullable=True)
    polygon_qps_limit = db.Column(db.Integer, nullable=True)
    
    # 默认搜索限额
    DEFAULT_SEARCH_LIMITS = {
        'keyword': 100,    # 关键字搜索限额
        'around': 100,     # 周边搜索限额
        'polygon': 100     # 多边形搜索限额
    }
    
    # 默认QPS限制
    DEFAULT_QPS_LIMITS = {
        'keyword': 3,      # 关键字搜索QPS
        'around': 3,       # 周边搜索QPS
        'polygon': 3       # 多边形搜索QPS
    }

    @property
    def SEARCH_LIMITS(self):
        """获取搜索限额（优先使用自定义限额）"""
        return {
            'keyword': self.keyword_search_limit or self.DEFAULT_SEARCH_LIMITS['keyword'],
            'around': self.around_search_limit or self.DEFAULT_SEARCH_LIMITS['around'],
            'polygon': self.polygon_search_limit or self.DEFAULT_SEARCH_LIMITS['polygon']
        }
    
    @property
    def QPS_LIMITS(self):
        """获取QPS限制（优先使用自定义限制）"""
        return {
            'keyword': self.keyword_qps_limit or self.DEFAULT_QPS_LIMITS['keyword'],
            'around': self.around_qps_limit or self.DEFAULT_QPS_LIMITS['around'],
            'polygon': self.polygon_qps_limit or self.DEFAULT_QPS_LIMITS['polygon']
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
        """增加指定搜索服务的使用次数"""
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

    def update_limits(self, limits: dict):
        """更新自定义限额"""
        try:
            for key, value in limits.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            return False

    def get_usage_status(self):
        """获取使用状态"""
        limits = self.SEARCH_LIMITS
        return {
            'keyword': {
                'used': self.keyword_search_used,
                'limit': limits['keyword'],
                'remaining': limits['keyword'] - self.keyword_search_used
            },
            'around': {
                'used': self.around_search_used,
                'limit': limits['around'],
                'remaining': limits['around'] - self.around_search_used
            },
            'polygon': {
                'used': self.polygon_search_used,
                'limit': limits['polygon'],
                'remaining': limits['polygon'] - self.polygon_search_used
            }
        }

    @classmethod
    def create_key(cls, key: str, limits: dict = None):
        """创建新的API密钥"""
        try:
            api_key = cls(key=key)
            if limits:
                api_key.update_limits(limits)
            db.session.add(api_key)
            db.session.commit()
            return api_key
        except Exception as e:
            db.session.rollback()
            return None

