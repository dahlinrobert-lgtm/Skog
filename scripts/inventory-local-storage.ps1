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
    $profileRoot = $env:USERPROFILE
    if (-not $profileRoot) { $profileRoot = $HOME }
    $githubRoot = Join-Path $profileRoot "GitHub"
    if (Test-Path -LiteralPath $githubRoot) { $candidateRoots += $githubRoot }

    $oneDriveRoot = $env:OneDrive
    if (-not $oneDriveRoot) { $oneDriveRoot = $env:OneDriveCommercial }
    if (-not $oneDriveRoot) {
        $personalCandidate = Join-Path $profileRoot "OneDrive"
        if (Test-Path -LiteralPath $personalCandidate) { $oneDriveRoot = $personalCandidate }
    }
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
        $discoveryComplete = $false
        $errors.Add([pscustomobject]@{ path="(removable-drive discovery)"; category="root_discovery"; error=$_.Exception.Message })
    }
}

$Roots = @($Roots | Where-Object { $_ } | ForEach-Object {
    if (Test-Path -LiteralPath $_ -PathType Container) { (Resolve-Path -LiteralPath $_).Path }
    else { [System.IO.Path]::GetFullPath($_) }
} | Sort-Object -Unique)

if (-not $Roots -or $Roots.Count -eq 0) {
    throw "No existing roots were found. Supply -Roots explicitly."
}

if (-not $OutputDirectory) {
    $profileRoot = $env:USERPROFILE
    if (-not $profileRoot) { $profileRoot = $HOME }
    $oneDriveRoot = $env:OneDrive
    if (-not $oneDriveRoot) { $oneDriveRoot = $env:OneDriveCommercial }
    if (-not $oneDriveRoot) {
        $personalCandidate = Join-Path $profileRoot "OneDrive"
        if (Test-Path -LiteralPath $personalCandidate) { $oneDriveRoot = $personalCandidate }
    }
    if ($oneDriveRoot -and (Test-Path -LiteralPath $oneDriveRoot)) {
        $OutputDirectory = Join-Path (Join-Path $oneDriveRoot "Skogskoll") "_inventory"
    } else {
        $OutputDirectory = Join-Path $HOME "storage-inventory"
    }
}
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

$items = New-Object System.Collections.Generic.List[object]
$errors = New-Object System.Collections.Generic.List[object]
$rootStates = New-Object System.Collections.Generic.List[object]
$discoveryComplete = $true

