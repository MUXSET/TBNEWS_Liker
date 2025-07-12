# 文件名: get_token_playwright.py
# 版本: 3.0 (Playwright 核心版)
# 描述: 放弃 Selenium，全面转向使用 Playwright。
#      利用其更底层的控制能力，从根源上解决原生弹窗问题。

import time
import json
import os
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

CONFIG_FILE = "config.json"
LOGIN_URL = "https://ejia.tbea.com/"


def get_token_with_playwright():
    """
    使用 Playwright 进行浏览器自动化，以获取 token。
    """
    print("🔄 [Token模块] 正在启动 Playwright 流程 (v3.0)...")

    # 1. 加载凭据 (逻辑不变)
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            creds = config.get("credentials")
            if not creds or not creds.get("username"):
                print("❌ [Token模块] 未找到凭据。")
                return False
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"❌ [Token模块] 配置文件 '{CONFIG_FILE}' 不存在或格式错误。")
        return False

    try:
        with sync_playwright() as p:
            # 启动浏览器。headless=False 可以在调试时看到界面
            # args 参数可以用来禁用我们之前尝试过的功能，作为双保险
            browser = p.chromium.launch(
                headless=False,
                args=["--disable-features=PasswordLeakDetection"]
            )

            # 创建一个浏览器上下文，可以理解为一个独立的浏览器会话
            context = browser.new_context()
            page = context.new_page()
            page.set_viewport_size({"width": 1920, "height": 1080})

            print("...浏览器已启动（Playwright模式），请观察屏幕。")

            print(f"...正在导航到: {LOGIN_URL}")
            page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30000)

            print("...正在切换到'帐号登录'模式")
            page.locator(".user-name").click()

            print("...正在自动填充登录信息")
            page.locator("#email").fill(creds["username"])
            page.locator("#password").fill(creds["password"])

            print("...正在自动点击登录")
            page.locator("#log-btn").click()

            print("✅ [Token模块] 自动登录指令已发送。")

            print("\n👍 登录成功确认中... 正在进入内容区...")
            # 等待 iframe 加载完成
            iframe_element = page.wait_for_selector("iframe", timeout=30000)
            frame = iframe_element.content_frame()

            print("🖱️ 正在点击'新闻资讯'的'更多'按钮...")
            more_button_xpath = "//span[@title='新闻资讯']/ancestor::div[contains(@class, 'card-component')]//div[contains(@class, 'card-header-button')]"

            # 使用 expect_popup() 来优雅地处理新窗口的打开
            with page.expect_popup() as popup_info:
                frame.locator(more_button_xpath).click()

            news_page = popup_info.value
            news_page.wait_for_load_state()  # 等待新页面加载完成
            print(f"🪟 已成功切换到新窗口: {news_page.title()}")

            print("📰 正在点击第一篇文章...")
            first_article_xpath = "(//li[@class='article-item'])[1]"
            news_page.locator(first_article_xpath).click()

            print("⏳ 正在等待 'tbea_art_token' 被设置...")
            # 等待直到 cookie 出现
            start_time = time.time()
            token_value = None
            while time.time() - start_time < 30:  # 最多等30秒
                cookies = context.cookies()
                for cookie in cookies:
                    if cookie['name'] == 'tbea_art_token':
                        token_value = cookie['value']
                        break
                if token_value:
                    break
                time.sleep(0.5)

            if not token_value:
                raise Exception("'tbea_art_token' 在30秒内未能成功设置！")

            print("✅ 'tbea_art_token' 已成功设置！")

            config["tokens"] = {"tbea_art_token": token_value}
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)

            print("\n" + "*" * 60)
            print(f"🎉 Playwright 成功！Token已成功捕获！")
            print("*" * 60)

            print("...程序将在5秒后关闭浏览器。")
            time.sleep(5)
            browser.close()
            return True

    except Exception as e:
        print(f"\n❌ Playwright 操作失败: {e}")
        # Playwright 也可以截图
        # page.screenshot(path="error_screenshot_playwright.png")
        return False

