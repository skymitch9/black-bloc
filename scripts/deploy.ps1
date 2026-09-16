# The one deploy path (incident 2026-09-01: an ungated chain deployed on a red suite).
# Refuses a dirty tree and a failing gate; escape hatch BLACKBLOC_SKIP_GATE=1 for a
# genuine emergency only. Appends the deploys.log line skeleton on success.
# It also writes and commits site/public/assets/release.json FIRST, so the tree the
# check-clean gate looks at is clean and the file ships inside the image.
$ErrorActionPreference = "Stop"
$repo = Split-Path $PSScriptRoot -Parent
Set-Location $repo
$flyctl = "$env:LOCALAPPDATA/Microsoft/WinGet/Packages/Fly-io.flyctl_Microsoft.Winget.Source_8wekyb3d8bbwe/flyctl.exe"

# Which features changed since the last deploy, so the boot can mark the guide screenshots
# of those features stale (guides-design §C4.2). The map lives in black_bloc/guides.py and is
# NEVER copied here; scripts/release_json.py is the only caller.
$logLine = (Get-Content docs\deploys.log -Encoding UTF8 | Where-Object { $_.Trim() } | Select-Object -Last 1)
if (-not $logLine) { Write-Error "REFUSED: docs\deploys.log has no line to diff against." }
$lastCommit = ($logLine -split '\s+')[2]
git cat-file -e "$lastCommit^{commit}" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Error "REFUSED: $lastCommit (column 3 of the last docs\deploys.log line) is not a commit in this tree, so this deploy cannot tell which features changed. Fix that line and run again."
}
$changed = git diff --name-only "$lastCommit..HEAD"
$releaseFile = "site/public/assets/release.json"
$changed | & .venv/Scripts/python scripts/release_json.py "$logLine" (git rev-parse --short HEAD) $releaseFile
if ($LASTEXITCODE -ne 0) { Write-Error "REFUSED: $releaseFile could not be written." }
if (git status --porcelain -- $releaseFile) {
    git add -- $releaseFile
    $release = ((Get-Content $releaseFile -Raw) | ConvertFrom-Json).release
    git commit -q -m "Release ${release}: release.json"
    if ($LASTEXITCODE -ne 0) { Write-Error "REFUSED: $releaseFile could not be committed." }
    Write-Host "Wrote and committed $releaseFile for $release."
}

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
