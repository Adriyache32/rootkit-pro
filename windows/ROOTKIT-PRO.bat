@echo off
title ROOT KIT PRO v2.1
color 0B
cls

echo.
echo   ██████╗ ██╗  ██╗ ███████╗ ████████╗ ██╗   ██╗
echo   ██╔══██╗██║  ██║ ██╔════╝ ╚══██╔══╝ ╚██╗ ██╔╝
echo   ██████╔╝███████║ █████╗      ██║      ╚████╔╝
echo   ██╔══██╗██╔══██║ ██╔══╝      ██║       ╚██╔╝
echo   ██║  ██║██║  ██║ ███████╗     ██║        ██║
echo   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚══════╝     ╚═╝        ╚═╝
echo.
echo   Universal Phone Root / Unlock Tool  v2.1
echo   ─────────────────────────────────────────
echo.

set APP_DIR=%USERPROFILE%\.rootkit-pro
set PYTHON=

:: Find Python
where python >nul 2>&1 && set PYTHON=python
where python3 >nul 2>&1 && set PYTHON=python3
if "%PYTHON%"=="" (
    echo   [ERROR] Python not found. Install Python 3.8+
    echo   https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Find browser
set BROWSER=
where msedge >nul 2>&1 && set BROWSER=msedge
where chrome >nul 2>&1 && set BROWSER=chrome
where firefox >nul 2>&1 && set BROWSER=firefox
where librewolf >nul 2>&1 && set BROWSER=librewolf

echo   [1/3] Starting API server...
start /b "" %PYTHON% "%APP_DIR%\backend\api.py"
timeout /t 2 /nobreak >nul

echo   [2/3] Opening interface...
if not "%BROWSER%"=="" (
    start "" %BROWSER% "http://localhost:20229"
) else (
    start "" "http://localhost:20229"
)

echo   [3/3] Running!
echo.
echo   ─────────────────────────────────────────
echo   Interface:  http://localhost:20229
echo   API Server: http://localhost:20229/api/*
echo.
echo   Close this window to stop.
echo   ─────────────────────────────────────────
echo.

:: Keep alive and handle cleanup
:loop
timeout /t 5 /nobreak >nul
tasklist /fi "WINDOWTITLE eq ROOT KIT PRO*" 2>nul | find /i "cmd.exe" >nul
if errorlevel 1 goto :cleanup
goto :loop

:cleanup
:: Kill API server
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :20229 ^| findstr LISTENING') do taskkill /f /pid %%a >nul 2>&1
echo   Server stopped.
