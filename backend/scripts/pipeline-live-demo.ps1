param(
    [switch]$SkipTests,
    [string]$ReportPath = "artifacts/pipeline-live-demo-latest.md"
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

function Invoke-PipelineProofTest {
    param(
        [Parameter(Mandatory = $true)][string]$PythonCommand,
        [Parameter(Mandatory = $true)][string]$Selector
    )

    if ($PythonCommand -eq "uv") {
        $output = & uv run pytest $Selector -q 2>&1 | ForEach-Object { $_.ToString() }
    } else {
        $output = & $PythonCommand -m pytest $Selector -q 2>&1 | ForEach-Object { $_.ToString() }
    }

    $exitCode = $LASTEXITCODE
    $summary = $output | Where-Object { $_ -match '(passed|failed|error|errors|skipped)' } | Select-Object -Last 1
    if (-not $summary) {
        $summary = "No pytest summary line captured"
    }

    return [pscustomobject]@{
        ExitCode = $exitCode
        Summary = $summary.Trim()
        Output = $output
    }
}

$backendRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$reportFilePath = Resolve-OutputPath -BackendRoot $backendRoot -RequestedPath $ReportPath
$reportDirectory = Split-Path -Path $reportFilePath -Parent

if (-not (Test-Path $reportDirectory)) {
    New-Item -Path $reportDirectory -ItemType Directory -Force | Out-Null
}

$stages = @(
    [pscustomobject]@{
        Name = "Collect"
        WorkerTask = "app.workers.tasks.collect.collect_mailbox_reports"
        Purpose = "Fetch unseen mailbox messages, apply idempotency, and upload report objects."
        KeyOutput = "fetched_messages, processed_messages, skipped_messages, uploaded_objects"
        ProofTest = "tests/test_collect_task.py::test_collect_task_applies_message_idempotency"
    },
    [pscustomobject]@{
        Name = "Parse"
        WorkerTask = "app.workers.tasks.parse.parse_report_object"
        Purpose = "Read report object, parse DMARC XML, persist report, and index records."
        KeyOutput = "report_id, report_db_id, record_count, indexed_count"
        ProofTest = "tests/test_parse_task.py::test_parse_task_pipeline_reads_parses_persists_and_indexes"
    },
    [pscustomobject]@{
        Name = "Analyze"
        WorkerTask = "app.workers.tasks.analysis.analyze_report_conformance"
        Purpose = "Compute SPF, DKIM, DMARC pass counts and conformance rate."
        KeyOutput = "total_records, dkim_pass_count, spf_pass_count, dmarc_pass_count, conformance_rate"
        ProofTest = "tests/test_analysis_task.py::test_analysis_worker_computes_metrics_and_enqueues_followups"
    },
    [pscustomobject]@{
        Name = "Correlate"
        WorkerTask = "app.workers.tasks.correlate.detect_correlations"
        Purpose = "Detect suspicious signals and create incidents for risky patterns."
        KeyOutput = "signals_detected, incidents_created, alerts_enqueued"
        ProofTest = "tests/test_correlate_task.py::test_correlate_task_enqueues_alert_dispatch_jobs"
    },
    [pscustomobject]@{
        Name = "Score"
        WorkerTask = "app.workers.tasks.score.compute_score"
        Purpose = "Compute tenant risk score and risk state with penalty breakdown."
        KeyOutput = "score, risk_state, conformance_penalty, dkim_penalty, spf_penalty"
        ProofTest = "infra/tests/test_score_task.py::test_compute_score_task_persists_current_and_history"
    },
    [pscustomobject]@{
        Name = "Recommend"
        WorkerTask = "app.workers.tasks.recommend.generate_recommendations"
        Purpose = "Generate remediation recommendations and maturity score."
        KeyOutput = "maturity_score, maturity_level, recommendations_count"
        ProofTest = "tests/test_recommend_task.py::test_recommend_task_persists_current_and_history"
    },
    [pscustomobject]@{
        Name = "Alert"
        WorkerTask = "app.workers.tasks.alert.create_and_dispatch_alert"
        Purpose = "Create alert, route to channels, store audit, and publish realtime events."
        KeyOutput = "target_channels, delivered_channels, failed_channels"
        ProofTest = "tests/test_alert_task.py::test_alert_worker_creates_and_dispatches_channels"
    },
    [pscustomobject]@{
        Name = "Collect-Parse Integration"
        WorkerTask = "collect -> parse"
        Purpose = "Prove handoff from mailbox collection to parser persistence and indexing."
        KeyOutput = "record_count, indexed_count, report_id"
        ProofTest = "tests/test_pipeline_integration.py::test_collect_parse_persist_index_integration"
    }
)

$pythonCommand = Resolve-PythonCommand
$results = @()
$failedStages = @()

Push-Location $backendRoot

try {
    $index = 0
    foreach ($stage in $stages) {
        $index += 1
        Write-Host "[$index/$($stages.Count)] Stage: $($stage.Name)" -ForegroundColor Cyan
        Write-Host "  Task: $($stage.WorkerTask)" -ForegroundColor DarkGray
        Write-Host "  Purpose: $($stage.Purpose)" -ForegroundColor DarkGray

        if ($SkipTests) {
            $results += [pscustomobject]@{
                Name = $stage.Name
                WorkerTask = $stage.WorkerTask
                Purpose = $stage.Purpose
                KeyOutput = $stage.KeyOutput
                ProofTest = $stage.ProofTest
                Status = "SKIPPED"
                Evidence = "Execution skipped by -SkipTests"
                RawOutput = @()
            }
            continue
        }

        $proof = Invoke-PipelineProofTest -PythonCommand $pythonCommand -Selector $stage.ProofTest
        $status = if ($proof.ExitCode -eq 0) { "PASS" } else { "FAIL" }

        if ($status -eq "FAIL") {
            $failedStages += $stage.Name
        }

        Write-Host "  Result: $status - $($proof.Summary)" -ForegroundColor $(if ($status -eq "PASS") { "Green" } else { "Red" })

        $results += [pscustomobject]@{
            Name = $stage.Name
            WorkerTask = $stage.WorkerTask
            Purpose = $stage.Purpose
            KeyOutput = $stage.KeyOutput
            ProofTest = $stage.ProofTest
            Status = $status
            Evidence = $proof.Summary
            RawOutput = $proof.Output
        }
    }

    $generatedAt = Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"
    $reportLines = @()
    $reportLines += "# NextDmarc Live Pipeline Proof"
    $reportLines += ""
    $reportLines += "- Generated: $generatedAt"
    $reportLines += "- Mode: " + $(if ($SkipTests) { "metadata-only" } else { "executed" })
    $reportLines += ""
    $reportLines += "## Stage by stage evidence"
    $reportLines += "| Stage | Worker task | What it does | Key output | Proof test | Status | Evidence |"
    $reportLines += "| --- | --- | --- | --- | --- | --- | --- |"

    foreach ($item in $results) {
        $reportLines += "| $($item.Name) | $($item.WorkerTask) | $($item.Purpose) | $($item.KeyOutput) | $($item.ProofTest) | $($item.Status) | $($item.Evidence) |"
    }

    if (-not $SkipTests) {
        $reportLines += ""
        $reportLines += "## Raw command used"
        $reportLines += "- pytest selectors executed individually with -q"
    }

    Set-Content -Path $reportFilePath -Value ($reportLines -join "`r`n") -Encoding UTF8

    $logPath = [System.IO.Path]::ChangeExtension($reportFilePath, ".log")
    $logLines = @()
    foreach ($item in $results) {
        if ($item.RawOutput.Count -eq 0) {
            continue
        }

        $logLines += "===== $($item.Name) | $($item.ProofTest) ====="
        $logLines += $item.RawOutput
        $logLines += ""
    }

    if ($logLines.Count -gt 0) {
        Set-Content -Path $logPath -Value ($logLines -join "`r`n") -Encoding UTF8
        Write-Host "Detailed stage logs saved to: $logPath" -ForegroundColor DarkGray
    }

    Write-Host "Pipeline demo report generated: $reportFilePath" -ForegroundColor Green

    if ($failedStages.Count -gt 0) {
        throw "Pipeline proof encountered failures in: $($failedStages -join ', ')"
    }
}
finally {
    Pop-Location
}