# Run from your existing checkout after verifying the bot works manually.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
$envFile = Join-Path $projectRoot '.env'
$taskName = 'TalkingBot'

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'Create .venv and install requirements.txt before registering the task.'
}
if (-not (Test-Path -LiteralPath $envFile -PathType Leaf)) {
    throw 'Configure your private .env file and verify the bot manually first.'
}
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    throw 'A TalkingBot task already exists. Review it in Task Scheduler; this script will not overwrite it.'
}

$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$action = New-ScheduledTaskAction -Execute $python -Argument '-u -m talking_bot' -WorkingDirectory $projectRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $currentUser
$principal = New-ScheduledTaskPrincipal -UserId $currentUser -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings `
    -Description 'Private Telegram bot; runs while this user is signed in. Keep the computer awake.' | Out-Null

Write-Host 'TalkingBot task registered for your next sign-in. It has not been started yet.'
Write-Host 'Stop any manually running bot, then run: Start-ScheduledTask -TaskName TalkingBot'
Write-Host 'Verify /help and /today in Telegram. Keep Windows awake and connected.'
