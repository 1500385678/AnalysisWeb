#!/bin/bash
# AnalysisWeb 启动脚本 (macOS / Linux)
# 双击或在终端运行: ./start.sh
#
# 2026-08-05 P0 修复:加 -X utf8 与 start.bat 对齐
# 原因:macOS 系统 Python 3.9 不强制 UTF-8 mode,中文 caption/label 写入 _json
#      或控制台打印会出现 UnicodeEncodeError 或乱码;Windows 端 start.bat 已用
#      `python -X utf8 server.py` 兜底,这里对称处理,跨平台一致。
#      (与服务端 AGENTS.md「主语言中文」约束一致,见 server.py 同步更新需求)

cd "$(dirname "$0")"
echo "AnalysisWeb 启动中..."
echo "访问地址: http://127.0.0.1:8082/"
echo "关闭请按 Ctrl+C"
echo ""
python3 -X utf8 server.py
