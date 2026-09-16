# Nightly pull of the live Black Bloc DB (drilled 2026-08-31; see docs/access/RECOVERY.md).
$flyctl = "$env:LOCALAPPDATA/Microsoft/WinGet/Packages/Fly-io.flyctl_Microsoft.Winget.Source_8wekyb3d8bbwe/flyctl.exe"
$dir = "$env:USERPROFILE\black-bloc-backups"
New-Item -ItemType Directory -Force $dir | Out-Null
$stamp = Get-Date -Format 'yyyy-MM-dd'
$out = Join-Path $dir "backup-$stamp.sqlite3"
$remote = "/data/black_bloc-nightly-snapshot.sqlite3"
& $flyctl ssh console --app black-bloc -C "python3 -m black_bloc.dbsnapshot" 2>&1 | Out-Null
& $flyctl ssh sftp get $remote $out --app black-bloc 2>&1 | Out-Null
& $flyctl ssh console --app black-bloc -C "rm $remote" 2>&1 | Out-Null
# The guide screenshots live beside the database on the same volume (black_bloc/guides.py:
# media_root). They are NOT in the snapshot, and a guide_media row without its file is a
# broken picture, so they travel with it or they are not recoverable.
$shots = Join-Path $dir "guides-$stamp.tar"
$remoteTar = "/data/guides-backup.tar"
& $flyctl ssh console --app black-bloc -C "sh -c 'cd /data && tar cf $remoteTar guides 2>/dev/null || true'" 2>&1 | Out-Null
& $flyctl ssh sftp get $remoteTar $shots --app black-bloc 2>&1 | Out-Null
& $flyctl ssh console --app black-bloc -C "rm -f $remoteTar" 2>&1 | Out-Null
if (Test-Path $shots) {
    Add-Content (Join-Path $dir 'backup.log') "$(Get-Date -Format o) shots $shots $((Get-Item $shots).Length) bytes"
    Get-ChildItem $dir -Filter 'guides-*.tar' | Sort-Object Name -Descending | Select-Object -Skip 14 | Remove-Item -Force -Confirm:$false
} else {
    # Not fatal: no guide has a picture until the first capture session, and an empty
    # /data/guides is the normal state before it. Never reported as a success.
    Add-Content (Join-Path $dir 'backup.log') "$(Get-Date -Format o) NO SHOTS (/data/guides did not come back - normal before the first capture session)"
}

if ((Test-Path $out) -and ((Get-Item $out).Length -gt 10000)) {
    Add-Content (Join-Path $dir 'backup.log') "$(Get-Date -Format o) ok $out $((Get-Item $out).Length) bytes"
    Get-ChildItem $dir -Filter 'backup-*.sqlite3' | Sort-Object Name -Descending | Select-Object -Skip 14 | Remove-Item -Force -Confirm:$false
} else {
    Add-Content (Join-Path $dir 'backup.log') "$(Get-Date -Format o) FAILED (missing or tiny file)"
    exit 1
}
