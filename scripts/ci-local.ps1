param(
    [ValidateSet("", "tests", "lint", "site")][string]$Only = "",
    [switch]$Rebuild,
    [string]$FakeNow = "",
    [string]$Ref = "",
    [int]$Cpus = 0
)
$ErrorActionPreference = "Continue"
$repo = Split-Path $PSScriptRoot -Parent
Set-Location $repo

docker info --format "{{.OSType}}" 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "CI MIRROR NOT RUN: Docker is not answering. Start Docker Desktop and run again."
    exit 3
}

$hash = (Get-FileHash -Algorithm SHA256 (Join-Path $repo "pyproject.toml")).Hash.Substring(0, 12).ToLower()
$dockerfileHash = (Get-FileHash -Algorithm SHA256 (Join-Path $repo "Dockerfile.ci")).Hash.Substring(0, 4).ToLower()
$image = "black-bloc-ci:$hash$dockerfileHash"
docker image inspect $image 2>$null | Out-Null
if ($Rebuild -or $LASTEXITCODE -ne 0) {
    Write-Host "== Building $image (pyproject.toml or Dockerfile.ci changed, or -Rebuild)"
    $t0 = Get-Date
    $env:DOCKER_BUILDKIT = "1"
    docker build -f Dockerfile.ci -t $image .
    if ($LASTEXITCODE -ne 0) { Write-Host "CI MIRROR NOT RUN: the image did not build (output above)."; exit 3 }
    Write-Host ("== Built $image in {0:N0}s" -f ((Get-Date) - $t0).TotalSeconds)
}

$source = $repo
$scratch = $null
if ($Ref) {
    $sha = (git rev-parse --verify "$Ref^{commit}").Trim()
    if ($LASTEXITCODE -ne 0) { Write-Host "CI MIRROR NOT RUN: $Ref is not a commit."; exit 3 }
    $scratch = Join-Path ([IO.Path]::GetTempPath()) "black-bloc-ci-$($sha.Substring(0, 12))-$PID"
    New-Item -ItemType Directory -Force -Path $scratch | Out-Null
    git archive -o "$scratch.tar" $sha
    & "$env:SystemRoot\System32\tar.exe" -xf "$scratch.tar" -C $scratch
    $unpacked = $LASTEXITCODE
    Remove-Item -LiteralPath "$scratch.tar" -Force
    if ($unpacked -ne 0) { Write-Host "CI MIRROR NOT RUN: could not unpack $sha into $scratch."; exit 3 }
    $source = $scratch
    Write-Host "== Mirroring commit $($sha.Substring(0, 12)) (exported, not the working tree)"
}

$runArgs = @(
    "run", "--rm", "--init",
    "-v", "${source}:/src:ro",
    "--tmpfs", "/work:exec,size=1g",
    "--tmpfs", "/tmp:exec,size=4g",
    "-e", "PYTHONPYCACHEPREFIX=/tmp/pycache",
    "-e", "CI=true",
    "-w", "/work"
)
if ($Cpus -gt 0) { $runArgs += @("--cpuset-cpus", "0-$($Cpus - 1)") }
if ($FakeNow) { $env:BB_FAKE_NOW = $FakeNow }
foreach ($var in Get-ChildItem env: | Where-Object { $_.Name -like "BB_*" }) {
    $runArgs += @("-e", $var.Name.ToUpper())
}
$skip = @("./.git", "./.venv*", "./.claude", "./data/*", "./scripts/scan", "./.env", "./.env.enc",
    "__pycache__", ".pytest_cache", ".ruff_cache", "./node_modules") | ForEach-Object { "--exclude='$_'" }
$copy = "tar -C /src $($skip -join ' ') -cf - . | tar -xf - -C /work"
$runArgs += @($image, "bash", "-c", "$copy && exec python scripts/ci_local.py $Only")

$t0 = Get-Date
try {
    & docker @runArgs
    $code = $LASTEXITCODE
} finally {
    if ($scratch) { Remove-Item -LiteralPath $scratch -Recurse -Force -ErrorAction SilentlyContinue }
}
Write-Host ("== Wall time {0:N0}s (container start to exit)" -f ((Get-Date) - $t0).TotalSeconds)
exit $code
