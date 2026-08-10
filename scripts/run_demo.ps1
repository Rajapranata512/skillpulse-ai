[CmdletBinding()]
param(
    [switch]$Install,
    [switch]$NoBrowser,
    [switch]$SmokeTest,
    [ValidateRange(1, 65535)]
    [int]$ApiPort = 8000,
    [ValidateRange(1, 65535)]
    [int]$UiPort = 8501
)

$ErrorActionPreference = "Stop"
$scriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = (Resolve-Path (Join-Path $scriptDirectory "..")).Path
$originalLocation = Get-Location
$previousApiUrl = $env:SKILLPULSE_API_URL
$apiProcess = $null
$uiProcess = $null

function Invoke-PythonChecked {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    & python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code $LASTEXITCODE."
    }
}

try {
    Set-Location -LiteralPath $projectRoot

    if ($Install) {
        Write-Host "Installing SkillPulse API and UI dependencies..."
        Invoke-PythonChecked -Arguments @("-m", "pip", "install", "-e", ".[api,ui]")
    }

    Invoke-PythonChecked -Arguments @(
        "-c",
        "import fastapi, skillpulse, streamlit, uvicorn; print('SkillPulse demo dependencies: OK')"
    )

    $apiArguments = @(
        "-m", "uvicorn", "skillpulse.api.app:app",
        "--host", "127.0.0.1",
        "--port", $ApiPort.ToString(),
        "--no-access-log"
    )
    $apiProcess = Start-Process `
        -FilePath "python" `
        -ArgumentList $apiArguments `
        -WorkingDirectory $projectRoot `
        -WindowStyle Hidden `
        -PassThru

    $apiUrl = "http://127.0.0.1:$ApiPort"
    $healthUrl = "$apiUrl/health"
    $deadline = (Get-Date).AddSeconds(30)
    $healthy = $false
    while ((Get-Date) -lt $deadline) {
        if ($apiProcess.HasExited) {
            throw "SkillPulse API exited before becoming healthy."
        }
        try {
            $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 2
            if ($health.status -eq "ok") {
                $healthy = $true
                break
            }
        }
        catch {
            Start-Sleep -Milliseconds 300
        }
    }
    if (-not $healthy) {
        throw "SkillPulse API did not become healthy within 30 seconds at $healthUrl."
    }

    $env:SKILLPULSE_API_URL = $apiUrl
    $headlessValue = if ($NoBrowser -or $SmokeTest) { "true" } else { "false" }
    $uiUrl = "http://127.0.0.1:$UiPort"
    Write-Host "SkillPulse API: $apiUrl/docs"
    Write-Host "SkillPulse UI:  $uiUrl"
    Write-Host "Press Ctrl+C to stop the demo and its API process."

    $uiArguments = @(
        "-m", "streamlit", "run", "src/skillpulse/ui/app.py",
        "--server.address", "127.0.0.1",
        "--server.port", $UiPort.ToString(),
        "--server.headless", $headlessValue,
        "--browser.gatherUsageStats", "false"
    )
    if ($SmokeTest) {
        $uiProcess = Start-Process `
            -FilePath "python" `
            -ArgumentList $uiArguments `
            -WorkingDirectory $projectRoot `
            -WindowStyle Hidden `
            -PassThru
        $uiHealthUrl = "$uiUrl/_stcore/health"
        $uiDeadline = (Get-Date).AddSeconds(30)
        $uiHealthy = $false
        while ((Get-Date) -lt $uiDeadline) {
            if ($uiProcess.HasExited) {
                throw "SkillPulse UI exited before becoming healthy."
            }
            try {
                $uiHealth = Invoke-WebRequest -Uri $uiHealthUrl -UseBasicParsing -TimeoutSec 2
                if ($uiHealth.StatusCode -eq 200) {
                    $uiHealthy = $true
                    break
                }
            }
            catch {
                Start-Sleep -Milliseconds 300
            }
        }
        if (-not $uiHealthy) {
            throw "SkillPulse UI did not become healthy within 30 seconds at $uiHealthUrl."
        }
        Write-Host "SkillPulse demo smoke test: OK"
        return
    }

    Invoke-PythonChecked -Arguments $uiArguments
}
finally {
    if ($null -ne $uiProcess -and -not $uiProcess.HasExited) {
        Stop-Process -Id $uiProcess.Id -ErrorAction SilentlyContinue
        $uiProcess.WaitForExit(5000) | Out-Null
    }
    if ($null -ne $apiProcess -and -not $apiProcess.HasExited) {
        Stop-Process -Id $apiProcess.Id -ErrorAction SilentlyContinue
        $apiProcess.WaitForExit(5000) | Out-Null
    }
    $env:SKILLPULSE_API_URL = $previousApiUrl
    Set-Location -LiteralPath $originalLocation
}
