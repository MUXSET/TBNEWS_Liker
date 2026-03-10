# =================================================================
#  task_manager.py
#  Version: 1.0.0
#  Author: MUXSET (Refactored by Senior Software Engineer)
#  Description: 通用后台任务调度器。
#               采用通用工作线程模型，可动态添加任意数量的定时任务。
#               (已重构): 使用 threading.Event 实现可瞬时打断的优雅休眠，
#               取代死板的 time.sleep()。
# =================================================================

import threading
import time
from typing import Callable, List, Dict
from logger import logger

class TaskManager:
    """管理后台工作线程，处理定时执行和优雅瞬时停止。"""

    def __init__(self):
        self.tasks: List[Dict] = []
        self.task_lock = threading.RLock()
        self.stop_event = threading.Event()
        self.threads: List[threading.Thread] = []

    def add_task(self, func: Callable, interval_hr: float, name: str, initial_delay_hr: float = 0):
        self.tasks.append({
            "func": func, "interval_sec": interval_hr * 3600,
            "name": name, "initial_delay_sec": initial_delay_hr * 3600
        })

    def _task_worker(self, task: Dict):
        name, interval, initial_delay = task['name'], task['interval_sec'], task['initial_delay_sec']

        logger.info(f"⚙️  [调度器] '{name}' 任务线程已准备。")
        if initial_delay > 0:
            first_run_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + initial_delay))
            logger.info(f"⏳ [调度器] '{name}' 任务首次运行计划于: {first_run_time}")
            # 使用 wait 代替 sleep，可以在等待期间瞬间响应 stop 信号
            if self.stop_event.wait(timeout=initial_delay):
                return

        while not self.stop_event.is_set():
            with self.task_lock:
                logger.info(f"▶️  [任务] 开始执行 '{name}'...")
                try:
                    task['func']()
                    logger.info(f"🏁 [任务] '{name}' 执行完成。")
                except Exception as e:
                    logger.error(f"❌ [任务] '{name}' 执行时发生严重错误: {e}")

            if self.stop_event.is_set():
                break

            next_run_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + interval))
            logger.info(f"😴 [调度器] '{name}' 任务休眠，下次运行: {next_run_time}")
            
            # 可被瞬间打断的优雅休眠
            if self.stop_event.wait(timeout=interval):
                break
                
        logger.info(f"⏹️  [调度器] '{name}' 任务线程已安全退出。")

    def start(self):
        if not self.tasks: return
        self.stop_event.clear()
        self.threads = []
        for task_info in self.tasks:
            thread = threading.Thread(target=self._task_worker, args=(task_info,), daemon=True)
            self.threads.append(thread)
            thread.start()
        logger.info("🚀 [调度器] 所有任务线程已启动。")

    def stop(self):
        logger.info("⏹️  [调度器] 正在发送停止信号给所有任务...")
        self.stop_event.set()

    @property
    def is_running(self) -> bool:
        """检查是否有任何任务线程仍在运行"""
        return any(t.is_alive() for t in self.threads)
