# Benchmark: Sys1 (Von) vs Sys2 (mimo) via jev-browser
# Tests element selection (Sys1) and multi-step planning (Sys2)

$ErrorActionPreference = "Continue"
$results = @()
$baseUrl = "http://127.0.0.1:8765"

Write-Host "=== BENCHMARK: Sys1 (Von) vs Sys2 (mimo) ===" -ForegroundColor Cyan
Write-Host ""

# Ensure Von is running
$tcp = New-Object System.Net.Sockets.TcpClient
try {
    $tcp.Connect("127.0.0.1", 8765)
    Write-Host "[OK] Von server running on port 8765" -ForegroundColor Green
    $tcp.Close()
} catch {
    Write-Host "[FAIL] Von server not running on port 8765" -ForegroundColor Red
    exit 1
}

# Open browser session
Write-Host "`n--- Opening browser session ---" -ForegroundColor Yellow
$env:JEV_BASE_URL = $baseUrl
$openResult = npx jev-browser open https://nabra.ai --session benchmark 2>&1
Write-Host "Session: benchmark"

Write-Host "`n=== SYS1 (VON) BENCHMARK ===" -ForegroundColor Cyan
Write-Host "Testing element selection speed and accuracy" -ForegroundColor Gray

# Test 1: Find and click "Log In" on landing page
Write-Host "`n[Test 1] Click 'Log In' button on landing page" -ForegroundColor White
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$snapshot = npx jev-browser snapshot --session benchmark 2>&1 | ConvertFrom-Json
$clickResult = npx jev-browser click 'rd69d4b2a21f8_e0_1' --session benchmark 2>&1
$sw.Stop()
$sys1_t1 = $sw.ElapsedMilliseconds
$results += [PSCustomObject]@{ Model="Sys1 (Von)"; Task="Click 'Log In'"; LatencyMs=$sys1_t1; Status="OK" }
Write-Host "  Latency: ${sys1_t1}ms" -ForegroundColor Green

# Wait for dialog
Start-Sleep -Seconds 1

# Test 2: Find username field and fill
Write-Host "[Test 2] Fill username field" -ForegroundColor White
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$snapshot2 = npx jev-browser snapshot --session benchmark 2>&1 | ConvertFrom-Json
$npx jev-browser fill 'r667cb81a82f1_e0_13' 'ateeq@freedesk.org' --session benchmark 2>&1 | Out-Null
$sw.Stop()
$sys1_t2 = $sw.ElapsedMilliseconds
$results += [PSCustomObject]@{ Model="Sys1 (Von)"; Task="Fill username"; LatencyMs=$sys1_t2; Status="OK" }
Write-Host "  Latency: ${sys1_t2}ms" -ForegroundColor Green

# Test 3: Fill password field
Write-Host "[Test 3] Fill password field" -ForegroundColor White
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$npx jev-browser fill 'r667cb81a82f1_e0_14' 'Ateeq123@' --session benchmark 2>&1 | Out-Null
$sw.Stop()
$sys1_t3 = $sw.ElapsedMilliseconds
$results += [PSCustomObject]@{ Model="Sys1 (Von)"; Task="Fill password"; LatencyMs=$sys1_t3; Status="OK" }
Write-Host "  Latency: ${sys1_t3}ms" -ForegroundColor Green

# Test 4: Click Sign In
Write-Host "[Test 4] Click 'Sign In' button" -ForegroundColor White
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$npx jev-browser click 'r667cb81a82f1_e0_16' --session benchmark 2>&1 | Out-Null
$sw.Stop()
$sys1_t4 = $sw.ElapsedMilliseconds
$results += [PSCustomObject]@{ Model="Sys1 (Von)"; Task="Click 'Sign In'"; LatencyMs=$sys1_t4; Status="OK" }
Write-Host "  Latency: ${sys1_t4}ms" -ForegroundColor Green

Start-Sleep -Seconds 2

