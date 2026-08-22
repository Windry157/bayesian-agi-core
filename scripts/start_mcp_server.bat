@echo off
REM Bayesian-AGI-Core MCP Server 启动脚本
REM 作者: Bayesian AGI Team
REM 版本: 2.0.0

set "PYTHONPATH=e:\laowut\Trae CN\bayesian-agi-core"
set "VIRTUAL_ENV=e:\laowut\Trae CN\bayesian-agi-core\.venv"

REM 激活虚拟环境
call "%VIRTUAL_ENV%\Scripts\activate.bat"

REM 启动MCP Server
echo 正在启动 Bayesian-AGI-Core MCP Server...
python src/mcp_server.py

REM 保持窗口打开（调试用）
REM pause