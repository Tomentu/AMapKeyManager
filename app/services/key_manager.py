from datetime import datetime, timedelta
from typing import Optional
from app.models.api_key import APIKey
from app.core.database import db
from app.core.logger import logger
import pytz
from app.core.config import Config

class KeyManager:
    """密钥管理服务"""
    
    @staticmethod
    def get_available_key(search_type: str) -> Optional[APIKey]:
        """获取一个可用的API key
        
        Args:
            search_type: 搜索类型 (keyword/around/polygon)
            
        Returns:
            Optional[APIKey]: 可用的key或None
        """
        try:
            tz = pytz.timezone(Config.TIMEZONE)
            now = datetime.now(tz)
            today_reset_time = now.replace(
                hour=Config.KEY_RESET_HOUR, 
                minute=0, 
                second=0, 
                microsecond=0
            )
            
            # 如果当前时间在今天的重置时间之后，使用今天的重置时间
            # 如果当前时间在今天的重置时间之前，使用昨天的重置时间
            if now < today_reset_time:
                reset_time = today_reset_time - timedelta(days=1)
            else:
                reset_time = today_reset_time

            # 获取所有活跃的key
            active_keys = APIKey.query.filter(
                APIKey.is_active == True
            ).all()

            # 检查并重置需要重置的key
            for key in active_keys:
                if not key.last_reset or key.last_reset.astimezone(tz) < reset_time:
                    key.keyword_search_used = 0
                    key.around_search_used = 0
                    key.polygon_search_used = 0
                    key.last_reset = now
                    logger.info(f"Key {key.key} 使用计数已重置 at {now}")

            # 如果有多个key需要重置，一次性提交
            if active_keys:
                db.session.commit()

            # 根据搜索类型查询未达到限额的key
            if search_type == 'keyword':
                key = APIKey.query.filter(
                    APIKey.is_active == True,
                    APIKey.keyword_search_used < APIKey.SEARCH_LIMITS['keyword']
                ).order_by(
                    APIKey.keyword_search_used.asc()  # 优先使用keyword_search_used少的key
                ).first()
            elif search_type == 'around':
                key = APIKey.query.filter(
                    APIKey.is_active == True,
                    APIKey.around_search_used < APIKey.SEARCH_LIMITS['around']
                ).order_by(
                    APIKey.around_search_used.asc()  # 优先使用around_search_used少的key
                ).first()
            elif search_type == 'polygon':
                key = APIKey.query.filter(
                    APIKey.is_active == True,
                    APIKey.polygon_search_used < APIKey.SEARCH_LIMITS['polygon']
                ).order_by(
                    APIKey.polygon_search_used.asc()  # 优先使用polygon_search_used少的key
                ).first()
            else:
                raise ValueError(f"无效的搜索类型: {search_type}")

            return key
            
        except Exception as e:
            logger.error(f"获取可用key失败: {str(e)}")
            return None

    @staticmethod
    def add_key(key: str, daily_limit: int = 30000, description: str = None) -> APIKey:
        """添加新的API key"""
        try:
            new_key = APIKey(
                key=key,
                daily_limit=daily_limit,
                description=description,
                is_active=True,
                used_count=0,
                last_reset=datetime.now()
            )
            db.session.add(new_key)
            db.session.commit()
            logger.info(f"新key已添加: {key}")
            return new_key
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"添加key失败: {str(e)}")
            raise 

    @staticmethod
    def mark_daily_limit(key_id: int, search_type: str) -> bool:
        """标记key某个搜索服务达到当日限制
        
        Args:
            key_id: API key的ID
            search_type: 搜索类型 (keyword/around/polygon)
            
        Returns:
            bool: 是否成功标记
        """
        try:
            key = APIKey.query.get(key_id)
            if not key:
                logger.error(f"Key not found: {key_id}")
                return False
                
            # 根据搜索类型更新对应的使用次数到限制值
            if search_type == 'keyword':
                key.keyword_search_used = key.SEARCH_LIMITS['keyword']
            elif search_type == 'around':
                key.around_search_used = key.SEARCH_LIMITS['around']
            elif search_type == 'polygon':
                key.polygon_search_used = key.SEARCH_LIMITS['polygon']
            else:
                logger.error(f"Invalid search type: {search_type}")
                return False
                
            db.session.commit()
            logger.warning(f"Key {key.key} 的 {search_type} 搜索已达到当日使用限制")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"更新key状态失败: {str(e)}")
            return False

    @staticmethod
    def disable_key(key: APIKey, reason: str = None) -> bool:
        """永久禁用key"""
        try:
            key.is_active = False
            key.description = f"{key.description or ''} | 禁用原因: {reason}"
            db.session.commit()
            logger.warning(f"Key {key.key} 已永久禁用, 原因: {reason}")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"禁用key失败: {str(e)}")
            return False

    @classmethod
    def increment_usage(cls, key_id: int, search_type: str) -> None:
        """增加密钥使用次数
        
        Args:
            key_id: 密钥ID
            search_type: 搜索类型 (keyword/around/polygon)
        """
        try:
            key = APIKey.query.get(key_id)
            if key:
                key.increment_usage(search_type)
                logger.debug(f"Key {key.key} {search_type} search usage increased")
        except Exception as e:
            logger.error(f"Failed to increment key usage: {str(e)}")
            db.session.rollback()



# 密钥管理服务 