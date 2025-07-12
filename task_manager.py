# =================================================================
#  task_manager.py
#  Version: 0.9
#  Author: MUXSET
#  Description: 后台任务调度器。
#               封装了所有与线程、定时、锁相关的逻辑，
#               负责管理和调度后台的自动化任务。
# =================================================================

import threading
import time
from typing import Callable, Optional

class TaskManager:
    """管理后台工作线程，处理定时执行和优雅停止。"""

    def __init__(self, liker_func: Callable, token_func: Callable,
                 liker_interval_hr: float, token_interval_hr: float):
        """
        初始化任务调度器。
        参数:
            liker_func (Callable): 要定时执行的点赞函数。
            token_func (Callable): 要定时执行的Token刷新函数。
            liker_interval_hr (float): 点赞任务的执行间隔（小时）。
            token_interval_hr (float): Token刷新任务的执行间隔（小时）。
        """
        self.liker_func = liker_func
        self.token_func = token_func
        self.liker_interval_sec = liker_interval_hr * 3600
        self.token_interval_sec = token_interval_hr * 3600

        # RLock允许同一线程多次获取锁，防止在嵌套调用中（如扫描时发现token失效而更新）发生死锁
        self.task_lock = threading.RLock()
        self.is_running = False
        self.threads = []

    def _liker_worker(self):
        """点赞线程的工作循环。"""
        print("  [调度器] 点赞线程已启动。")
        while self.is_running:
            with self.task_lock:
                print(f"\n{'='*25}\n▶️  [{time.strftime('%H:%M:%S')}] [任务] 开始执行扫描点赞...")
                self.liker_func()
                print(f"🏁 [{time.strftime('%H:%M:%S')}] [任务] 本轮扫描点赞完成。")

            if not self.is_running: break

            next_run_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + self.liker_interval_sec))
            print(f"😴 [{time.strftime('%H:%M:%S')}] [调度器] 点赞任务休眠，下次运行: {next_run_time}")
            print(f"{'='*25}")
            time.sleep(self.liker_interval_sec)

    def _token_worker(self):
        """Token刷新线程的工作循环。"""
        print("  [调度器] Token刷新线程已启动。")
        # 首次运行时，先等待一个周期，因为主程序已确保Token有效
        first_run_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + self.token_interval_sec))
        print(f"  [调度器] Token任务首次刷新计划于: {first_run_time}")
        time.sleep(self.token_interval_sec)

        while self.is_running:
            with self.task_lock:
                print(f"\n{'='*25}\n🔄 [{time.strftime('%H:%M:%S')}] [任务] 开始执行Token刷新...")
                self.token_func()
                print(f"✅ [{time.strftime('%H:%M:%S')}] [任务] Token刷新完成。")

            if not self.is_running: break

            next_run_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + self.token_interval_sec))
            print(f"😴 [{time.strftime('%H:%M:%S')}] [调度器] Token任务休眠，下次运行: {next_run_time}")
            print(f"{'='*25}")
            time.sleep(self.token_interval_sec)

    def start(self):
        """启动所有后台任务线程。"""
        self.is_running = True
        liker_thread = threading.Thread(target=self._liker_worker, daemon=True)
        token_thread = threading.Thread(target=self._token_worker, daemon=True)
        self.threads = [liker_thread, token_thread]
        for t in self.threads:
            t.start()

    def stop(self):
        """设置停止标志，以优雅地终止所有线程。"""
        self.is_running = False
