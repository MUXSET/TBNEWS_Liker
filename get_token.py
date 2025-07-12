# =================================================================
#  get_token.py
#  Version: 0.5
#  Author: MUXSET
#  Description: 令牌获取专家模块。
#               职责：自动化操作Edge浏览器，捕获并保存tbea_art_token。
# =================================================================

import json
import time
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.microsoft import EdgeChromiumDriverManager

# --- 模块配置 ---
LOGIN_URL = "https://ejia.tbea.com/"
CONFIG_FILE = "config.json"


def main():
    """模块主函数：执行完整的Token捕获流程。"""
    print("🚀 [Token模块] 正在初始化Edge浏览器...")
    service = Service(EdgeChromiumDriverManager().install())
    driver = webdriver.Edge(service=service)
    driver.maximize_window()

    try:
        driver.get(LOGIN_URL)

        print("\n" + "=" * 60)
        print("下一步操作：")
        print("1. 请在弹出的Edge浏览器中手动完成登录。")
        print("2. 登录成功看到主界面后，回到本窗口按【回车键】。")
        input("=" * 60 + "\n")

        wait = WebDriverWait(driver, 40)
        main_window_handle = driver.current_window_handle

        # 1. 进入iframe，点击"更多"
        print("👍 [Token模块] 登录已确认，正在进入内容区...")
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.TAG_NAME, "iframe")))

        print("🖱️ [Token模块] 正在点击'新闻资讯'的'更多'按钮...")
        more_button_xpath = "//span[@title='新闻资讯']/ancestor::div[contains(@class, 'card-component')]//div[contains(@class, 'card-header-button')]"
        more_button = wait.until(EC.element_to_be_clickable((By.XPATH, more_button_xpath)))
        more_button.click()

        # 2. 切换到新窗口
        print("🪟 [Token模块] 正在切换到新闻列表窗口...")
        driver.switch_to.default_content()
        wait.until(EC.number_of_windows_to_be(2))
        news_window_handle = [h for h in driver.window_handles if h != main_window_handle][0]
        driver.switch_to.window(news_window_handle)

        # 3. 点击第一篇文章
        print("📰 [Token模块] 正在点击第一篇文章...")
        first_article_xpath = "(//li[@class='article-item'])[1]"
        wait.until(EC.element_to_be_clickable((By.XPATH, first_article_xpath))).click()

        # 4. 核心步骤：等待 'tbea_art_token' Cookie 出现
        print("⏳ [Token模块] 等待文章页加载并设置关键Cookie...")
        wait.until(lambda d: d.get_cookie('tbea_art_token'))
        print("✅ [Token模块] 关键Cookie已捕获！")

        # 5. 提取并保存Token
        token_value = driver.get_cookie('tbea_art_token')['value']
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"tbea_art_token": token_value}, f, indent=4)

        print("\n" + "*" * 60)
        print(f"🎉 [Token模块] 成功！Token已保存至 '{CONFIG_FILE}'！")
        print("*" * 60)

    except Exception as e:
        print(f"\n❌ [Token模块] 操作失败: {e}")
    finally:
        time.sleep(2)
        driver.quit()
        print("✅ [Token模块] 浏览器已关闭。")


if __name__ == '__main__':
    main()
