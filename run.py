# =================================================================
#  run.py
#  Version: 2.0.0
#  Author: MUXSET (GUI 重构)
#  Description: 应用程序主入口。
#               统一处理环境准备，并启动 CustomTkinter 现代图形用户界面。
# =================================================================

import os
import sys

import app_context

def initialize_environment():
    """在程序启动时执行一次性的环境检查。"""
    print("🚀 [环境初始化] 正在检查应用环境...")
    # 检查浏览器目录是否存在，因为 get_token.py 依赖它
    if getattr(sys, 'frozen', False) and not os.path.exists(app_context.BROWSER_DATA_PATH):
        # 打包环境下，如果缺失浏览器文件，弹出错误提示框而不是控制台输出
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "环境缺失错误",
                f"浏览器数据目录不存在！\n\n缺少组件: '{os.path.basename(app_context.BROWSER_DATA_PATH)}'\n\n请确保解压了所有文件，并将 'ms-playwright' 文件夹与主程序放在同一级目录中。"
            )
        except Exception:
            print("❌ [严重错误] 缺少 ms-playwright 浏览器环境目录！")
        sys.exit(1)
    print("✅ [环境初始化] 环境检查通过。")

if __name__ == "__main__":
    initialize_environment()
    
    # Lazy load GUI to ensure environment is fully checked before importing GUI frameworks
    from gui_app import App
    app = App()
    app.mainloop()
