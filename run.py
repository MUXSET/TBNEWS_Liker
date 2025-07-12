# =================================================================
#  run.py
#  Version: 0.9.1
#  Author: MUXSET
#  Description: 应用程序主入口和编排器。
#               负责整合所有模块，处理用户交互，并协调整个应用流程。
# =================================================================

import requests
import time

# --- 导入重构后的模块 ---
import config_manager
import ui_manager
import task_manager
import get_token
import liker

# --- 全局常量 ---
VALIDATION_API_URL = "https://tbeanews.tbea.com/api/article/detail"
VALIDATION_ARTICLE_ID = 8141

class Application:
    """主应用程序类，负责编排所有模块。"""

    def __init__(self):
        """初始化应用程序，加载或创建配置。"""
        if config_manager.ensure_config_exists():
            # 如果是首次创建，引导用户设置凭据
            self.update_credentials()

    def check_token_validity(self) -> bool:
        """检查当前存储的Token是否有效。"""
        token = config_manager.get_token()
        if not token:
            return False
        try:
            response = requests.get(
                VALIDATION_API_URL,
                headers={"token": token},
                params={'id': VALIDATION_ARTICLE_ID},
                timeout=10
            )
            return response.json().get("code") == 1
        except Exception:
            return False

    def run_token_update_flow(self):
        """
        执行一次完整的Token更新流程：
        1. 从配置获取凭据。
        2. 调用get_token模块获取新Token。
        3. 如果成功，将新Token存入配置。
        """
        username, password = config_manager.get_credentials()
        if not username or not password:
            ui_manager.display_message("❌ [主控] 无法更新Token，请先设置账号信息。")
            return

        new_token = get_token.get_new_token(username, password)
        if new_token:
            config_manager.save_token(new_token)
            print("✅ [主控] Token已成功更新并保存。")
        else:
            print("❌ [主控] Token更新失败。")

    def run_scan_flow(self):
        """
        执行一次完整的扫描点赞流程：
        1. 检查Token有效性。
        2. 如果Token无效，则自动触发更新流程。
        3. 如果Token有效（或更新后有效），则执行扫描。
        """
        ui_manager.clear_screen()
        ui_manager.display_header()
        print("👍 [主控] 正在准备执行扫描点赞...")

        if not self.check_token_validity():
            print("  ⚠️ Token无效或已过期，将首先自动更新Token。")
            self.run_token_update_flow()
            if not self.check_token_validity():
                print("  ❌ 自动更新Token后依然无效，任务中止。")
                return

        print("  ✅ Token状态良好，开始调用扫描模块...")
        token = config_manager.get_token()
        liker.run_like_scan(token)

    def update_credentials(self):
        """引导用户更新账号密码并保存。"""
        username, password = ui_manager.prompt_for_credentials()
        config_manager.update_credentials(username, password)

    def start_auto_mode(self):
        """启动自动挂机模式。"""
        # 1. 让用户确认/设置时间间隔
        scan_hr, token_hr = config_manager.get_intervals()
        new_scan_hr, new_token_hr = ui_manager.prompt_for_intervals(scan_hr, token_hr)
        config_manager.save_intervals(new_scan_hr, new_token_hr)

        # 2. 确保初次运行时Token有效
        if not self.check_token_validity():
            print("\n⚠️ [主控] 启动前Token无效，正在执行首次更新...")
            self.run_token_update_flow()
            if not self.check_token_validity():
                ui_manager.display_message("❌ [主控] Token更新失败，无法启动自动模式。", 3)
                return

        # 3. 初始化并启动任务调度器
        ui_manager.display_auto_mode_start()
        scheduler = task_manager.TaskManager(
            liker_func=self.run_scan_flow,
            token_func=self.run_token_update_flow,
            liker_interval_hr=new_scan_hr,
            token_interval_hr=new_token_hr
        )
        scheduler.start()
        ui_manager.display_auto_mode_running()

        # 4. 主线程在此等待用户中断
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            scheduler.stop()
            ui_manager.display_auto_mode_shutdown()

    def main_loop(self):
        """应用程序的主循环，处理用户输入。"""
        while True:
            username, _ = config_manager.get_credentials()
            token_status = "✅ 有效" if self.check_token_validity() else "❌ 无效或不存在"
            ui_manager.display_dashboard(username, token_status)
            choice = ui_manager.display_main_menu()

            if choice == '1':
                self.start_auto_mode()
                break  # 自动模式结束后直接退出程序
            elif choice == '2':
                self.run_scan_flow()
                input("\n...单次任务完成，按回车键返回主菜单...")
            elif choice == '3':
                self.update_credentials()
            elif choice == '0':
                ui_manager.display_exit_message()
                break
            else:
                ui_manager.display_message("\n无效输入，请重新选择。", 1)

if __name__ == "__main__":
    app = Application()
    app.main_loop()
