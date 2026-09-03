$ErrorActionPreference = "Stop"
$fly = "$env:LOCALAPPDATA/Microsoft/WinGet/Packages/Fly-io.flyctl_Microsoft.Winget.Source_8wekyb3d8bbwe/flyctl.exe"
$t = & .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
if ($t.Length -lt 32) { throw "mint failed: value too short" }
& $fly secrets set --stage --app black-bloc "OPERATOR_READ_TOKEN=$t" | Out-Null
[Environment]::SetEnvironmentVariable('BLACK_BLOC_OPERATOR_TOKEN', $t, 'User')
Remove-Variable t
Write-Output "OPERATOR_READ_TOKEN staged on black-bloc (applies at the next deploy); BLACK_BLOC_OPERATOR_TOKEN set for this user. Value never printed."
