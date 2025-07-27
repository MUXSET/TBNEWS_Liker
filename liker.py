# =================================================================
#  liker.py
#  Version: 1.0.0
#  Author: MUXSET (Refactored by Senior Software Engineer)
#  Description: 自动扫描点赞专家模块。
#               从 app_context 获取标准路径，通过接收Token参数执行
#               扫描和点赞，实现了业务逻辑的完全分离。
# =================================================================

import requests
import time
import json
import os
from app_context import PROGRESS_FILE_PATH

INITIAL_SCAN_START_ID = 8141
MAX_CONSECUTIVE_INVALID_ARTICLES = 15
ARTICLE_DETAIL_API_URL = "https://tbeanews.tbea.com/api/article/detail"
LIKE_API_URL = "https://tbeanews.tbea.com/api/article/addDigg"

def _load_progress() -> int:
    if os.path.exists(PROGRESS_FILE_PATH):
        try:
            with open(PROGRESS_FILE_PATH, "r", encoding="utf-8") as f:
                return int(json.load(f).get("last_liked_id", INITIAL_SCAN_START_ID - 1))
        except (json.JSONDecodeError, ValueError, OSError):
            pass
    return INITIAL_SCAN_START_ID - 1

def _save_progress(liked_id: int):
    with open(PROGRESS_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump({"last_liked_id": liked_id}, f, indent=4)
    print(f"  💾 [点赞模块] 进度已保存: 最后一个成功点赞的ID是 {liked_id}。")

def _perform_like(session: requests.Session, article_id: int, token: str) -> bool:
    headers = {"token": token, "User-Agent": "Mozilla/5.0"}
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
            response = session.get(ARTICLE_DETAIL_API_URL, params={'id': current_id}, headers={"token": token}, timeout=10)
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
                print(f"  - [点赞模块] 无效ID {current_id} (连续 {consecutive_invalid_count}/{MAX_CONSECUTIVE_INVALID_ARTICLES})")

        except requests.exceptions.RequestException as e:
            print(f"  ↳ 检查ID {current_id} 时发生网络错误: {e}。中止任务。")
            break

        current_id += 1
        time.sleep(0.5)

    if consecutive_invalid_count >= MAX_CONSECUTIVE_INVALID_ARTICLES:
        print(f"\n  🏁 [点赞模块] 已连续发现 {MAX_CONSECUTIVE_INVALID_ARTICLES} 个无效ID，本轮扫描正常结束。")
