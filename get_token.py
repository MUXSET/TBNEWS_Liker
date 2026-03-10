# =================================================================
#  get_token.py
#  Version: 1.0.0 (Final Build)
#  Author: MUXSET
#  Description: Token获取模块 (完全异步版)。
#               - 采用定制化路径逻辑，完美支持安装包和便携版打包。
# =================================================================

import os
import sys
import glob
from typing import Optional
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from logger import logger

LOGIN_URL = "https://ejia.tbea.com/"


def _find_bundled_browser() -> Optional[str]:
    """在打包环境中自动查找 ms-playwright/ 下的 Chromium 可执行文件。"""
    import app_context
    browser_root = app_context.BROWSER_DATA_PATH

    if not os.path.isdir(browser_root):
        logger.error(f"❌ [Token] 未找到浏览器目录: {browser_root}")
        return None

    if sys.platform == 'darwin':
        # macOS: ms-playwright/chromium-*/chrome-mac-*/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing
        pattern = os.path.join(browser_root, 'chromium-*', 'chrome-mac-*',
                               'Google Chrome for Testing.app', 'Contents', 'MacOS',
                               'Google Chrome for Testing')
        matches = glob.glob(pattern)
    elif sys.platform == 'win32':
        # Windows: ms-playwright/chromium-*/chrome-win*/chrome.exe
        pattern = os.path.join(browser_root, 'chromium-*', 'chrome-win*', 'chrome.exe')
        matches = glob.glob(pattern)
    else:
        # Linux: ms-playwright/chromium-*/chrome-linux*/chrome
        pattern = os.path.join(browser_root, 'chromium-*', 'chrome-linux*', 'chrome')
        matches = glob.glob(pattern)

    if matches:
        logger.info(f"📦 [Token] 发现打包浏览器: {matches[0]}")
        return matches[0]

    logger.error(f"❌ [Token] 在 {browser_root} 中未找到 Chromium 可执行文件")
    return None


async def get_new_token(username: str, password: str) -> Optional[dict]:
    """
    使用Playwright执行完整的无头浏览器Token捕获流程 (异步版本)。
    提取 tbea_art_token 以及所有的 ejia session cookies 供 IM API 使用。
    此版本兼容直接运行、便携版和安装包环境。
    """
    logger.info("🛠️ [Token] 正在启动Playwright无头浏览器...")
    if not username or not password:
        logger.error("❌ [Token] 错误: 未提供有效的凭据。")
        return None

    try:
        async with async_playwright() as p:

            # ========================[ 核心路径逻辑：适配打包环境 ]========================
            executable_path = None

            if getattr(sys, 'frozen', False):
                executable_path = _find_bundled_browser()
                if not executable_path:
                    return None
            # ========================[ 核心路径逻辑：结束 ]==========================

            browser = await p.chromium.launch(
                headless=True,
                executable_path=executable_path  # 在打包时使用计算出的路径，开发时为None则使用默认
            )

            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            logger.info("🌐 [Token] 页面加载中...")
            await page.goto(LOGIN_URL, timeout=60000)
            await page.locator(".user-name").click()
            await page.locator("#email").fill(username)
            await page.locator("#password").fill(password)
            await page.locator("#log-btn").click()
            logger.info("✅ [Token] 登录信息已提交，等待跳转...")

            # Use a robust cross-platform way to find the specific iframe containing the news
            # Playwright's page.frames might return different counts based on load timing
            news_frame = page.frame_locator("iframe[src*='portal']")
            # Instead of matching exact text which might contain spaces/newlines or be translated,
            # we just click the header button on the news card directly.
            news_card_locator = news_frame.locator("div.card-component:has(span[title='新闻资讯'])")
            async with context.expect_page() as new_page_info:
                await news_card_locator.locator(".card-header-button").click()

            news_page = await new_page_info.value
            await news_page.wait_for_load_state()

            await news_page.locator("(//li[@class='article-item'])[1]").click()
            logger.info("🔍 [Token] 正在捕获关键Cookie...")
            await news_page.wait_for_load_state('networkidle', timeout=30000)

            all_cookies = await context.cookies()
            
            # 使用更简洁的方式查找Token
            token_value = next((c['value'] for c in all_cookies if c['name'] == 'tbea_art_token'), None)
            
            # 提取 ejia cookies (供 IM API / checkLogin 使用)
            ejia_cookie_names = [
                'JSESSIONID', 'toweibologin', 'gl', 'ERPPRD', 'cd', 'cn', 'cu', 
                'at', '__loginType', 'uuid', 'webLappToken', 'sync_networkid', 'sync_userid',
                'redirectIndexUrl'
            ]
            ejia_cookies = {c['name']: c['value'] for c in all_cookies if c['name'] in ejia_cookie_names}

            # 重要！提取 IM 专用的正确 userId
            # cookie 中的 'cu' 字段和 IM groupId 中的 userId 不同！
            # 必须从 IM 页面的 HTML 属性中提取。
            im_user_id = ejia_cookies.get('cu', '')
            try:
                logger.info("📡 [Token] 正在提取 IM 专用 userId...")
                # 尝试导航到 IM 页面取 data-groupid
                im_page_url = "https://ejia.tbea.com/im/xiaoxi/"
                await page.goto(im_page_url, timeout=30000)
                await page.wait_for_load_state('networkidle', timeout=15000)
                
                # 尝试从 iframe 或页面中找 data-groupid
                chat_name_el = page.locator('[data-groupid]').first
                if await chat_name_el.count() > 0:
                    data_gid = await chat_name_el.get_attribute('data-groupid')
                    if data_gid and data_gid.startswith('XT-'):
                        # 格式: XT-{userId}-XT-{channelId}
                        parts = data_gid.split('-XT-')
                        if len(parts) >= 2:
                            im_user_id = parts[0].replace('XT-', '')
                            logger.info(f"✅ [Token] 成功提取 IM userId: {im_user_id}")
            except Exception as e:
                logger.warning(f"⚠️ [Token] 无法从 IM 页面提取 userId，使用 cookie cu 值: {e}")

            await browser.close()

            if token_value:
                logger.info("✅ [Token] 成功！已在浏览器中捕获 Token 和会话 Cookies。")
                return {
                    "token": token_value,
                    "ejia_cookies": ejia_cookies,
                    "ejia_user_id": im_user_id
                }
            else:
                logger.error("❌ [Token] 操作完成，但未能在Cookie中找到'tbea_art_token'。")
                return None

    except PlaywrightTimeoutError:
        logger.error("❌ [Token] 自动化操作失败: 页面元素加载超时。")
        logger.info("ℹ️ [Token] 可能原因: 网站结构变更或网络极差。")
        return None
    except Exception as e:
        logger.error(f"❌ [Token] 自动化操作发生未知错误: {e}")
        logger.info("ℹ️ [Token] 可能原因: 凭据错误、网站结构变更或网络问题。")
        return None

