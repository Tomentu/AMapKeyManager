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
import pytz

# 获取东八区时区
tz = pytz.timezone('Asia/Shanghai')

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
            result_file=f"{task_id}_poi.csv"
        )
        db.session.add(task)
        db.session.commit()
        
        # 提交到任务执行器
        TaskExecutor().submit_task(task_id, PolygonCrawler.execute_task)
        
        return task

    @staticmethod
    def execute_task(task_id: str,stop_event=None) -> bool:
        """执行任务（供任务执行器调用）"""
        task = PolygonTask.query.filter_by(task_id=task_id).first()
        if not task:
            return False
            
        try:
            task.status = 'running'
            task.updated_at = datetime.now(tz)
            db.session.commit()
            
            # 获取所有POI类型
            poi_types = PolygonCrawler.get_poi_types()
            
            # 如果没有当前类型，从第一个开始
            if not task.current_type or task.current_type not in poi_types:
                task.current_type = next(iter(poi_types))
                task.current_page = 1
                db.session.commit()
            
            # 从当前类型开始遍历
            current_found = False
            for poi_type, type_codes in poi_types.items():
                # 跳过直到找到当前类型
                if not current_found and poi_type != task.current_type:
                    continue
                current_found = True
                
                task.current_type = poi_type
                # 使用当前页码继续执行，不重置为1
                if poi_type not in task.progress:
                    task.current_page = 1
                # 否则保持当前页码
                db.session.commit()
                
                if stop_event and stop_event.is_set():
                    task.status = 'pending'
                    db.session.commit()
                    return False
                # 获取当前页数据
                polygon = task.polygon.strip().replace('\n', '').replace('\r', '').replace(' ', '')
                result, status_code = PolygonCrawler._fetch_page(
                    polygon= polygon,
                    types=type_codes,
                    page=task.current_page,
                    offset=25
                )

            
                
                # 检查是否返回503或info_code为1008611
                if status_code == 503 and (result and result.get('info_code') == '1008611'):
                    logger.warning(f"Task {task.task_id} received info_code 1008611, setting to pending")
                    task.status = 'pending'
                    db.session.commit()
                    return False
                if status_code != 200:
                    raise Exception(f"Proxy request failed with status {status_code}")
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
                    'processed_count': len(result['pois']),
                    'completed': False  # 添加完成标识
                }
                task.progress = progress  # 使用setter方法
                task.updated_at = datetime.now(tz)
                db.session.commit()
                time.sleep(2)
                # 获取剩余页面
                for page in range(2, total_pages + 1):
                    task.current_page = page
                    result, status_code = PolygonCrawler._fetch_page(
                        polygon=polygon,
                        types=type_codes,
                        page=page,
                        offset=25
                    )
                    
                    # 检查是否返回503或info_code为1008611
                    if status_code == 503 and (result and result.get('info_code') == '1008611'):
                        logger.warning(f"Task {task.task_id} received info_code 1008611, setting to pending")
                        task.status = 'pending'
                        db.session.commit()
                        return False
                    if status_code != 200:
                        raise Exception(f"Proxy request failed with status {status_code}")
                    if not result or not result.get('pois'):
                        progress = task.progress
                        progress[task.current_type]['completed'] = True  # 标记为已完成
                        task.progress = progress
                        task.updated_at = datetime.now(tz)
                        time.sleep(1)
                        logger.info(f"Task {task.task_id} {task.current_type} completed")
                        break
                    PolygonCrawler._save_to_csv(task.result_file, result['pois'], task.current_type)
                    
                    # 更新进度数据
                    progress = task.progress
                    progress[task.current_type]['processed_pages'] += 1
                    progress[task.current_type]['processed_count'] += len(result['pois'])
                    task.progress = progress
                    task.updated_at = datetime.now(tz)
                    #print(f"Task {task.task_id} updated at {task.updated_at}")
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
                    return response[0].json, response[1]
                    
                return response.json, response.status_code
                    
            except Exception as e:
                retry_count += 1
                if 'No available API key' in str(e) or retry_count >= max_retries:
                    logger.error(f"Request failed after {retry_count} retries: {str(e)}")
                    raise
                
                logger.warning(f"Request failed (attempt {retry_count}/{max_retries}): {str(e)}")
                time.sleep(10)  # 固定5秒重试间隔
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
        # 先找出所有running状态但已停滞的任务
        running_tasks = PolygonTask.query.filter_by(status='running').all()
        stalled_task_ids = [task.task_id for task in running_tasks if task.is_stalled()]
        
        # 获取待恢复的任务（包括pending和stalled状态，按优先级排序）
        pending_tasks = PolygonTask.query.filter(
            db.or_(
                PolygonTask.status == 'pending',
                PolygonTask.task_id.in_(stalled_task_ids)
            )
        ).order_by(PolygonTask.priority).limit(limit).all()
            
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