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
    $oneDriveRoot = $env:OneDrive
    if (-not $oneDriveRoot) { $oneDriveRoot = $env:OneDriveCommercial }
    if ($oneDriveRoot -and (Test-Path -LiteralPath $oneDriveRoot)) {
        $OutputDirectory = Join-Path (Join-Path $oneDriveRoot "Skogskoll") "_inventory"
    } else {
        $OutputDirectory = Join-Path $HOME "storage-inventory"
    }
}
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

$items = New-Object System.Collections.Generic.List[object]
$errors = New-Object System.Collections.Generic.List[object]

foreach ($root in $Roots) {
    Write-Host "Scanning: $root"
    try {
        $files = Get-ChildItem -LiteralPath $root -File -Recurse -Force -ErrorAction SilentlyContinue | Where-Object {
            -not ($OutputDirectory -and $_.FullName.StartsWith($OutputDirectory, [System.StringComparison]::OrdinalIgnoreCase))
        }
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

$previousSnapshot = Get-ChildItem -LiteralPath $OutputDirectory -Filter "local-storage-inventory-*.json" -File -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1

$changes = New-Object System.Collections.Generic.List[object]
if ($previousSnapshot) {
    try {
        $previous = Get-Content -LiteralPath $previousSnapshot.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
        $previousByPath = @{}
        foreach ($old in $previous.files) { $previousByPath[$old.path] = $old }
        $currentByPath = @{}
        foreach ($current in $items) {
            $currentByPath[$current.path] = $current
            if (-not $previousByPath.ContainsKey($current.path)) {
                $changes.Add([pscustomobject]@{ change="added"; path=$current.path; old_size_bytes=$null; new_size_bytes=$current.size_bytes })
            } else {
                $old = $previousByPath[$current.path]
                if ([long]$old.size_bytes -ne [long]$current.size_bytes -or $old.last_write_time_utc -ne $current.last_write_time_utc) {
                    $changes.Add([pscustomobject]@{ change="modified"; path=$current.path; old_size_bytes=[long]$old.size_bytes; new_size_bytes=[long]$current.size_bytes })
                }
            }
        }
        foreach ($old in $previous.files) {
            if (-not $currentByPath.ContainsKey($old.path)) {
                $changes.Add([pscustomobject]@{ change="missing"; path=$old.path; old_size_bytes=[long]$old.size_bytes; new_size_bytes=$null })
            }
        }
    } catch {
        $errors.Add([pscustomobject]@{ path=$previousSnapshot.FullName; error="Could not compare previous inventory: $($_.Exception.Message)" })
    }
} else {
    $changes.Add([pscustomobject]@{ change="baseline"; path=$null; old_size_bytes=$null; new_size_bytes=$null })
}

$report = [ordered]@{
    schema_version = "1.0"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    computer_name = $env:COMPUTERNAME
    user_name = $env:USERNAME
    scan_mode = "read-only"
    hash_enabled = [bool]$HashFiles
    max_hash_bytes = $MaxHashBytes
    previous_snapshot = if ($previousSnapshot) { $previousSnapshot.Name } else { $null }
    roots = @($rootSummary)
    change_count = $changes.Count
    changes = @($changes)
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
$lines.Add("")
$lines.Add("Changes since previous snapshot: $($changes.Count)")
$lines.Add("| Change | Path | Old bytes | New bytes |")
$lines.Add("|---|---|---:|---:|")
foreach ($change in $changes) { $lines.Add("| $($change.change) | $($change.path) | $($change.old_size_bytes) | $($change.new_size_bytes) |") }
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
