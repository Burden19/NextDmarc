param(
    [switch]$SkipAudit
)

$ErrorActionPreference = "Stop"

$workspacePython = Join-Path $PSScriptRoot "../../.venv/Scripts/python.exe"
$pythonCommand = $null

if (Get-Command uv -ErrorAction SilentlyContinue) {
    $pythonCommand = "uv"
} elseif (Test-Path $workspacePython) {
    $pythonCommand = $workspacePython
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCommand = "python"
} else {
    throw "Neither 'uv' nor a Python interpreter is available."
}

function Invoke-QualityTool {
    param(
        [Parameter(Mandatory = $true)][string]$Module,
        [string[]]$Arguments = @()
    )

    if ($pythonCommand -eq "uv") {
        & uv run $Module @Arguments
    } else {
        & $pythonCommand -m $Module @Arguments
    }

    if ($LASTEXITCODE -ne 0) {
        throw "Quality gate command failed: $Module"
    }
}

$pythonFiles = Get-ChildItem -Path app, tests, scripts -Recurse -File -Filter *.py -ErrorAction SilentlyContinue
$hasPythonSources = ($pythonFiles | Measure-Object).Count -gt 0

Write-Host "[1/5] Ruff lint + format check" -ForegroundColor Cyan
if ($hasPythonSources) {
    Invoke-QualityTool -Module ruff -Arguments @("check", "app", "tests", "scripts")
    Invoke-QualityTool -Module ruff -Arguments @("format", "--check", "app", "tests", "scripts")
} else {
    Write-Host "No Python files found; skipping Ruff checks." -ForegroundColor Yellow
}

Write-Host "[2/5] Mypy strict" -ForegroundColor Cyan
if ($hasPythonSources) {
    Invoke-QualityTool -Module mypy -Arguments @("--strict", "app")
} else {
    Write-Host "No Python files found; skipping Mypy." -ForegroundColor Yellow
}

Write-Host "[3/5] Bandit security scan" -ForegroundColor Cyan
if ($hasPythonSources) {
    Invoke-QualityTool -Module bandit -Arguments @("-r", "app", "-c", "pyproject.toml")
} else {
    Write-Host "No Python files found; skipping Bandit." -ForegroundColor Yellow
}

if (-not $SkipAudit) {
    Write-Host "[4/5] pip-audit dependency scan" -ForegroundColor Cyan
    Invoke-QualityTool -Module pip_audit -Arguments @(
        "--ignore-vuln",
        "CVE-2024-23342",
        "--ignore-vuln",
        "CVE-2026-4539"
    )
} else {
    Write-Host "[4/5] pip-audit skipped" -ForegroundColor Yellow
}

Write-Host "[5/5] Pytest with coverage" -ForegroundColor Cyan
if ($hasPythonSources) {
    Invoke-QualityTool -Module pytest -Arguments @()
} else {
    Write-Host "No Python files found; skipping Pytest." -ForegroundColor Yellow
}

Write-Host "All quality gates passed." -ForegroundColor Green
