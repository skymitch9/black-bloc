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
if ((Test-Path $out) -and ((Get-Item $out).Length -gt 10000)) {
    Add-Content (Join-Path $dir 'backup.log') "$(Get-Date -Format o) ok $out $((Get-Item $out).Length) bytes"
    Get-ChildItem $dir -Filter 'backup-*.sqlite3' | Sort-Object Name -Descending | Select-Object -Skip 14 | Remove-Item -Force -Confirm:$false
} else {
    Add-Content (Join-Path $dir 'backup.log') "$(Get-Date -Format o) FAILED (missing or tiny file)"
    exit 1
}
