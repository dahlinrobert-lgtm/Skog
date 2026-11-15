# Install a daily background inventory task that can run while the user is signed out.
# Task Scheduler stores the supplied account password using Windows-protected task credentials.
# The password is prompted locally and is never written to this script or repository.
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
$user = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$securePassword = Read-Host "Enter the Windows account PASSWORD for $user (not Windows Hello PIN)" -AsSecureString
if ($securePassword.Length -eq 0) { throw "An account password is required for a background task." }

$bstr = [IntPtr]::Zero
$plainPassword = $null
try {
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
    $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)

    $actionArgs = '-NoProfile -ExecutionPolicy Bypass -File "' + $inventoryScript + '" -IncludeRemovableDrives'
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $actionArgs
    $trigger = New-ScheduledTaskTrigger -Daily -At $time
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 4)
    $principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Password -RunLevel Limited

    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -User $user -Password $plainPassword -Description "Read-only local inventory. Runs in the background while signed out; report files are written to the local OneDrive sync folder for synchronization after the user signs in." -Force | Out-Null
}
finally {
    $plainPassword = $null
    if ($bstr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
    if ($securePassword) { $securePassword.Dispose() }
}

Write-Host "Installed background scheduled task: $TaskName"
Write-Host "Runs daily at $RunAt, including while the user is signed out."
Write-Host "WakeToRun is enabled; hibernate wake still requires Windows wake timers and firmware support."
Write-Host "IMPORTANT: OneDrive sync does not normally run in a signed-out session. Reports are written to the local OneDrive folder and sync after the next sign-in."
Write-Host "The computer cannot be started from a fully powered-off state by this task."
Write-Host "To remove later: Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:\$false"
