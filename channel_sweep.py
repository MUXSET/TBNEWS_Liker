# =================================================================
#  channel_sweep.py
#  Version: 2.1.0
#  Description: 频道扫描点赞模块（新通道版）。
#               改用全新的 pubacc_v2 公众号接口，免装配 groupId，
#               直接使用频道 ID 拉取文章列表，彻底解决 0 篇文章问题。
# =================================================================

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
from datetime import datetime
import threading
from typing import List, Dict, Tuple
from logger import logger
import config_manager
import liked_cache

PUBACC_ARTICLE_API_URL = "https://ejia.tbea.com/pubacc_v2/api/card/getArticleList"
CHECK_LOGIN_URL = "https://ejia.tbea.com/space/c/rest/user/checkLogin"
ARTICLE_DETAIL_API_URL = "https://tbeanews.tbea.com/api/article/detail"
LIKE_API_URL = "https://tbeanews.tbea.com/api/article/addDigg"

class CookiesExpiredError(Exception):
    """当 API 返回 401 时抛出，通知调用者需要刷新 Cookies"""
    pass

def _get_channel_articles(session: requests.Session, channel_id: str,
                          start_date: str, end_date: str) -> List[Dict]:
    """
    获取指定频道、指定日期范围的推送文章。
    start_date/end_date 格式: "YYYY-MM-DD"
    """
    all_articles = []
    
    for page in range(1, 20):  # 最多翻 20 页
        data = {
            "ids": f'["{channel_id}"]',
            "source": "1",
            "pageIndex": str(page),
            "pageSize": "20"
        }
        
        try:
            r = session.post(PUBACC_ARTICLE_API_URL, data=data, timeout=15)
            
            # PubAcc API 如果会话过期可能不直接 401，也可能返回特殊的 code，
            # 这里保守判断
            if r.status_code == 401:
                raise CookiesExpiredError("Session Cookies 已过期 (401)")
            
            r.raise_for_status()
            resp = r.json()
            # print(f"DEBUG resp: {resp}") # For manual debugging if needed
            if not resp.get("success", False) and str(resp.get("errorCode", "")) != "200":
                logger.error(f"❌ [频道扫描] API 返回异常状态: {resp.get('error')} | Raw: {str(resp)[:100]}")
                break
                
            # data 直接是个列表
            articles_list = resp.get("data", [])
            
            if not articles_list:
                break
                
            page_articles = []
            for item in articles_list:
                # pubacc_v2 返回的是 UUID (eg. 403ade1d-af2f-4eb6-b8dd-0e7ed13bde00)
                # 但 tbeanews API 需要的是纯数字 ID (eg. 11947)
                # 这个数字 ID 藏在 url 里: https://tbeanews.tbea.com/pc/show?id=11947&appid=...
                art_id = None
                url = item.get("url", "")
                if url:
                    import re
                    m = re.search(r'[?&]id=(\d+)', url)
                    if m:
                        art_id = int(m.group(1))
                
                # 如果没有提取到数字 ID，退而求其次用 UUID（虽然后续可能会报错）
                if not art_id:
                    art_id = item.get("id") or item.get("yzj_id")
                    
                title = item.get("title", "")
                
                # pubacc_v2 API 提供 publishTimeStamp (毫秒)
                pub_ts = item.get("publishTimeStamp") or item.get("sendTime")
                if pub_ts:
                    try:
                        send_time = datetime.fromtimestamp(pub_ts / 1000.0).strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        send_time = item.get("publishTime", "2000-01-01 00:00:00")
                else:
                    send_time = item.get("publishTime", "2000-01-01 00:00:00")
                
                if art_id and title:
                    page_articles.append({
                        "id": art_id,
                        "title": title,
                        "send_time": str(send_time)
                    })
            
            
            # 过滤日期范围内的文章
            for a in page_articles:
                send_date = a["send_time"][:10]  # "YYYY-MM-DD"
                if start_date <= send_date <= end_date:
                    all_articles.append(a)
            
            # 如果所有消息都早于开始日期，停止翻页
            earliest_date = min((a["send_time"][:10] for a in page_articles), default="9999")
            if earliest_date < start_date:
                break
                
            if len(articles_list) < 20:
                break
                
            time.sleep(0.5)
            
        except CookiesExpiredError:
            raise
        except Exception as e:
            logger.error(f"❌ [频道扫描] 获取频道历史文章失败: {e}")
            break
            
    return all_articles

