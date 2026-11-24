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

    # Exercise a real access-denied subdirectory on Windows. The explicit deny ACE
    # is restored before cleanup, even if the inventory assertion fails.
    $rootAcl = Join-Path $temp "root-acl"
    $outAcl = Join-Path $temp "acl-output"
    $blocked = Join-Path $rootAcl "blocked"
    New-Item -ItemType Directory -Path $blocked,$outAcl | Out-Null
    Set-Content -LiteralPath (Join-Path $rootAcl "visible.txt") -Value "visible"
    Set-Content -LiteralPath (Join-Path $blocked "hidden.txt") -Value "hidden"

    & $scriptPath -Roots @($rootAcl) -OutputDirectory $outAcl
    $aclBaseline = Read-LatestReport $outAcl
    if ($aclBaseline.inventory_status -ne "complete" -or $aclBaseline.comparison_status -ne "baseline") {
        throw "ACL-test baseline assertion failed."
    }

    $originalAcl = Get-Acl -LiteralPath $blocked
    try {
        $currentSid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
        if (-not $currentSid) { throw "Could not resolve current Windows user SID for ACL test." }
        $denyRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
            $currentSid,
            [System.Security.AccessControl.FileSystemRights]::ReadAndExecute,
            [System.Security.AccessControl.InheritanceFlags]::ContainerInherit,
            [System.Security.AccessControl.PropagationFlags]::None,
            [System.Security.AccessControl.AccessControlType]::Deny
        )
        $deniedAcl = Get-Acl -LiteralPath $blocked
        $deniedAcl.SetAccessRule($denyRule)
        Set-Acl -LiteralPath $blocked -AclObject $deniedAcl

        Start-Sleep -Seconds 1
        & $scriptPath -Roots @($rootAcl) -OutputDirectory $outAcl
        $aclPartial = Read-LatestReport $outAcl
        if ($aclPartial.inventory_status -ne "partial" -or $aclPartial.comparison_status -ne "suppressed") {
            throw "Denied subdirectory did not make inventory partial and suppress comparison."
        }
        if ($aclPartial.error_count -lt 1 -or @($aclPartial.changes | Where-Object { $_.change -eq "missing" }).Count -ne 0) {
            throw "Denied subdirectory was not recorded safely or produced missing events."
        }
        if ($aclPartial.roots[0].status -ne "partial") {
            throw "Root with denied subdirectory was not marked partial."
        }
    }
    finally {
        Set-Acl -LiteralPath $blocked -AclObject $originalAcl
    }

    Write-Host "PASS: baseline, changed-root scope suppression, missing-root suppression, and denied-subdirectory ACL suppression."
}
finally {
    Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue
}
