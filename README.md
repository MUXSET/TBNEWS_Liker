# E+ 新闻全自动点赞工具 v2.0.0

![版本](https://img.shields.io/badge/version-2.0.0-blue.svg) ![语言](https://img.shields.io/badge/language-Python-green.svg) ![作者](https://img.shields.io/badge/author-MUXSET-orange.svg) ![协议](https://img.shields.io/badge/license-MIT-lightgrey.svg)

> **🚀 v2.0.0 史诗级更新！**
> 全面重构的架构升级。全新 GUI 仪表板 + 手机 Web 远程控制面板 + 智能缓存 + 按日期扫描 + 多账号管理，从命令行工具进化为真正的桌面应用。

**E+ 新闻全自动点赞工具** 是一款专为 TBEA E+ 新闻平台设计的自动化文章扫描与点赞工具。支持 7×24 小时无人值守运行，智能处理 Token 过期与 Session 保活。

---

## ✨ v2.0.0 新功能

### :computer: 全新 GUI 仪表板
- 现代化桌面界面（基于 CustomTkinter）
- 实时统计卡片：本月文章数 / 已点赞 / 上次扫描时间 / Token 状态
- 支持 System / Dark / Light 主题切换

### :calendar: 按日期范围扫描
- 内置预设：**今天 / 昨天 / 最近3天 / 本周 / 本月 / 上月**
- 支持自定义日期范围，精确补赞历史文章
- 替代旧版 ID 递增盲扫，更高效更精准

### :iphone: 手机远程控制（Web 面板）
- 启动后自动开放 `http://局域网IP:5050`
- 手机浏览器即可远程触发扫描、导出报告、刷新 Token
- 暗色毛玻璃风格 UI，移动端自适应

### 📦 本地智能缓存
- 点赞成功后自动记录到本地缓存（`liked_articles.json`）
- 再次扫描时自动跳过已赞文章，大幅减少 API 请求
- **严格策略**：仅 API 确认成功才写入缓存，绝不误判

### 👥 多账号管理
- 支持添加 / 切换 / 删除多个账号
- 每个账号独立的扫描统计和配置
- 一键侧边栏切换，无需重启

### 🔑 Token 实时校验
- 每 5 分钟通过 API 真实验证 Token 有效性
- 替代旧版估算倒计时，状态显示更准确
- Token 失效时自动调用浏览器模块刷新

### :bar_chart: 月报导出
- 一键导出本月点赞数据为 CSV 报告
- 详细记录每篇文章的点赞状态

---

## :wrench: 项目架构

```
TBNEWS_Liker/
├── run.py                # 应用入口
├── gui_app.py            # GUI 主界面（仪表板）
├── channel_sweep.py      # 频道扫描引擎（按日期范围）
├── liked_cache.py        # 本地点赞缓存
├── web_panel.py          # Web 远程控制面板 (Flask)
├── config_manager.py     # 配置中心（多账号/频道/频率）
├── get_token.py          # Token 自动获取（Playwright）
├── task_manager.py       # 后台定时任务调度器
├── report_exporter.py    # 月报 CSV 导出
├── logger.py             # 日志系统
├── app_context.py        # 路径上下文管理
├── config.json           # 用户配置（自动生成）
├── liked_articles.json   # 点赞缓存（自动生成）
└── requirements.txt      # 依赖清单
```

---

## 🚀 快速开始

### 从源码运行

```bash
# 1. 克隆仓库
git clone https://github.com/MUXSET/TBNEWS_Liker.git
cd TBNEWS_Liker

# 2. 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 安装 Playwright 浏览器
playwright install chromium

# 5. 启动
python run.py
```

### 首次使用

1. 启动后点击 **⚙️ 设置**，输入工号和密码
2. 确认目标频道列表（默认已预置主要频道）
3. 选择扫描范围（如「本月」），点击 **▶ 开始扫描**
4. 手机访问 `http://你的电脑IP:5050` 即可远程查看

---

## ⚙️ 配置说明

所有配置存储在 `config.json` 中，可通过 GUI 设置界面修改：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| 扫描间隔 | 自动模式下的扫描周期 | 1 小时 |
| Token 刷新间隔 | 自动刷新 Token 的周期 | 6 小时 |
| 目标频道 | 要扫描的 IM 频道列表 | 3 个预置频道 |

---

## 📋 版本历史

### v2.0.0 (2026-03-10) — 史诗级更新
- 🖥️ 全新 GUI 仪表板，替代命令行界面
- 📅 按日期范围扫描，替代 ID 递增盲扫
- 📱 Web 远程控制面板（手机可用）
- 📦 本地智能点赞缓存
- 👥 多账号管理
- 🔑 Token 实时 API 校验
- 📊 月报 CSV 导出
- 🧹 删除废弃模块（liker.py, ui_manager.py, monthly_sweep.py）

### v1.0.0 (2025-07-28)
- 首个稳定版：命令行界面，ID 递增扫描，基础 Token 管理

---

## 🔍 问题排查

| 问题 | 解决方案 |
|------|---------|
| Token 获取失败 | 检查工号密码是否正确；确认已安装 `playwright install chromium` |
| 扫描无文章 | 检查频道 ID 是否正确（格式为 `XT-xxx-xxx`） |
| Web 面板打不开 | 确认防火墙允许 5050 端口；检查 Flask 是否安装 |
| 程序被杀软拦截 | 将程序目录加入杀软白名单 |

---

## 📜 开源协议

本项目采用 [MIT License](LICENSE) 开源协议。