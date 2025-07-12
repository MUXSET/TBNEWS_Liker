# =================================================================
#  liker.py
#  Version: 0.9
#  Author: MUXSET
#  Description: 文章扫描与点赞模块。
#               负责从断点处开始扫描文章，对有效文章执行点赞，
#               并记录进度。
# =================================================================

import requests
import time
import json
import os

# --- 模块常量 ---
CONFIG_FILE = "config.json"
PROGRESS_FILE = "liker_progress.json"
INITIAL_SCAN_START_ID = 8141
MAX_CONSECUTIVE_INVALID_ARTICLES = 15
ARTICLE_DETAIL_API_URL = "https://tbeanews.tbea.com/api/article/detail"
LIKE_API_URL = "https://tbeanews.tbea.com/api/article/addDigg"


def _load_progress():
    """从进度文件加载最后一个成功点赞的ID。"""
    if not os.path.exists(PROGRESS_FILE):
        return INITIAL_SCAN_START_ID - 1
    try:
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return int(json.load(f).get("last_liked_id", INITIAL_SCAN_START_ID - 1))
    except (json.JSONDecodeError, ValueError):
        return INITIAL_SCAN_START_ID - 1


def _save_progress(liked_id):
    """将最新的、成功点赞的ID写入进度文件。"""
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_liked_id": int(liked_id)}, f, indent=4)
    print(f"  [Liker] 💾 进度已保存: last_liked_id = {liked_id}")


def _get_token_from_config():
    """从主配置文件安全地加载Token。"""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("tbea_art_token")
    except (FileNotFoundError, json.JSONDecodeError):
        return None


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
            print(f"  [Liker] ✅ ID {article_id} 点赞成功 (或已点赞)。")
            return True
        else:
            print(f"  [Liker] ❌ ID {article_id} 点赞失败: {data.get('msg', '未知错误')}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"  [Liker] ❌ ID {article_id} 点赞时网络错误: {e}")
        return False


def main():
    """模块主入口：执行一轮完整的文章扫描和点赞流程。"""
    print("  [Liker] --- 开始本轮扫描点赞任务 ---")
    token = _get_token_from_config()
    if not token:
        print(f"  [Liker] ❌ 致命错误: 未找到Token，任务中止。")
        return

    session = requests.Session()
    current_id = _load_progress() + 1
    consecutive_invalid_count = 0
    print(f"  [Liker] ▶️ 扫描起点: ID {current_id}")

    while consecutive_invalid_count < MAX_CONSECUTIVE_INVALID_ARTICLES:
        try:
            # 1. 检查文章是否存在
            response = session.get(ARTICLE_DETAIL_API_URL, params={'id': current_id}, headers={"token": token},
                                   timeout=10)
            response.raise_for_status()
            data = response.json()

            # 2. 处理响应
            if data.get('code') == 1 and data.get('data'):
                print(f"  [Liker] 🔎 发现有效文章 ID {current_id}: {data['data'].get('title', 'N/A')[:30]}...")
                consecutive_invalid_count = 0
                if _perform_like(session, current_id, token):
                    _save_progress(current_id)
                else:
                    print("  [Liker] ⏹️ 关键操作(点赞)失败，中止本轮任务以便下次重试。")
                    break
            else:
                consecutive_invalid_count += 1
                print(
                    f"  [Liker] ...ID {current_id} 无效 (连续 {consecutive_invalid_count}/{MAX_CONSECUTIVE_INVALID_ARTICLES})")

        except requests.exceptions.RequestException as e:
            print(f"  [Liker] ❌ 检查ID {current_id} 时网络错误: {e}。中止任务。")
            break

        current_id += 1
        time.sleep(0.5)  # 避免请求过于频繁

    if consecutive_invalid_count >= MAX_CONSECUTIVE_INVALID_ARTICLES:
        print(f"\n  [Liker] 🏁 已连续发现 {MAX_CONSECUTIVE_INVALID_ARTICLES} 个无效ID，本轮扫描正常结束。")
    print("  [Liker] --- 本轮任务结束 ---")


if __name__ == '__main__':
    main()
