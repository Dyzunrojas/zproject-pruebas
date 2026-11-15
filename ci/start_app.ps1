param(
  [Parameter(Mandatory=$true)][string]$CodeDir,
  [Parameter(Mandatory=$true)][string]$EnvFile,
  [int]$BackendPort = 8100,
  [int]$FrontendPort = 5174
)
$ErrorActionPreference = 'Stop'
$backend  = Join-Path $CodeDir 'code\zproject-backend'
$frontend = Join-Path $CodeDir 'code\zproject-frontend'
$logs = Join-Path (Split-Path $CodeDir -Parent) 'logs'
New-Item -ItemType Directory -Force $logs | Out-Null

# .env del backend (viene de la credencial secreta de Jenkins)
Copy-Item $EnvFile (Join-Path $backend '.env') -Force

# Permitir el origen del frontend de Jenkins (CORS) y apuntar el frontend al backend
$env:CORSORIGINS = "[`"http://127.0.0.1:$FrontendPort`",`"http://localhost:$FrontendPort`"]"
$env:VITE_API_URL = "http://127.0.0.1:$BackendPort"

# Dependencias del frontend (solo la primera vez)
if (-not (Test-Path (Join-Path $frontend 'node_modules'))) {
  Push-Location $frontend
  npm ci --no-audit --no-fund
  if ($LASTEXITCODE -ne 0) { throw 'npm ci fallo' }
  Pop-Location
}

# Backend
$py = Join-Path $backend '.venv\Scripts\python.exe'
$be = Start-Process -FilePath $py `
  -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port',$BackendPort `
  -WorkingDirectory $backend -WindowStyle Hidden -PassThru `
  -RedirectStandardOutput (Join-Path $logs 'backend.out.log') `
  -RedirectStandardError  (Join-Path $logs 'backend.err.log')

# Frontend
$fe = Start-Process -FilePath 'cmd.exe' `
  -ArgumentList '/c',"npm run dev -- --host 127.0.0.1 --port $FrontendPort --strictPort" `
  -WorkingDirectory $frontend -WindowStyle Hidden -PassThru `
  -RedirectStandardOutput (Join-Path $logs 'frontend.out.log') `
  -RedirectStandardError  (Join-Path $logs 'frontend.err.log')

"$($be.Id)`n$($fe.Id)" | Set-Content (Join-Path $logs 'pids.txt')

function Wait-Url([string]$url, [int]$seconds) {
  $limit = (Get-Date).AddSeconds($seconds)
  while ((Get-Date) -lt $limit) {
    try {
      $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5
      if ($r.StatusCode -eq 200) { Write-Host "Listo: $url"; return }
    } catch { Start-Sleep -Seconds 2 }
  }
  throw "No respondio a tiempo: $url"
}

try {
  Wait-Url "http://127.0.0.1:$BackendPort/health/db" 60
  Wait-Url "http://127.0.0.1:$FrontendPort/" 90
} catch {
  Write-Host "--- backend.err.log ---"
  Get-Content (Join-Path $logs 'backend.err.log') -Tail 30 -ErrorAction SilentlyContinue
  Write-Host "--- frontend.err.log ---"
  Get-Content (Join-Path $logs 'frontend.err.log') -Tail 30 -ErrorAction SilentlyContinue
  throw
}