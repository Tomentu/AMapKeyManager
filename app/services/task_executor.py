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
                    logger.info("Creating new TaskExecutor instance")
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            logger.info("Initializing TaskExecutor")
            self.max_workers = 3  # 确保只有一个工作线程
            self.task_queue = Queue()
            self.running_tasks: Dict[str, threading.Event] = {}
            self.stop_flag = False
            self.workers = []
            self.stop_tasks_flag = False
            self.semaphore = threading.Semaphore(3)
            
            # 启动工作线程
            for _ in range(self.max_workers):
                worker = threading.Thread(target=self._worker_loop, name=f"TaskExecutor-Worker-{_}")
                worker.daemon = True
                worker.start()
                self.workers.append(worker)
                logger.info(f"Started worker thread: {worker.name}")
            
            self.initialized = True
    
    def submit_task(self, task_id: str, task_func: Callable) -> bool:
        """提交任务到队列"""
        with self._lock:
            if task_id in self.running_tasks:
                logger.warning(f"Task {task_id} is already running")
                return False
            
            # 创建任务的停止事件
            stop_event = threading.Event()
            self.running_tasks[task_id] = stop_event
            
            # 将任务添加到队列
            app = current_app._get_current_object()
            
            self.task_queue.put((task_id, task_func, app, stop_event))
            logger.info(f"Task {task_id} added to queue")
            return True
    
    def _worker_loop(self):
        """工作线程循环"""
        while not self.stop_flag:
            try:
                # 从队列获取任务
                task_id, task_func, app, stop_event = self.task_queue.get(timeout=1)
                
                # 使用信号量限制同时执行的任务数
                with self.semaphore:
                    try:
                        logger.info(f"Starting task {task_id}")
                        with app.app_context():
                            if self.stop_tasks_flag or stop_event.is_set():
                                logger.info(f"Task {task_id} stopped")
                                continue
                            # 传入stop_event给任务函数
                            task_func(task_id, stop_event)
                    except Exception as e:
                        logger.error(f"Task {task_id} failed: {str(e)}")
                    finally:
                        with self._lock:
                            self.running_tasks.pop(task_id, None)
                        self.task_queue.task_done()
                    
            except Empty:
                continue
    
    def get_running_tasks(self) -> list:
        """获取运行中的任务列表"""
        with self._lock:
            return list(self.running_tasks.keys())
    
    def is_task_running(self, task_id: str) -> bool:
        """检查任务是否在运行"""
        with self._lock:
            return task_id in self.running_tasks and not self.running_tasks[task_id].is_set()
    
    def get_queue_size(self) -> int:
        """获取队列中等待的任务数"""
        return self.task_queue.qsize()
    
    def get_active_tasks_count(self) -> int:
        """获取当前活动的任务数"""
        return 3 - self.semaphore._value
    
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
            # 设置所有运行中任务的停止标志
            running_tasks = list(self.running_tasks.keys())
            for task_id, stop_event in self.running_tasks.items():
                stop_event.set()
                logger.info(f"Stopping task {task_id}")
        return running_tasks