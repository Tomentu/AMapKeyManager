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
from app.api.proxy import proxy_request  # 导入proxy模块的函数
from flask import request, Request
from werkzeug.test import EnvironBuilder

class PolygonCrawler:
    """多边形POI爬取服务"""
    
    @staticmethod
    def get_poi_types():
        """获取POI类型配置"""
        return current_app.config['POI_TYPES']
    
    @staticmethod
    def create_task(task_id: str, name: str, polygon: str, priority: int = 0) -> PolygonTask:
        """创建新任务"""
        task = PolygonTask(
            task_id=task_id,
            name=name,
            polygon=polygon,
            priority=priority,
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
        if not task:
            return False
            
        try:
            task.status = 'running'
            db.session.commit()
            
            # 遍历所有POI类型
            for poi_type, type_codes in PolygonCrawler.get_poi_types().items():
                task.current_type = poi_type
                task.current_page = 1
                db.session.commit()
                
                # 先获取第一页和总数
                result = PolygonCrawler._fetch_page(
                    polygon=task.polygon,
                    types=type_codes,
                    page=1,
                    offset=25
                )
                
                # 检查是否返回503或info_code为1008611
                if result and result.get('info_code') == '1008611':
                    logger.warning(f"Task {task.task_id} received info_code 1008611, setting to pending")
                    task.status = 'pending'
                    db.session.commit()
                    return False
                
                if not result or not result.get('pois'):
                    continue
                    
                # 保存第一页数据
                PolygonCrawler._save_to_csv(task.result_file, result['pois'], task.current_type)
                
                # 计算总页数并初始化进度数据
                total_count = int(result.get('count', 0))
                total_pages = (total_count + 24) // 25  # 修改为25条
                
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
                        page=page,
                        offset=25
                    )
                    
                    # 检查是否返回503或info_code为1008611
                    if result and result.get('info_code') == '1008611':
                        logger.warning(f"Task {task.task_id} received info_code 1008611, setting to pending")
                        task.status = 'pending'
                        db.session.commit()
                        return False
                    
                    if not result or not result.get('pois'):
                        break
                        
                    PolygonCrawler._save_to_csv(task.result_file, result['pois'], task.current_type)
                    
                    # 更新进度数据
                    progress = task.progress
                    progress[task.current_type]['processed_pages'] += 1
                    progress[task.current_type]['processed_count'] += len(result['pois'])
                    task.progress = progress
                    db.session.commit()
                    time.sleep(2)
            
            task.status = 'completed'
            db.session.commit()
            return True
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 503:
                logger.warning(f"Task {task.task_id} received 503 error, setting to pending")
                task.status = 'pending'
                db.session.commit()
                return False
            raise
        except Exception as e:
            logger.error(f"Task execution failed: {str(e)}")
            task.status = 'failed'
            db.session.commit()
            raise

    @staticmethod
    def _fetch_page(polygon: str, types: str, page: int, offset: int = 25, max_retries: int = 3) -> List[Dict]:
        """获取单页数据"""
        retry_count = 0
        while retry_count < max_retries:
            try:
                # 构造请求参数
                params = {
                    'polygon': polygon,
                    'types': types,
                    'offset': offset,
                    'page': page,
                    'extensions': 'all'
                }
                
                # 构造请求环境
                builder = EnvironBuilder(
                    path=f'/amap/v3/place/polygon',
                    method='GET',
                    query_string=params
                )
                env = builder.get_environ()
                request_ctx = current_app.request_context(env)
                
                with request_ctx:
                    # 调用proxy_request
                    response = proxy_request('v3/place/polygon')
                
                if isinstance(response, tuple):
                    status_code = response[1]
                    data = response[0].json
                    
                    # 检查503错误和info_code
                    if status_code == 503:
                        if data.get('info_code') == '1008611':
                            logger.warning(f"Received info_code 1008611")
                            raise Exception("No available API key")
                        raise Exception(f"Proxy request failed with status {status_code}")
                    
                    return data
                    
                return response.json
                    
            except Exception as e:
                retry_count += 1
                if 'No available API key' in str(e) or retry_count >= max_retries:
                    logger.error(f"Request failed after {retry_count} retries: {str(e)}")
                    raise
                
                logger.warning(f"Request failed (attempt {retry_count}/{max_retries}): {str(e)}")
                time.sleep(5)  # 固定5秒重试间隔
                continue

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
                    'location', 'tel', 'business_area', 'poi_type',
                    'province', 'city', 'district'
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
                    poi_type,
                    poi.get('pname', ''),
                    poi.get('cityname', ''),
                    poi.get('adname', '')
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

    @staticmethod
    def resume_tasks(limit: int = 5) -> List[str]:
        """批量恢复任务
        Args:
            limit: 最大恢复任务数量
        Returns:
            已恢复的任务ID列表
        """
        # 获取待恢复的任务（按优先级排序）
        pending_tasks = PolygonTask.query.filter_by(status='pending')\
            .order_by(PolygonTask.priority)\
            .limit(limit)\
            .all()
            
        resumed_tasks = []
        for task in pending_tasks:
            try:
                if TaskExecutor().is_task_running(task.task_id):
                    continue
                    
                if TaskExecutor().submit_task(task.task_id, PolygonCrawler.execute_task):
                    resumed_tasks.append(task.task_id)
                    
            except Exception as e:
                logger.error(f"Failed to resume task {task.task_id}: {str(e)}")
                continue
                
        return resumed_tasks