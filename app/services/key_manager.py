from datetime import datetime, timedelta
from typing import Optional, Dict
from app.models.api_key import APIKey
from app.core.database import db
from app.core.logger import logger
import pytz
from app.core.config import Config

class KeyManager:
    """密钥管理服务"""
    
    @staticmethod
    def get_available_key(search_type: str) -> Optional[APIKey]:
        """获取一个可用的API key"""
        try:
            tz = pytz.timezone(Config.TIMEZONE)
            now = datetime.now(tz)
            today_reset_time = now.replace(
                hour=Config.KEY_RESET_HOUR, 
                minute=0, 
                second=0, 
                microsecond=0
            )
            
            # 确定重置时间
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
                    logger.info(f"Key {key.masked_key} 使用计数已重置")

            if active_keys:
                db.session.commit()

            # 根据搜索类型和限额查询可用的key
            if search_type == 'keyword':
                keys = APIKey.query.filter(
                    APIKey.is_active == True,
                    APIKey.keyword_search_used < APIKey.keyword_search_limit
                ).all()
            elif search_type == 'around':
                keys = APIKey.query.filter(
                    APIKey.is_active == True,
                    APIKey.around_search_used < APIKey.around_search_limit
                ).all()
            elif search_type == 'polygon':
                keys = APIKey.query.filter(
                    APIKey.is_active == True,
                    APIKey.polygon_search_used < APIKey.polygon_search_limit
                ).all()
            else:
                raise ValueError(f"无效的搜索类型: {search_type}")

            # 从可用的keys中随机选择一个
            import random
            key = random.choice(keys) if keys else None

            return key
            
        except Exception as e:
            logger.error(f"获取可用key失败: {str(e)}")
            return None

    @staticmethod
    def add_key(key: str, limits: Dict = None, description: str = None) -> APIKey:
        """添加新的API key
        
        Args:
            key: API密钥
            limits: 可选的限额设置
            description: 可选的描述
        """
        try:
            new_key = APIKey.create_key(key, limits)
            if new_key and description:
                new_key.description = description
                db.session.commit()
            logger.info(f"新key已添加: {new_key.masked_key}")
            return new_key
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"添加key失败: {str(e)}")
            raise

    @staticmethod
    def update_limits(key_id: int, limits: Dict) -> bool:
        """更新key的限额设置"""
        try:
            key = APIKey.query.get(key_id)
            if not key:
                logger.error(f"Key not found: {key_id}")
                return False
                
            success = key.update_limits(limits)
            if success:
                logger.info(f"Key {key.masked_key} 的限额已更新")
            return success
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"更新key限额失败: {str(e)}")
            return False

    @staticmethod
    def get_usage_status(key_id: int) -> Dict:
        """获取key的使用状态"""
        try:
            key = APIKey.query.get(key_id)
            if not key:
                return {}
            return key.get_usage_status()
        except Exception as e:
            logger.error(f"获取key使用状态失败: {str(e)}")
            return {}

    @staticmethod
    def disable_key(key: APIKey, reason: str = None) -> bool:
        """永久禁用key"""
        try:
            key.is_active = False
            key.description = f"{key.description or ''} | 禁用原因: {reason}"
            db.session.commit()
            logger.warning(f"Key {key.masked_key} 已永久禁用, 原因: {reason}")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"禁用key失败: {str(e)}")
            return False

    @classmethod
    def increment_usage(cls, key_id: int, search_type: str) -> bool:
        """增加密钥使用次数"""
        try:
            key = APIKey.query.get(key_id)
            if key:
                success = key.increment_usage(search_type)
                if success:
                    logger.debug(f"Key {key.masked_key} {search_type} 搜索使用次数已增加")
                return success
            return False
        except Exception as e:
            logger.error(f"增加key使用次数失败: {str(e)}")
            return False

    @classmethod
    def mark_daily_limit(cls, key_id: int, search_type: str) -> None:
        """标记某个key的某项服务达到每日限额"""
        try:
            key = APIKey.query.get(key_id)
            if not key:
                logger.warning(f"Key {key_id} not found when marking daily limit")
                return

            # 直接将使用次数设置为限额值
            if search_type == 'keyword':
                key.keyword_search_used = key.SEARCH_LIMITS['keyword']
            elif search_type == 'around':
                key.around_search_used = key.SEARCH_LIMITS['around']
            elif search_type == 'polygon':
                key.polygon_search_used = key.SEARCH_LIMITS['polygon']
            
            db.session.commit()
            logger.info(f"Key {key.masked_key} 已标记为{search_type}搜索达到每日限额")
            
        except Exception as e:
            logger.error(f"标记key每日限额失败: {str(e)}")
            db.session.rollback()



# 密钥管理服务 