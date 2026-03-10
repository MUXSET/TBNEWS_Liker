# =================================================================
#  channel_sweep.py
#  Version: 1.0.0
#  Description: 频道扫描点赞模块（统一版）。
#               替代 monthly_sweep.py 和 liker.py，支持自定义日期范围。
#               通过 IM 消息 API 拉取目标频道文章，结合本地缓存
#               跳过已赞文章，对未赞文章执行点赞。
# =================================================================

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import re
from datetime import datetime, timedelta
import threading
from typing import List, Dict, Tuple, Optional
from logger import logger
import config_manager
import liked_cache

IM_MESSAGE_API_URL = "https://ejia.tbea.com/im/rest/message/listMessage"
CHECK_LOGIN_URL = "https://ejia.tbea.com/space/c/rest/user/checkLogin"
ARTICLE_DETAIL_API_URL = "https://tbeanews.tbea.com/api/article/detail"
LIKE_API_URL = "https://tbeanews.tbea.com/api/article/addDigg"

class CookiesExpiredError(Exception):
    """当 IM API 返回 401 时抛出，通知调用者需要刷新 Cookies"""
    pass

def _extract_articles_from_messages(messages: list) -> List[Dict]:
    """从 IM 消息列表中提取文章信息 (去重)"""
    articles = []
    seen_ids = set()
    
    for msg in messages:
        send_time = msg.get("sendTime", "")
        param = msg.get("param", {})
        
        if msg.get("msgType") != 6:
            continue
            
        items = param.get("list", [])
        if not items:
            url = param.get("url", "")
            m = re.search(r'id=(\d+)', url)
            if m:
                art_id = int(m.group(1))
                if art_id not in seen_ids:
                    seen_ids.add(art_id)
                    articles.append({
                        "id": art_id,
                        "title": param.get("title", param.get("text", "")),
                        "send_time": send_time,
                    })
        else:
            for item in items:
                url = item.get("url", "")
                m = re.search(r'id=(\d+)', url)
                if m:
                    art_id = int(m.group(1))
                    if art_id not in seen_ids:
                        seen_ids.add(art_id)
                        articles.append({
                            "id": art_id,
                            "title": item.get("title", item.get("text", "")),
                            "send_time": send_time,
                        })
    return articles

def _get_channel_articles(session: requests.Session, group_id: str,
                          start_date: str, end_date: str) -> List[Dict]:
    """
    获取指定频道、指定日期范围的推送文章。
    start_date/end_date 格式: "YYYY-MM-DD"
    """
    all_articles = []
    msg_id = ""
    
    for page in range(15):  # 最多翻 15 页
        data = {
            "groupId": group_id,
            "userId": "",
            "type": "new" if page == 0 else "old",
            "count": 20,
            "msgId": msg_id,
        }
        
        try:
            r = session.post(IM_MESSAGE_API_URL, data=data, timeout=15)
            
            if r.status_code == 401:
                raise CookiesExpiredError("IM Session Cookies 已过期 (401)")
            
            r.raise_for_status()
            resp = r.json()
            resp_data = resp.get("data", {})
            messages = resp_data.get("list", [])
            has_more = resp_data.get("more", False)
            
            if not messages:
                break
                
            page_articles = _extract_articles_from_messages(messages)
            
            # 过滤日期范围内的文章
            for a in page_articles:
                send_date = a["send_time"][:10]  # "YYYY-MM-DD"
                if start_date <= send_date <= end_date:
                    all_articles.append(a)
            
            # 如果所有消息都早于开始日期，停止翻页
            earliest_date = min((a["send_time"][:10] for a in page_articles), default="9999")
            if earliest_date < start_date:
                break
                
            if not has_more:
                break
                
            msg_id = messages[-1].get("msgId", "")
            time.sleep(0.5)
            
        except CookiesExpiredError:
            raise
        except Exception as e:
            logger.error(f"❌ [频道扫描] 获取频道历史消息失败: {e}")
            break
            
    return all_articles

