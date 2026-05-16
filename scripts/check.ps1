$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

py -m unittest discover -s tests
py scripts/run_evals.py
