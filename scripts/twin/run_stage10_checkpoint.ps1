param(
    [string]$OutputDir = "results\cohort\stage10-decoupled-selection-v1"
)

$ErrorActionPreference = "Stop"

Write-Host "== Stage 10 targeted tests =="
& python -m pytest -q tests\models\test_decoupled_damage.py tests\workflows\test_stage10_model_family.py tests\workflows\test_stage10_protocol.py tests\workflows\test_stage10_forecast.py tests\workflows\test_stage10_forecast_integration.py tests\workflows\test_stage10_selection.py
if ($LASTEXITCODE -ne 0) {
    throw "Stage 10 targeted tests failed with exit code $LASTEXITCODE"
}

Write-Host ""
Write-Host "== Full Python quality gates =="
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
    "results\cohort\stage8-internal-validation-v1\stage8_internal_validation.json",
    "results\cohort\stage9-delayed-selection-v2\stage9_delayed_selection.json",
    "results\cohort\reference-fidelity-v2\reference_fidelity.json"
)

foreach ($path in $required) {
    if (-not (Test-Path $path)) {
        throw "Required sealed input is missing: $path"
    }
}

if (Test-Path $OutputDir) {
    throw "Stage 10 output already exists: $OutputDir"
}

Write-Host ""
Write-Host "== Stage 10 decoupled-damage diagnostic =="
& python scripts\twin\select_stage10_decoupled_damage.py --repo-root "." --output-dir $OutputDir
if ($LASTEXITCODE -ne 0) {
    throw "Stage 10 selection failed with exit code $LASTEXITCODE"
}

Write-Host ""
Write-Host "== Render Stage 10 result report =="
& python scripts\twin\render_stage10_result.py --result-root $OutputDir
if ($LASTEXITCODE -ne 0) {
    throw "Stage 10 report rendering failed with exit code $LASTEXITCODE"
}

Write-Host ""
Write-Host "Stage 10 checkpoint completed."
Write-Host "Human-readable report: $OutputDir\STAGE10_RESULT.md"
