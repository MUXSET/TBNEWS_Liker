# =================================================================
#  logger.py
#  Version: 1.0.0
#  Description: 全局日志管理器。
#               1. 记录运行日志到文件 (自动滚动)。
#               2. 输出到控制台 (调试用)。
#               3. 输出到队列，供 GUI 主线程安全地拉取并刷新显示。
# =================================================================

import logging
import queue
import os
from logging.handlers import RotatingFileHandler
from app_context import BASE_PATH

LOG_FILE = os.path.join(BASE_PATH, "app.log")

# 线程安全的队列，后台线程的打印推送到这里，UI线程负责定时去读取
log_queue = queue.Queue()

class QueueHandler(logging.Handler):
    """将日志发送到队列，以便 GUI 主事件循环安全读取。"""
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue
    
    def emit(self, record):
        # 使用自定义的格式化
        msg = self.format(record)
        self.log_queue.put((record.levelname, msg))

def setup_logger():
    # 使用唯一的名称获取logger，防止重复配置
    app_logger = logging.getLogger("TBNEWS_Liker")
    app_logger.setLevel(logging.INFO)
    
    # 避免重复添加Handler
    if app_logger.handlers:
        return app_logger
        
    formatter_file = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s', '%Y-%m-%d %H:%M:%S')
    formatter_gui = logging.Formatter('[%(asctime)s] %(message)s', '%H:%M:%S')
    
    # 1. 文件 Handler (最大 5MB，保留 3 个备份)
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=1024*1024*5, backupCount=3, encoding='utf-8')
    file_handler.setFormatter(formatter_file)
    app_logger.addHandler(file_handler)
    
    # 2. 控制台 Handler (适用于开发环境调试)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter_file)
    app_logger.addHandler(console_handler)
    
    # 3. GUI 队列 Handler
    queue_handler = QueueHandler(log_queue)
    queue_handler.setFormatter(formatter_gui)
    app_logger.addHandler(queue_handler)
    
    # 防止向 ROOT logger 传递，避免第三方库刷屏
    app_logger.propagate = False
    
    return app_logger

# 导出全局单例 instance 和 queue
logger = setup_logger()
