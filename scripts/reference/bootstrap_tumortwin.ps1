param(
    [string]$Python = "python",
    [string]$EnvironmentDir = ".reference\tumortwin-venv"
)

$ErrorActionPreference = "Stop"

$repoUrl = "https://github.com/OncologyModelingGroup/TumorTwin.git"
$commit = "bedf90a6d47ba48cf5cdb25901967d84730061d1"

if (-not (Test-Path $EnvironmentDir)) {
    & $Python -m venv $EnvironmentDir
}

$venvPython = Join-Path $EnvironmentDir "Scripts\python.exe"

& $venvPython -m pip install --upgrade pip setuptools wheel

$packageSpec = "git+$repoUrl@$commit"
& $venvPython -m pip install $packageSpec

& $venvPython -c "import tumortwin, torch, torchdiffeq, numpy; print('TumorTwin import OK'); print('python environment ready')"

$marker = Join-Path $EnvironmentDir "GBM_TWIN_TUMORTWIN_COMMIT.txt"
Set-Content -Path $marker -Value $commit -Encoding ascii

Write-Host ""
Write-Host "TumorTwin reference environment ready."
Write-Host "Pinned commit: $commit"
Write-Host "Python: $venvPython"
