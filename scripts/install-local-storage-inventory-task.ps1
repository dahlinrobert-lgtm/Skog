# Install a per-user daily inventory task. No administrator rights required.
[CmdletBinding()]
param(
    [string]$TaskName = "Skogskoll - local storage inventory",
    [string]$RunAt = "21:00"
)

$ErrorActionPreference = "Stop"
$inventoryScript = Join-Path $PSScriptRoot "inventory-local-storage.ps1"
if (-not (Test-Path -LiteralPath $inventoryScript)) {
    throw "Inventory script not found: $inventoryScript"
}

$time = [datetime]::ParseExact($RunAt, "HH:mm", [Globalization.CultureInfo]::InvariantCulture)
$actionArgs = '-NoProfile -ExecutionPolicy Bypass -File "' + $inventoryScript + '" -IncludeRemovableDrives'
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $actionArgs
$trigger = New-ScheduledTaskTrigger -Daily -At $time
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Read-only inventory of selected GitHub, OneDrive-synced and connected removable storage. Reports are saved to OneDrive when available." -Force | Out-Null

Write-Host "Installed per-user scheduled task: $TaskName"
Write-Host "Runs daily at $RunAt when the user session is available."
Write-Host "The computer must be on; missed runs start when possible."
Write-Host "To remove later: Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:$false"
