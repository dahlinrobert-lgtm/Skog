$ErrorActionPreference = "Stop"
$scriptPath = Join-Path $PSScriptRoot "inventory-local-storage.ps1"
$temp = Join-Path ([System.IO.Path]::GetTempPath()) ("skog-inventory-test-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $temp | Out-Null

function Read-LatestReport {
    param([string]$Directory)
    $file = Get-ChildItem -LiteralPath $Directory -Filter "local-storage-inventory-*.json" -File |
        Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
    if (-not $file) { throw "No report created in test directory." }
    return (Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8 | ConvertFrom-Json)
}

try {
    $rootA = Join-Path $temp "root-a"
    $rootB = Join-Path $temp "root-b"
    $outScope = Join-Path $temp "scope-output"
    $outPartial = Join-Path $temp "partial-output"
    New-Item -ItemType Directory -Path $rootA,$rootB,$outScope,$outPartial | Out-Null
    Set-Content -LiteralPath (Join-Path $rootA "one.txt") -Value "one"

    & $scriptPath -Roots @($rootA) -OutputDirectory $outScope
    $baseline = Read-LatestReport $outScope
    if ($baseline.schema_version -ne "2.0" -or $baseline.inventory_status -ne "complete" -or $baseline.comparison_status -ne "baseline") {
        throw "Baseline assertion failed."
    }

    Start-Sleep -Seconds 1
    & $scriptPath -Roots @($rootB) -OutputDirectory $outScope
    $scopeChanged = Read-LatestReport $outScope
    if ($scopeChanged.comparison_status -ne "suppressed" -or $scopeChanged.comparison_reason -ne "root_scope_changed") {
        throw "Changed root scope was not suppressed."
    }
    if (@($scopeChanged.changes | Where-Object { $_.change -eq "missing" }).Count -ne 0) {
        throw "Changed root scope produced missing events."
    }

    $outComparable = Join-Path $temp "comparable-output"
    New-Item -ItemType Directory -Path $outComparable | Out-Null
    & $scriptPath -Roots @($rootA) -OutputDirectory $outComparable
    $comparableBaseline = Read-LatestReport $outComparable
    if ($comparableBaseline.comparison_status -ne "baseline") { throw "Initial comparable baseline assertion failed." }
    Start-Sleep -Seconds 1
    Set-Content -LiteralPath (Join-Path $rootA "two.txt") -Value "two"
    & $scriptPath -Roots @($rootA) -OutputDirectory $outComparable
    $comparable = Read-LatestReport $outComparable
    if ($comparable.comparison_status -ne "compared" -or @($comparable.changes | Where-Object { $_.change -eq "added" }).Count -ne 1) {
        throw "Complete same-scope comparison assertion failed."
    }

    & $scriptPath -Roots @($rootA) -OutputDirectory $outPartial
    $partialBaseline = Read-LatestReport $outPartial
    if ($partialBaseline.inventory_status -ne "complete") { throw "Partial-test baseline was not complete." }

    Start-Sleep -Seconds 1
    $missingRoot = Join-Path $temp "does-not-exist"
    & $scriptPath -Roots @($rootA,$missingRoot) -OutputDirectory $outPartial
    $partial = Read-LatestReport $outPartial
    if ($partial.inventory_status -eq "complete" -or $partial.comparison_status -ne "suppressed") {
        throw "Missing root did not make inventory incomplete and suppress comparison."
    }
    if (@($partial.changes | Where-Object { $_.change -eq "missing" }).Count -ne 0) {
        throw "Partial inventory produced missing events."
    }

    Write-Host "PASS: baseline, changed-root scope suppression, and partial-root suppression."
}
finally {
    Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue
}
