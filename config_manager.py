# =================================================================
#  config_manager.py
#  Version: 2.0.0
#  Author: MUXSET
#  Description: 配置管理中心 (多账号版)。
#               支持多账号管理，每个账号独立存储凭据和会话信息。
#               全局设置（频率、频道）所有账号共享。
# =================================================================

import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple
from app_context import CONFIG_FILE_PATH
from logger import logger

DEFAULT_CHANNELS = [
    {"name": "特变电工股份有限公司", "id": "XT-2bb8a866-d2a3-47da-bbad-8c63db21e9b6"},
    {"name": "新变厂新闻资讯", "id": "XT-0ba2025b-e2cb-498b-99b1-cdc741a21f75"},
    {"name": "开讲了", "id": "XT-1b1e03a9-8222-4b7f-a7eb-a5d91e2d012d"}
]

def _load_config() -> Dict[str, Any]:
    if not os.path.exists(CONFIG_FILE_PATH):
        return {}
    try:
        with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}

def _save_config(config_data: Dict[str, Any]):
    temp_file = CONFIG_FILE_PATH + ".tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4, ensure_ascii=False)
    os.replace(temp_file, CONFIG_FILE_PATH)

def _migrate_config(config: Dict) -> Dict:
    """将旧的单账号 config 迁移为新的多账号格式。"""
    if "accounts" in config:
        return config  # 已经是新格式
    
    logger.info("🔄 [配置] 检测到旧版配置，正在迁移到多账号格式...")
    
    # 将旧字段提取为一个 account
    account = {
        "username": config.pop("username", ""),
        "password": config.pop("password", ""),
        "tbea_art_token": config.pop("tbea_art_token", ""),
        "ejia_cookies": config.pop("ejia_cookies", {}),
        "ejia_user_id": config.pop("ejia_user_id", ""),
        "token_refresh_time": config.pop("token_refresh_time", 0),
        "sweep_stats": config.pop("sweep_stats", {}),
    }
    
    config["accounts"] = [account] if account["username"] else []
    config["active_account"] = 0 if config["accounts"] else -1
    
    # 保留全局设置
    config.setdefault("scan_interval_hours", 1.0)
    config.setdefault("token_refresh_interval_hours", 6.0)
    config.setdefault("channels", DEFAULT_CHANNELS)
    
    _save_config(config)
    logger.info("✅ [配置] 迁移完成！")
    return config

def ensure_config_exists() -> bool:
    if not os.path.exists(CONFIG_FILE_PATH):
        logger.info("🔧 [配置] 首次运行，正在创建新的配置文件...")
        default_config = {
            "accounts": [],
            "active_account": -1,
            "scan_interval_hours": 1.0,
            "token_refresh_interval_hours": 6.0,
            "channels": DEFAULT_CHANNELS
        }
        _save_config(default_config)
        logger.info(f"✅ [配置] '{os.path.basename(CONFIG_FILE_PATH)}' 创建成功。")
        return True
    
    # 迁移旧配置
    config = _load_config()
    if "accounts" not in config:
        _migrate_config(config)
    config.setdefault("channels", DEFAULT_CHANNELS)
    return False

# ============================
# 账号管理 (Feature 8)
# ============================

def _get_active_account() -> Dict:
    """获取当前激活的账号配置。"""
    config = _load_config()
    if "accounts" not in config:
        config = _migrate_config(config)
    
    accounts = config.get("accounts", [])
    idx = config.get("active_account", -1)
    if 0 <= idx < len(accounts):
        return accounts[idx]
    return {}

def _update_active_account(updates: Dict):
    """更新当前激活账号的指定字段。"""
    config = _load_config()
    if "accounts" not in config:
        config = _migrate_config(config)
    
    accounts = config.get("accounts", [])
    idx = config.get("active_account", -1)
    if 0 <= idx < len(accounts):
        accounts[idx].update(updates)
        _save_config(config)

def get_all_accounts() -> List[Dict]:
    """返回所有账号列表 (仅含用户名，不泄露密码)。"""
    config = _load_config()
    if "accounts" not in config:
        config = _migrate_config(config)
    return [{"index": i, "username": a.get("username", "")} 
            for i, a in enumerate(config.get("accounts", []))]

def get_active_account_index() -> int:
    config = _load_config()
    if "accounts" not in config:
        config = _migrate_config(config)
    return config.get("active_account", -1)

