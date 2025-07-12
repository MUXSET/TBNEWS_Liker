# E+新闻全自动点赞工具 v0.9.1-pre

![版本](https://img.shields.io/badge/version-0.9.1--pre-yellow.svg)![语言](https://img.shields.io/badge/language-Python-green.svg)![作者](https://img.shields.io/badge/author-MUXSET-orange.svg)![协议](https://img.shields.io/badge/license-MIT-lightgrey.svg)

> **⚠️ 注意：这是一个预发布测试版 (Pre-release)**
> 当前版本的主要目标是测试 **`.exe` 可执行程序的兼容性** 以及 **并发死锁修复的稳定性**。欢迎大家下载试用并提供反馈，但它可能包含未知的 Bug。

**E+新闻全自动点赞工具** 是一款由 MUXSET 开发（借助AI工具，嗯没错，这个README也是AI写的，AI真好用！)，专为 TBEA E+ 新闻平台设计的稳定、可靠的自动化文章扫描与点赞工具。它被精心设计为无人值守模式，能够7x24小时自动执行任务，并智能处理Token过期问题。

## ✨ 核心功能

*   **🚀 全自动任务**：在后台自动执行“扫描点赞”和“刷新Token”两个核心任务。
*   **🧠 智能Token管理**：在执行任务前自动检查Token有效性，若失效则调用浏览器模块自动获取新Token，实现无缝衔接。
*   **⚙️ 健壮的并发控制 (v0.9.1 核心修复)**：采用 `threading.RLock` 替代 `Lock`，彻底解决了在“扫描时自动更新Token”等嵌套场景下可能发生的死锁问题，确保长期运行的绝对稳定性。
*   **友好交互界面**：清晰的命令行菜单和状态仪表盘，让用户对程序状态一目了然。
*   **📝 外部化配置**：所有用户凭据和设置都存储在 `config.json` 文件中，与代码完全分离。
*   **💾 进度持久化**：点赞进度会自动保存在 `liker_progress.json` 文件中，即使程序重启也能从上次的位置继续扫描。
*   **💻 跨平台支持**：可在 Windows, macOS, 和 Linux 系统上运行。

## 🏗️ 项目架构 (v0.9.x 系列)

v0.9.x系列遵循“高内聚、低耦合”的设计原则，将项目拆分为多个职责分明的模块：

*   `run.py`: **应用主入口与编排器**。负责整合所有模块，处理顶层用户交互，是整个应用的总指挥。
*   `config_manager.py`: **配置中心**。唯一负责 `config.json` 的读写，为其他模块提供统一的配置访问接口。
*   `ui_manager.py`: **用户界面层**。专门处理所有控制台的输入输出（菜单、仪表盘、提示信息），将UI与业务逻辑完全分离。
*   `task_manager.py`: **后台任务调度器**。封装了所有与线程、定时、锁相关的复杂逻辑，负责启动和管理后台任务。
*   `get_token.py`: **Token获取模块**。一个独立的、通过Selenium驱动无头浏览器获取Token的功能提供者。
*   `liker.py`: **点赞执行模块**。一个独立的、通过requests库执行文章扫描和点赞的功能提供者。

## 🛠️ 安装与准备 (从源码运行)

在开始之前，请确保您的系统已安装以下环境：

1.  **Python 3.7+**
2.  **Pip** (Python包管理器)
3.  **Microsoft Edge** 浏览器

### 安装步骤

1.  **克隆仓库**
    ```bash
    git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git
    cd YOUR_REPOSITORY_NAME
    ```

2.  **创建 `requirements.txt` 文件**
    ```text
    requests
    selenium
    webdriver-manager
    ```

3.  **安装依赖**
    ```bash
    pip install -r requirements.txt
    ```

## 🚀 如何使用

请参考最新的 [Release 页面](https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME/releases) 下载 `.exe` 可执行程序，或按照上述步骤从源码运行。

## 🔍 问题排查

*   **WebDriver或浏览器错误**:
    *   请确保您的 **Microsoft Edge 浏览器**已正确安装并且可以正常打开。
    *   `webdriver-manager` 库会自动下载匹配您浏览器版本的驱动。请确保您的网络连接正常。

*   **登录失败或Token获取失败**:
    *   首先检查您在 `config.json` 中配置的 `username` 和 `password` 是否完全正确。
    *   程序在自动化失败时会生成 `token_error.png` 截图，可用于帮助定位问题。

## 📜 开源协议

本项目采用 [MIT License](LICENSE) 开源协议。
