# =================================================================
#  app_context.py
#  Version: 1.0.0
#  Author: MUXSET (Refactored by Senior Software Engineer)
#  Description: 应用上下文中心。
#               提供全局、统一的路径管理，确保在开发和打包环境中
#               都能正确定位资源文件，是解决路径问题的核心。
# =================================================================

import sys
import os

def get_base_path() -> str:
    """获取应用程序的根目录路径。"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

BASE_PATH = get_base_path()
CONFIG_FILE_PATH = os.path.join(BASE_PATH, "config.json")
PROGRESS_FILE_PATH = os.path.join(BASE_PATH, "liker_progress.json")
BROWSER_DATA_PATH = os.path.join(BASE_PATH, "ms-playwright")
