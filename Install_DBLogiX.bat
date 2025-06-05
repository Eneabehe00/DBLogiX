@echo off
cls
color 0B

REM Imposta il percorso corretto dello script
cd /d "%~dp0"

echo.
echo  ===============================================================================
echo  #                          DBLOGIX INSTALLER                                 #
echo  #                     Sistema di Gestione Task Avanzato                      #
echo  ===============================================================================
echo.
echo  Percorso di lavoro: %CD%
echo.

REM ===============================================================================
echo  +-----------------------------------------------------------------------------+
echo  ^|                        CONFIGURAZIONE DATABASE                             ^|
echo  +-----------------------------------------------------------------------------+
echo.

set DB_HOST=192.168.1.32
set DB_PORT=3306
set DB_NAME=sys_datos
set DB_USER=user

echo  Host............: %DB_HOST%
echo  Porta...........: %DB_PORT%
echo  Database........: %DB_NAME%
echo  Utente..........: %DB_USER%
echo.

REM ===============================================================================
echo  +-----------------------------------------------------------------------------+
echo  ^|                           AUTENTICAZIONE                                   ^|
echo  +-----------------------------------------------------------------------------+
echo.
echo  Inserisci la password per MySQL:
set /p DB_PASSWORD=     Password: 

echo.
echo  +-----------------------------------------------------------------------------+
echo  ^|                         RIEPILOGO CONNESSIONE                              ^|
echo  +-----------------------------------------------------------------------------+
echo.
echo   [OK] Host............: %DB_HOST%
echo   [OK] Porta...........: %DB_PORT%
echo   [OK] Database........: %DB_NAME%
echo   [OK] Utente..........: %DB_USER%
echo   [OK] Password........: [NASCOSTA]
echo.

REM ===============================================================================
echo  +-----------------------------------------------------------------------------+
echo  ^|                          VERIFICA PREREQUISITI                             ^|
echo  +-----------------------------------------------------------------------------+
echo.

REM Verifica file SQL
echo  Ricerca file Install_DBLogiX_Complete.sql...
if not exist "Install_DBLogiX_Complete.sql" (
    color 0C
    echo.
    echo  [ERRORE] File Install_DBLogiX_Complete.sql non trovato!
    echo.
    echo  Percorso corrente: %CD%
    echo  File SQL presenti:
    echo     +-----------------------------+
    dir *.sql /b 2>nul | findstr /v "^$" || echo     ^|      [NESSUN FILE SQL]      ^|
    echo     +-----------------------------+
    echo.
    echo  Assicurati che il file sia nella stessa cartella dello script.
    echo.
    pause
    exit /b 1
)

for %%A in (Install_DBLogiX_Complete.sql) do set FILE_SIZE=%%~zA
echo     [OK] File trovato: Install_DBLogiX_Complete.sql
echo     [OK] Dimensione: %FILE_SIZE% bytes
echo.

REM Verifica connessione MySQL
echo  Test connessione MySQL...
mysql -h %DB_HOST% -P %DB_PORT% -u %DB_USER% -p%DB_PASSWORD% -e "SELECT 1;" %DB_NAME% >nul 2>&1

if errorlevel 1 (
    color 0C
    echo.
    echo  [ERRORE] Impossibile connettersi al database!
    echo.
    echo  Verifica i seguenti parametri:
    echo     - Host %DB_HOST% raggiungibile
    echo     - Porta %DB_PORT% aperta  
    echo     - Database '%DB_NAME%' esistente
    echo     - Credenziali '%DB_USER%' corrette
    echo     - Password valida
    echo.
    pause
    exit /b 1
) else (
    echo     [OK] Connessione MySQL: SUCCESSO
    echo.
)

REM ===============================================================================
echo  +-----------------------------------------------------------------------------+
echo  ^|                        INSTALLAZIONE IN CORSO                              ^|
echo  +-----------------------------------------------------------------------------+
echo.

echo  Avvio installazione database DBLogiX...
echo  Esecuzione script SQL in corso...
echo.
echo  ===============================================================================
echo.

REM Esegui lo script SQL
mysql -h %DB_HOST% -P %DB_PORT% -u %DB_USER% -p%DB_PASSWORD% %DB_NAME% < Install_DBLogiX_Complete.sql

REM Controllo risultato
if errorlevel 1 (
    color 0C
    echo.
    echo  ===============================================================================
    echo  #                           INSTALLAZIONE FALLITA                          #
    echo  ===============================================================================
    echo.
    echo  Si e' verificato un errore durante l'esecuzione dello script.
    echo  Controlla i messaggi sopra per i dettagli dell'errore.
    echo.
    echo  Possibili cause:
    echo     - Password MySQL errata
    echo     - Database non esistente o inaccessibile
    echo     - Permessi insufficienti per l'utente
    echo     - Errori di sintassi nelle query SQL
    echo     - Problemi di rete con il server MySQL
    echo.
) else (
    color 0A
    echo.
    echo  ===============================================================================
    echo  #                          INSTALLAZIONE COMPLETATA                        #
    echo  ===============================================================================
    echo.
    echo  Tutte le tabelle sono state create con successo!
    echo  Il sistema DBLogiX e' ora pronto per l'uso.
    echo.
)

REM ===============================================================================
echo  +-----------------------------------------------------------------------------+
echo  ^|                       RIEPILOGO TABELLE INSTALLATE                         ^|
echo  +-----------------------------------------------------------------------------+
echo.
echo  TABELLE BASE:
echo     + users ........................ [Gestione utenti]
echo     + scan_log ..................... [Log scansioni]  
echo     + system_config ................ [Configurazioni sistema]
echo.
echo  SISTEMA CHAT:
echo     + chat_room .................... [Stanze chat]
echo     + chat_message ................. [Messaggi chat]
echo.
echo  TASK MANAGEMENT:
echo     + tasks ........................ [Gestione task]
echo     + task_tickets ................. [Associazione task-ticket]
echo     + task_ticket_scans ............ [Scansioni prodotti]
echo     + task_notifications .......... [Notifiche task]
echo.

echo  +-----------------------------------------------------------------------------+
echo  ^|                         CONTROLLO MESSAGGI DEBUG                           ^|
echo  +-----------------------------------------------------------------------------+
echo.
echo  Controlla attentamente i messaggi sopra per verificare:
echo     [V] Successo creazione di tutte le tabelle
echo     [!] Warning eventuali su foreign key  
echo     [i] Messaggi di stato delle 7 fasi di installazione
echo     [#] Conteggio finale delle tabelle create
echo     [*] Risultato modifica tabelle esistenti
echo.

echo  ===============================================================================
echo.
echo  Installazione terminata. Premi un tasto per chiudere...
pause >nul

REM Reset colore terminale
color 07 