def run_sweep(start_date: str = None, end_date: str = None,
              stop_event: threading.Event = None) -> Tuple[int, int, int]:
    """
    执行频道文章扫描点赞。
    
    Returns:
        (总文章数, 新点赞数, 跳过数)
        总文章数=-1 表示 Cookies 过期
    """
    if not start_date:
        start_date = datetime.now().strftime("%Y-%m-01")
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")
    
    logger.info(f"🔄 [频道扫描] 扫描日期范围: {start_date} ~ {end_date}")
    
    tbea_token = config_manager.get_token()
    ejia_cookies = config_manager.get_ejia_cookies()
    
    if not tbea_token or not ejia_cookies:
        logger.error("❌ [频道扫描] 凭据不足，请先更新 Token。")
        return 0, 0, 0

    try:
        probe = requests.post(CHECK_LOGIN_URL, cookies=ejia_cookies,
                              headers={"Content-Length": "0"}, timeout=10)
        if probe.status_code == 401:
            logger.warning("⚠️ [频道扫描] Session 已过期，需要重新登录。")
            return -1, 0, 0
    except Exception:
        pass
    
    target_channels = config_manager.get_channels()
    
    retry = Retry(connect=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    
    pub_session = requests.Session()
    pub_session.mount('https://', adapter)
    pub_session.cookies.update(ejia_cookies)
    pub_session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://ejia.tbea.com",
        "Referer": "https://ejia.tbea.com/im/xiaoxi/",
    })
    
    news_session = requests.Session()
    news_session.mount('https://', adapter)
    news_session.headers.update({"User-Agent": "Mozilla/5.0", "token": tbea_token})

    all_articles = []
    
    try:
        for ch in target_channels:
            if stop_event and stop_event.is_set():
                logger.info("⏹️ [频道扫描] 收到停止信号。")
                return 0, 0, 0
                
            ch_id = ch['id']  # 直接使用频道自身ID，不再需要拼接 userId
            logger.info(f"📡 [频道扫描] 拉取频道 [{ch['name']}]...")
            arts = _get_channel_articles(pub_session, ch_id, start_date, end_date)
            all_articles.extend(arts)
            logger.info(f"    ↳ 找到 {len(arts)} 篇对应日期范围文章")
    except CookiesExpiredError:
        logger.warning("⚠️ [频道扫描] Cookies 已过期。")
        return -1, 0, 0
        
    unique = list({a['id']: a for a in all_articles}.values())
    unique.sort(key=lambda x: x['send_time'])
    
    total = len(unique)
    logger.info(f"📋 [频道扫描] 共有 {total} 篇文章（去重后），开始检查点赞状态...")
    
    if total == 0:
        logger.info("ℹ️ [频道扫描] 暂无文章需要处理。")
        return 0, 0, 0
        
    liked_count = 0
    skipped_count = 0
    
    for art in unique:
        if stop_event and stop_event.is_set():
            logger.info("⏹️ [频道扫描] 收到停止信号。")
            break
            
        art_id = art['id']
        title = art['title'][:20]
        display = f"「{title}」(ID:{art_id})"
        
        if liked_cache.is_liked(art_id):
            logger.info(f"💨 [频道扫描] 本地已记录，跳过: {display}")
            skipped_count += 1
            continue
        
        try:
            detail_res = news_session.get(ARTICLE_DETAIL_API_URL, params={'id': art_id}, timeout=10)
            detail_res.raise_for_status()
            d_data = detail_res.json()
            
            if d_data.get('code') == 1 and d_data.get('data'):
                is_digg = d_data['data'].get("is_digg", True)
                if is_digg:
                    logger.info(f"⏭️ [频道扫描] 服务端已赞，跳过: {display}")
                    liked_cache.mark_liked(art_id)
                    skipped_count += 1
                else:
                    logger.info(f"🌟 [频道扫描] 发现漏赞，点赞中: {display}")
                    like_res = news_session.post(LIKE_API_URL, json={"id": str(art_id)}, timeout=10)
                    like_data = like_res.json()
                    
                    if like_data.get("code") == 1:
                        liked_cache.mark_liked(art_id)
                        logger.info(f"✅ [频道扫描] {display} 点赞成功！")
                        liked_count += 1
                    elif "重复" in like_data.get('msg', ''):
                        liked_cache.mark_liked(art_id)
                        logger.info(f"✅ [频道扫描] {display} 已点赞（重试响应）")
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
