# E+新闻全自动点赞工具 v1.0.0

![版本](https://img.shields.io/badge/version-1.0.0-blue.svg)![语言](https://img.shields.io/badge/language-Python-green.svg)![作者](https://img.shields.io/badge/author-MUXSET-orange.svg)![协议](https://img.shields.io/badge/license-MIT-lightgrey.svg)

> **🎉 正式版发布！**
> 经过多个版本的迭代和重构，v1.0.0 标志着本项目进入了**首个官方稳定版**。此版本对底层架构进行了全面优化，根除了历史版本中存在的路径和权限问题，致力于提供极致的稳定性和可靠性。

**E+新闻全自动点赞工具** 是一款由 MUXSET 开发（AI 在此过程中提供了亿点点帮助），专为 TBEA E+ 新闻平台设计的稳定、可靠的自动化文章扫描与点赞工具。它被精心设计为无人值守模式，能够7x24小时自动执行任务，并智能处理Token过期问题。

## ✨ 核心功能 (v1.0.0)

*   **🚀 全自动任务**：在后台自动执行“扫描点赞”和“刷新Token”两个核心任务。
*   **🧠 智能Token管理**：任务执行前自动检查Token有效性，若失效则调用浏览器模块自动获取新Token，实现无缝衔接。
*   **📁 全新路径管理**：**(v1.0.0 核心升级)** 引入 `app_context` 模块，自动适应开发和打包环境，生成所有文件的绝对路径。**彻底告别**因路径问题导致的“找不到文件”或“需要管理员权限运行”的烦恼。
*   **🛡️ 健壮的并发控制**：采用 `threading.RLock`，解决了在“扫描时自动更新Token”等嵌套场景下可能发生的死锁问题，确保长期运行的绝对稳定性。
*   **🤖 可靠的浏览器自动化**：使用 **Playwright** 替代 Selenium，它能更好地管理浏览器实例，自动化过程更稳定、更高效。
*   **🎨 友好交互界面**：清晰的命令行菜单和状态仪表盘，让用户对程序状态一目了然。
*   **📝 外部化配置**：所有用户凭据和设置都存储在 `config.json` 文件中，与代码完全分离。
*   **💾 进度持久化**：点赞进度会自动保存在 `liker_progress.json` 文件中，即使程序重启也能从上次的位置继续扫描。
*   **💻 跨平台支持**：可在 Windows, macOS, 和 Linux 系统上运行。

## 🏗️ 项目架构 (v1.0.0)

v1.0.0 版本遵循“高内聚、低耦合”的设计原则，将项目拆分为多个职责分明的模块：

*   `run.py`: **应用主入口与编排器**。负责初始化环境，整合所有模块，处理顶层用户交互，是整个应用的总指挥。
*   `app_context.py`: **(新增) 应用上下文中心**。项目的基石，唯一负责管理所有文件和目录的路径，确保在任何环境下路径的绝对正确性。
*   `config_manager.py`: **配置中心**。从 `app_context` 获取路径，唯一负责 `config.json` 的读写，提供统一的配置访问接口。
*   `ui_manager.py`: **用户界面层**。专门处理所有控制台的输入输出，将UI与业务逻辑完全分离。
*   `task_manager.py`: **后台任务调度器**。经过重构的通用调度器，封装了所有与线程、定时、锁相关的复杂逻辑，可动态添加和管理后台任务。
*   `get_token.py`: **Token获取模块**。基于 **Playwright** 的独立功能提供者，负责驱动无头浏览器模拟登录并捕获Token。
*   `liker.py`: **点赞执行模块**。基于 `requests` 库的独立功能提供者，负责执行文章扫描和点赞。

## 🚀 如何使用

### 方法一：直接运行 (Windows 用户推荐)

这是最简单快捷的方式。

1.  访问项目的 [**Releases 页面**](https://github.com/MUXSET/TBNEWS_Liker/releases)。
2.  下载最新版本（v1.0.0）的 `.zip` 压缩包。
3.  解压到一个你喜欢的文件夹。
4.  **重要**：确保解压后的所有文件和文件夹（尤其是 `ms-playwright` 文件夹和 `.exe` 主程序）都在同一个目录下。
5.  双击运行 `run.exe` 即可。

### 方法二：从源码运行 (开发者)

在开始之前，请确保您的系统已安装 **Python 3.7+** 和 **Pip**。

1.  **克隆本仓库**
    ```bash
    git clone https://github.com/MUXSET/TBNEWS_Liker.git
    cd TBNEWS_Liker
    ```

2.  **创建 `requirements.txt` 文件**
    此文件应包含以下内容：
    ```text
    requests
    playwright
    ```

3.  **安装 Python 依赖库**
    ```bash
    pip install -r requirements.txt
    ```

4.  **安装 Playwright 浏览器依赖**
    这是非常关键的一步！此命令会自动下载并安装项目所需的 Chromium 浏览器。
    ```bash
    playwright install chromium
    ```

5.  **运行程序**
    ```bash
    python run.py
    ```

## 🔍 问题排查 (Troubleshooting)

*   **程序闪退，或提示 `ms-playwright` 目录不存在**
    *   **原因**: 主程序 `.exe` 找不到所需的浏览器文件。
    *   **解决方案**: 请确保从 `.zip` 包解压出来的所有内容都在同一个文件夹内，不要移动或删除 `ms-playwright` 文件夹。

*   **Token 获取失败**
    *   **原因 1**: 账号或密码错误。
    *   **解决方案 1**: 在程序主菜单选择 `[3] 更改账号信息`，重新输入正确的凭据。
    *   **原因 2**: 目标网站（E+平台）的登录流程或页面结构发生了变化。
    *   **解决方案 2**: 这是正常现象，需要更新 `get_token.py` 模块中的自动化代码以适应网站变更。可以提交一个 [Issue](https://github.com/MUXSET/TBNEWS_Liker/issues) 来报告此问题。
    *   **原因 3**: 网络问题或防火墙阻止了程序访问。
    *   **解决方案 3**: 检查您的网络连接和防火墙设置。

*   **程序被杀毒软件拦截或删除**
    *   **原因**: 使用 PyInstaller 打包的 `.exe` 程序没有数字签名，容易被一些杀毒软件误判为病毒。
    *   **解决方案**: 将程序所在的文件夹添加到杀毒软件的信任区或白名单中。

## 📜 开源协议

本项目采用 [MIT License](LICENSE) 开源协议。