# =================================================================
#  get_token.py
#  Version: 0.9.1
#  Author: MUXSET
#  Description: Token获取模块 (重构版)。
#               通过函数接收凭据，执行自动化流程，并返回获取到的Token。
#               不再直接读写配置文件，实现与配置模块的解耦。
# =================================================================

import os
import time
from typing import Optional
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.microsoft import EdgeChromiumDriverManager

LOGIN_URL = "https://ejia.tbea.com/"


def get_new_token(username: str, password: str) -> Optional[str]:
    """
    执行完整的无头浏览器Token捕获流程。
    参数:
        username (str): 登录账号。
        password (str): 登录密码。
    返回:
        str: 成功时返回获取到的Token字符串。
        None: 失败时返回None。
    """
    print("  [Token] 正在启动无头浏览器...")
    if not username or not password:
        print("  [Token] ❌ 错误: 未提供有效的凭据。")
        return None

    edge_options = EdgeOptions()
    edge_options.add_argument("--headless")
    edge_options.add_argument("--disable-gpu")
    edge_options.add_argument("--window-size=1920,1080")
    edge_options.add_argument("--log-level=3")
    edge_options.add_experimental_option('excludeSwitches', ['enable-logging'])

    driver = None
    try:
        # 将webdriver日志输出重定向到os.devnull以保持控制台清洁
        service = Service(EdgeChromiumDriverManager().install(), log_output=os.devnull)
        driver = webdriver.Edge(service=service, options=edge_options)

        driver.get(LOGIN_URL)
        wait = WebDriverWait(driver, 40)
        print("  [Token] 页面加载中...")

        # --- 登录流程 ---
        wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "user-name"))).click()
        wait.until(EC.visibility_of_element_located((By.ID, "email"))).send_keys(username)
        wait.until(EC.visibility_of_element_located((By.ID, "password"))).send_keys(password)
        wait.until(EC.element_to_be_clickable((By.ID, "log-btn"))).click()
        print("  [Token] 登录信息已提交，等待跳转...")

        # --- 进入iframe并点击新闻 ---
        main_window_handle = driver.current_window_handle
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.TAG_NAME, "iframe")))
        time.sleep(3)  # 等待iframe内JS加载

        more_button_xpath = "//span[@title='新闻资讯']/ancestor::div[contains(@class, 'card-component')]//div[contains(@class, 'card-header-button')]"
        more_button = wait.until(EC.element_to_be_clickable((By.XPATH, more_button_xpath)))
        ActionChains(driver).move_to_element(more_button).click().perform()

        # --- 切换窗口并获取Token ---
        driver.switch_to.default_content()
        wait.until(EC.number_of_windows_to_be(2))
        news_window_handle = [h for h in driver.window_handles if h != main_window_handle][0]
        driver.switch_to.window(news_window_handle)

        first_article_xpath = "(//li[@class='article-item'])[1]"
        wait.until(EC.element_to_be_clickable((By.XPATH, first_article_xpath))).click()

        print("  [Token] 正在捕获关键Cookie...")
        wait.until(lambda d: d.get_cookie('tbea_art_token'))
        token_value = driver.get_cookie('tbea_art_token')['value']

        print(f"  [Token] ✅ 成功！已在浏览器中捕获Token。")
        return token_value

    except Exception as e:
        print(f"  [Token] ❌ 自动化操作失败: {e}")
        print("  [Token] ℹ️  可能原因: 凭据错误、网站结构变更或网络超时。")
        if driver:
            driver.save_screenshot("token_error.png")
            print("  [Token] ℹ️  已保存截图 'token_error.png' 供调试。")
        return None
    finally:
        if driver:
            driver.quit()
