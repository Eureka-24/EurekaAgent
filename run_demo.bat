@echo off
REM AgentFrame 快速启动脚本
REM 使用方法:
REM 1. 首次运行，运行此脚本自动安装依赖
REM 2. 编辑 config.env 填入 API Key
REM 3. 运行 python examples/demo_agent.py

echo ========================================
echo AgentFrame Demo 启动器
echo ========================================
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

REM 检查conda环境
where conda >nul 2>&1
if %ERRORLEVEL%==0 (
    echo [提示] 检测到 Conda 环境
    echo 如果遇到问题，请运行: conda activate agentframe
    echo.
)

REM 检查依赖
python -c "import openai" >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装依赖...
    pip install openai tiktoken pydantic structlog
    echo.
)

REM 检查配置文件
if not exist config.env (
    echo [提示] 创建配置文件模板...
    copy config.env.example config.env
    echo.
    echo 请编辑 config.env 填入您的 API Key！
    notepad config.env
    echo.
)

echo ========================================
echo 启动演示程序...
echo ========================================
echo.

python examples/demo_agent.py

pause
