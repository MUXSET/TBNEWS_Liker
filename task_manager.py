# =================================================================
#  task_manager.py
#  Version: 1.0.0
#  Author: MUXSET (Refactored by Senior Software Engineer)
#  Description: 通用后台任务调度器。
#               采用通用工作线程模型，可动态添加任意数量的定时任务，
#               并负责所有线程的生命周期管理。
# =================================================================

import threading
import time
from typing import Callable, List, Dict


class TaskManager:
    """管理后台工作线程，处理定时执行和优雅停止。"""

    def __init__(self):
        self.tasks: List[Dict] = []
        self.task_lock = threading.RLock()
        self.is_running = False
        self.threads: List[threading.Thread] = []

    def add_task(self, func: Callable, interval_hr: float, name: str, initial_delay_hr: float = 0):
        self.tasks.append({
            "func": func, "interval_sec": interval_hr * 3600,
            "name": name, "initial_delay_sec": initial_delay_hr * 3600
        })

    def _task_worker(self, task: Dict):
        name, interval, initial_delay = task['name'], task['interval_sec'], task['initial_delay_sec']

        print(f"  [调度器] '{name}' 任务线程已准备。")
        if initial_delay > 0:
            first_run_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + initial_delay))
            print(f"  [调度器] '{name}' 任务首次运行计划于: {first_run_time}")
            time.sleep(initial_delay)

        while self.is_running:
            with self.task_lock:
                print(f"\n{'=' * 25}\n▶️  [{time.strftime('%H:%M:%S')}] [任务] 开始执行 '{name}'...")
                try:
                    task['func']()
                    print(f"🏁 [{time.strftime('%H:%M:%S')}] [任务] '{name}' 执行完成。")
                except Exception as e:
                    print(f"❌ [{time.strftime('%H:%M:%S')}] [任务] '{name}' 执行时发生严重错误: {e}")

            if not self.is_running: break

            next_run_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + interval))
            print(f"😴 [{time.strftime('%H:%M:%S')}] [调度器] '{name}' 任务休眠，下次运行: {next_run_time}")
            print(f"{'=' * 25}")
            time.sleep(interval)

    def start(self):
        if not self.tasks: return
        self.is_running = True
        for task_info in self.tasks:
            thread = threading.Thread(target=self._task_worker, args=(task_info,), daemon=True)
            self.threads.append(thread)
            thread.start()
        print("  [调度器] 所有任务线程已启动。")

    def stop(self):
        print("\n⏹️  [调度器] 正在发送停止信号给所有任务...")
        self.is_running = False
