[CmdletBinding()]
param(
    [string]$CodexHome,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

function Find-Python {
    $PyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($null -ne $PyLauncher) {
        return @($PyLauncher.Source, "-3")
    }
    $Python = Get-Command python -ErrorAction SilentlyContinue
    if ($null -ne $Python) {
        return @($Python.Source)
    }
    throw "Python 3.11 or newer is required. Install Python, then rerun this script."
}

$PythonCommand = Find-Python
$PythonExe = $PythonCommand[0]
$PythonPrefix = @()
if ($PythonCommand.Count -gt 1) {
    $PythonPrefix = $PythonCommand[1..($PythonCommand.Count - 1)]
}

& $PythonExe @PythonPrefix -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
if ($LASTEXITCODE -ne 0) {
    throw "Python 3.11 or newer is required."
}

& $PythonExe @PythonPrefix -m pip install $ProjectRoot
if ($LASTEXITCODE -ne 0) {
    throw "Package installation failed. Check network access and run: python -m pip install ."
}

& $PythonExe @PythonPrefix -m scales_pet validate (Join-Path $ProjectRoot "pet") --target desktop --strict
if ($LASTEXITCODE -ne 0) {
    throw "Pet validation failed. Do not install it. Follow docs/REPAIR.md."
}

$InstallArgs = @(
    "-m", "scales_pet", "install",
    "--source", (Join-Path $ProjectRoot "pet")
)
if ($CodexHome) {
    $InstallArgs += @("--codex-home", $CodexHome)
}
if ($DryRun) {
    $InstallArgs += "--dry-run"
}

& $PythonExe @PythonPrefix @InstallArgs
if ($LASTEXITCODE -ne 0) {
    throw "Installation failed. The transactional installer preserved or restored the prior pet."
}

Write-Host "Scales is ready. Refresh Settings > Pets in Codex."
