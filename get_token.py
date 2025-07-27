# =================================================================
#  get_token.py
#  Version: 1.0.0
#  Author: MUXSET
#  Description: Token获取模块 (完全异步版)。
#               采用内部路径逻辑，确保在打包环境中能精确定位浏览器。
# =================================================================

import os
import sys
from typing import Optional
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

LOGIN_URL = "https://ejia.tbea.com/"


async def get_new_token(username: str, password: str) -> Optional[str]:
    """
    使用Playwright执行完整的无头浏览器Token捕获流程 (异步版本)。
    此版本兼容直接运行和文件夹模式打包环境。
    """
    print("  [Token] 正在启动Playwright无头浏览器...")
    if not username or not password:
        print("  [Token] ❌ 错误: 未提供有效的凭据。")
        return None

    try:
        async with async_playwright() as p:
            executable_path = None
            # --- 核心路径逻辑：在打包环境中，自动计算浏览器可执行文件路径 ---
            if getattr(sys, 'frozen', False):
                base_path = os.path.dirname(sys.executable)
                # 注意：这里的路径分隔符和文件夹名称需要与您打包时的一致
                executable_path = os.path.join(base_path, 'ms-playwright', 'chromium-1076', 'chrome-win', 'chrome.exe')
                if not os.path.exists(executable_path):
                    print(f"  [Token] ❌ 严重错误: 在打包目录中未找到浏览器: {executable_path}")
                    return None

            browser = await p.chromium.launch(
                headless=True,
                executable_path=executable_path  # 在打包时使用计算出的路径，开发时为None则使用默认
            )

            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            print("  [Token] 页面加载中...")
            await page.goto(LOGIN_URL, timeout=60000)
            await page.locator(".user-name").click()
            await page.locator("#email").fill(username)
            await page.locator("#password").fill(password)
            await page.locator("#log-btn").click()
            print("  [Token] 登录信息已提交，等待跳转...")

            news_frame = page.frame_locator("iframe")
            news_card_locator = news_frame.locator("div.card-component:has(span[title='新闻资讯'])")

            async with context.expect_page() as new_page_info:
                await news_card_locator.get_by_text("更多").click()

            news_page = await new_page_info.value
            await news_page.wait_for_load_state()

            await news_page.locator("(//li[@class='article-item'])[1]").click()
            print("  [Token] 正在捕获关键Cookie...")
            await news_page.wait_for_load_state('networkidle', timeout=30000)

            all_cookies = await context.cookies()
            token_value = next((c['value'] for c in all_cookies if c['name'] == 'tbea_art_token'), None)

            await browser.close()

            if token_value:
                print("  [Token] ✅ 成功！已在浏览器中捕获Token。")
                return token_value
            else:
                print("  [Token] ❌ 操作完成，但未能在Cookie中找到'tbea_art_token'。")
                return None

    except PlaywrightTimeoutError:
        print("  [Token] ❌ 自动化操作失败: 页面元素加载超时。")
        print("  [Token] ℹ️  可能原因: 网站结构变更或网络极差。")
        return None
    except Exception as e:
        print(f"  [Token] ❌ 自动化操作发生未知错误: {e}")
        print("  [Token] ℹ️  可能原因: 凭据错误、网站结构变更或网络问题。")
        return None
