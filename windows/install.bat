@echo off
title ROOT KIT PRO - Windows Installer v2.1
color 0B
cls

echo.
echo   ROOT KIT PRO v2.1 - Windows Installer
echo   ═══════════════════════════════════════
echo.

:: Check admin
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo   [!] Run as Administrator for full install
    echo   [i] Continuing without admin...
    echo.
)

:: Find Python
set PYTHON=
where python >nul 2>&1 && set PYTHON=python
where python3 >nul 2>&1 && set PYTHON=python3
if "%PYTHON%"=="" (
    echo   [!] Python not found. Installing...
    echo   [i] Downloading Python 3.12...
    curl -L -o "%TEMP%\python-installer.exe" "https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe" 2>nul
    if exist "%TEMP%\python-installer.exe" (
        "%TEMP%\python-installer.exe" /passive InstallAllUsers=0 PrependPath=1 Include_test=0
        set PYTHON=python
        echo   [OK] Python installed
    ) else (
        echo   [FAIL] Could not download Python
        echo   [i] Install manually: https://www.python.org/downloads/
        pause
        exit /b 1
    )
)
echo   [OK] Python: %PYTHON%

:: Find ADB
set ADB=
if exist "%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe" (
    set ADB=%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe
)
if exist "C:\platform-tools\adb.exe" set ADB=C:\platform-tools\adb.exe
if "%ADB%"=="" (
    echo.
    echo   [!] ADB not found. Installing platform-tools...
    curl -L -o "%TEMP%\platform-tools.zip" "https://dl.google.com/android/repository/platform-tools-latest-windows.zip" 2>nul
    if exist "%TEMP%\platform-tools.zip" (
        mkdir "%USERPROFILE%\platform-tools" 2>nul
        powershell -command "Expand-Archive -Path '%TEMP%\platform-tools.zip' -DestinationPath '%USERPROFILE%' -Force" 2>nul
        set ADB=%USERPROFILE%\platform-tools\adb.exe
        echo   [OK] ADB installed to %USERPROFILE%\platform-tools\
        echo   [i] Add to PATH: %%USERPROFILE%%\platform-tools
    ) else (
        echo   [FAIL] Could not download ADB
        echo   [i] Install manually: https://developer.android.com/tools/releases/platform-tools
    )
) else (
    echo   [OK] ADB: %ADB%
)

:: Setup directory
echo.
echo   [i] Setting up %USERPROFILE%\.rootkit-pro...
mkdir "%USERPROFILE%\.rootkit-pro" 2>nul
mkdir "%USERPROFILE%\.rootkit-pro\html" 2>nul
mkdir "%USERPROFILE%\.rootkit-pro\backend" 2>nul
mkdir "%USERPROFILE%\.rootkit-pro\windows" 2>nul

:: Copy files
echo   [i] Copying files...
copy /Y "%~dp0..\html\index.html" "%USERPROFILE%\.rootkit-pro\html\index.html" >nul 2>&1
copy /Y "%~dp0..\backend\api.py" "%USERPROFILE%\.rootkit-pro\backend\api.py" >nul 2>&1
copy /Y "%~dp0ROOTKIT-PRO.bat" "%USERPROFILE%\.rootkit-pro\windows\ROOTKIT-PRO.bat" >nul 2>&1
copy /Y "%~dp0rootkit-pro.ps1" "%USERPROFILE%\.rootkit-pro\windows\rootkit-pro.ps1" >nul 2>&1

:: Create desktop shortcut
echo   [i] Creating desktop shortcut...
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%TEMP%\shortcut.vbs"
echo Set oLink = oWS.CreateShortcut("%USERPROFILE%\Desktop\ROOT KIT PRO.lnk") >> "%TEMP%\shortcut.vbs"
echo oLink.TargetPath = "%USERPROFILE%\.rootkit-pro\windows\ROOTKIT-PRO.bat" >> "%TEMP%\shortcut.vbs"
echo oLink.WorkingDirectory = "%USERPROFILE%\.rootkit-pro\windows" >> "%TEMP%\shortcut.vbs"
echo oLink.Description = "ROOT KIT PRO v2.1" >> "%TEMP%\shortcut.vbs"
echo oLink.WindowStyle = 1 >> "%TEMP%\shortcut.vbs"
cscript //nologo "%TEMP%\shortcut.vbs" >nul 2>&1
del "%TEMP%\shortcut.vbs" >nul 2>&1
del "%TEMP%\python-installer.exe" >nul 2>&1
del "%TEMP%\platform-tools.zip" >nul 2>&1

echo.
echo   ═══════════════════════════════════════
echo   ROOT KIT PRO v2.1 installed!
echo.
echo   Start methods:
echo     1. Desktop shortcut "ROOT KIT PRO"
echo     2. Double-click ROOTKIT-PRO.bat
echo     3. Run: powershell -File rootkit-pro.ps1
echo.
echo   Requirements:
echo     - USB Drivers for your phone
echo     - USB Debugging enabled
echo   ═══════════════════════════════════════
echo.
pause