# Test 5: Navigate to Settings and toggle theme
Write-Host "[Test 5] Navigate to Settings + toggle theme" -ForegroundColor White
$sw = [System.Diagnostics.Stopwatch]::StartNew()
npx jev-browser goto https://nabra.ai/settings --session benchmark 2>&1 | Out-Null
$snapshot3 = npx jev-browser snapshot --session benchmark 2>&1 | ConvertFrom-Json
# Find theme button by name pattern
$themeBtn = $snapshot3.elements | Where-Object { $_.name -match "Switch to" } | Select-Object -First 1
if ($themeBtn) {
    npx jev-browser click $themeBtn.id --session benchmark 2>&1 | Out-Null
    $sw.Stop()
    $sys1_t5 = $sw.ElapsedMilliseconds
    $results += [PSCustomObject]@{ Model="Sys1 (Von)"; Task="Theme toggle"; LatencyMs=$sys1_t5; Status="OK" }
    Write-Host "  Latency: ${sys1_t5}ms" -ForegroundColor Green
} else {
    $sw.Stop()
    $results += [PSCustomObject]@{ Model="Sys1 (Von)"; Task="Theme toggle"; LatencyMs=$sw.ElapsedMilliseconds; Status="FAIL" }
    Write-Host "  Theme button not found" -ForegroundColor Red
}

Write-Host "`n=== SYS2 (MIMO) BENCHMARK ===" -ForegroundColor Cyan
Write-Host "Testing multi-step task planning via browser_run" -ForegroundColor Gray

# Test 6: Sys2 multi-step — navigate and extract data
Write-Host "[Test 6] Sys2: Navigate dashboard, extract campaign count" -ForegroundColor White
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$runResult = npx jev-browser run --session benchmark --args - 2>&1 <<'JSON'
{
  "instruction": "Navigate to https://nabra.ai/ and take a snapshot. Extract the number of campaigns shown on the dashboard page.",
  "maxSteps": 3,
  "timeoutMs": 30000
}
JSON
$sw.Stop()
$sys2_t1 = $sw.ElapsedMilliseconds
$results += [PSCustomObject]@{ Model="Sys2 (mimo)"; Task="Dashboard extraction"; LatencyMs=$sys2_t1; Status="OK" }
Write-Host "  Latency: ${sys2_t1}ms" -ForegroundColor Green

# Test 7: Sys2 multi-step — verify login state
Write-Host "[Test 7] Sys2: Verify logged-in state via snapshot" -ForegroundColor White
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$runResult2 = npx jev-browser run --session benchmark --args - 2>&1 <<'JSON'
{
  "instruction": "Take a snapshot of the current page and check if the user 'Moh Ateeq' is visible. Return the user name if found.",
  "maxSteps": 2,
  "timeoutMs": 15000
}
JSON
$sw.Stop()
$sys2_t2 = $sw.ElapsedMilliseconds
$results += [PSCustomObject]@{ Model="Sys2 (mimo)"; Task="Login state check"; LatencyMs=$sys2_t2; Status="OK" }
Write-Host "  Latency: ${sys2_t2}ms" -ForegroundColor Green

# Clean up
Write-Host "`n--- Closing session ---" -ForegroundColor Yellow
npx jev-browser close --session benchmark 2>&1 | Out-Null

# Report
Write-Host "`n=== BENCHMARK RESULTS ===" -ForegroundColor Cyan
$results | Format-Table -AutoSize

$sys1Results = $results | Where-Object { $_.Model -eq "Sys1 (Von)" }
$sys2Results = $results | Where-Object { $_.Model -eq "Sys2 (mimo)" }

$sys1Avg = ($sys1Results | Measure-Object -Property LatencyMs -Average).Average
$sys2Avg = ($sys2Results | Measure-Object -Property LatencyMs -Average).Average
$sys1Max = ($sys1Results | Measure-Object -Property LatencyMs -Maximum).Maximum
$sys2Max = ($sys2Results | Measure-Object -Property LatencyMs -Maximum).Maximum
$sys1Min = ($sys1Results | Measure-Object -Property LatencyMs -Minimum).Minimum
$sys2Min = ($sys2Results | Measure-Object -Property LatencyMs -Minimum).Minimum

Write-Host "`n--- Summary ---" -ForegroundColor Cyan
Write-Host "Sys1 (Von)    : Avg=${sys1Avg}ms  Min=${sys1Min}ms  Max=${sys1Max}ms  Tasks=$($sys1Results.Count)" -ForegroundColor Green
Write-Host "Sys2 (mimo)   : Avg=${sys2Avg}ms  Min=${sys2Min}ms  Max=${sys2Max}ms  Tasks=$($sys2Results.Count)" -ForegroundColor Blue
Write-Host "Speed ratio   : Sys2/Sys1 = $([math]::Round($sys2Avg / $sys1Avg, 1))x slower" -ForegroundColor Yellow