foreach ($root in $Roots) {
    Write-Host "Scanning: $root"
    try {
        $enumerationErrors = @()
        $files = @(Get-ChildItem -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue -ErrorVariable +enumerationErrors | Where-Object {
            -not ($OutputDirectory -and $_.FullName.StartsWith($OutputDirectory, [System.StringComparison]::OrdinalIgnoreCase))
        })
        foreach ($file in $files) {
            if ($file.PSIsContainer) {
                $rootDirectories++
                continue
            }
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
        foreach ($enumerationError in @($enumerationErrors)) {
            $errors.Add([pscustomobject]@{ path=$root; category="enumeration"; error=$enumerationError.Exception.Message })
        }
        $rootStatus = if (@($enumerationErrors).Count -gt 0) { "partial" } else { "complete" }
        if (-not (Test-Path -LiteralPath $root -PathType Container)) { $rootStatus = "failed" }
    } catch {
        $errors.Add([pscustomobject]@{ path=$root; category="enumeration"; error=$_.Exception.Message })
        $rootStatus = "failed"
    }
    $rootMatching = @($items | Where-Object { $_.root -eq $root })
    $rootStates.Add([pscustomobject]@{
        root = $root
        status = $rootStatus
        directory_count = $rootDirectories
        file_count = $rootMatching.Count
        total_bytes = [long](($rootMatching | Measure-Object -Property size_bytes -Sum).Sum)
        error_count = @($errors | Where-Object { $_.path -eq $root }).Count
    })
}

$rootSummary = foreach ($root in $Roots) {
    $matching = @($items | Where-Object { $_.root -eq $root })
    [pscustomobject]@{
        root = $root
        file_count = $matching.Count
        total_bytes = [long](($matching | Measure-Object -Property size_bytes -Sum).Sum)
    }
}

$inventoryStatus = "complete"
if (@($rootStates | Where-Object { $_.status -ne "complete" }).Count -gt 0 -or -not $discoveryComplete) {
    $inventoryStatus = "partial"
}
if (@($rootStates | Where-Object { $_.status -eq "failed" }).Count -eq $rootStates.Count) {
    $inventoryStatus = "failed"
}

$previousSnapshot = Get-ChildItem -LiteralPath $OutputDirectory -Filter "local-storage-inventory-*.json" -File -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1

$changes = New-Object System.Collections.Generic.List[object]
$comparisonStatus = "baseline"
$comparisonReason = "no_previous_snapshot"
if ($previousSnapshot) {
    try {
        $previous = Get-Content -LiteralPath $previousSnapshot.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($inventoryStatus -ne "complete") {
            $comparisonStatus = "suppressed"
            $comparisonReason = "current_inventory_not_complete"
        } elseif ([string]$previous.schema_version -ne "2.0" -or [string]$previous.inventory_status -ne "complete") {
            $comparisonStatus = "suppressed"
            $comparisonReason = "previous_report_not_comparable"
        } else {
            $currentRoots = @($rootStates | ForEach-Object { [string]$_.root } | Sort-Object)
            $previousRoots = @($previous.roots | ForEach-Object { [string]$_.root } | Sort-Object)
            $sameRoots = ($currentRoots.Count -eq $previousRoots.Count) -and (($currentRoots -join [Environment]::NewLine) -ceq ($previousRoots -join [Environment]::NewLine))
            if (-not $sameRoots) {
                $comparisonStatus = "suppressed"
                $comparisonReason = "root_scope_changed"
            } else {
                $comparisonStatus = "compared"
                $comparisonReason = "complete_same_scope"
                $previousByPath = @{}
                foreach ($old in @($previous.files)) { $previousByPath[[string]$old.path] = $old }
                $currentByPath = @{}
                foreach ($current in $items) {
                    $currentByPath[[string]$current.path] = $current
                    if (-not $previousByPath.ContainsKey([string]$current.path)) {
                        $changes.Add([pscustomobject]@{ change="added"; path=$current.path; old_size_bytes=$null; new_size_bytes=$current.size_bytes })
                    } else {
                        $old = $previousByPath[[string]$current.path]
                        if ([long]$old.size_bytes -ne [long]$current.size_bytes -or $old.last_write_time_utc -ne $current.last_write_time_utc) {
                            $changes.Add([pscustomobject]@{ change="modified"; path=$current.path; old_size_bytes=[long]$old.size_bytes; new_size_bytes=$current.size_bytes })
                        }
                    }
                }
                foreach ($old in @($previous.files)) {
                    if (-not $currentByPath.ContainsKey([string]$old.path)) {
                        $changes.Add([pscustomobject]@{ change="missing"; path=$old.path; old_size_bytes=[long]$old.size_bytes; new_size_bytes=$null })
                    }
                }
            }
        }
    } catch {
        $comparisonStatus = "suppressed"
        $comparisonReason = "previous_report_unreadable"
        $errors.Add([pscustomobject]@{ path=$previousSnapshot.Name; category="previous_report"; error=$_.Exception.Message })
    }
}
if ($comparisonStatus -ne "compared") {
    $changes.Clear()
    $changes.Add([pscustomobject]@{ change="comparison_suppressed"; path=$null; old_size_bytes=$null; new_size_bytes=$null; reason=$comparisonReason })
}

$previousSnapshotName = $null
if ($previousSnapshot) {
    $previousSnapshotName = $previousSnapshot.Name
}

$report = [ordered]@{
    schema_version = "2.0"
    inventory_status = $inventoryStatus
    discovery_complete = [bool]$discoveryComplete
    comparison_status = $comparisonStatus
    comparison_reason = $comparisonReason
    root_count = $rootStates.Count
    directory_count = [long](($rootStates | Measure-Object -Property directory_count -Sum).Sum)
    file_count = $items.Count
    error_count = $errors.Count
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    scan_mode = "read-only"
    hash_enabled = [bool]$HashFiles
    max_hash_bytes = $MaxHashBytes
    previous_snapshot = $previousSnapshotName
    roots = @($rootStates)
    change_count = $changes.Count
    changes = $changes.ToArray()
    files = $items.ToArray()
    errors = $errors.ToArray()
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
