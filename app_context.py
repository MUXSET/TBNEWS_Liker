# =================================================================
#  app_context.py
#  Version: 2.0.0
#  Author: MUXSET (Refactored by Senior Software Engineer)
#  Description: 应用上下文中心。
#               提供全局、统一的路径管理，确保在开发和打包环境中
#               都能正确定位资源文件，是解决路径问题的核心。
# =================================================================

import sys
import os

def get_base_path() -> str:
    """获取应用程序的根目录路径。
    
    开发模式: 返回脚本所在目录。
    打包模式 (macOS .app): sys.executable 在 *.app/Contents/MacOS/ 内，
                          需要向上 3 级到达 .app 所在目录。
    打包模式 (Windows):    sys.executable 在打包目录内，dirname 即可。
    """
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        # macOS .app bundle: exe 在 MyApp.app/Contents/MacOS/ 下
        if sys.platform == 'darwin' and '.app/Contents/MacOS' in exe_dir:
            return os.path.dirname(os.path.dirname(os.path.dirname(exe_dir)))
        return exe_dir
    else:
        return os.path.dirname(os.path.abspath(__file__))

BASE_PATH = get_base_path()
CONFIG_FILE_PATH = os.path.join(BASE_PATH, "config.json")
PROGRESS_FILE_PATH = os.path.join(BASE_PATH, "liker_progress.json")
BROWSER_DATA_PATH = os.path.join(BASE_PATH, "ms-playwright")