def switch_account(index: int) -> bool:
    """切换到指定索引的账号。"""
    config = _load_config()
    if "accounts" not in config:
        config = _migrate_config(config)
    
    accounts = config.get("accounts", [])
    if 0 <= index < len(accounts):
        config["active_account"] = index
        _save_config(config)
        logger.info(f"🔀 [配置] 已切换到账号: {accounts[index].get('username', '?')}")
        return True
    return False

def add_account(username: str, password: str) -> int:
    """添加新账号，返回其索引。"""
    config = _load_config()
    if "accounts" not in config:
        config = _migrate_config(config)
    
    accounts = config.get("accounts", [])
    
    # 检查是否已存在
    for i, a in enumerate(accounts):
        if a.get("username") == username:
            logger.warning(f"⚠️ [配置] 账号 {username} 已存在。")
            return i
    
    new_account = {
        "username": username, "password": password,
        "tbea_art_token": "", "ejia_cookies": {},
        "ejia_user_id": "", "token_refresh_time": 0,
        "sweep_stats": {},
    }
    accounts.append(new_account)
    config["accounts"] = accounts
    
    # 如果是第一个账号，自动激活
    if len(accounts) == 1:
        config["active_account"] = 0
    
    _save_config(config)
    logger.info(f"➕ [配置] 已添加账号: {username}")
    return len(accounts) - 1

def remove_account(index: int) -> bool:
    """删除指定索引的账号。"""
    config = _load_config()
    if "accounts" not in config:
        config = _migrate_config(config)
    
    accounts = config.get("accounts", [])
    if 0 <= index < len(accounts):
        removed = accounts.pop(index)
        config["accounts"] = accounts
        
        # 调整 active_account
        active = config.get("active_account", 0)
        if active >= len(accounts):
            config["active_account"] = max(0, len(accounts) - 1) if accounts else -1
        elif active > index:
            config["active_account"] = active - 1
        
        _save_config(config)
        logger.info(f"🗑️ [配置] 已删除账号: {removed.get('username', '?')}")
        return True
    return False

# ============================
# 兼容层 (原有 API，操作当前账号)
# ============================

def get_credentials() -> Tuple[Optional[str], Optional[str]]:
    acc = _get_active_account()
    return acc.get("username"), acc.get("password")

def get_token() -> Optional[str]:
    return _get_active_account().get("tbea_art_token")

def update_credentials(username: str, password: str):
    _update_active_account({"username": username.strip(), "password": password.strip()})

def save_token(token_data: dict | str):
    if isinstance(token_data, dict):
        updates = {
            "tbea_art_token": token_data.get("token", ""),
            "ejia_cookies": token_data.get("ejia_cookies", {}),
            "token_refresh_time": time.time(),
        }
        # 仅在当前账号没有 ejia_user_id 时才写入
        acc = _get_active_account()
        new_uid = token_data.get("ejia_user_id", "")
        if new_uid and not acc.get("ejia_user_id"):
            updates["ejia_user_id"] = new_uid
        _update_active_account(updates)
    else:
        _update_active_account({"tbea_art_token": token_data, "token_refresh_time": time.time()})

def get_ejia_cookies() -> dict:
    return _get_active_account().get("ejia_cookies", {})

def get_ejia_user_id() -> str:
    return _get_active_account().get("ejia_user_id", "")

def get_token_refresh_time() -> float:
    return float(_get_active_account().get("token_refresh_time", 0))

def save_sweep_stats(total: int, liked: int, skipped: int):
    _update_active_account({"sweep_stats": {
        "total": total, "liked": liked, "skipped": skipped,
        "last_sweep_time": time.strftime("%Y-%m-%d %H:%M:%S")
    }})

def get_sweep_stats() -> dict:
    return _get_active_account().get("sweep_stats", {})

# ============================
# 全局设置 (所有账号共享)
# ============================

def get_intervals() -> Tuple[float, float]:
    config = _load_config()
    return float(config.get("scan_interval_hours", 1.0)), float(config.get("token_refresh_interval_hours", 6.0))

def save_intervals(scan_interval: float, token_interval: float):
    config = _load_config()
    config["scan_interval_hours"] = scan_interval
    config["token_refresh_interval_hours"] = token_interval
    _save_config(config)

def get_channels() -> List[Dict]:
    config = _load_config()
    return config.get("channels", DEFAULT_CHANNELS)

def save_channels(channels: List[Dict]):
    config = _load_config()
    config["channels"] = channels
    _save_config(config)
