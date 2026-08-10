param(
    [string]$OutputPath = "lowongan data dan analytics jobstreet.csv"
)

$ErrorActionPreference = "Stop"
$datasetRef = "raflirizkya/indonesian-data-and-analytics-jobs-in-jobstreet"
$expectedHash = "A857603F6D8A2B0344F4A4F00747E037ECC4CA3AA6B760800560AD4FE906887C"
$expectedBytes = 1059991
$outputFullPath = [System.IO.Path]::GetFullPath($OutputPath)

if (Test-Path -LiteralPath $outputFullPath) {
    $existingHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $outputFullPath).Hash
    $existingBytes = (Get-Item -LiteralPath $outputFullPath).Length
    if ($existingHash -eq $expectedHash -and $existingBytes -eq $expectedBytes) {
        Write-Output "Dataset already present and verified: $outputFullPath"
        exit 0
    }
    throw "Output exists but does not match Kaggle version 1: $outputFullPath"
}

$temporaryRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("skillpulse-kaggle-" + [guid]::NewGuid().ToString("N"))
$null = New-Item -ItemType Directory -Path $temporaryRoot
try {
    $archivePath = Join-Path $temporaryRoot "dataset.zip"
    $extractPath = Join-Path $temporaryRoot "dataset"
    $downloadUri = "https://www.kaggle.com/api/v1/datasets/download/$datasetRef"
    Invoke-WebRequest -Uri $downloadUri -OutFile $archivePath -UseBasicParsing -TimeoutSec 120
    Expand-Archive -LiteralPath $archivePath -DestinationPath $extractPath
    $downloaded = @(Get-ChildItem -LiteralPath $extractPath -File -Recurse)
    if ($downloaded.Count -ne 1) {
        throw "Expected one dataset file, found $($downloaded.Count)."
    }

    $downloadedHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $downloaded[0].FullName).Hash
    if ($downloadedHash -ne $expectedHash -or $downloaded[0].Length -ne $expectedBytes) {
        throw "Downloaded dataset does not match the pinned Kaggle version 1 identity."
    }

    $parentPath = Split-Path -Parent $outputFullPath
    if ($parentPath) {
        $null = New-Item -ItemType Directory -Path $parentPath -Force
    }
    Copy-Item -LiteralPath $downloaded[0].FullName -Destination $outputFullPath
    Write-Output "Downloaded and verified Kaggle dataset: $outputFullPath"
}
finally {
    $resolvedTemporaryRoot = [System.IO.Path]::GetFullPath($temporaryRoot)
    $systemTemporaryRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
    if ($resolvedTemporaryRoot.StartsWith($systemTemporaryRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        Remove-Item -LiteralPath $resolvedTemporaryRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
