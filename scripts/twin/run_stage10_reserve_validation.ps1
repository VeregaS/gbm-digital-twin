param(
    [string]$PlanDir = "results\cohort\stage10-reserve-validation-plan-v1",
    [string]$OutputDir = "results\cohort\stage10-internal-validation-v1",
    [int]$Workers = 1
)

$ErrorActionPreference = "Stop"

Write-Host "== Stage 10 reserve-validation targeted tests =="
& python -m pytest -q tests\workflows\test_stage10_validation_protocol.py tests\workflows\test_stage10_validation_plan.py tests\workflows\test_stage10_validation.py tests\workflows\test_stage10_validation_report.py
if ($LASTEXITCODE -ne 0) {
    throw "Stage 10 reserve-validation targeted tests failed with exit code $LASTEXITCODE"
}

Write-Host ""
Write-Host "== Python quality gates =="
& python -m ruff check .
if ($LASTEXITCODE -ne 0) {
    throw "ruff failed with exit code $LASTEXITCODE"
}

& python -m pytest -q
if ($LASTEXITCODE -ne 0) {
    throw "pytest failed with exit code $LASTEXITCODE"
}

$required = @(
    "results\cohort\stage8-data-audit-v1\stage8_data_audit.json",
    "results\cohort\stage8-model-selection-v1\stage8_model_selection.json",
    "results\cohort\stage10-decoupled-selection-v1\stage10_decoupled_selection.json",
    "results\cohort\stage10-decoupled-selection-v1\stage10_decoupled_selection.sha256",
    "configs\research\stage10_frozen_model.yaml",
    "configs\research\stage10_reserve_validation.yaml"
)

foreach ($path in $required) {
    if (-not (Test-Path $path)) {
        throw "Required frozen input is missing: $path"
    }
}

if (-not (Test-Path $PlanDir)) {
    Write-Host ""
    Write-Host "== Seal Stage 10 reserve-validation plan =="
    & python scripts\twin\plan_stage10_validation.py --repo-root "." --output-dir $PlanDir
    if ($LASTEXITCODE -ne 0) {
        throw "Stage 10 validation planning failed with exit code $LASTEXITCODE"
    }
}
else {
    Write-Host ""
    Write-Host "Using existing sealed validation plan: $PlanDir"
}

if (Test-Path $OutputDir) {
    throw "Stage 10 validation output already exists: $OutputDir"
}

Write-Host ""
Write-Host "== Stage 10 reserve internal validation =="
& python scripts\twin\validate_stage10_model.py --repo-root "." --validation-plan-root $PlanDir --output-dir $OutputDir --workers $Workers
if ($LASTEXITCODE -ne 0) {
    throw "Stage 10 reserve validation failed with exit code $LASTEXITCODE"
}

Write-Host ""
Write-Host "== Render Stage 10 validation report =="
& python scripts\twin\render_stage10_validation_result.py --result-root $OutputDir
if ($LASTEXITCODE -ne 0) {
    throw "Stage 10 validation report rendering failed with exit code $LASTEXITCODE"
}

Write-Host ""
Write-Host "Stage 10 reserve-validation checkpoint completed."
Write-Host "Human-readable report: $OutputDir\STAGE10_VALIDATION_RESULT.md"
