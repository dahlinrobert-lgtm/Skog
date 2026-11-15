# Inventory selected local folders and removable drives.
# Read-only: this script never moves, edits, or deletes files.
[CmdletBinding()]
param(
    [string[]]$Roots = @(),
    [string]$OutputDirectory = "",
    [switch]$IncludeRemovableDrives,
    [switch]$HashFiles,
    [long]$MaxHashBytes = 268435456
)

$ErrorActionPreference = "Stop"
$timestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")

if (-not $Roots -or $Roots.Count -eq 0) {
    $candidateRoots = @()
    $githubRoot = Join-Path $HOME "GitHub"
    if (Test-Path -LiteralPath $githubRoot) { $candidateRoots += $githubRoot }

    $oneDriveRoot = $env:OneDrive
    if (-not $oneDriveRoot) { $oneDriveRoot = $env:OneDriveCommercial }
    if ($oneDriveRoot) {
        $skogskollRoot = Join-Path $oneDriveRoot "Skogskoll"
        if (Test-Path -LiteralPath $skogskollRoot) { $candidateRoots += $skogskollRoot }
    }
    $Roots = $candidateRoots
}

if ($IncludeRemovableDrives) {
    try {
        $removable = Get-CimInstance Win32_LogicalDisk -Filter "DriveType=2"
        foreach ($disk in $removable) {
            $mount = "$($disk.DeviceID)\"
            if (Test-Path -LiteralPath $mount) { $Roots += $mount }
        }
    } catch {
        Write-Warning "Could not enumerate removable drives: $($_.Exception.Message)"
    }
}

$Roots = @($Roots | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | ForEach-Object {
    (Resolve-Path -LiteralPath $_).Path
} | Sort-Object -Unique)

if (-not $Roots -or $Roots.Count -eq 0) {
    throw "No existing roots were found. Supply -Roots explicitly."
}

if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path (Get-Location).Path "storage-inventory"
}
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

$items = New-Object System.Collections.Generic.List[object]
$errors = New-Object System.Collections.Generic.List[object]

foreach ($root in $Roots) {
    Write-Host "Scanning: $root"
    try {
        $files = Get-ChildItem -LiteralPath $root -File -Recurse -Force -ErrorAction SilentlyContinue
        foreach ($file in $files) {
            $hash = $null
            if ($HashFiles -and $file.Length -le $MaxHashBytes) {
                try { $hash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash }
                catch { $errors.Add([pscustomobject]@{ path=$file.FullName; error=$_.Exception.Message }) }
            }

            $items.Add([pscustomobject]@{
                root = $root
                path = $file.FullName
                relative_path = $file.FullName.Substring($root.TrimEnd('\').Length).TrimStart('\')
                name = $file.Name
                extension = $file.Extension
                size_bytes = [long]$file.Length
                last_write_time_utc = $file.LastWriteTimeUtc.ToString("o")
                sha256 = $hash
            })
        }
    } catch {
        $errors.Add([pscustomobject]@{ path=$root; error=$_.Exception.Message })
    }
}

$rootSummary = foreach ($root in $Roots) {
    $matching = @($items | Where-Object { $_.root -eq $root })
    [pscustomobject]@{
        root = $root
        file_count = $matching.Count
        total_bytes = [long](($matching | Measure-Object -Property size_bytes -Sum).Sum)
    }
}

$report = [ordered]@{
    schema_version = "1.0"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    computer_name = $env:COMPUTERNAME
    user_name = $env:USERNAME
    scan_mode = "read-only"
    hash_enabled = [bool]$HashFiles
    max_hash_bytes = $MaxHashBytes
    roots = @($rootSummary)
    files = @($items)
    errors = @($errors)
}

$jsonPath = Join-Path $OutputDirectory "local-storage-inventory-$timestamp.json"
$mdPath = Join-Path $OutputDirectory "local-storage-inventory-$timestamp.md"
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

$lines = New-Object System.Collections.Generic.List[string]
$lines.Add("# Local storage inventory")
$lines.Add("")
$lines.Add("- Generated (UTC): $($report.generated_at_utc)")
$lines.Add("- Computer: $env:COMPUTERNAME")
$lines.Add("- Mode: read-only")
$lines.Add("")
$lines.Add("| Root | Files | Total size (GB) |")
$lines.Add("|---|---:|---:|")
foreach ($entry in $rootSummary) {
    $gb = [math]::Round(($entry.total_bytes / 1GB), 3)
    $lines.Add("| $($entry.root) | $($entry.file_count) | $gb |")
}
$lines.Add("")
$lines.Add("Errors: $($errors.Count)")
$lines.Add("")
$lines.Add("Detailed file metadata is in the JSON report. SHA-256 is only populated when -HashFiles is used and files are within -MaxHashBytes.")
$lines | Set-Content -LiteralPath $mdPath -Encoding UTF8

Write-Host ""
Write-Host "Inventory complete."
Write-Host "JSON: $jsonPath"
Write-Host "Markdown: $mdPath"
Write-Host "Files: $($items.Count); errors: $($errors.Count)"
