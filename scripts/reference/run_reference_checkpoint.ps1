param(
    [switch]$SkipBootstrap,
    [switch]$RunBenchmark,
    [switch]$IncludeLmCalibration
)

$ErrorActionPreference = "Stop"

Write-Host "== Python quality gates =="
python -m pytest `
  tests\reference\test_tumortwin_adapter.py `
  tests\workflows\test_reference_benchmark.py `
  tests\workflows\test_mpmri_audit.py `
  tests\workflows\test_stage9_selection.py `
  tests\workflows\test_stage9_validation_plan.py `
  tests\workflows\test_stage9_split.py `
  -v
if ($LASTEXITCODE -ne 0) {
    throw "pytest failed with exit code $LASTEXITCODE"
}

python -m ruff check .
if ($LASTEXITCODE -ne 0) {
    throw "ruff failed with exit code $LASTEXITCODE"
}

if (-not $SkipBootstrap) {
    Write-Host ""
    Write-Host "== Bootstrap pinned TumorTwin environment =="
    powershell -ExecutionPolicy Bypass -File `
      scripts\reference\bootstrap_tumortwin.ps1
    if ($LASTEXITCODE -ne 0) {
        throw "TumorTwin bootstrap failed with exit code $LASTEXITCODE"
    }
}

Write-Host ""
Write-Host "== TumorTwin synthetic smoke test =="
python scripts\reference\smoke_test_tumortwin.py
if ($LASTEXITCODE -ne 0) {
    throw "TumorTwin smoke test failed with exit code $LASTEXITCODE"
}

$mpmriOutput = "results\cohort\mpmri-availability-v1"
if (Test-Path $mpmriOutput) {
    Write-Host ""
    Write-Host "mpMRI audit already exists: $mpmriOutput"
    Write-Host "Skipping audit rather than overwriting an existing artifact."
}
else {
    Write-Host ""
    Write-Host "== Local mpMRI availability audit =="
    python scripts\twin\audit_mpmri_availability.py `
      --repo-root . `
      --data-audit-root results\cohort\stage8-data-audit-v1 `
      --output-dir $mpmriOutput
}

if ($RunBenchmark) {
    $benchmarkOutput = if ($IncludeLmCalibration) {
        "results\cohort\reference-benchmark-full-v1"
    }
    else {
        "results\cohort\reference-benchmark-frozen-v1"
    }

    if (Test-Path $benchmarkOutput) {
        throw "Reference benchmark output already exists: $benchmarkOutput"
    }

    Write-Host ""
    Write-Host "== Published reference benchmark =="

    $args = @(
        "scripts\twin\benchmark_reference_models.py",
        "--repo-root", ".",
        "--stage8-selection-root",
        "results\cohort\stage8-model-selection-v1",
        "--stage9-selection-root",
        "results\cohort\stage9-delayed-selection-v2",
        "--tumortwin-python",
        ".reference\tumortwin-venv\Scripts\python.exe",
        "--cache-root",
        "results\cache\reference-tumortwin-v1",
        "--output-dir",
        $benchmarkOutput
    )

    if (-not $IncludeLmCalibration) {
        $args += "--frozen-only"
    }

    python @args
    if ($LASTEXITCODE -ne 0) {
        throw "Reference benchmark failed with exit code $LASTEXITCODE"
    }
}

Write-Host ""
Write-Host "Reference checkpoint completed."
