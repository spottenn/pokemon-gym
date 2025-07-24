Write-Host "Starting Pokemon Gym Streaming Setup..." -ForegroundColor Green
Write-Host ""

# Use non-default ports to avoid conflicts
$EvaluatorPort = 8081
$VitePort = 5174

# Activate virtual environment
& ".\.venv\Scripts\Activate.ps1"

# Start evaluator server in new PowerShell window with custom port
Write-Host "Starting evaluator server on port $EvaluatorPort..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& '.\.venv\Scripts\Activate.ps1'; python -m server.evaluator_server --port $EvaluatorPort" -WindowStyle Normal

# Wait for server to start
Start-Sleep -Seconds 3

# Start vision agent in new PowerShell window
Write-Host "Starting vision agent..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& '.\.venv\Scripts\Activate.ps1'; python agents\vision_agent.py --server-url http://localhost:$EvaluatorPort" -WindowStyle Normal

# Wait for agent to start
Start-Sleep -Seconds 2

# Start streaming dashboard in new PowerShell window with custom port
Write-Host "Starting streaming dashboard on port $VitePort..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd streaming-dashboard; yarn dev --port $VitePort" -WindowStyle Normal

Write-Host ""
Write-Host "All components started!" -ForegroundColor Green
Write-Host "- Evaluator Server: http://localhost:$EvaluatorPort" -ForegroundColor Cyan
Write-Host "- Vision Agent: Check second window" -ForegroundColor Cyan
Write-Host "- Streaming Dashboard: http://localhost:$VitePort" -ForegroundColor Cyan
Write-Host ""
Write-Host "This launcher will close automatically in 3 seconds..." -ForegroundColor Gray
Start-Sleep -Seconds 3
exit