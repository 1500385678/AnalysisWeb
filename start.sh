#!/bin/bash
# AnalysisWeb 启动脚本 (macOS / Linux)
# 双击或在终端运行: ./start.sh

cd "$(dirname "$0")"
echo "AnalysisWeb 启动中..."
echo "访问地址: http://127.0.0.1:8082/"
echo "关闭请按 Ctrl+C"
echo ""
python3 server.py
