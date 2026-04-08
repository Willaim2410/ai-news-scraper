# Install Windows Task Scheduler job for the daily AI news scraper.
# Run once in PowerShell as Administrator.
#
# IMPORTANT: -StartWhenAvailable means if your PC was off at 8am,
# the task fires as soon as it wakes up — so you never miss a digest.

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = (Get-Command python -ErrorAction Stop).Source
$ScraperScript = Join-Path $ScriptDir "scraper.py"
$TaskName = "AI-News-Scraper"

$Action = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument "`"$ScraperScript`"" `
    -WorkingDirectory $ScriptDir

$Trigger = New-ScheduledTaskTrigger -Daily -At "08:00AM"

$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -RestartCount 2 `
    -RestartInterval (New-TimeSpan -Minutes 5)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -RunLevel Highest `
    -Description "Daily AI news scraper — RSS + Twitter digest" `
    -Force

Write-Host ""
Write-Host "Task '$TaskName' registered. Runs daily at 8:00 AM."
Write-Host "Even if your PC is off at 8am, it fires when you wake it up."
Write-Host ""
Write-Host "Test immediately:    Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "Check status:        Get-ScheduledTask -TaskName '$TaskName' | Select State"
Write-Host "Remove:              Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
