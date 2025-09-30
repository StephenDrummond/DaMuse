# DaMuse Process Management Script
# This script ensures only one instance of DaMuse runs at a time

Write-Host "🤖 DaMuse Process Manager" -ForegroundColor Cyan
Write-Host "=========================" -ForegroundColor Cyan

# Function to check for existing DaMuse processes
function Get-DaMuseProcesses {
    $processes = Get-WmiObject Win32_Process | Where-Object {
        $_.CommandLine -like "*DaMuse.js*" -or 
        $_.CommandLine -like "*damuse*" -or
        ($_.Name -eq "node.exe" -and $_.CommandLine -like "*DaMuse*")
    }
    return $processes
}

# Check for existing DaMuse processes
Write-Host "🔍 Checking for existing DaMuse processes..." -ForegroundColor Yellow
$existingProcesses = Get-DaMuseProcesses

if ($existingProcesses.Count -gt 0) {
    Write-Host "⚠️  Found $($existingProcesses.Count) existing DaMuse process(es):" -ForegroundColor Red
    foreach ($process in $existingProcesses) {
        Write-Host "   PID: $($process.ProcessId) - $($process.CommandLine)" -ForegroundColor Red
    }
    
    $response = Read-Host "Do you want to kill existing processes and start fresh? (y/N)"
    if ($response -eq 'y' -or $response -eq 'Y') {
        Write-Host "🛑 Terminating existing DaMuse processes..." -ForegroundColor Yellow
        foreach ($process in $existingProcesses) {
            try {
                Stop-Process -Id $process.ProcessId -Force
                Write-Host "   ✅ Terminated PID: $($process.ProcessId)" -ForegroundColor Green
            } catch {
                Write-Host "   ❌ Failed to terminate PID: $($process.ProcessId) - $($_.Exception.Message)" -ForegroundColor Red
            }
        }
        Start-Sleep -Seconds 2
    } else {
        Write-Host "❌ Cannot start DaMuse - other instances are running" -ForegroundColor Red
        Write-Host "Please stop existing instances first or choose 'y' to kill them" -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "✅ No existing DaMuse processes found" -ForegroundColor Green
}

# Check if we're in the correct directory
$currentDir = Get-Location
$expectedDir = "G:\GitHub\DaMuse\DaMusejs"

if ($currentDir.Path -ne $expectedDir) {
    Write-Host "📁 Changing to DaMuse directory..." -ForegroundColor Yellow
    Set-Location $expectedDir
}

# Verify required files exist
if (-not (Test-Path "DaMuse.js")) {
    Write-Host "❌ DaMuse.js not found in current directory" -ForegroundColor Red
    Write-Host "Current directory: $((Get-Location).Path)" -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path "package.json")) {
    Write-Host "❌ package.json not found in current directory" -ForegroundColor Red
    exit 1
}

# Start DaMuse
Write-Host "🚀 Starting DaMuse..." -ForegroundColor Green
Write-Host "📁 Working directory: $((Get-Location).Path)" -ForegroundColor Gray
Write-Host "⏰ Start time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host ""

try {
    # Start the bot
    npm start
} catch {
    Write-Host "❌ Failed to start DaMuse: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
