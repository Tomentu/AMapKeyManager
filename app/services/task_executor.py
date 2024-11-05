from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Callable
import threading
from queue import Queue, Empty
from app.core.logger import logger
from flask import current_app

class TaskExecutor:
    """任务执行器"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.max_workers = 3  # 最大线程数
            self.task_queue = Queue()  # 任务队列
            self.running_tasks: Dict[str, bool] = {}  # 记录运行中的任务
            self.stop_flag = False  # 停止标志
            self.workers = []  # 工作线程列表
            self.stop_tasks_flag = False  # 停止所有任务的标志
            
            # 启动工作线程
            for _ in range(self.max_workers):
                worker = threading.Thread(target=self._worker_loop)
                worker.daemon = True
                worker.start()
                self.workers.append(worker)
                
            self.initialized = True
    
    def submit_task(self, task_id: str, task_func: Callable) -> bool:
        """提交任务到队列"""
        with self._lock:
            if task_id in self.running_tasks:
                logger.warning(f"Task {task_id} is already running")
                return False
            
            # 将任务添加到队列
            app = current_app._get_current_object()
            self.task_queue.put((task_id, task_func, app))
            logger.info(f"Task {task_id} added to queue")
            return True
    
    def _worker_loop(self):
        """工作线程循环"""
        while not self.stop_flag:
            try:
                # 从队列获取任务，设置超时以便检查停止标志
                task_id, task_func, app = self.task_queue.get(timeout=1)
                
                # 检查任务是否已在运行
                with self._lock:
                    if task_id in self.running_tasks:
                        logger.warning(f"Task {task_id} is already running")
                        self.task_queue.task_done()
                        continue
                    self.running_tasks[task_id] = True
                
                try:
                    logger.info(f"Starting task {task_id}")
                    with app.app_context():
                        # 检查是否需要停止所有任务
                        if self.stop_tasks_flag:
                            logger.info(f"Task {task_id} stopped by stop_all_tasks")
                            continue
                        task_func(task_id)
                    logger.info(f"Task {task_id} completed")
                except Exception as e:
                    logger.error(f"Task {task_id} failed: {str(e)}")
                finally:
                    with self._lock:
                        self.running_tasks.pop(task_id, None)
                    self.task_queue.task_done()
                    
            except Empty:
                continue  # 队列为空，继续等待
            except Exception as e:
                logger.error(f"Worker error: {str(e)}")
    
    def get_running_tasks(self) -> list:
        """获取运行中的任务列表"""
        with self._lock:
            return list(self.running_tasks.keys())
    
    def is_task_running(self, task_id: str) -> bool:
        """检查任务是否在运行"""
        with self._lock:
            return task_id in self.running_tasks
            
    def get_queue_size(self) -> int:
        """获取队列中等待的任务数"""
        return self.task_queue.qsize()
    
    def shutdown(self):
        """关闭任务执行器"""
        self.stop_flag = True
        # 等待所有工作线程结束
        for worker in self.workers:
            worker.join()
        # 清空队列
        self.task_queue.queue.clear()
    
    def stop_all_tasks(self):
        """停止所有任务"""
        with self._lock:
            self.stop_tasks_flag = True
            # 清空任务队列
            self.task_queue.queue.clear()
            # 记录当前运行的任务
            running = list(self.running_tasks.keys())
        return running