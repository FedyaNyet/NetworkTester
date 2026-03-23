# PowerShell script to create a desktop shortcut for the Network Monitor

$WScriptShell = New-Object -ComObject WScript.Shell
$Desktop = [System.Environment]::GetFolderPath('Desktop')
$ShortcutPath = Join-Path $Desktop "Network Monitor.lnk"

# Resolve project root (parent of the scripts/ folder)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$TargetPath = Join-Path $ScriptDir "launch_monitor.bat"

# Create the shortcut
$Shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetPath
$Shortcut.WorkingDirectory = $ProjectRoot
$Shortcut.Description = "Launch Network Monitor with Overlay"
$Shortcut.IconLocation = "shell32.dll,18"
$Shortcut.Save()

Write-Host "Desktop shortcut created successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Shortcut location: $ShortcutPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "Double-click 'Network Monitor' on your desktop to start!" -ForegroundColor Yellow
Write-Host ""
Read-Host "Press Enter to exit"
