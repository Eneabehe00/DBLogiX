@echo off
title DBLogiX - Kiosk Statico
color 0A
setlocal enabledelayedexpansion

echo ========================================
echo       DBLogiX - Kiosk Statico
echo ========================================
echo.

:: CONFIGURAZIONE MANUALE - MODIFICA QUI:
set TARGET_IP=192.168.1.26
:: MONITOR_NUMBER: 1=primo monitor, 2=secondo monitor, ecc.
set MONITOR_NUMBER=3
set KIOSK_URL=https://!TARGET_IP!:5000/auth/kiosk-login

echo IP Server: !TARGET_IP!
echo Monitor: !MONITOR_NUMBER!
echo URL Kiosk: !KIOSK_URL!
echo.
echo NOTA: Per cambiare IP o monitor, modifica questo file .bat
echo.

:: Calcola posizione monitor (assumendo monitor 1920x1080)
set WINDOW_X=0
set WINDOW_Y=0
if !MONITOR_NUMBER! EQU 2 (
    set WINDOW_X=1920
    set WINDOW_Y=0
    echo Posizionamento su secondo monitor ^(X: 1920^)
) else if !MONITOR_NUMBER! EQU 3 (
    set WINDOW_X=3840
    set WINDOW_Y=0
    echo Posizionamento su terzo monitor ^(X: 3840^)
) else (
    echo Posizionamento su primo monitor ^(X: 0^)
)

:: Chiudi Chrome esistenti
echo Chiudo Chrome esistenti...
taskkill /F /IM chrome.exe >nul 2>&1
timeout /t 2 /nobreak >nul

:: Trova Chrome
echo Cerco Chrome...
set CHROME_PATH=""
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe"
) else if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH="C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
) else if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH="%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
)

if "!CHROME_PATH!"=="" (
    echo ERRORE: Chrome non trovato!
    pause
    exit /b 1
)

echo Chrome trovato: !CHROME_PATH!
echo.

:: Prepara cartella dati temporanea unica per kiosk
set KIOSK_DATA_DIR=%TEMP%\DBLogiX_Kiosk_%RANDOM%
if exist "!KIOSK_DATA_DIR!" rmdir /s /q "!KIOSK_DATA_DIR!" >nul 2>&1
mkdir "!KIOSK_DATA_DIR!" >nul 2>&1

echo ========================================
echo Avvio Chrome Kiosk su Monitor !MONITOR_NUMBER!...
echo Coordinate: X=!WINDOW_X!, Y=!WINDOW_Y!
echo ========================================
echo.

:: Avvia Chrome in modalità kiosk con posizione specifica
start "" !CHROME_PATH! ^
    --kiosk ^
    --start-fullscreen ^
    --window-position=!WINDOW_X!,!WINDOW_Y! ^
    --window-size=1920,1080 ^
    --no-first-run ^
    --no-sandbox ^
    --test-type ^
    --disable-session-crashed-bubble ^
    --disable-infobars ^
    --disable-notifications ^
    --disable-save-password-bubble ^
    --disable-password-manager ^
    --disable-password-manager-reauthentication ^
    --password-store=basic ^
    --disable-web-security ^
    --disable-extensions ^
    --disable-plugins ^
    --disable-default-apps ^
    --disable-background-timer-throttling ^
    --disable-backgrounding-occluded-windows ^
    --disable-renderer-backgrounding ^
    --disable-dev-shm-usage ^
    --disable-gpu-sandbox ^
    --disable-ipc-flooding-protection ^
    --disable-extensions-http-throttling ^
    --disable-blink-features=AutomationControlled ^
    --disable-features=VizDisplayCompositor,TranslateUI,BlinkGenPropertyTrees ^
    --ignore-ssl-errors ^
    --ignore-certificate-errors ^
    --ignore-certificate-errors-spki-list ^
    --ignore-certificate-policy-errors ^
    --ignore-ssl-errors-list ^
    --allow-running-insecure-content ^
    --allow-insecure-localhost ^
    --disable-ssl-false-start ^
    --user-data-dir="!KIOSK_DATA_DIR!" ^
    "!KIOSK_URL!"

:: Attendi un momento per l'avvio di Chrome
timeout /t 3 /nobreak >nul

:: Usa PowerShell per forzare la finestra sul monitor corretto
echo Forzo posizionamento finestra...
powershell -Command "& {Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public class Win32 { [DllImport(\"user32.dll\")] public static extern IntPtr FindWindow(string lpClassName, string lpWindowName); [DllImport(\"user32.dll\")] public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags); }'; $hwnd = [Win32]::FindWindow('Chrome_WidgetWin_1', $null); if ($hwnd -ne [IntPtr]::Zero) { [Win32]::SetWindowPos($hwnd, [IntPtr]::Zero, !WINDOW_X!, !WINDOW_Y!, 1920, 1080, 0x0040); Write-Host 'Finestra spostata sul monitor !MONITOR_NUMBER!' } else { Write-Host 'Finestra Chrome non trovata' }}"

echo.
echo ✓ Chrome avviato in modalità kiosk!
echo ✓ URL: !KIOSK_URL!
echo ✓ IP Server: !TARGET_IP!
echo ✓ Monitor: !MONITOR_NUMBER! ^(X: !WINDOW_X!, Y: !WINDOW_Y!^)
echo.
echo Per uscire dal kiosk: Alt+F4 o Ctrl+Alt+T
echo.
echo IMPORTANTE: Se i monitor hanno risoluzioni diverse da 1920x1080,
echo modifica le coordinate WINDOW_X nel file .bat
echo.
timeout /t 3 /nobreak >nul
exit 