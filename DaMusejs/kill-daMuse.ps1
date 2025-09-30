# DaMuse Process Killer Script
# This script finds and terminates all running DaMuse processes

Write-Host "🛑 DaMuse Process Killer" -ForegroundColor Red
Write-Host "=======================" -ForegroundColor Red

# Function to find DaMuse processes
function Get-DaMuseProcesses {
    $processes = Get-WmiObject Win32_Process | Where-Object {
        $_.CommandLine -like "*DaMuse.js*" -or 
        $_.CommandLine -like "*damuse*" -or
        ($_.Name -eq "node.exe" -and $_.CommandLine -like "*DaMuse*")
    }
    return $processes
}

# Find existing DaMuse processes
Write-Host "🔍 Searching for DaMuse processes..." -ForegroundColor Yellow
$daMuseProcesses = Get-DaMuseProcesses

if ($daMuseProcesses.Count -eq 0) {
    Write-Host "✅ No DaMuse processes found" -ForegroundColor Green
    exit 0
}

Write-Host "⚠️  Found $($daMuseProcesses.Count) DaMuse process(es):" -ForegroundColor Yellow
foreach ($process in $daMuseProcesses) {
    Write-Host "   PID: $($process.ProcessId) - $($process.CommandLine)" -ForegroundColor Yellow
}

# Ask for confirmation
$response = Read-Host "Do you want to kill all DaMuse processes? (y/N)"
if ($response -eq 'y' -or $response -eq 'Y') {
    Write-Host "🛑 Terminating DaMuse processes..." -ForegroundColor Red
    foreach ($process in $daMuseProcesses) {
        try {
            Stop-Process -Id $process.ProcessId -Force
            Write-Host "   ✅ Terminated PID: $($process.ProcessId)" -ForegroundColor Green
        } catch {
            Write-Host "   ❌ Failed to terminate PID: $($process.ProcessId) - $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    Write-Host "✅ All DaMuse processes terminated" -ForegroundColor Green
} else {
    Write-Host "❌ Operation cancelled" -ForegroundColor Yellow
}
