#!/bin/bash
# =================================================================
#  E+新闻 全自动点赞工具 - macOS 一键启动脚本
#  双击此文件即可自动激活虚拟环境并启动 GUI 程序。
# =================================================================

# 切换到脚本所在目录（防止从其它位置双击时路径出错）
cd "$(dirname "$0")"

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo "❌ 错误：未找到 venv 虚拟环境目录！"
    echo "   请先运行以下命令创建环境："
    echo "   python3.12 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    read -p "按回车键退出..."
    exit 1
fi

# 激活虚拟环境并启动
source venv/bin/activate
python run.py
