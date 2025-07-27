# =================================================================
#  run.py
#  Version: 1.0.0
#  Author: MUXSET (Refactored by Senior Software Engineer)
#  Description: 应用程序主入口和编排器。
#               负责初始化环境(路径)，整合所有模块，处理用户交互，
#               并协调整个应用流程。
# =================================================================

import os
import sys
import time
import asyncio
import requests

# --- 导入上下文和业务模块 ---
import app_context
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
        self.token_is_valid: bool = False
        if config_manager.ensure_config_exists():
            self.update_credentials()
        self.check_token_validity(force_check=True)

    def check_token_validity(self, force_check: bool = False) -> bool:
        """检查Token有效性，并使用缓存避免不必要的网络请求。"""
        if not force_check:
            return self.token_is_valid

        print("  [主控] 正在联网验证Token有效性...")
        token = config_manager.get_token()
        if not token:
            self.token_is_valid = False
            return False
        try:
            response = requests.get(
                VALIDATION_API_URL,
                headers={"token": token},
                params={'id': VALIDATION_ARTICLE_ID},
                timeout=10
            )
            self.token_is_valid = response.json().get("code") == 1
        except requests.RequestException:
            self.token_is_valid = False

        print(f"  [主控] Token验证结果: {'有效' if self.token_is_valid else '无效'}")
        return self.token_is_valid

    def run_token_update_flow(self):
        """执行一次完整的Token更新流程。"""
        username, password = config_manager.get_credentials()
        if not username or not password:
            ui_manager.display_message("❌ [主控] 无法更新Token，请先在菜单[3]中设置账号信息。")
            return

        new_token = asyncio.run(get_token.get_new_token(username, password))

        if new_token:
            config_manager.save_token(new_token)
            ui_manager.display_message("✅ [主控] Token已成功更新并保存。")
        else:
            ui_manager.display_message("❌ [主控] Token更新失败，请检查账号密码或网络。")

        self.check_token_validity(force_check=True)

    def run_scan_flow(self):
        """执行一次完整的扫描点赞流程。"""
        ui_manager.clear_screen()
        ui_manager.display_header()
        print("👍 [主控] 正在准备执行扫描点赞...")

        if not self.check_token_validity(force_check=True):
            print("  ⚠️ Token无效或已过期，将首先自动更新Token。")
            self.run_token_update_flow()
            if not self.token_is_valid:
                ui_manager.display_message("  ❌ 自动更新Token后依然无效，任务中止。", 3)
                return

        print("  ✅ Token状态良好，开始调用扫描模块...")
        token = config_manager.get_token()
        liker.run_like_scan(token)

    def update_credentials(self):
        """引导用户更新账号密码并保存。"""
        username, password = ui_manager.prompt_for_credentials()
        config_manager.update_credentials(username, password)
        self.run_token_update_flow()

    def start_auto_mode(self):
        """启动自动挂机模式。"""
        scan_hr, token_hr = config_manager.get_intervals()
        new_scan_hr, new_token_hr = ui_manager.prompt_for_intervals(scan_hr, token_hr)
        config_manager.save_intervals(new_scan_hr, new_token_hr)

        if not self.check_token_validity(force_check=True):
            print("\n⚠️ [主控] 启动前Token无效，正在执行首次更新...")
            self.run_token_update_flow()
            if not self.token_is_valid:
                ui_manager.display_message("❌ [主控] Token更新失败，无法启动自动模式。", 3)
                return

        ui_manager.display_auto_mode_start()
        scheduler = task_manager.TaskManager()
        scheduler.add_task(self.run_scan_flow, new_scan_hr, "扫描点赞")
        scheduler.add_task(self.run_token_update_flow, new_token_hr, "Token刷新", initial_delay_hr=new_token_hr)
        scheduler.start()
        ui_manager.display_auto_mode_running()

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
            token_status = "✅ 有效" if self.token_is_valid else "❌ 无效或不存在"
            ui_manager.display_dashboard(username, token_status)
            choice = ui_manager.display_main_menu()

            if choice == '1':
                self.start_auto_mode()
                break
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


def initialize_environment():
    """在程序启动时执行一次性的环境检查。"""
    print("🚀 [环境初始化] 正在检查应用环境...")
    # 检查浏览器目录是否存在，因为 get_token.py 依赖它
    if getattr(sys, 'frozen', False) and not os.path.exists(app_context.BROWSER_DATA_PATH):
        print(f"❌ [严重错误] 浏览器目录 '{os.path.basename(app_context.BROWSER_DATA_PATH)}' 不存在！")
        print("   请确保 'ms-playwright' 文件夹与主程序在同一目录下。")
        input("   按回车键退出...")
        sys.exit(1)
    print("✅ [环境初始化] 环境检查通过。")


if __name__ == "__main__":
    initialize_environment()
    app = Application()
    app.main_loop()
