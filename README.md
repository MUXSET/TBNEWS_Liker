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

*   `run.py`: **应用主入口与编排器**。
*   `app_context.py`: **(新增) 应用上下文中心**，负责所有路径管理。
*   `config_manager.py`: **配置中心**，负责读写 `config.json`。
*   `ui_manager.py`: **用户界面层**，负责所有控制台交互。
*   `task_manager.py`: **后台任务调度器**，负责线程和定时任务。
*   `get_token.py`: **Token获取模块** (基于 Playwright)。
*   `liker.py`: **点赞执行模块** (基于 requests)。

## 🚀 如何使用 (v1.0.0)

我们提供多种方式供您选择，请根据您的偏好下载使用。

### 方法一：使用安装包 (推荐)

这是最简单、最推荐的方式，适合绝大多数 Windows 用户。

1.  📥 **下载**：访问项目的 [**Releases 页面**](https://github.com/MUXSET/TBNEWS_Liker/releases)，下载名为 `E+Liker-v1.0.0-setup.exe` (或类似名称) 的安装程序。
2.  ➡️ **安装**：双击下载的文件，根据屏幕上的提示一步步完成安装。
3.  ✅ **运行**：安装完成后，即可在桌面或开始菜单找到程序快捷方式，双击运行。

### 方法二：使用便携版压缩包 (解压即用)

适合喜欢绿色软件、不希望在系统中留下安装痕迹的用户。

1.  📥 **下载**：访问项目的 [**Releases 页面**](https://github.com/MUXSET/TBNEWS_Liker/releases)，下载名为 `E+Liker-v1.0.0-portable.zip` (或类似名称) 的压缩包。
2.  ➡️ **解压**：将下载的 `.zip` 文件解压到您喜欢的任意文件夹（例如 `D:\Tools\E+Liker`）。
3.  ⚠️ **重要**：请确保解压后的所有文件和文件夹（尤其是 `ms-playwright` 文件夹和 `.exe` 主程序）都位于同一个目录下，**不要移动或删除它们**。
4.  ✅ **运行**：双击目录中的 `run.exe` 即可启动程序。

### 方法三：从源码运行 (开发者)

适合开发者或希望自定义代码的用户。

1.  **克隆本仓库**
    ```bash
    git clone https://github.com/MUXSET/TBNEWS_Liker.git
    cd TBNEWS_Liker
    ```

2.  **创建 `requirements.txt` 文件**
    ```text
    requests
    playwright
    ```

3.  **安装 Python 依赖库**
    ```bash
    pip install -r requirements.txt
    ```

4.  **安装 Playwright 浏览器依赖 (关键步骤)**
    ```bash
    playwright install chromium
    ```

5.  **运行程序**
    ```bash
    python run.py
    ```

## 🔍 问题排查 (Troubleshooting)

*   **程序闪退，或提示 `ms-playwright` 目录不存在**
    *   **原因**: (主要针对便携版) 主程序 `.exe` 找不到所需的浏览器文件。
    *   **解决方案**: 请确保从 `.zip` 包解压出来的所有内容都在同一个文件夹内，不要移动或删除 `ms-playwright` 文件夹。

*   **Token 获取失败**
    *   **原因 1**: 账号或密码错误。
    *   **解决方案 1**: 在程序主菜单选择 `[3] 更改账号信息`，重新输入正确的凭据。
    *   **原因 2**: 目标网站（E+平台）的登录流程或页面结构发生了变化。
    *   **解决方案 2**: 这是正常现象，需要更新代码以适应网站变更。可以提交一个 [Issue](https://github.com/MUXSET/TBNEWS_Liker/issues) 来报告此问题。

*   **安装包或程序被杀毒软件拦截**
    *   **原因**: 程序没有数字签名，容易被一些杀毒软件误报。
    *   **解决方案**: 这是正常现象。请将程序或其所在文件夹添加到杀毒软件的信任区或白名单中。

## 📜 开源协议

本项目采用 [MIT License](LICENSE) 开源协议。