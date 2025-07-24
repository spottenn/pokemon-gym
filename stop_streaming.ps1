Write-Host "Stopping Pokemon Gym Streaming Components..." -ForegroundColor Red
Write-Host ""

# Stop processes by name
Write-Host "Stopping evaluator server..." -ForegroundColor Yellow
Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*server.evaluator_server*" } | Stop-Process -Force

Write-Host "Stopping vision agent..." -ForegroundColor Yellow  
Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*vision_agent.py*" } | Stop-Process -Force

Write-Host "Stopping streaming dashboard..." -ForegroundColor Yellow
Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*vite*" } | Stop-Process -Force

# Also stop by port if processes are still running
Write-Host "Stopping processes on ports 8081 and 5174..." -ForegroundColor Yellow
$EvaluatorPortProcess = Get-NetTCPConnection -LocalPort 8081 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess
$VitePortProcess = Get-NetTCPConnection -LocalPort 5174 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess

if ($EvaluatorPortProcess) {
    Stop-Process -Id $EvaluatorPortProcess -Force -ErrorAction SilentlyContinue
}

if ($VitePortProcess) {
    Stop-Process -Id $VitePortProcess -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "All streaming components stopped!" -ForegroundColor Green
Write-Host ""
Write-Host "This script will close automatically in 2 seconds..." -ForegroundColor Gray
Start-Sleep -Seconds 2
exit