# =================================================================
#  run.py
#  Version: 0.9.1
#  Author: MUXSET
#  Description: 应用程序主入口和调度器。
#               修复了因嵌套调用锁而导致的死锁问题，
#               通过将 threading.Lock 更换为 threading.RLock。
# =================================================================

import get_token
import liker
import json
import os
import platform
import threading
import time
import requests  # 确保 requests 被导入
from typing import Optional

# --- 全局常量 ---
CONFIG_FILE = "config.json"
VALIDATION_API_URL = "https://tbeanews.tbea.com/api/article/detail"
VALIDATION_ARTICLE_ID = 8141


class AutoLikerApp:
    """
    主应用程序类，负责管理配置、UI、状态和后台任务。
    """

    def __init__(self):
        self.config = {}
        # --- 核心修复：使用RLock替代Lock，允许同一线程多次获取锁 ---
        self.task_lock = threading.RLock()
        self.auto_threads = []
        self.is_auto_running = False
        self.next_scan_time: Optional[float] = None
        self.next_token_time: Optional[float] = None
        self._load_or_create_config()

    def _clear_screen(self):
        """清空控制台屏幕。"""
        os.system('cls' if platform.system() == "Windows" else 'clear')

    def _load_or_create_config(self):
        """加载或初始化配置文件，并在必要时引导用户设置凭据。"""
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            print("🔧 [首次运行] 欢迎使用！正在为您创建新的配置文件...")
            self.config = {
                "username": "", "password": "", "tbea_art_token": "",
                "scan_interval_hours": 1.0, "token_refresh_interval_hours": 6.0
            }
            self._save_config()
            time.sleep(1)

        if not self.config.get("username") or not self.config.get("password"):
            self._update_credentials()

    def _save_config(self):
        """将当前配置写入文件。"""
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)

    def _update_credentials(self):
        """引导用户输入并更新账号密码。"""
        self._clear_screen()
        print("🔐 [凭据设置] 请输入您的登录信息。")
        username = input("  请输入登录账号: ")
        password = input("  请输入登录密码: ")
        self.config["username"] = username.strip()
        self.config["password"] = password.strip()
        self._save_config()
        print("\n✅ 凭据已保存！")
        time.sleep(1.5)

    def _update_intervals(self):
        """引导用户更新任务时间间隔。"""
        self._clear_screen()
        print("⚙️ [定时器设置] 您可以设置新的任务间隔 (单位: 小时)。")

        current_scan = self.config.get('scan_interval_hours', 1.0)
        scan_input = input(f"  扫描间隔 (当前: {current_scan} 小时, 直接回车跳过): ")
        if scan_input:
            try:
                self.config['scan_interval_hours'] = float(scan_input)
            except ValueError:
                print("  ❌ 输入无效，保留原值。")

        current_token = self.config.get('token_refresh_interval_hours', 6.0)
        token_input = input(f"  Token刷新间隔 (当前: {current_token} 小时, 直接回车跳过): ")
        if token_input:
            try:
                self.config['token_refresh_interval_hours'] = float(token_input)
            except ValueError:
                print("  ❌ 输入无效，保留原值。")

        self._save_config()
        print("\n✅ 定时器设置已更新！")
        time.sleep(1.5)

    def _check_token_validity(self) -> bool:
        """检查当前Token是否有效。"""
        token = self.config.get("tbea_art_token")
        if not token:
            return False
        try:
            response = requests.get(
                VALIDATION_API_URL,
                headers={"token": token},
                params={'id': VALIDATION_ARTICLE_ID},
                timeout=10
            )
            response.raise_for_status()
            # 增加对返回json的健壮性判断
            return response.json().get("code") == 1
        except Exception:
            return False

    def _run_token_update(self):
        """执行一次Token更新流程。"""
        with self.task_lock:
            print("\n🔄 [主控] 正在调用Token更新模块...")
            get_token.main()
            self._load_or_create_config()

    def _run_scan_logic(self):
        """执行一次扫描点赞流程，并在需要时自动更新Token。"""
        with self.task_lock:
            print("\n👍 [主控] 正在准备执行扫描点赞...")
            if not self._check_token_validity():
                print("  ⚠️ Token无效或已过期，将首先自动更新Token。")
                # 此处嵌套调用是安全的，因为我们使用了RLock
                self._run_token_update()
                if not self._check_token_validity():
                    print("  ❌ 自动更新Token后依然无效，任务中止。")
                    return
                print("  ✅ Token更新成功，继续执行扫描。")

            liker.main()

    def _liker_worker(self):
        """点赞线程的工作循环。"""
        interval_hours = self.config.get('scan_interval_hours', 1.0)
        while self.is_auto_running:
            self._run_scan_logic()

            if not self.is_auto_running: break  # 检查任务执行后是否需要退出

            sleep_seconds = interval_hours * 3600
            self.next_scan_time = time.time() + sleep_seconds
            # 在休眠前打印下次运行时间
            next_run_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.next_scan_time))
            print(f"  [主控] 点赞任务完成，下次扫描时间: {next_run_str}")
            time.sleep(sleep_seconds)

    def _token_worker(self):
        """Token刷新线程的工作循环。"""
        interval_hours = self.config.get('token_refresh_interval_hours', 6.0)
        sleep_seconds = interval_hours * 3600
        self.next_token_time = time.time() + sleep_seconds

        # 首次运行时打印计划
        next_run_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.next_token_time))
        print(f"  [主控] Token刷新任务已计划，首次刷新时间: {next_run_str}")

        time.sleep(sleep_seconds)

        while self.is_auto_running:
            self._run_token_update()

            if not self.is_auto_running: break  # 检查任务执行后是否需要退出

            sleep_seconds = interval_hours * 3600
            self.next_token_time = time.time() + sleep_seconds
            next_run_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.next_token_time))
            print(f"  [主控] Token刷新完成，下次刷新时间: {next_run_str}")
            time.sleep(sleep_seconds)

    def _start_auto_mode(self):
        """启动自动挂机模式。"""
        self.is_auto_running = True
        self._clear_screen()
        print("🚀 [自动模式] 正在启动后台任务线程...")

        liker_thread = threading.Thread(target=self._liker_worker, daemon=True)
        token_thread = threading.Thread(target=self._token_worker, daemon=True)
        self.auto_threads = [liker_thread, token_thread]

        liker_thread.start()
        token_thread.start()

        # --- 优化：短暂延时，让线程的初始日志有机会先打印 ---
        time.sleep(0.1)

        print("\n✅ [自动模式] 所有线程已启动，进入无人值守模式。")
        print("   按 Ctrl+C 可随时停止并退出程序。")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.is_auto_running = False
            print("\n\n⏹️ [主控] 检测到用户中断，正在等待任务安全结束...")
            # 不再需要join，因为daemon线程会随主线程退出
            print("程序已安全退出。")

    def _display_dashboard(self):
        """显示主操作界面和状态仪表盘。"""
        self._clear_screen()

        is_valid = self._check_token_validity()
        token_status = "✅ 有效" if is_valid else "❌ 无效或不存在"
        username = self.config.get("username", "未设置")

        print("=" * 60)
        print(f" MUXSET 全自动点赞工具 v0.9.1".center(54))
        print("=" * 60)
        print(f"  👤 当前账号: {username}")
        print(f"  🔑 Token状态: {token_status}")

        if self.is_auto_running:
            scan_time_str = time.strftime('%H:%M:%S',
                                          time.localtime(self.next_scan_time)) if self.next_scan_time else "计算中..."
            token_time_str = time.strftime('%H:%M:%S',
                                           time.localtime(self.next_token_time)) if self.next_token_time else "计算中..."
            print(f"  🕒 下次扫描: {scan_time_str}")
            print(f"  🕒 下次刷新Token: {token_time_str}")
        print("-" * 60)

        print("  [1] 启动自动挂机")
        print("  [2] 立即执行一次扫描")
        print("  [3] 更改账号或定时器")
        print("\n  [0] 退出程序")
        print("-" * 60)

    def run(self):
        """应用程序主循环。"""
        while True:
            self._display_dashboard()
            choice = input("  请输入您的选择: ")

            if choice == '1':
                self._start_auto_mode()
                break
            elif choice == '2':
                self._run_scan_logic()
                input("\n...单次任务完成，按回车键返回主菜单...")
            elif choice == '3':
                self._update_credentials()
                self._update_intervals()
            elif choice == '0':
                print("\n感谢使用，程序已退出。")
                break
            else:
                print("\n无效输入，请重新选择。")
                time.sleep(1)


if __name__ == "__main__":
    # 确保requests库存在
    try:
        import requests
    except ImportError:
        print("错误：缺少'requests'库。请运行 'pip install requests' 来安装。")
        exit()

    app = AutoLikerApp()
    app.run()
