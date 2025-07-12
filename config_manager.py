# =================================================================
#  config_manager.py
#  Version: 0.9
#  Author: MUXSET
#  Description: 配置管理中心。
#               负责所有与 config.json 文件的读取、写入和更新操作，
#               为整个应用程序提供统一、安全的配置访问接口。
# =================================================================

import json
import os
from typing import Any, Dict, Optional, Tuple

CONFIG_FILE = "config.json"

def _load_config() -> Dict[str, Any]:
    """
    从文件加载配置。如果文件不存在或为空，返回一个空字典。
    """
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}

def _save_config(config_data: Dict[str, Any]):
    """
    将配置数据以格式化的JSON形式写入文件。
    """
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4, ensure_ascii=False)

def ensure_config_exists():
    """
    确保配置文件存在。如果不存在，则创建一个包含默认值的模板。
    返回:
        bool: 如果是首次创建，返回 True，否则返回 False。
    """
    if not os.path.exists(CONFIG_FILE):
        print("🔧 [配置] 首次运行，正在创建新的配置文件...")
        default_config = {
            "username": "",
            "password": "",
            "tbea_art_token": "",
            "scan_interval_hours": 1.0,
            "token_refresh_interval_hours": 6.0
        }
        _save_config(default_config)
        print(f"✅ [配置] '{CONFIG_FILE}' 创建成功。")
        return True
    return False

def get_credentials() -> Tuple[Optional[str], Optional[str]]:
    """获取用户名和密码。"""
    config = _load_config()
    return config.get("username"), config.get("password")

def get_token() -> Optional[str]:
    """获取TBEA文章Token。"""
    return _load_config().get("tbea_art_token")

def get_intervals() -> Tuple[float, float]:
    """获取扫描和Token刷新的时间间隔（小时）。"""
    config = _load_config()
    scan_interval = config.get("scan_interval_hours", 1.0)
    token_interval = config.get("token_refresh_interval_hours", 6.0)
    return float(scan_interval), float(token_interval)

def update_credentials(username, password):
    """更新并保存用户名和密码。"""
    config = _load_config()
    config["username"] = username.strip()
    config["password"] = password.strip()
    _save_config(config)

def save_token(token: str):
    """更新并保存TBEA文章Token。"""
    config = _load_config()
    config["tbea_art_token"] = token
    _save_config(config)

def save_intervals(scan_interval: float, token_interval: float):
    """更新并保存时间间隔。"""
    config = _load_config()
    config["scan_interval_hours"] = scan_interval
    config["token_refresh_interval_hours"] = token_interval
    _save_config(config)
