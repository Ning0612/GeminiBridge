# Universal Python Project Task Scheduler Setup
# Creates a scheduled task to run a Python application at system startup
# 
# Usage:
#   .\setup_task_scheduler.ps1                          # Auto-detect from script location
#   .\setup_task_scheduler.ps1 -TaskName "MyApp"        # Custom task name
#   .\setup_task_scheduler.ps1 -ProjectPath "C:\MyApp"  # Custom project path

param(
    [string]$TaskName = "",
    [string]$ProjectPath = "",
    [string]$PythonScript = "main.py",
    [string]$Description = ""
)

$ErrorActionPreference = "Stop"

# ============================================================================
# Auto-detect Configuration
# ============================================================================

# If ProjectPath not specified, use script directory
if ([string]::IsNullOrWhiteSpace($ProjectPath)) {
    $ProjectPath = Split-Path -Parent $PSCommandPath
    Write-Host "[*] Auto-detected project path: $ProjectPath" -ForegroundColor Gray
}

# Convert to absolute path
$ProjectPath = (Resolve-Path $ProjectPath).Path

# If TaskName not specified, use project directory name
if ([string]::IsNullOrWhiteSpace($TaskName)) {
    $TaskName = Split-Path -Leaf $ProjectPath
    Write-Host "[*] Auto-detected task name: $TaskName" -ForegroundColor Gray
}

# If Description not specified, create a default one
if ([string]::IsNullOrWhiteSpace($Description)) {
    $Description = "$TaskName - Python application auto-start"
}

# ============================================================================
# Validate Configuration
# ============================================================================

Write-Host ""
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host " Python Project Task Scheduler Setup" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Task Name:    $TaskName" -ForegroundColor Gray
Write-Host "  Project Path: $ProjectPath" -ForegroundColor Gray
Write-Host "  Python Script: $PythonScript" -ForegroundColor Gray
Write-Host "  Description:  $Description" -ForegroundColor Gray
Write-Host ""

# Paths
$PythonExe = "$ProjectPath\.venv\Scripts\python.exe"
$MainScript = "$ProjectPath\$PythonScript"
$LogDir = "$ProjectPath\logs\task_scheduler"

# Validate Python virtual environment
if (-not (Test-Path $PythonExe)) {
    Write-Host "[X] Error: Python virtual environment not found" -ForegroundColor Red
    Write-Host "   Expected: $PythonExe" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Tip: Create virtual environment with:" -ForegroundColor Yellow
    Write-Host "   cd $ProjectPath" -ForegroundColor Gray
    Write-Host "   python -m venv .venv" -ForegroundColor Gray
    exit 1
}

# Validate Python script
if (-not (Test-Path $MainScript)) {
    Write-Host "[X] Error: Python script not found" -ForegroundColor Red
    Write-Host "   Expected: $MainScript" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Tip: Specify custom script with:" -ForegroundColor Yellow
    Write-Host "   .\setup_task_scheduler.ps1 -PythonScript 'your_script.py'" -ForegroundColor Gray
    exit 1
}

# Create log directory
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
    Write-Host "[OK] Created log directory: $LogDir" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Step 1: Removing existing task (if any)..." -ForegroundColor Yellow
$ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($ExistingTask) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "[OK] Existing task removed" -ForegroundColor Green
} else {
    Write-Host "[i] No existing task found" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Step 2: Creating scheduled task..." -ForegroundColor Yellow

# Create task action (what to run)
$Action = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument "`"$MainScript`"" `
    -WorkingDirectory $ProjectPath

# Create trigger (when to run)
$Trigger = New-ScheduledTaskTrigger -AtStartup

# Create settings
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Days 365)

# Create principal (run as current user with highest privileges)
$Principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType S4U `
    -RunLevel Highest

# Register the task
Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description $Description | Out-Null

Write-Host "[OK] Scheduled task created" -ForegroundColor Green

Write-Host ""
Write-Host "Step 3: Starting task..." -ForegroundColor Yellow

Start-ScheduledTask -TaskName $TaskName

Write-Host "[OK] Task start command sent" -ForegroundColor Green

Write-Host ""
Write-Host "Step 4: Verifying task and application status..." -ForegroundColor Yellow
Write-Host "Waiting for application to initialize..." -ForegroundColor Gray
Start-Sleep -Seconds 5

$TaskInfo = Get-ScheduledTaskInfo -TaskName $TaskName
$TaskState = (Get-ScheduledTask -TaskName $TaskName).State

Write-Host ""
Write-Host " Task Status:" -ForegroundColor Cyan
Write-Host "  State:            $TaskState" -ForegroundColor $(if ($TaskState -eq "Running") { "Green" } elseif ($TaskState -eq "Ready") { "Yellow" } else { "Gray" })
Write-Host "  Last Run:         $($TaskInfo.LastRunTime)" -ForegroundColor Gray
Write-Host "  Last Result:      $($TaskInfo.LastTaskResult)" -ForegroundColor Gray

# Check if Python process is running
Write-Host ""
Write-Host " Python Processes:" -ForegroundColor Cyan
$PythonProcesses = Get-Process python* -ErrorAction SilentlyContinue
if ($PythonProcesses) {
    $PythonProcesses | ForEach-Object {
        Write-Host "  [OK] PID $($_.Id) - $([math]::Round($_.WorkingSet/1MB, 2)) MB" -ForegroundColor Green
    }
} else {
    Write-Host "  [!]  No Python processes found" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($PythonProcesses) {
    Write-Host "[OK] Setup Complete - Application Running!" -ForegroundColor Green
} else {
    Write-Host "[!]  Setup Complete - Application May Need Manual Start" -ForegroundColor Yellow
}
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host " Task Details:" -ForegroundColor Cyan
Write-Host "  Name:       $TaskName" -ForegroundColor Gray
Write-Host "  Python:     $PythonExe" -ForegroundColor Gray
Write-Host "  Script:     $MainScript" -ForegroundColor Gray
Write-Host "  Work Dir:   $ProjectPath" -ForegroundColor Gray
Write-Host "  Logs:       $LogDir" -ForegroundColor Gray
Write-Host ""
Write-Host " Management Commands:" -ForegroundColor Yellow
Write-Host "  View task:     Get-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
Write-Host "  Start task:    Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
Write-Host "  Stop task:     Stop-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
Write-Host "  Check status:  Get-ScheduledTaskInfo -TaskName '$TaskName'" -ForegroundColor Gray
Write-Host "  Remove task:   Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false" -ForegroundColor Gray
Write-Host ""
Write-Host "[*] Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Task will auto-start on next system boot" -ForegroundColor Gray
Write-Host "  2. Monitor logs at: $LogDir" -ForegroundColor Gray
Write-Host "  3. Manage via GUI: taskschd.msc" -ForegroundColor Gray
Write-Host ""
