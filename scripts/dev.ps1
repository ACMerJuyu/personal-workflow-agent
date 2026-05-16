$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match "^\s*#" -or $_ -notmatch "=") {
            return
        }
        $name, $value = $_.Split("=", 2)
        [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim(), "Process")
    }
}

$hostName = if ($env:APP_HOST) { $env:APP_HOST } else { "127.0.0.1" }
$port = if ($env:APP_PORT) { $env:APP_PORT } else { "8010" }

py scripts\init_db.py
Write-Host "Starting Personal Workflow Agent on http://$hostName`:$port/dashboard"
py -m uvicorn api:app --reload --host $hostName --port $port
