@echo off
REM AnalysisWeb 启动脚本 (Windows)
REM 双击或在 cmd 窗口运行: start.bat
REM
REM 2026-07-24 v1.0.0:加 -X utf8,中文 caption/label 写入 _json 不再乱码
REM (与 server.py 主语言中文一致,跨平台镜像 start.sh)

chcp 65001 >nul 2>&1
cd /d %~dp0
echo AnalysisWeb 启动中...
echo 访问地址: http://127.0.0.1:8082/
echo 关闭请按 Ctrl+C 或关闭此窗口
echo.
python -X utf8 server.py
