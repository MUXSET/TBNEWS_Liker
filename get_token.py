# =================================================================
#  get_token.py
#  Version: 0.9
#  Author: MUXSET
#  Description: Token获取模块。
#               通过Selenium无头浏览器自动化登录流程，
#               捕获并更新配置文件中的'tbea_art_token'。
# =================================================================

import json
import time
import os
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.microsoft import EdgeChromiumDriverManager

# --- 模块常量 ---
LOGIN_URL = "https://ejia.tbea.com/"
CONFIG_FILE = "config.json"


def _load_credentials():
    """从配置文件加载用户名和密码。"""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            return config.get("username"), config.get("password")
    except (FileNotFoundError, json.JSONDecodeError):
        return None, None


def main():
    """模块主入口：执行完整的无头浏览器Token捕获流程。"""
    print("  [Token] 正在启动无头浏览器...")

    username, password = _load_credentials()
    if not username or not password:
        print(f"  [Token] ❌ 错误: 无法从'{CONFIG_FILE}'加载凭据。")
        return

    edge_options = EdgeOptions()
    edge_options.add_argument("--headless")
    edge_options.add_argument("--disable-gpu")
    edge_options.add_argument("--window-size=1920,1080")
    edge_options.add_argument("--log-level=3")  # 抑制不必要的日志
    edge_options.add_experimental_option('excludeSwitches', ['enable-logging'])

    try:
        service = Service(EdgeChromiumDriverManager().install(), log_output=os.devnull)
        driver = webdriver.Edge(service=service, options=edge_options)
    except Exception as e:
        print(f"  [Token] ❌ 无法初始化WebDriver: {e}")
        print("  [Token] ℹ️ 请确保已安装Edge浏览器且网络连接正常。")
        return

    try:
        driver.get(LOGIN_URL)
        wait = WebDriverWait(driver, 40)
        print("  [Token] 页面加载中...")

        # 登录流程
        wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "user-name"))).click()
        wait.until(EC.visibility_of_element_located((By.ID, "email"))).send_keys(username)
        wait.until(EC.visibility_of_element_located((By.ID, "password"))).send_keys(password)
        wait.until(EC.element_to_be_clickable((By.ID, "log-btn"))).click()
        print("  [Token] 登录信息已提交，等待跳转...")

        # 进入iframe并点击新闻
        main_window_handle = driver.current_window_handle
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.TAG_NAME, "iframe")))
        time.sleep(3)  # 等待JS加载

        more_button_xpath = "//span[@title='新闻资讯']/ancestor::div[contains(@class, 'card-component')]//div[contains(@class, 'card-header-button')]"
        more_button = wait.until(EC.element_to_be_clickable((By.XPATH, more_button_xpath)))
        ActionChains(driver).move_to_element(more_button).click().perform()

        # 切换窗口并获取Token
        driver.switch_to.default_content()
        wait.until(EC.number_of_windows_to_be(2))
        news_window_handle = [h for h in driver.window_handles if h != main_window_handle][0]
        driver.switch_to.window(news_window_handle)

        first_article_xpath = "(//li[@class='article-item'])[1]"
        wait.until(EC.element_to_be_clickable((By.XPATH, first_article_xpath))).click()

        print("  [Token] 正在捕获关键Cookie...")
        wait.until(lambda d: d.get_cookie('tbea_art_token'))
        token_value = driver.get_cookie('tbea_art_token')['value']

        # 更新配置文件
        with open(CONFIG_FILE, "r+", encoding="utf-8") as f:
            config_data = json.load(f)
            config_data["tbea_art_token"] = token_value
            f.seek(0)
            f.truncate()
            json.dump(config_data, f, indent=4, ensure_ascii=False)

        print(f"  [Token] ✅ 成功！Token已自动获取并更新至 '{CONFIG_FILE}'。")

    except Exception as e:
        print(f"  [Token] ❌ 自动化操作失败: {e}")
        print("  [Token] ℹ️  可能原因: 凭据错误、网站结构变更或网络超时。")
        driver.save_screenshot("token_error.png")
        print("  [Token] ℹ️  已保存截图 'token_error.png' 供调试。")
    finally:
        if 'driver' in locals():
            driver.quit()


if __name__ == '__main__':
    main()
