# =================================================================
#  ui_manager.py
#  Version: 1.0.0
#  Author: MUXSET (Refactored by Senior Software Engineer)
#  Description: 用户界面管理器。
#               负责所有控制台的输入输出，将UI展示与业务逻辑分离。
# =================================================================

import os
import platform
import time
from typing import Tuple

def clear_screen():
    os.system('cls' if platform.system() == "Windows" else 'clear')

def display_header():
    print("=" * 60)
    print(f" E+新闻 全自动点赞工具 v1.0.0".center(54))
    print("=" * 60)

def display_dashboard(username: str, token_status: str):
    clear_screen()
    display_header()
    print(f"  👤 当前账号: {username or '未设置'}")
    print(f"  🔑 Token状态: {token_status}")
    print("-" * 60)

def display_main_menu():
    print("  [1] 启动自动挂机模式")
    print("  [2] 立即执行一次扫描")
    print("  [3] 更改账号信息")
    print("\n  [0] 退出程序")
    print("-" * 60)
    return input("  请输入您的选择: ")

def prompt_for_credentials() -> Tuple[str, str]:
    clear_screen()
    display_header()
    print("🔐 [凭据设置] 请输入您的登录信息。")
    username = input("  请输入登录账号: ")
    password = input("  请输入登录密码: ")
    return username, password

def prompt_for_intervals(current_scan: float, current_token: float) -> Tuple[float, float]:
    clear_screen()
    display_header()
    print("⚙️  [自动模式设置] 请确认任务间隔 (单位: 小时)。")
    print("   直接按回车键可使用括号内的当前值。\n")
    try:
        scan_input = input(f"  ➡️  扫描间隔 (当前: {current_scan} 小时): ")
        new_scan = float(scan_input) if scan_input else current_scan
    except ValueError:
        new_scan = current_scan
    try:
        token_input = input(f"  ➡️  Token刷新间隔 (当前: {current_token} 小时): ")
        new_token = float(token_input) if token_input else current_token
    except ValueError:
        new_token = current_token
    print("\n✅ 设置已确认！")
    time.sleep(1.5)
    return new_scan, new_token

def display_auto_mode_start():
    clear_screen()
    display_header()
    print("🚀 [自动模式] 正在启动后台任务调度器...")

def display_auto_mode_running():
    print("\n✅ [自动模式] 所有线程已启动，进入无人值守模式。")
    print("   按 Ctrl+C 可随时停止并退出程序。")

def display_auto_mode_shutdown():
    print("\n\n⏹️  [主控] 检测到用户中断 (Ctrl+C)，正在关闭程序...")
    print("感谢使用，再见！")

def display_exit_message():
    print("\n感谢使用，程序已退出。")

def display_message(message: str, delay: float = 2.0):
    print(message)
    time.sleep(delay)
