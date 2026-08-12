[CmdletBinding()]
param(
    [switch]$Install,
    [switch]$NoBrowser,
    [switch]$SmokeTest,
    [switch]$AllowLan,
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

function Get-PrivateIPv4Addresses {
    $addresses = foreach ($networkInterface in [System.Net.NetworkInformation.NetworkInterface]::GetAllNetworkInterfaces()) {
        if (
            $networkInterface.OperationalStatus -ne [System.Net.NetworkInformation.OperationalStatus]::Up -or
            $networkInterface.NetworkInterfaceType -eq [System.Net.NetworkInformation.NetworkInterfaceType]::Loopback
        ) {
            continue
        }
        foreach ($unicastAddress in $networkInterface.GetIPProperties().UnicastAddresses) {
            $address = $unicastAddress.Address
            if ($address.AddressFamily -ne [System.Net.Sockets.AddressFamily]::InterNetwork) {
                continue
            }
            $bytes = $address.GetAddressBytes()
            $isPrivate = (
                $bytes[0] -eq 10 -or
                ($bytes[0] -eq 172 -and $bytes[1] -ge 16 -and $bytes[1] -le 31) -or
                ($bytes[0] -eq 192 -and $bytes[1] -eq 168)
            )
            if ($isPrivate) {
                $address.ToString()
            }
        }
    }
    return @($addresses | Sort-Object -Unique)
}

try {
    Set-Location -LiteralPath $projectRoot

    if ($AllowLan -and $SmokeTest) {
        throw "-AllowLan cannot be combined with -SmokeTest. Use the default loopback smoke test."
    }

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
    $headlessValue = if ($NoBrowser -or $SmokeTest -or $AllowLan) { "true" } else { "false" }
    $uiBindAddress = if ($AllowLan) { "0.0.0.0" } else { "127.0.0.1" }
    $uiUrl = "http://127.0.0.1:$UiPort"
    Write-Host "SkillPulse API: $apiUrl/docs"
    Write-Host "SkillPulse UI (this computer): $uiUrl"
    if ($AllowLan) {
        Write-Warning "LAN review mode exposes the Streamlit UI without TLS or authentication."
        Write-Warning "Use only a trusted private network and synthetic/redacted inputs; stop immediately after review."
        $lanAddresses = @(Get-PrivateIPv4Addresses)
        if ($lanAddresses.Count -eq 0) {
            Write-Warning "No private LAN IPv4 address was found. Do not use port forwarding or a public tunnel."
        }
        else {
            foreach ($lanAddress in $lanAddresses) {
                Write-Host "SkillPulse UI (physical device): http://${lanAddress}:$UiPort"
            }
        }
    }
    Write-Host "Press Ctrl+C to stop the demo and its API process."

    $uiArguments = @(
        "-m", "streamlit", "run", "src/skillpulse/ui/app.py",
        "--server.address", $uiBindAddress,
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
