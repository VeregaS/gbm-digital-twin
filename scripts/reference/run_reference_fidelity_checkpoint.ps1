param(
    [switch]$SkipBootstrap,
    [string]$OutputDir = "results\cohort\reference-fidelity-v2",
    [string]$CacheRoot = "results\cache\reference-fidelity-v2",
    [int]$OptimizerIterations = 8,
    [int]$RoiPaddingVoxels = 10
)

$ErrorActionPreference = "Stop"

Write-Host "== Reference fidelity quality gates =="
$pytestArgs = @(
    "-m", "pytest",
    "tests\reference\test_tumortwin_adapter.py",
    "tests\reference\test_tumortwin_cellularity.py",
    "tests\workflows\test_reference_benchmark.py",
    "tests\workflows\test_reference_fidelity.py",
    "tests\workflows\test_mpmri_audit.py",
    "-v"
)
& python @pytestArgs
if ($LASTEXITCODE -ne 0) {
    throw "pytest failed with exit code $LASTEXITCODE"
}

& python -m ruff check .
if ($LASTEXITCODE -ne 0) {
    throw "ruff failed with exit code $LASTEXITCODE"
}

if (-not $SkipBootstrap) {
    Write-Host ""
    Write-Host "== Bootstrap pinned TumorTwin environment =="
    & powershell -ExecutionPolicy Bypass -File scripts\reference\bootstrap_tumortwin.ps1
    if ($LASTEXITCODE -ne 0) {
        throw "TumorTwin bootstrap failed with exit code $LASTEXITCODE"
    }
}

Write-Host ""
Write-Host "== TumorTwin synthetic smoke test =="
& python scripts\reference\smoke_test_tumortwin.py
if ($LASTEXITCODE -ne 0) {
    throw "TumorTwin smoke test failed with exit code $LASTEXITCODE"
}

$mpmriAudit = "results\cohort\mpmri-availability-v1\mpmri_availability.json"
if (-not (Test-Path $mpmriAudit)) {
    throw "mpMRI audit is missing: $mpmriAudit"
}

if (Test-Path $OutputDir) {
    throw "Reference fidelity output already exists: $OutputDir"
}

Write-Host ""
Write-Host "== TumorTwin reference fidelity v2 =="
$benchmarkArgs = @(
    "scripts\twin\benchmark_reference_fidelity.py",
    "--repo-root", ".",
    "--stage8-selection-root", "results\cohort\stage8-model-selection-v1",
    "--stage9-selection-root", "results\cohort\stage9-delayed-selection-v2",
    "--mpmri-audit", $mpmriAudit,
    "--tumortwin-python", ".reference\tumortwin-venv\Scripts\python.exe",
    "--cache-root", $CacheRoot,
    "--output-dir", $OutputDir,
    "--roi-padding-voxels", $RoiPaddingVoxels,
    "--optimizer-iterations", $OptimizerIterations
)
& python @benchmarkArgs
if ($LASTEXITCODE -ne 0) {
    throw "Reference fidelity benchmark failed with exit code $LASTEXITCODE"
}

Write-Host ""
Write-Host "Reference fidelity checkpoint completed."
