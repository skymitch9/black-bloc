# The one deploy path (incident 2026-09-01: an ungated chain deployed on a red suite).
# Refuses a dirty tree and a failing gate; escape hatch BLACKBLOC_SKIP_GATE=1 for a
# genuine emergency only. Appends the deploys.log line skeleton on success.
$ErrorActionPreference = "Stop"
$repo = Split-Path $PSScriptRoot -Parent
Set-Location $repo
$flyctl = "$env:LOCALAPPDATA/Microsoft/WinGet/Packages/Fly-io.flyctl_Microsoft.Winget.Source_8wekyb3d8bbwe/flyctl.exe"

$dirty = git status --porcelain
if ($dirty) { Write-Error "REFUSED: the working tree is dirty. Commit first.`n$dirty" }

if ($env:BLACKBLOC_SKIP_GATE -eq "1") {
    Write-Warning "GATE SKIPPED by BLACKBLOC_SKIP_GATE=1 - emergency use only"
} else {
    & .venv/Scripts/python -m ruff check .
    if ($LASTEXITCODE -ne 0) { Write-Error "REFUSED: ruff is not clean." }
    & .venv/Scripts/python -m pytest -q -n auto
    if ($LASTEXITCODE -ne 0) { Write-Error "REFUSED: the test suite is red." }
    foreach ($js in Get-ChildItem site/public/assets/*.js) {
        cmd /c "node --input-type=module --check < `"$($js.FullName)`""
        if ($LASTEXITCODE -ne 0) { Write-Error "REFUSED: $($js.Name) does not parse as an ES module." }
    }
    Get-NetTCPConnection -LocalPort 8788 -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique |
        ForEach-Object { try { Stop-Process -Id $_ -Force -Confirm:$false } catch {} }
    Start-Sleep 1
    $mock = Start-Process -FilePath node -ArgumentList 'site/mock/server.mjs' -PassThru -WindowStyle Hidden
    Start-Sleep 2
    node site/mock/check.mjs
    $contract = $LASTEXITCODE
    try { Stop-Process -Id $mock.Id -Force -Confirm:$false -ErrorAction Stop } catch {}
    if ($contract -ne 0) { Write-Error "REFUSED: check.mjs is not green." }
}

cmd /c "git push origin main 2>&1"
if ($LASTEXITCODE -ne 0) { Write-Error "REFUSED: the push failed." }

cmd /c "`"$flyctl`" deploy --app black-bloc --ha=false --remote-only --yes 2>&1"
if ($LASTEXITCODE -ne 0) { Write-Error "The deploy itself failed - fix before logging." }

$commit = git rev-parse --short HEAD
$stamp = Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"
Add-Content -Path docs\deploys.log -Encoding UTF8 -Value "$stamp  black-bloc  $commit  machine=85e744c4d959d8 region=lax  by=deploy.ps1  <EDIT: what shipped>; verified: <EDIT: what was checked>"
Write-Host "Deployed $commit. EDIT the new deploys.log line, then commit it."
