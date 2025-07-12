# =================================================================
#  ui_manager.py
#  Version: 0.9.1
#  Author: MUXSET
#  Description: 用户界面管理器。
#               负责所有控制台的输入输出，将UI展示与业务逻辑分离。
# =================================================================

import os
import platform
import time
from typing import Tuple

def clear_screen():
    """清空控制台屏幕。"""
    os.system('cls' if platform.system() == "Windows" else 'clear')

def display_header():
    """显示程序的主标题。"""
    print("=" * 60)
    print(f" MUXSET 全自动点赞工具 v0.9".center(54))
    print("=" * 60)

def display_dashboard(username: str, token_status: str):
    """
    显示主操作界面和状态仪表盘。
    参数:
        username (str): 当前配置的用户名。
        token_status (str): 格式化后的Token状态字符串。
    """
    clear_screen()
    display_header()
    print(f"  👤 当前账号: {username or '未设置'}")
    print(f"  🔑 Token状态: {token_status}")
    print("-" * 60)

def display_main_menu():
    """显示主菜单选项。"""
    print("  [1] 启动自动挂机模式")
    print("  [2] 立即执行一次扫描")
    print("  [3] 更改账号信息")
    print("\n  [0] 退出程序")
    print("-" * 60)
    return input("  请输入您的选择: ")

def prompt_for_credentials() -> Tuple[str, str]:
    """引导用户输入并返回账号密码。"""
    clear_screen()
    display_header()
    print("🔐 [凭据设置] 请输入您的登录信息。")
    username = input("  请输入登录账号: ")
    password = input("  请输入登录密码: ")
    print("\n✅ 凭据已保存！")
    time.sleep(1.5)
    return username, password

def prompt_for_intervals(current_scan: float, current_token: float) -> Tuple[float, float]:
    """
    在启动自动模式前，引导用户确认或设置时间间隔。
    """
    clear_screen()
    display_header()
    print("⚙️  [自动模式设置] 请确认任务间隔 (单位: 小时)。")
    print("   直接按回车键可使用括号内的当前值。\n")

    try:
        scan_input = input(f"  ➡️  扫描间隔 (当前: {current_scan} 小时): ")
        new_scan = float(scan_input) if scan_input else current_scan
    except ValueError:
        print("  ❌ 输入无效，保留原值。")
        new_scan = current_scan

    try:
        token_input = input(f"  ➡️  Token刷新间隔 (当前: {current_token} 小时): ")
        new_token = float(token_input) if token_input else current_token
    except ValueError:
        print("  ❌ 输入无效，保留原值。")
        new_token = current_token

    print("\n✅ 设置已确认！")
    time.sleep(1.5)
    return new_scan, new_token

def display_auto_mode_start():
    clear_screen()
    display_header()
    print("🚀 [自动模式] 正在启动后台任务线程...")

def display_auto_mode_running():
    print("\n✅ [自动模式] 所有线程已启动，进入无人值守模式。")
    print("   按 Ctrl+C 可随时停止并退出程序。")

def display_auto_mode_shutdown():
    print("\n\n⏹️  [主控] 检测到用户中断，正在关闭程序...")
    print("感谢使用，再见！")

def display_exit_message():
    print("\n感谢使用，程序已退出。")

def display_message(message: str, delay: float = 1.5):
    print(message)
    time.sleep(delay)
