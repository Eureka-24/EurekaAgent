#!/usr/bin/env pwsh
# AgentFrame 快速启动脚本 (PowerShell)
# 使用方法:
# 1. 运行此脚本自动安装依赖
# 2. 编辑 config.env 填入 API Key
# 3. 运行 python examples/demo_agent.py

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "AgentFrame Demo 启动器" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "[错误] 未找到 Python，请先安装 Python 3.10+" -ForegroundColor Red
    Read-Host "按 Enter 退出"
    exit 1
}

$pythonVersion = python --version 2>&1
Write-Host "[信息] 检测到 $pythonVersion" -ForegroundColor Green

# 检查conda环境
$condaCmd = Get-Command conda -ErrorAction SilentlyContinue
if ($condaCmd) {
    Write-Host "[提示] 检测到 Conda 环境" -ForegroundColor Yellow
    Write-Host "       如有问题请运行: conda activate agentframe" -ForegroundColor Yellow
    Write-Host ""
}

# 检查依赖
try {
    python -c "import openai; import tiktoken; import pydantic; import structlog" 2>$null
    if ($LASTEXITCODE -ne 0) { throw }
    Write-Host "[信息] 依赖已安装" -ForegroundColor Green
} catch {
    Write-Host "[提示] 正在安装依赖..." -ForegroundColor Yellow
    pip install openai tiktoken pydantic structlog
    Write-Host ""
}

# 检查配置文件
if (-not (Test-Path "config.env")) {
    Write-Host "[提示] 创建配置文件模板..." -ForegroundColor Yellow
    Copy-Item "config.env.example" "config.env"
    Write-Host ""
    Write-Host "请编辑 config.env 填入您的 API Key！" -ForegroundColor Yellow
    
    # 打开记事本编辑
    notepad config.env 2>$null
    Write-Host ""
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "启动演示程序..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 运行演示
python examples/demo_agent.py

Write-Host ""
Read-Host "按 Enter 退出"
