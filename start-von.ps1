# start-von.ps1 — Start Von decision server
cd $PSScriptRoot
.\.venv\Scripts\Activate.ps1
Write-Host "Starting Von System 1 server on http://127.0.0.1:8765 ..." -ForegroundColor Green
von serve --host 127.0.0.1 --port 8765
