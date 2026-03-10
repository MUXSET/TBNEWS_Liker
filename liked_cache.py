# =================================================================
#  liked_cache.py
#  Version: 1.0.0
#  Description: 本地点赞记录缓存。
#               只有在 API 确认点赞成功后才记录，避免冗余请求。
#               数据存储在 liked_articles.json。
# =================================================================

import json
import os
from app_context import BASE_PATH
from logger import logger

CACHE_FILE = os.path.join(BASE_PATH, "liked_articles.json")

_cache = None  # 内存缓存，避免频繁读文件

def _load_cache() -> set:
    """从文件加载缓存到内存。"""
    global _cache
    if _cache is not None:
        return _cache
    
    if not os.path.exists(CACHE_FILE):
        _cache = set()
        return _cache
    
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            _cache = set(data) if isinstance(data, list) else set()
    except (json.JSONDecodeError, OSError):
        _cache = set()
    
    return _cache

def _save_cache():
    """将内存缓存写回文件（原子写入）。"""
    if _cache is None:
        return
    tmp = CACHE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(sorted(_cache, key=str), f)
    os.replace(tmp, CACHE_FILE)

def is_liked(article_id: int) -> bool:
    """检查文章是否已在本地缓存中标记为已赞。"""
    return article_id in _load_cache()

def mark_liked(article_id: int):
    """
    将文章标记为已点赞。
    ⚠️ 调用方必须确保只在 API 确认点赞成功后才调用此函数。
    """
    cache = _load_cache()
    if article_id not in cache:
        cache.add(article_id)
        _save_cache()

def get_cache_size() -> int:
    """返回缓存中的文章数量。"""
    return len(_load_cache())

def clear_cache():
    """清空缓存（一般不使用）。"""
    global _cache
    _cache = set()
    _save_cache()
    logger.info("🗑️ [缓存] 点赞记录缓存已清空。")
