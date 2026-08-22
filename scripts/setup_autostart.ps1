<#
.SYNOPSIS
配置 Bayesian-AGI-Core MCP Server 开机自动启动

.DESCRIPTION
此脚本将创建Windows任务计划程序任务，使MCP Server在系统启动时自动运行
#>

$taskName = "BayesianAGICore-MCPServer"
$scriptPath = "e:\laowut\Trae CN\bayesian-agi-core\scripts\start_mcp_server.bat"
$workingDir = "e:\laowut\Trae CN\bayesian-agi-core"

# 检查脚本文件是否存在
if (-not (Test-Path $scriptPath)) {
    Write-Error "启动脚本不存在: $scriptPath"
    exit 1
}

# 创建任务计划程序任务
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$scriptPath`"" -WorkingDirectory $workingDir
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# 注册任务
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force

Write-Host "`n✅ 任务 '$taskName' 已成功创建！"
Write-Host "`n任务配置:"
Write-Host "- 任务名称: $taskName"
Write-Host "- 启动脚本: $scriptPath"
Write-Host "- 工作目录: $workingDir"
Write-Host "- 触发条件: 系统启动时"
Write-Host "- 运行账户: SYSTEM"
Write-Host "`n您可以在任务计划程序中查看和管理此任务。"
