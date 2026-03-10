# =================================================================
#  report_exporter.py
#  Version: 1.0.0
#  Author: MUXSET
#  Description: 月度报告导出模块。
#               拉取本月所有目标频道的文章，查询点赞状态，
#               生成 CSV 报告文件，方便应对月度抽查。
# =================================================================

import csv
import os
import time
import re
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime
from typing import List, Dict
from logger import logger
import config_manager

PUBACC_ARTICLE_API_URL = "https://ejia.tbea.com/pubacc_v2/api/card/getArticleList"
ARTICLE_DETAIL_API_URL = "https://tbeanews.tbea.com/api/article/detail"

def _fetch_channel_articles(im_session, channel_id, channel_name, target_month):
    """获取指定频道本月所有推送文章"""
    all_articles = []
    
    for page in range(1, 10):  # 最多翻 10 页
        data = {
            "ids": f'["{channel_id}"]',
            "source": "1",
            "pageIndex": str(page),
            "pageSize": "30" # 一次多拉取点
        }
        
        try:
            r = im_session.post(PUBACC_ARTICLE_API_URL, data=data, timeout=15)
            if r.status_code == 401:
                logger.error("❌ [报告导出] API Session 过期，无法生成报告。")
                return []
            
            r.raise_for_status()
            resp = r.json()
            
            if not resp.get("success", False) and str(resp.get("errorCode", "")) != "200":
                break
                
            articles_list = resp.get("data", [])
            if not articles_list:
                break
                
            page_articles = []
            for item in articles_list:
                art_id = None
                url = item.get("url", "")
                if url:
                    m = re.search(r'[?&]id=(\d+)', url)
                    if m:
                        art_id = int(m.group(1))
                        
                if not art_id:
                    continue  # 忽略提取不到纯数字ID记录的文章
                    
                title = item.get("title", "")
                
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
                        "channel": channel_name,
                        "send_time": str(send_time)
                    })
            
            # 过滤本月的文章
            for a in page_articles:
                if a["send_time"].startswith(target_month):
                    all_articles.append(a)
            
            # 如果所有消息都早于目标月份，停止翻页
            earliest_time = min((a["send_time"] for a in page_articles), default="9999")
            if earliest_time < target_month:
                break
                
            if len(articles_list) < 20:
                break
                
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"❌ [报告导出] 拉取频道 {channel_name} 失败: {e}")
            break
            
    return all_articles


def export_monthly_report(stop_event=None) -> str:
    """
    导出本月点赞报告为 CSV。
    返回: 生成的文件路径，失败返回空字符串。
    """
    logger.info("📊 [报告导出] 开始生成本月点赞报告...")
    
    tbea_token = config_manager.get_token()
    ejia_cookies = config_manager.get_ejia_cookies()
    
    if not tbea_token or not ejia_cookies:
        logger.error("❌ [报告导出] 凭据不足，无法生成报告。")
        return ""
    
    current_month = datetime.now().strftime("%Y-%m")
    channels = config_manager.get_channels()
    
    # 准备 Sessions
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
    
    # 收集所有文章
    all_articles = []
    for ch in channels:
        if stop_event and stop_event.is_set():
            return ""
        logger.info(f"📡 [报告导出] 拉取频道: {ch['name']}...")
        arts = _fetch_channel_articles(im_session, ch['id'], ch['name'], current_month)
        all_articles.extend(arts)
        logger.info(f"    ↳ {len(arts)} 篇")
    
    # 去重
    seen = set()
    unique = []
    for a in all_articles:
        if a['id'] not in seen:
            seen.add(a['id'])
            unique.append(a)
    unique.sort(key=lambda x: x['send_time'])
    
    logger.info(f"📋 [报告导出] 共 {len(unique)} 篇文章，正在查询点赞状态...")
    
    # 查询每篇的点赞状态
    for art in unique:
        if stop_event and stop_event.is_set():
            return ""
        try:
            r = news_session.get(ARTICLE_DETAIL_API_URL, params={'id': art['id']}, timeout=10)
            d = r.json()
            if d.get('code') == 1 and d.get('data'):
                art['is_digg'] = "✅ 已赞" if d['data'].get('is_digg') else "❌ 未赞"
            else:
                art['is_digg'] = "⚠️ 未知"
        except:
            art['is_digg'] = "⚠️ 查询失败"
        time.sleep(0.5)
    
    # 写入 CSV
    desktop = os.path.expanduser("~/Desktop")
    filename = f"E+月度点赞报告_{current_month}.csv"
    filepath = os.path.join(desktop, filename)
    
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(["文章ID", "标题", "来源频道", "推送日期", "点赞状态"])
        for art in unique:
            writer.writerow([
                art['id'], art['title'], art['channel'],
                art['send_time'][:10], art['is_digg']
            ])
    
    liked = sum(1 for a in unique if "已赞" in a.get('is_digg', ''))
    logger.info(f"🎉 [报告导出] 报告已生成！共 {len(unique)} 篇（已赞 {liked}）")
    logger.info(f"📁 [报告导出] 文件位置: {filepath}")
    return filepath
