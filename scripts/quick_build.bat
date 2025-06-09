@echo off
REM ===============================================
REM DBLogiX - Quick Build Script per Windows
REM ===============================================

title DBLogiX Build Script

echo.
echo ===============================================
echo 🚀 DBLogiX - Quick Build Script
echo ===============================================
echo.

REM Controlla se Python è installato
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python non trovato nel PATH!
    echo    Installa Python da https://python.org/downloads/
    echo    Assicurati di aggiungere Python al PATH durante l'installazione
    pause
    exit /b 1
)

echo ✅ Python trovato
python --version

REM Controlla se pip è installato
pip --version >nul 2>&1
if errorlevel 1 (
    echo ❌ pip non trovato!
    pause
    exit /b 1
)

echo ✅ pip trovato

REM Installa/aggiorna dipendenze
echo.
echo 📦 Installazione dipendenze...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Errore durante l'installazione delle dipendenze
    pause
    exit /b 1
)

echo ✅ Dipendenze installate

REM Controlla PyInstaller
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo.
    echo 📦 Installazione PyInstaller...
    pip install pyinstaller>=6.3.0
    if errorlevel 1 (
        echo ❌ Errore durante l'installazione di PyInstaller
        pause
        exit /b 1
    )
)

echo ✅ PyInstaller disponibile

REM Avvia build automatico
echo.
echo 🏗️ Avvio build automatico...
echo.

python build_and_package.py

if errorlevel 1 (
    echo.
    echo ❌ Build fallito!
    echo    Controlla i messaggi di errore sopra
    pause
    exit /b 1
)

echo.
echo ✅ Build completato con successo!
echo.
echo 📁 Risultati disponibili in:
echo    📂 dist\DBLogiX\                    - Applicazione compilata
echo    💾 installer_output\                - Installer Windows  
echo    📦 release_package\                 - Pacchetto portable
echo.
echo 🌐 Dopo l'installazione, l'app sarà disponibile su:
echo    https://localhost:5000
echo.
echo 📖 Leggi BUILD_INSTRUCTIONS.md per dettagli completi
echo.

pause 