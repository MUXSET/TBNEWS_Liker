# =================================================================
#  run.py
#  Version: 0.5
#  Author: MUXSET
#  Description: 项目总指挥。
#               职责：提供用户交互菜单，并调用其他专家模块完成任务。
# =================================================================

import get_token
import liker
import time


def display_menu():
    """显示主菜单。"""
    print("\n" + "=" * 24 + " 主菜单 " + "=" * 24)
    print("  [1] 获取/更新 Token (需Edge浏览器手动登录)")
    print("  [2] 运行一次扫描点赞")
    print("  [3] 启动持续自动化扫描 (按 Ctrl+C 停止)")
    print("  [0] 退出程序")
    print("=" * 60)


def start_continuous_mode():
    """启动持续扫描模式。"""
    try:
        interval_input = input("请输入扫描间隔时间（小时，默认6）: ")
        interval_hours = float(interval_input) if interval_input else 6
        if interval_hours <= 0:
            interval_hours = 6
    except ValueError:
        print("输入无效，将使用默认间隔 6 小时。")
        interval_hours = 6

    print(f"✅ 已启动持续扫描模式，每隔 {interval_hours} 小时执行一次。")
    print("💡 按下【Ctrl + C】组合键可以随时安全地停止此模式并返回主菜单。")

    while True:
        try:
            # 执行一轮扫描
            liker.main()

            # 等待指定时间
            wait_seconds = interval_hours * 3600
            print(f"\n本轮任务完成。脚本将暂停 {interval_hours} 小时...")
            print(
                f"下一次扫描将在 {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + wait_seconds))} 左右开始。")
            time.sleep(wait_seconds)

        except KeyboardInterrupt:
            print("\n🚦 检测到用户中断操作(Ctrl+C)，已停止持续扫描模式。")
            break
        except Exception as e:
            print(f"\n❌ 在持续扫描循环中发生未知错误: {e}")
            print("为了安全，已停止持续扫描模式。请检查问题后重试。")
            break


def main():
    """程序主循环。"""
    while True:
        display_menu()
        choice = input("请输入您的选择: ")

        if choice == '1':
            get_token.main()
        elif choice == '2':
            liker.main()
        elif choice == '3':
            start_continuous_mode()
        elif choice == '0':
            print("👋 感谢使用，程序已退出。")
            break
        else:
            print("❌ 无效的输入，请重新选择。")

        time.sleep(1)


if __name__ == "__main__":
    main()
