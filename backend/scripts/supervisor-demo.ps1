param(
    [switch]$SkipTests,
    [string]$ReportPath = "artifacts/supervisor-progress-latest.md"
)

$ErrorActionPreference = "Stop"

function Resolve-PythonCommand {
    $workspacePython = Join-Path $PSScriptRoot "../../.venv/Scripts/python.exe"

    if (Get-Command uv -ErrorAction SilentlyContinue) {
        return "uv"
    }

    if (Test-Path $workspacePython) {
        return (Resolve-Path $workspacePython).Path
    }

    if (Get-Command python -ErrorAction SilentlyContinue) {
        return "python"
    }

    throw "Neither 'uv' nor a Python interpreter is available."
}

function Get-PlanPhaseStatus {
    param(
        [Parameter(Mandatory = $true)][string]$PlanFilePath
    )

    if (-not (Test-Path $PlanFilePath)) {
        return @()
    }

    $phases = @()
    $current = $null

    foreach ($line in Get-Content -Path $PlanFilePath) {
        if ($line -match '^\s*\d+\.\s+Phase\s+(?<id>\d+)\s+-\s+(?<name>.+?)\s*(\(|$)') {
            if ($null -ne $current) {
                $phases += [pscustomobject]$current
            }

            $phaseId = [int]$matches['id']
            $phaseName = $matches['name'].Trim()
            $current = @{
                Id = $phaseId
                Name = $phaseName
                Completed = 0
                Total = 0
            }

            continue
        }

        if ($line -match '^\s*\[(?<state>[xX ])\]') {
            if ($null -ne $current) {
                $current['Total'] += 1
                if ($matches['state'].ToLower() -eq 'x') {
                    $current['Completed'] += 1
                }
            }
        }
    }

    if ($null -ne $current) {
        $phases += [pscustomobject]$current
    }

    return $phases
}

function Resolve-OutputPath {
    param(
        [Parameter(Mandatory = $true)][string]$BackendRoot,
        [Parameter(Mandatory = $true)][string]$RequestedPath
    )

    if ([System.IO.Path]::IsPathRooted($RequestedPath)) {
        return $RequestedPath
    }

    return (Join-Path $BackendRoot $RequestedPath)
}

$backendRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$repoRoot = (Resolve-Path (Join-Path $backendRoot "..")).Path
$planFilePath = Join-Path $backendRoot "plan-nextdmarc-backend.prompt.md"
$reportFilePath = Resolve-OutputPath -BackendRoot $backendRoot -RequestedPath $ReportPath
$reportDirectory = Split-Path -Path $reportFilePath -Parent

if (-not (Test-Path $reportDirectory)) {
    New-Item -Path $reportDirectory -ItemType Directory -Force | Out-Null
}

$pythonCommand = Resolve-PythonCommand
$showcaseTests = @(
    "tests/test_health.py",
    "tests/test_auth_api.py",
    "tests/test_domains_api.py",
    "tests/test_reports_records_api.py",
    "tests/test_analytics_api.py",
    "tests/test_alerts_api.py",
    "tests/test_alerts_websocket_api.py",
    "tests/test_rbac.py"
)

$pytestOutputLines = @()
$pytestExitCode = 0
$pytestSummary = "Tests were skipped."
$passedCount = $null
$duration = $null

Push-Location $backendRoot

