#requires -Version 5.1
[CmdletBinding()]
param(
    [string]$OutputDirectory = (Join-Path $env:USERPROFILE "Desktop\Skogskoll_AFO_geometry"),
    [int]$BatchSize = 10,
    [int]$ExpectedCount = 2927
)
$ErrorActionPreference = "Stop"
$Base = "https://ext-geodata-applikationer.lansstyrelsen.se/arcgis/rest/services/Jaktadm/lst_jaktadm_visning/MapServer/0"
$Utf8NoBom = [System.Text.UTF8Encoding]::new($false)
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
Write-Host "Hämtar objekt-ID-inventering..." -ForegroundColor Cyan
$IdUrl = "$Base/query?where=1%3D1&returnIdsOnly=true&f=json"
$IdResponse = Invoke-RestMethod -Uri $IdUrl
if ($IdResponse.error) { throw ($IdResponse.error | ConvertTo-Json -Depth 10) }
$Ids = @($IdResponse.objectIds | Sort-Object)
if ($Ids.Count -ne $ExpectedCount) { throw "Förväntade $ExpectedCount objekt men tjänsten returnerade $($Ids.Count). Ingen export startas." }
if (($Ids | Select-Object -Unique).Count -ne $Ids.Count) { throw "ID-inventeringen innehåller dubbletter. Ingen export startas." }

$AsoPartial = Join-Path $OutputDirectory "algskotselomraden_original.partial.geojson"
$LicensePartial = Join-Path $OutputDirectory "licensomraden_original.partial.geojson"
$AsoFinal = Join-Path $OutputDirectory "algskotselomraden_original.geojson"
$LicenseFinal = Join-Path $OutputDirectory "licensomraden_original.geojson"
$ReportPath = Join-Path $OutputDirectory "geometry_export_report.json"
foreach ($path in @($AsoFinal, $LicenseFinal)) {
    if (Test-Path $path) { throw "Filen finns redan: $path. Flytta/byt namn på den manuellt innan en ny export." }
}
Remove-Item $AsoPartial,$LicensePartial -Force -ErrorAction SilentlyContinue
$AsoWriter = [System.IO.StreamWriter]::new($AsoPartial, $false, $Utf8NoBom)
$LicenseWriter = [System.IO.StreamWriter]::new($LicensePartial, $false, $Utf8NoBom)
$AsoWriter.Write('{"type":"FeatureCollection","features":[')
$LicenseWriter.Write('{"type":"FeatureCollection","features":[')
$Seen = [System.Collections.Generic.HashSet[long]]::new()
$AsoCount = 0
$LicenseCount = 0
$AsoCoordinates = 0L
$LicenseCoordinates = 0L
$AsoFirst = $true
$LicenseFirst = $true
$BatchNumber = 0
$Completed = $false

