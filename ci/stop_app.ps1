param([Parameter(Mandatory=$true)][string]$LogDir)
$pidFile = Join-Path $LogDir 'pids.txt'
if (Test-Path $pidFile) {
  Get-Content $pidFile | Where-Object { $_ -match '^\d+$' } | ForEach-Object {
    taskkill /PID $_ /T /F 2>$null | Out-Null
  }
  Remove-Item $pidFile -Force
}
exit 0