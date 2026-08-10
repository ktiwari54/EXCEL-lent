# Start Data Analyst Engine (API + Frontend)
$root = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path "$root\backend")) { $root = "C:\Users\PC\EXCEL-lent" }

Write-Host "Starting API on :8000 ..." -ForegroundColor Cyan
$api = Start-Process -FilePath "$root\backend\.venv\Scripts\python.exe" `
  -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8000" `
  -WorkingDirectory "$root\backend" -PassThru -WindowStyle Minimized

Start-Sleep -Seconds 2
try {
  $h = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 5
  Write-Host "API OK: $($h.Content)" -ForegroundColor Green
} catch {
  Write-Host "API failed to start: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "Starting Frontend on :3000 ..." -ForegroundColor Cyan
Start-Process -FilePath "npm" -ArgumentList "run","dev","--","-p","3000" `
  -WorkingDirectory "$root\frontend" -WindowStyle Minimized

Start-Sleep -Seconds 4
Start-Process "http://localhost:3000"
Write-Host "Open http://localhost:3000" -ForegroundColor Green
