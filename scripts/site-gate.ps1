param([int]$Port = 8788, [switch]$LeaveHolders)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$repo = Split-Path $PSScriptRoot -Parent
Set-Location $repo

function Describe-Process([int]$id) {
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$id" -ErrorAction SilentlyContinue
    if (-not $proc) { return "pid $id (no longer running or not visible to this user)" }
    $started = if ($proc.CreationDate) { $proc.CreationDate.ToString("yyyy-MM-dd HH:mm:ss") } else { "unknown start" }
    $line = if ($proc.CommandLine) { $proc.CommandLine } else { $proc.Name }
    return "pid $id started $started - $line"
}

function Get-PortHolders([int]$port) {
    $found = @()
    foreach ($row in (netstat -ano -p TCP) + (netstat -ano -p TCPv6)) {
        if ($row -match "^\s*TCP\s+\S+:$port\s+\S+\s+LISTENING\s+(\d+)\s*$") { $found += [int]$Matches[1] }
    }
    $found += @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess)
    return @($found | Where-Object { $_ -gt 0 } | Sort-Object -Unique)
}

function Ask-Whoami([int]$port) {
    try {
        $answer = Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 -Uri "http://127.0.0.1:$port/api/mock/whoami"
        $body = $answer.Content | ConvertFrom-Json
        return @{ answered = $true; nonce = [string]$body.nonce; pid = $body.pid; started = $body.started_at }
    } catch [System.Net.WebException] {
        if ($_.Exception.Response) {
            return @{ answered = $true; nonce = [string]$_.Exception.Response.Headers["x-mock-nonce"]; pid = $null; started = $null }
        }
        return @{ answered = $false }
    }
}

function Tail-Log([string]$path) {
    if (Test-Path -LiteralPath $path) { return ((Get-Content -LiteralPath $path -Tail 15 -Encoding UTF8) -join "`n") }
    return "(no log written)"
}

$holders = Get-PortHolders $Port
foreach ($id in $holders) {
    if ($LeaveHolders) { Write-Host "site gate: leaving the process on port ${Port} alone (-LeaveHolders): $(Describe-Process $id)"; continue }
    Write-Host "site gate: stopping the process on port ${Port}: $(Describe-Process $id)"
    try { Stop-Process -Id $id -Force -Confirm:$false -ErrorAction Stop } catch { Write-Warning "could not stop pid ${id}: $($_.Exception.Message)" }
}
$mocks = @(Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match 'site[\\/]+mock[\\/]+server\.mjs' -and $holders -notcontains [int]$_.ProcessId })
foreach ($other in $mocks) {
    Write-Warning "another mock is running and was left alone (not on port $Port; it may be another session's): $(Describe-Process $other.ProcessId)"
}
if ($holders -and -not $LeaveHolders) { Start-Sleep 1 }
$still = if ($LeaveHolders) { @() } else { Get-PortHolders $Port }
if ($still) {
    Write-Error ("REFUSED: port $Port is still held after the sweep - " + (($still | ForEach-Object { Describe-Process $_ }) -join "; ") + ". Stop it and run again.")
}

$nonce = [guid]::NewGuid().ToString()
$logDir = Join-Path $env:TEMP "black-bloc-gate"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$outLog = Join-Path $logDir "mock-$Port.out.log"
$errLog = Join-Path $logDir "mock-$Port.err.log"
$priorPort = $env:MOCK_PORT
$env:MOCK_NONCE = $nonce
$env:MOCK_PORT = "$Port"
try {
    $mock = Start-Process -FilePath node -ArgumentList 'site/mock/server.mjs' -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput $outLog -RedirectStandardError $errLog
    $null = $mock.Handle
} finally {
    Remove-Item Env:MOCK_NONCE -ErrorAction SilentlyContinue
}

try {
    $seen = @{ answered = $false }
    $deadline = (Get-Date).AddSeconds(15)
    while ((Get-Date) -lt $deadline) {
        $seen = Ask-Whoami $Port
        if ($seen.answered -and $seen.nonce -eq $nonce) { break }
        if ($mock.HasExited) { break }
        Start-Sleep -Milliseconds 300
    }
    if (-not ($seen.answered -and $seen.nonce -eq $nonce)) {
        $why = if ($mock.HasExited) {
            "this gate's mock (pid $($mock.Id)) exited with code $($mock.ExitCode) - its log:`n$(Tail-Log $errLog)`n$(Tail-Log $outLog)"
        } else {
            "this gate's mock (pid $($mock.Id)) is still running but did not answer within 15 s - its log:`n$(Tail-Log $outLog)`n$(Tail-Log $errLog)"
        }
        if ($seen.answered) {
            $foreign = @(Get-PortHolders $Port | Where-Object { $_ -ne $mock.Id } | ForEach-Object { Describe-Process $_ })
            $who = if ($foreign) { $foreign -join "; " } elseif ($seen.pid) { Describe-Process $seen.pid } else { "a listener netstat could not name" }
            Write-Error "REFUSED: port $Port is answered by a process that is not this gate's mock - $who. Stop it and run again.`n$why"
        }
        Write-Error "REFUSED: no mock is answering on port $Port - $why"
    }
    Write-Host "site gate: the mock on port $Port is this gate's own (pid $($mock.Id), nonce $($nonce.Substring(0, 8)))"
    node site/mock/check.mjs
    $contract = $LASTEXITCODE
} finally {
    $env:MOCK_PORT = $priorPort
    if (-not $mock.HasExited) { try { Stop-Process -Id $mock.Id -Force -Confirm:$false -ErrorAction Stop } catch {} }
}
if ($contract -ne 0) { Write-Error "REFUSED: check.mjs is not green." }
