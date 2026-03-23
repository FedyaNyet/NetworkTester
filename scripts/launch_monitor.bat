@echo off
REM Network Monitor Launcher

echo Starting Network Monitor...
echo.

REM Get the directory where this script is located, then go up to project root
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%.."

REM Start the network monitor
echo Starting network monitor and WebSocket server...
uv run -m netmon.monitor

echo.
echo Network Monitor stopped.
echo.
pause
