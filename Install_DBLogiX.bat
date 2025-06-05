@echo off
cls
color 0A

REM Imposta il percorso corretto dello script
cd /d "%~dp0"

echo ========================================
echo     DBLOGIX - INSTALLAZIONE DATABASE
echo ========================================
echo.
echo Percorso di lavoro: %CD%
echo.

REM Configurazione parametri database
set DB_HOST=192.168.1.32
set DB_PORT=3306
set DB_NAME=sys_datos
set DB_USER=user

REM Chiedi password MySQL
echo Inserisci la password per MySQL:
set /p DB_PASSWORD=Password: 

echo.
echo ========================================
echo Parametri di connessione:
echo ========================================
echo Host: %DB_HOST%
echo Porta: %DB_PORT%
echo Database: %DB_NAME%
echo Utente: %DB_USER%
echo ========================================
echo.

REM Verifica se il file SQL esiste
if not exist "Install_DBLogiX_Complete.sql" (
    echo ERRORE: File Install_DBLogiX_Complete.sql non trovato!
    echo Percorso corrente: %CD%
    echo.
    echo File presenti nella directory:
    dir *.sql /b
    echo.
    echo Assicurati che il file sia nella stessa cartella dello script.
    echo.
    color 0C
    pause
    exit /b 1
)

echo File SQL trovato: Install_DBLogiX_Complete.sql
echo Dimensione: 
for %%A in (Install_DBLogiX_Complete.sql) do echo %%~zA bytes
echo.

echo Avvio installazione database...
echo.
echo ========================================
echo ESECUZIONE SCRIPT SQL IN CORSO...
echo ========================================
echo.

REM Verifica se MySQL è accessibile
echo Verifica connessione MySQL...
mysql -h %DB_HOST% -P %DB_PORT% -u %DB_USER% -p%DB_PASSWORD% -e "SELECT 1;" %DB_NAME% >nul 2>&1

if errorlevel 1 (
    echo.
    color 0C
    echo ERRORE: Impossibile connettersi al database!
    echo Verifica:
    echo - Host: %DB_HOST% raggiungibile
    echo - Porta: %DB_PORT% aperta
    echo - Database: %DB_NAME% esistente
    echo - Credenziali: %DB_USER% / password corretti
    echo.
    pause
    exit /b 1
) else (
    echo Connessione MySQL: OK
    echo.
)

REM Esegui lo script SQL con output dettagliato
mysql -h %DB_HOST% -P %DB_PORT% -u %DB_USER% -p%DB_PASSWORD% %DB_NAME% < Install_DBLogiX_Complete.sql

REM Controlla il risultato
if errorlevel 1 (
    echo.
    echo ========================================
    echo ERRORE DURANTE L'INSTALLAZIONE!
    echo ========================================
    echo.
    echo Si è verificato un errore durante l'esecuzione dello script.
    echo Controlla i messaggi sopra per i dettagli.
    echo.
    echo Possibili cause:
    echo - Password errata
    echo - Database non esistente
    echo - Permessi insufficienti
    echo - Errori nelle query SQL
    echo.
    color 0C
) else (
    echo.
    echo ========================================
    echo INSTALLAZIONE COMPLETATA!
    echo ========================================
    echo.
    echo Tutte le tabelle sono state create con successo.
    echo Il sistema DBLogiX è ora pronto per l'uso.
    echo.
    color 0B
)

echo.
echo ========================================
echo RIEPILOGO TABELLE INSTALLATE:
echo ========================================
echo.
echo Tabelle Base:
echo - users (gestione utenti)
echo - scan_log (log scansioni)
echo - system_config (configurazioni sistema)
echo.
echo Tabelle Chat:
echo - chat_room (stanze chat)
echo - chat_message (messaggi chat)
echo.
echo Tabelle Task Management:
echo - tasks (gestione task)
echo - task_tickets (associazione task-ticket)
echo - task_ticket_scans (scansioni prodotti)
echo - task_notifications (notifiche task)
echo.
echo ========================================
echo CONTROLLO MESSAGGI DI DEBUG
echo ========================================
echo.
echo Controlla attentamente i messaggi sopra per:
echo - Errori di creazione tabelle
echo - Warning su foreign key
echo - Messaggi di stato delle varie fasi
echo - Conteggio finale tabelle create
echo.

REM Pausa per controllo messaggi
echo Premi un tasto per chiudere dopo aver controllato i messaggi...
pause >nul

REM Reset colore
color 07 