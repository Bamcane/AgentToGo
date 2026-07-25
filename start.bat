@echo off
cd /d "%~dp0"

if not exist "venv" (
    echo 创建虚拟环境...
    python -m venv venv
)

call venv\Scripts\activate.bat

#echo 安装依赖...
pip install -r server\requirements.txt

#echo 启动 AgentToGo...
python server\main.py