try {
    if (-not $SkipTests) {
        Write-Host "Running supervisor showcase test suite..." -ForegroundColor Cyan

        if ($pythonCommand -eq "uv") {
            $pytestOutputLines = & uv run pytest @showcaseTests --no-cov -q 2>&1 | ForEach-Object { $_.ToString() }
        } else {
            $pytestOutputLines = & $pythonCommand -m pytest @showcaseTests --no-cov -q 2>&1 | ForEach-Object { $_.ToString() }
        }

        $pytestExitCode = $LASTEXITCODE
        $pytestSummaryLine = $pytestOutputLines | Where-Object {
            $_ -match '(passed|failed|error|errors|skipped)'
        } | Select-Object -Last 1

        if ($pytestSummaryLine) {
            $pytestSummary = $pytestSummaryLine.Trim()
        } else {
            $pytestSummary = "Pytest completed but summary line was not captured."
        }

        if ($pytestSummary -match '(?<passed>\d+)\s+passed(?:,\s*\d+\s+\w+)*\s+in\s+(?<duration>.+)$') {
            $passedCount = [int]$matches['passed']
            $duration = $matches['duration'].Trim()
        }
    }

    $phaseStatuses = Get-PlanPhaseStatus -PlanFilePath $planFilePath
    $generatedAt = Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"
    $branchName = (& git -C $repoRoot rev-parse --abbrev-ref HEAD 2>$null).Trim()
    $shortCommit = (& git -C $repoRoot rev-parse --short HEAD 2>$null).Trim()

    if ([string]::IsNullOrWhiteSpace($branchName)) {
        $branchName = "unknown"
    }

    if ([string]::IsNullOrWhiteSpace($shortCommit)) {
        $shortCommit = "unknown"
    }

    $testCommand = "python -m pytest " + ($showcaseTests -join " ") + " --no-cov -q"

    $reportLines = @()
    $reportLines += "# NextDmarc Backend Progress Snapshot"
    $reportLines += ""
    $reportLines += "- Generated: $generatedAt"
    $reportLines += "- Git branch: $branchName"
    $reportLines += "- Git commit: $shortCommit"
    $reportLines += "- Context: Supervisor checkpoint while backend delivery is still in progress"
    $reportLines += ""
    $reportLines += "## Verified showcase test run"
    $reportLines += "- Command: $testCommand"
    $reportLines += "- Result: $pytestSummary"

    if ($null -ne $passedCount) {
        $reportLines += "- Passed tests: $passedCount"
    }

    if ($null -ne $duration) {
        $reportLines += "- Runtime: $duration"
    }

    if ($SkipTests) {
        $reportLines += "- Note: This report was generated with -SkipTests."
    }

    $reportLines += ""
    $reportLines += "### Capabilities represented by this test slice"
    $reportLines += "- Service health and readiness checks"
    $reportLines += "- Auth flow (login, refresh, tenant registration)"
    $reportLines += "- Domain and report API behavior"
    $reportLines += "- Analytics endpoint behavior"
    $reportLines += "- Alert triage + realtime websocket path"
    $reportLines += "- RBAC authorization enforcement"
    $reportLines += ""
    $reportLines += "## Phase checklist status"

    if ($phaseStatuses.Count -eq 0) {
        $reportLines += "Plan file was not found, so phase summary could not be calculated."
    } else {
        $reportLines += "| Phase | Completion |"
        $reportLines += "| --- | --- |"

        foreach ($phase in $phaseStatuses | Sort-Object -Property Id) {
            $percentage = 0
            if ($phase.Total -gt 0) {
                $percentage = [Math]::Round(($phase.Completed / [double]$phase.Total) * 100)
            }

            $reportLines += "| Phase $($phase.Id) - $($phase.Name) | $($phase.Completed)/$($phase.Total) ($percentage%) |"
        }
    }

    $reportLines += ""
    $reportLines += "## What can be shown live right now"
    $reportLines += "1. Open this report and show objective progress metrics."
    $reportLines += "2. Run the same test command live to prove repeatability."
    $reportLines += "3. Open backend/README.md and walk through the implemented API groups and operations runbook."
    $reportLines += ""
    $reportLines += "## What is intentionally still pending"
    $reportLines += "- Phase 5 verification/release-readiness checklist is not complete yet."
    $reportLines += "- End-to-end and performance baseline sign-off still need to be finalized."

    Set-Content -Path $reportFilePath -Value ($reportLines -join "`r`n") -Encoding UTF8

    if ($pytestOutputLines.Count -gt 0) {
        $logPath = [System.IO.Path]::ChangeExtension($reportFilePath, ".log")
        Set-Content -Path $logPath -Value ($pytestOutputLines -join "`r`n") -Encoding UTF8
        Write-Host "Saved pytest log to: $logPath" -ForegroundColor DarkGray
    }

    Write-Host "Supervisor snapshot generated: $reportFilePath" -ForegroundColor Green

    if ((-not $SkipTests) -and $pytestExitCode -ne 0) {
        throw "Showcase tests failed. Report has been generated, but please review the pytest log before presenting."
    }
}
finally {
    Pop-Location
}