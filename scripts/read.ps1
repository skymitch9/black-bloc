# Read one Black Bloc API path with the operator token (docs/access/operator-read.md).
param(
    [Parameter(Mandatory = $true)][string]$Path,
    [string]$Base = "https://blackbloc.heygabi.ai"
)
$ErrorActionPreference = "Stop"

$token = $env:BLACK_BLOC_OPERATOR_TOKEN
if (-not $token) {
    $token = [Environment]::GetEnvironmentVariable('BLACK_BLOC_OPERATOR_TOKEN', 'User')
}
if (-not $token) {
    Write-Error ("BLACK_BLOC_OPERATOR_TOKEN is not set on this machine, so nothing was read. " +
        "It holds the same value as the OPERATOR_READ_TOKEN secret on the bot, and it is the " +
        "owner who mints it: docs/access/operator-read.md has the one command that sets both " +
        "halves. Nothing is wrong with the bot or with your access.")
}

if (-not $Path.StartsWith("/")) { $Path = "/$Path" }
$url = "$($Base.TrimEnd('/'))$Path"

try {
    $answer = Invoke-RestMethod -Uri $url -Method Get -Headers @{ Authorization = "Bearer $token" }
    $answer | ConvertTo-Json -Depth 12
} catch {
    $body = $null
    try { $body = $_.ErrorDetails.Message } catch {}
    if (-not $body -and $_.Exception.Response) {
        $stream = $_.Exception.Response.GetResponseStream()
        $body = (New-Object System.IO.StreamReader($stream)).ReadToEnd()
    }
    $said = $null
    if ($body) { try { $said = ($body | ConvertFrom-Json).message } catch {} }
    if (-not $said) { $said = $_.Exception.Message }
    Write-Error "GET $url did not answer with data. It said: $said"
}
