# =================================================================
#  config_manager.py
#  Version: 1.0.0
#  Author: MUXSET (Refactored by Senior Software Engineer)
#  Description: 配置管理中心。
#               从 app_context 获取标准路径，负责 config.json 的
#               读写操作，为程序提供统一的配置访问接口。
# =================================================================

import json
import os
from typing import Any, Dict, Optional, Tuple
from app_context import CONFIG_FILE_PATH

def _load_config() -> Dict[str, Any]:
    if not os.path.exists(CONFIG_FILE_PATH):
        return {}
    try:
        with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}

def _save_config(config_data: Dict[str, Any]):
    with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4, ensure_ascii=False)

def ensure_config_exists() -> bool:
    if not os.path.exists(CONFIG_FILE_PATH):
        print("🔧 [配置] 首次运行，正在创建新的配置文件...")
        default_config = {
            "username": "", "password": "", "tbea_art_token": "",
            "scan_interval_hours": 1.0, "token_refresh_interval_hours": 6.0
        }
        _save_config(default_config)
        print(f"✅ [配置] '{os.path.basename(CONFIG_FILE_PATH)}' 创建成功。")
        return True
    return False

def get_credentials() -> Tuple[Optional[str], Optional[str]]:
    config = _load_config()
    return config.get("username"), config.get("password")

def get_token() -> Optional[str]:
    return _load_config().get("tbea_art_token")

def get_intervals() -> Tuple[float, float]:
    config = _load_config()
    return float(config.get("scan_interval_hours", 1.0)), float(config.get("token_refresh_interval_hours", 6.0))

def update_credentials(username: str, password: str):
    config = _load_config()
    config["username"] = username.strip()
    config["password"] = password.strip()
    _save_config(config)

def save_token(token: str):
    config = _load_config()
    config["tbea_art_token"] = token
    _save_config(config)

def save_intervals(scan_interval: float, token_interval: float):
    config = _load_config()
    config["scan_interval_hours"] = scan_interval
    config["token_refresh_interval_hours"] = token_interval
    _save_config(config)