def run_sweep(start_date: str = None, end_date: str = None,
              stop_event: threading.Event = None) -> Tuple[int, int, int]:
    """
    执行频道文章扫描点赞。
    
    Args:
        start_date: 起始日期 "YYYY-MM-DD"，默认本月1号
        end_date: 结束日期 "YYYY-MM-DD"，默认今天
        stop_event: 停止信号
    
    Returns:
        (总文章数, 新点赞数, 跳过数)
        总文章数=-1 表示 Cookies 过期
    """
    # 默认日期范围: 本月
    if not start_date:
        start_date = datetime.now().strftime("%Y-%m-01")
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")
    
    logger.info(f"🔄 [频道扫描] 扫描日期范围: {start_date} ~ {end_date}")
    
    # 1. 验证凭证
    tbea_token = config_manager.get_token()
    ejia_cookies = config_manager.get_ejia_cookies()
    user_id = config_manager.get_ejia_user_id()
    
    if not tbea_token or not ejia_cookies or not user_id:
        logger.error("❌ [频道扫描] 凭据不足，请先更新 Token。")
        return 0, 0, 0

    # 先探测 Cookies 是否存活
    try:
        probe = requests.post(CHECK_LOGIN_URL, cookies=ejia_cookies,
                              headers={"Content-Length": "0"}, timeout=10)
        if probe.status_code == 401:
            logger.warning("⚠️ [频道扫描] IM Session 已过期，需要重新登录。")
            return -1, 0, 0
    except Exception:
        pass
    
    target_channels = config_manager.get_channels()
    
    # 2. 准备 Sessions
    retry = Retry(connect=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    
    im_session = requests.Session()
    im_session.mount('https://', adapter)
    im_session.cookies.update(ejia_cookies)
    im_session.headers.update({
        "User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://ejia.tbea.com", "Referer": "https://ejia.tbea.com/im/xiaoxi/",
    })
    
    news_session = requests.Session()
    news_session.mount('https://', adapter)
    news_session.headers.update({"User-Agent": "Mozilla/5.0", "token": tbea_token})

    # 3. 收集文章
    all_articles = []
    
    try:
        for ch in target_channels:
            if stop_event and stop_event.is_set():
                logger.info("⏹️ [频道扫描] 收到停止信号。")
                return 0, 0, 0
                
            group_id = f"XT-{user_id}-{ch['id']}"
            logger.info(f"📡 [频道扫描] 拉取频道 [{ch['name']}]...")
            arts = _get_channel_articles(im_session, group_id, start_date, end_date)
            all_articles.extend(arts)
            logger.info(f"    ↳ {len(arts)} 篇文章")
    except CookiesExpiredError:
        logger.warning("⚠️ [频道扫描] Cookies 已过期。")
        return -1, 0, 0
        
    # 全局去重
    unique = list({a['id']: a for a in all_articles}.values())
    unique.sort(key=lambda x: x['send_time'])
    
    total = len(unique)
    logger.info(f"📋 [频道扫描] 共 {total} 篇文章（去重后），开始检查点赞状态...")
    
    if total == 0:
        logger.info("ℹ️ [频道扫描] 暂无文章需要处理。")
        return 0, 0, 0
        
    # 4. 逐个处理
    liked_count = 0
    skipped_count = 0
    
    for art in unique:
        if stop_event and stop_event.is_set():
            logger.info("⏹️ [频道扫描] 收到停止信号。")
            break
            
        art_id = art['id']
        title = art['title'][:20]
        display = f"「{title}」(ID:{art_id})"
        
        # 先查本地缓存
        if liked_cache.is_liked(art_id):
            logger.info(f"💨 [频道扫描] 本地已记录，跳过: {display}")
            skipped_count += 1
            continue
        
        # 查 API 确认
        try:
            detail_res = news_session.get(ARTICLE_DETAIL_API_URL, params={'id': art_id}, timeout=10)
            detail_res.raise_for_status()
            d_data = detail_res.json()
            
            if d_data.get('code') == 1 and d_data.get('data'):
                is_digg = d_data['data'].get("is_digg", True)
                if is_digg:
                    logger.info(f"⏭️ [频道扫描] 服务端已赞，跳过: {display}")
                    # 服务端确认已赞 → 安全写入缓存
                    liked_cache.mark_liked(art_id)
                    skipped_count += 1
                else:
                    logger.info(f"🌟 [频道扫描] 发现漏赞，点赞中: {display}")
                    like_res = news_session.post(LIKE_API_URL, json={"id": str(art_id)}, timeout=10)
                    like_data = like_res.json()
                    
                    if like_data.get("code") == 1:
                        # ✅ API 确认点赞成功 → 写入缓存
                        liked_cache.mark_liked(art_id)
                        logger.info(f"✅ [频道扫描] {display} 点赞成功！")
                        liked_count += 1
                    elif "重复点赞" in like_data.get('msg', ''):
                        # 重复点赞也算成功
                        liked_cache.mark_liked(art_id)
                        logger.info(f"✅ [频道扫描] {display} 已点赞（重复确认）")
                        skipped_count += 1
                    else:
                        logger.error(f"❌ [频道扫描] {display} 点赞失败: {like_data.get('msg')}")
            else:
                logger.warning(f"⚠️ [频道扫描] 无法获取文章详情: {art_id}")
                
        except Exception as e:
            logger.error(f"❌ [频道扫描] 处理 {display} 时网络错误: {e}")
            
        time.sleep(1.0)
        
    logger.info(f"🎉 [频道扫描] 完成！共 {total} 篇: 新点赞 {liked_count}，跳过 {skipped_count}。")
    logger.info(f"💾 [频道扫描] 本地缓存已记录 {liked_cache.get_cache_size()} 篇文章。")
    
    config_manager.save_sweep_stats(total, liked_count, skipped_count)
    
    return total, liked_count, skipped_count
