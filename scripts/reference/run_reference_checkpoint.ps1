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

python -m ruff check .

if (-not $SkipBootstrap) {
    Write-Host ""
    Write-Host "== Bootstrap pinned TumorTwin environment =="
    powershell -ExecutionPolicy Bypass -File `
      scripts\reference\bootstrap_tumortwin.ps1
}

Write-Host ""
Write-Host "== TumorTwin synthetic smoke test =="
python scripts\reference\smoke_test_tumortwin.py

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
    $benchmarkOutput = "results\cohort\reference-benchmark-v1"

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
}

Write-Host ""
Write-Host "Reference checkpoint completed."
