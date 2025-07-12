# =================================================================
#  liker.py
#  Version: 0.9
#  Author: MUXSET
#  Description: 自动扫描点赞专家模块 (重构版)。
#               通过函数接收Token执行扫描，不再直接访问配置文件。
# =================================================================

import requests
import time
import json
import os

# --- 模块常量 ---
PROGRESS_FILE = "liker_progress_v0.9.json"
INITIAL_SCAN_START_ID = 8141
MAX_CONSECUTIVE_INVALID_ARTICLES = 15
ARTICLE_DETAIL_API_URL = "https://tbeanews.tbea.com/api/article/detail"
LIKE_API_URL = "https://tbeanews.tbea.com/api/article/addDigg"


def _load_progress():
    """从进度文件加载最后一个成功点赞的ID。"""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return int(json.load(f).get("last_liked_id", INITIAL_SCAN_START_ID - 1))
        except (json.JSONDecodeError, ValueError, OSError):
            return INITIAL_SCAN_START_ID - 1
    return INITIAL_SCAN_START_ID - 1


def _save_progress(liked_id):
    """将最新的、成功点赞的ID写入进度文件。"""
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_liked_id": int(liked_id)}, f, indent=4)
    print(f"  💾 [点赞模块] 进度已保存: 最后一个成功点赞的ID是 {liked_id}。")


def _perform_like(session, article_id, token):
    """对指定文章执行点赞，返回True/False。"""
    headers = {
        "Accept": "application/json", "Content-Type": "application/json",
        "Origin": "https://tbeanews.tbea.com",
        "Referer": f"https://tbeanews.tbea.com/pc/show?id={article_id}",
        "token": token,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    try:
        response = session.post(LIKE_API_URL, headers=headers, json={"id": str(article_id)}, timeout=15)
        response.raise_for_status()
        data = response.json()
        if data.get("code") == 1 or "重复点赞" in data.get('msg', ''):
            print(f"  ✅ [点赞模块] 文章ID {article_id} 点赞成功 (或已点赞)。")
            return True
        else:
            print(f"  ❌ [点赞模块] 文章ID {article_id} 点赞失败: {data.get('msg', '未知错误')}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"  ❌ [点赞模块] 点赞文章 {article_id} 时网络错误: {e}")
        return False


def run_like_scan(token: str):
    """
    模块主函数：执行一轮完整的文章扫描和点赞流程。
    参数:
        token (str): 用于API请求的认证Token。
    """
    if not token:
        print("  ❌ [点赞模块] 致命错误: 未提供有效的Token。")
        return

    session = requests.Session()
    last_liked_id = _load_progress()
    current_id = last_liked_id + 1
    consecutive_invalid_count = 0
    print(f"  ▶️  [点赞模块] 扫描起点: ID {current_id}")

    while consecutive_invalid_count < MAX_CONSECUTIVE_INVALID_ARTICLES:
        try:
            # 1. 检查文章是否存在
            response = session.get(ARTICLE_DETAIL_API_URL, params={'id': current_id}, headers={"token": token},
                                   timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get('code') == 1 and data.get('data'):
                consecutive_invalid_count = 0
                if _perform_like(session, current_id, token):
                    _save_progress(current_id)
                else:
                    print("  ↳ 关键操作(点赞)失败，中止本轮任务以便下次重试。")
                    break
            else:
                consecutive_invalid_count += 1
                print(
                    f"  - [点赞模块] 无效ID {current_id} (连续 {consecutive_invalid_count}/{MAX_CONSECUTIVE_INVALID_ARTICLES})")

        except requests.exceptions.RequestException as e:
            print(f"  ↳ 检查ID {current_id} 时发生网络错误: {e}。中止任务。")
            break

        current_id += 1
        time.sleep(0.5)

    if consecutive_invalid_count >= MAX_CONSECUTIVE_INVALID_ARTICLES:
        print(f"\n  🏁 [点赞模块] 已连续发现 {MAX_CONSECUTIVE_INVALID_ARTICLES} 个无效ID，本轮扫描正常结束。")
