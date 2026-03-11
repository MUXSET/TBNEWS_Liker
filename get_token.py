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

            import platform
            system_os = platform.system()
            if system_os == "Darwin":
                ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
            elif system_os == "Windows":
                ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
            else:
                ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"

            context = await browser.new_context(
                user_agent=ua,
                ignore_https_errors=True
            )
            page = await context.new_page()

            logger.info("🌐 [Token] 页面加载中...")
            await page.goto(LOGIN_URL, timeout=60000)
            await page.locator(".user-name").click()
            await page.locator("#email").fill(username)
            await page.locator("#password").fill(password)
            await page.locator("#log-btn").click()
            logger.info("✅ [Token] 登录信息已提交，等待跳转...")

            # 关键修复：等待登录后页面完全加载
            try:
                await page.wait_for_load_state('load', timeout=30000)
                logger.info("✅ [Token] 登录后页面已加载。")
            except PlaywrightTimeoutError:
                logger.warning("⚠️ [Token] 登录后页面 load 事件超时，继续尝试...")
                
            # 重大修复: 补回登录后显式等待时间，确保会话/SSO等后台握手初始化完成，否则直接请求子API会被拒绝跳转
            await page.wait_for_timeout(3000)

            # 关键修复1：绕过不稳定且可能为空的门户 iframe 和新闻卡片
            # 直接构造官方接口的新闻列表 URL
            import urllib.parse
            import config_manager
            
            logger.info("🔍 [Token] 正在构造统一的新闻列表入口以绕过首页 UI...")
            channels = config_manager.get_channels()
            # 使用用户常扫的第一个频道作保障，若没配置则使用默认的特变资讯频道
            ch_id = channels[0]['id'] if channels else "XT-2bb8a866-d2a3-47da-bbad-8c63db21e9b6"
            
            content_src = f'[{{"title":"","ids":["{ch_id}"]}}]'
            encoded_src = urllib.parse.quote(content_src)
            list_url = f"https://ejia.tbea.com/pubacc-front/article/list?contentSource={encoded_src}"
            
            try:
                await page.goto(list_url, timeout=30000)
                # 等待页面最初始响应
            except Exception as e:
                logger.warning(f"⚠️ [Token] 跳转列表时遇到网络波动: {e}")

            logger.info("🔍 [Token] 正在等待列表界面的文章元素...")
            try:
                # 不再依赖不可靠的页面 load 或 networkidle 状态，只认具体 DOM 元素
                await page.wait_for_selector("(//li[@class='article-item'])[1]", state="visible", timeout=30000)
                logger.info("✅ [Token] 找到可用文章链接。")
            except PlaywrightTimeoutError:
                logger.error("❌ [Token] 新闻列表内找不到文章 (可能该频道确实暂无推送)。")
                await browser.close()
                return None

            try:
                # 关键修复4: 移除 target="_blank" 以防止新标签页拦截，并在页面上下文中直接执行点击
                logger.info("🔍 [Token] 点击文章触发 SSO 跳转...")
                locator = page.locator("(//li[@class='article-item'])[1]")
                
                # 确保元素可交互后再执行 JS
                await locator.wait_for(state="visible", timeout=10000)
                # 等待 1.5 秒，防止前端框架(Vue/React)尚未绑定好 href 或点击事件
                await page.wait_for_timeout(1500) 
                
                await locator.evaluate("""
                    node => {
                        let a = node.querySelector('a');
                        if(a) a.removeAttribute('target');
                        node.click();
                    }
                """)
                
                # 等待跳转到包含 tbeanews 的具体文章页面（携带有 ticket）
                # Relaxed to "commit" instead of default "load" to prevent timeouts if the heavy news page stalls
                await page.wait_for_url("**/tbeanews.tbea.com/**", wait_until="commit", timeout=15000)
                logger.info(f"✅ [Token] SSO 跳转成功!")
            except Exception as e:
                logger.warning(f"⚠️ [Token] 跳转过程遇到阻碍 (这可能不影响 Cookie 库获取): {e}")
                
            logger.info("🔍 [Token] 正在轮询捕获认证凭据 (tbea_art_token)...")
            
            # 关键修复2：使用长轮询代替脆弱的 await networkidle (如果开了新标签页不阻断)
            token_value = None
            all_cookies = []
            for _ in range(30):
                all_cookies = await context.cookies()
                token_cookie = next((c for c in all_cookies if c['name'] == 'tbea_art_token'), None)
                if token_cookie:
                    logger.info("✅ [Token] 捕获成功！")
                    token_value = token_cookie['value']
                    # 等待一下确保所有相关 cookie 落盘
                    await page.wait_for_timeout(1000)
                    all_cookies = await context.cookies()
                    break
                await page.wait_for_timeout(1000)
            
            # 提取 ejia cookies (供 IM API / checkLogin 使用)
            ejia_cookie_names = [
                'JSESSIONID', 'toweibologin', 'gl', 'ERPPRD', 'cd', 'cn', 'cu', 
                'at', '__loginType', 'uuid', 'webLappToken', 'sync_networkid', 'sync_userid',
                'redirectIndexUrl'
            ]
            ejia_cookies = {c['name']: c['value'] for c in all_cookies if c['name'] in ejia_cookie_names}

            # 现在的 pubacc_v2 接口不再需要真实的 IM userId，
            # 仅仅保留 cu cookie 作为占位符，以防其他旧接口还需要
            im_user_id = ejia_cookies.get('cu', '')

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

