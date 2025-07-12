# =================================================================
#  liker.py
#  Version: 0.5
#  Author: MUXSET
#  Description: 自动扫描点赞专家模块。
#               融合了自动扫描、断点续传、智能暂停的健壮逻辑。
# =================================================================

import requests
import time
import json
import os

# --- 模块配置 ---
CONFIG_FILE = "config.json"  # 从此文件读取自动获取的Token
PROGRESS_FILE = "liker_progress_v0.5.json"  # 独立的进度文件
INITIAL_SCAN_START_ID = 8141
MAX_CONSECUTIVE_INVALID_ARTICLES = 15
ARTICLE_DETAIL_API_URL = "https://tbeanews.tbea.com/api/article/detail"
LIKE_API_URL = "https://tbeanews.tbea.com/api/article/addDigg"


def _load_progress():
    """从进度文件加载最后一个成功点赞的ID。"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                return int(data.get("last_liked_id", INITIAL_SCAN_START_ID - 1))
            except (json.JSONDecodeError, ValueError):
                return INITIAL_SCAN_START_ID - 1
    return INITIAL_SCAN_START_ID - 1


def _save_progress(liked_id):
    """将最新的、成功点赞的ID写入进度文件。"""
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_liked_id": int(liked_id)}, f, indent=4)
    print(f"💾 [点赞模块] 进度已保存: 最后一个成功点赞的ID是 {liked_id}。")


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
    payload = {"id": str(article_id)}

    try:
        response = session.post(LIKE_API_URL, headers=headers, data=json.dumps(payload), timeout=15)
        response.raise_for_status()
        data = response.json()

        if data.get("code") == 1 or "重复点赞" in data.get('msg', ''):
            print(f"✅ [点赞模块] 文章ID {article_id} 点赞成功 (或已点赞)。")
            return True
        else:
            print(f"❌ [点赞模块] 文章ID {article_id} 点赞失败: {data.get('msg', '未知错误')}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ [点赞模块] 点赞文章 {article_id} 时网络错误: {e}")
        return False


def main():
    """模块主函数：执行一轮完整的文章扫描和点赞流程。"""
    print("\n" + "---" * 10)
    print("👍 [点赞模块] 开始执行自动扫描点赞任务...")

    token = _get_token_from_config()
    if not token:
        print(f"❌ [点赞模块] 致命错误: 未在'{CONFIG_FILE}'中找到Token。请先运行 [1] 获取/更新 Token。")
        return

    session = requests.Session()
    last_liked_id = _load_progress()
    current_id = last_liked_id + 1
    consecutive_invalid_count = 0

    print(f"▶️ [点赞模块] 扫描起点: ID {current_id}")

    while consecutive_invalid_count < MAX_CONSECUTIVE_INVALID_ARTICLES:
        print(f"\n🔎 [点赞模块] 正在处理ID: {current_id}...")
        try:
            # 1. 检查文章是否存在
            api_headers = {"token": token}
            response = session.get(ARTICLE_DETAIL_API_URL, params={'id': current_id}, headers=api_headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            # 2. 如果文章有效
            if data.get('code') == 1 and data.get('data'):
                print(f"  ↳ 发现有效文章: {data['data'].get('title', 'N/A')}")
                consecutive_invalid_count = 0

                # 3. 尝试点赞
                if _perform_like(session, current_id, token):
                    _save_progress(current_id)  # 仅在点赞成功时保存进度
                else:
                    print("  ↳ 关键操作(点赞)失败，中止本轮任务以便下次重试。")
                    break

                    # 4. 如果文章无效
            else:
                print(f"  ↳ 无效ID。 (连续无效计数: {consecutive_invalid_count + 1}/{MAX_CONSECUTIVE_INVALID_ARTICLES})")
                consecutive_invalid_count += 1

        except requests.exceptions.RequestException as e:
            print(f"  ↳ 检查ID {current_id} 时发生网络错误: {e}。中止任务。")
            break

        current_id += 1
        time.sleep(0.5)

    if consecutive_invalid_count >= MAX_CONSECUTIVE_INVALID_ARTICLES:
        print(f"\n🏁 [点赞模块] 已连续发现 {MAX_CONSECUTIVE_INVALID_ARTICLES} 个无效ID，本轮扫描正常结束。")
    else:
        print("\n⏹️ [点赞模块] 本轮扫描因错误提前中止，下次将从失败处重试。")
    print("---" * 10)


if __name__ == '__main__':
    main()