try {
    for ($i = 0; $i -lt $Ids.Count; $i += $BatchSize) {
        $BatchNumber++
        $End = [Math]::Min($i + $BatchSize - 1, $Ids.Count - 1)
        $Batch = @($Ids[$i..$End])
        $Url = "$Base/query?objectIds=$($Batch -join ',')&outFields=OBJECTID,afo_id,bslarea_ha,namn_afo,namn_ajo,objtyp,omrnum&returnGeometry=true&outSR=4326&f=geojson"
        $Response = Invoke-RestMethod -Uri $Url
        if ($Response.error) { throw ("ArcGIS-fel i batch " + $BatchNumber + ": " + ($Response.error | ConvertTo-Json -Compress)) }
        $Features = @($Response.features)
        if ($Features.Count -ne $Batch.Count) { throw ("Ofullständig batch " + $BatchNumber + ": begärde " + $Batch.Count + ", fick " + $Features.Count + ".") }

        foreach ($Feature in $Features) {
            $Props = $Feature.properties
            $ObjectId = [long]$Props.OBJECTID
            if (-not $Seen.Add($ObjectId)) { throw "Dubblett-OBJECTID $ObjectId. Exporten avbryts." }
            if (-not $Feature.geometry -or -not $Feature.geometry.coordinates) { throw "Geometri saknas för OBJECTID $ObjectId. Exporten avbryts." }
            $Stack = [System.Collections.Stack]::new()
            $Stack.Push($Feature.geometry.coordinates)
            $CoordinateCount = 0L
            while ($Stack.Count -gt 0) {
                $Node = $Stack.Pop()
                if ($null -eq $Node) { continue }
                if ($Node -is [System.Array] -or $Node -is [System.Collections.IList]) {
                    if ($Node.Count -ge 2 -and $Node[0] -is [ValueType] -and $Node[1] -is [ValueType]) {
                        $CoordinateCount++
                    } else {
                        foreach ($Child in $Node) { $Stack.Push($Child) }
                    }
                }
            }
            $Json = ConvertTo-Json -InputObject $Feature -Depth 100 -Compress
            switch ($Props.objtyp) {
                "Älgskötselområde" {
                    if (-not $AsoFirst) { $AsoWriter.Write(",") }
                    $AsoWriter.Write($Json)
                    $AsoFirst = $false
                    $AsoCount++
                    $AsoCoordinates += $CoordinateCount
                }
                "Licensområde" {
                    if (-not $LicenseFirst) { $LicenseWriter.Write(",") }
                    $LicenseWriter.Write($Json)
                    $LicenseFirst = $false
                    $LicenseCount++
                    $LicenseCoordinates += $CoordinateCount
                }
                default { throw "Okänd objtyp '$($Props.objtyp)' för OBJECTID $ObjectId." }
            }
        }
        Write-Host "Batch $BatchNumber klar: $($Seen.Count) / $($Ids.Count)" -ForegroundColor Green
    }
    if ($Seen.Count -ne $Ids.Count) { throw "Ofullständig totalexport: $($Seen.Count) av $($Ids.Count) unika objekt." }
    if (($AsoCount + $LicenseCount) -ne $ExpectedCount) { throw "Områdestyperna summerar till $($AsoCount + $LicenseCount), förväntade $ExpectedCount." }
    if ($AsoCount -ne 832 -or $LicenseCount -ne 2095) { throw "Områdesfördelningen avviker: ÄSO=$AsoCount, licens=$LicenseCount. Kontrollera källförändring." }
    $AsoWriter.Write("]}")
    $LicenseWriter.Write("]}")
    $AsoWriter.Flush()
    $LicenseWriter.Flush()
    $Completed = $true
}
finally {
    $AsoWriter.Dispose()
    $LicenseWriter.Dispose()
}
if (-not $Completed) { throw "Exporten slutfördes inte. *.partial.geojson är ofullständiga och får inte användas." }
Move-Item -LiteralPath $AsoPartial -Destination $AsoFinal
Move-Item -LiteralPath $LicensePartial -Destination $LicenseFinal
$Report = [ordered]@{
    source = "Länsstyrelsernas JaktAdm MapServer, layer 0"
    source_url = $Base
    retrieved_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    output_crs = "EPSG:4326"
    requested_ids = $Ids.Count
    unique_ids_written = $Seen.Count
    complete = $true
    batch_size = $BatchSize
    batches = $BatchNumber
    elk_management_areas = $AsoCount
    elk_management_area_coordinate_pairs = $AsoCoordinates
    license_areas = $LicenseCount
    license_area_coordinate_pairs = $LicenseCoordinates
    files = @(
        [ordered]@{ path = [System.IO.Path]::GetFileName($AsoFinal); bytes = (Get-Item $AsoFinal).Length }
        [ordered]@{ path = [System.IO.Path]::GetFileName($LicenseFinal); bytes = (Get-Item $LicenseFinal).Length }
    )
}
$Report | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $ReportPath -Encoding UTF8
Write-Host "EXPORT KLAR" -ForegroundColor Green
$Report | ConvertTo-Json -Depth 10
Write-Host "Filer sparade i: $OutputDirectory"
