from typing import Dict, List
import csv
import os
import requests
from datetime import datetime
from app.models.polygon_task import PolygonTask
from app.core.database import db
from app.core.logger import logger
from flask import current_app
from app.services.task_executor import TaskExecutor
import time

class PolygonCrawler:
    """多边形POI爬取服务"""
    
    POI_TYPES = {
        '交通设施服务': '150104|150200|150400|150500',
        '风景名胜': '110000|110200'
        #'住宿服务': '100000|100100|100101|100102|100103|100104|100105|100200|100201',
        # ... 其他类型 ...
    }

    
    @staticmethod
    def create_task(task_id: str, name: str, polygon: str) -> PolygonTask:
        """创建新任务"""
        task = PolygonTask(
            task_id=task_id,
            name=name,
            polygon=polygon,
            result_file=f"poi_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        db.session.add(task)
        db.session.commit()
        
        # 提交到任务执行器
        TaskExecutor().submit_task(task_id, PolygonCrawler.execute_task)
        
        return task

    @staticmethod
    def execute_task(task_id: str) -> bool:
        """执行任务（供任务执行器调用）"""
        task = PolygonTask.query.filter_by(task_id=task_id).first()
        if not task or task.status == 'running':
            return False
            
        try:
            task.status = 'running'
            db.session.commit()
            
            # 遍历所有POI类型
            for poi_type, type_codes in PolygonCrawler.POI_TYPES.items():
                task.current_type = poi_type
                task.current_page = 1
                db.session.commit()
                
                # 先获取第一页和总数
                result = PolygonCrawler._fetch_page(
                    polygon=task.polygon,
                    types=type_codes,
                    page=1
                )
                
                if not result or not result.get('pois'):
                    continue
                    
                # 保存第一页数据
                PolygonCrawler._save_to_csv(task.result_file, result['pois'], task.current_type)
                
                # 计算总页数并初始化进度数据
                total_count = int(result.get('count', 0))
                total_pages = (total_count + 19) // 20  # 向上取整，每页20条
                
                # 初始化或更新当前类型的进度数据
                progress = task.progress
                progress[task.current_type] = {
                    'total_pages': total_pages,
                    'processed_pages': 1,  # 第一页已处理
                    'total_count': total_count,
                    'processed_count': len(result['pois'])
                }
                task.progress = progress  # 使用setter方法
                db.session.commit()
                
                # 获取剩余页面
                for page in range(2, total_pages + 1):
                    task.current_page = page
                    
                    result = PolygonCrawler._fetch_page(
                        polygon=task.polygon,
                        types=type_codes,
                        page=page
                    )
                    
                    if not result or not result.get('pois'):
                        break
                        
                    PolygonCrawler._save_to_csv(task.result_file, result['pois'], task.current_type)
                    
                    # 更新进度数据
                    progress = task.progress
                    progress[task.current_type]['processed_pages'] += 1
                    progress[task.current_type]['processed_count'] += len(result['pois'])
                    task.progress = progress
                    db.session.commit()
                    time.sleep(3)
            
            task.status = 'completed'
            db.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Task execution failed: {str(e)}")
            task.status = 'failed'
            db.session.commit()
            raise

    @staticmethod
    def _fetch_page(polygon: str, types: str, page: int, offset: int = 20) -> List[Dict]:
        """获取单页数据"""
        try:
            params = {
                'polygon': polygon,
                'types': types,
                'offset': offset,
                'page': page,
                'extensions': 'all'
            }
            #print(f"{current_app.config['CUSTOM_PROXY_URL']}/v3/place/polygon")
            # 使用自定义代理接口
            response = requests.get(
                f"{current_app.config['CUSTOM_PROXY_URL']}/v3/place/polygon",
                params=params,

                verify=False
            )
            #print(response.content)
            data = response.json()
            
            return data
                
        except requests.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            raise Exception(f"Request failed: {str(e)}")

    @staticmethod
    def _save_to_csv(filename: str, pois: List[Dict], poi_type: str):
        """保存POI数据到CSV"""
        # 获取当前脚本所在目录的上级目录
        current_dir = os.path.dirname(os.path.abspath(__file__))  # app/services
        results_dir = os.path.join(os.path.dirname(current_dir), 'results')  # app/results
        os.makedirs(results_dir, exist_ok=True)
        
        # 构建文件完整路径
        filepath = os.path.join(results_dir, filename)
        
        file_exists = os.path.exists(filepath)
        
        with open(filepath, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            
            if not file_exists:
                writer.writerow([
                    'id', 'name', 'type', 'type_code', 'address', 
                    'location', 'tel', 'business_area', 'poi_type'
                ])
            
            for poi in pois:
                writer.writerow([
                    poi.get('id', ''),
                    poi.get('name', ''),
                    poi.get('type', ''),
                    poi.get('typecode', ''),
                    poi.get('address', ''),
                    poi.get('location', ''),
                    poi.get('tel', ''),
                    poi.get('business_area', ''),
                    poi_type
                ])

    @staticmethod
    def resume_task(task_id: str) -> bool:
        """恢复任务"""
        task = PolygonTask.query.filter_by(task_id=task_id).first()
        if not task:
            raise ValueError(f"Task not found: {task_id}")
            
        if TaskExecutor().is_task_running(task_id):
            raise ValueError(f"Task is already running: {task_id}")
            
        if task.status == 'completed':
            raise ValueError(f"Task is already completed: {task_id}")
            
        # 提交到任务执行器
        return TaskExecutor().submit_task(task_id, PolygonCrawler.execute_task)