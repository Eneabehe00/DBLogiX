; DBLogiX Installer Script for Inno Setup
; Crea un installer .exe completo per distribuzione ai clienti

#define MyAppName "DBLogiX"
#define MyAppVersion "2.0"
#define MyAppPublisher "DBLogiX Solutions"
#define MyAppURL "https://www.dblogix.com"
#define MyAppServiceName "DBLogiXEmbedded"

[Setup]
; Nome e versione applicazione
AppId={{B8F12345-ABCD-4567-8901-123456789ABC}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Directory installazione
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; File di output
OutputDir=..\installer_output
OutputBaseFilename=DBLogiX_Setup

; Compressione
Compression=lzma
SolidCompression=yes

; Interfaccia utente
WizardStyle=modern

; Privilegi amministratore RICHIESTI AUTOMATICAMENTE
PrivilegesRequired=admin

; Configurazioni avanzate
DisableDirPage=yes
AllowNoIcons=yes

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Crea icona sul desktop"; GroupDescription: "Icone aggiuntive:"
Name: "windowsservice"; Description: "Installa come servizio Windows (raccomandato)"; GroupDescription: "Opzioni servizio:"
Name: "firewall"; Description: "Configura firewall Windows automaticamente"; GroupDescription: "Opzioni rete:"
Name: "autostart"; Description: "Avvia servizio automaticamente"; GroupDescription: "Opzioni servizio:"

[Files]
; File applicazione Python Embedded
Source: "..\installer_output\DBLogiX\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; File di configurazione
Source: "..\DBLogix.exe.config"; DestDir: "{app}\config"; Flags: ignoreversion

; Certificati SSL se esistono
Source: "..\cert.pem"; DestDir: "{app}\certs"; Flags: ignoreversion external skipifsourcedoesntexist
Source: "..\key.pem"; DestDir: "{app}\certs"; Flags: ignoreversion external skipifsourcedoesntexist

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\start_dblogix.bat"; WorkingDir: "{app}"
Name: "{group}\Disinstalla {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\start_dblogix.bat"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
; Installa servizio Windows
Filename: "{app}\python\python.exe"; Parameters: """{app}\DBLogiX_Service.py"" install"; WorkingDir: "{app}"; StatusMsg: "Installando servizio Windows..."; Flags: runhidden waituntilterminated; Tasks: windowsservice

; Configura firewall
Filename: "netsh"; Parameters: "advfirewall firewall add rule name=""DBLogiX HTTP"" dir=in action=allow protocol=TCP localport=5000 enable=yes"; StatusMsg: "Configurando firewall per HTTP..."; Flags: runhidden waituntilterminated; Tasks: firewall
Filename: "netsh"; Parameters: "advfirewall firewall add rule name=""DBLogiX HTTPS"" dir=in action=allow protocol=TCP localport=5000 enable=yes"; StatusMsg: "Configurando firewall per HTTPS..."; Flags: runhidden waituntilterminated; Tasks: firewall

; Avvia servizio
Filename: "net"; Parameters: "start {#MyAppServiceName}"; StatusMsg: "Avviando servizio DBLogiX..."; Flags: runhidden waituntilterminated; Tasks: windowsservice and autostart

; Apri browser alla fine (opzionale)
Filename: "https://localhost:5000"; Description: "Apri DBLogiX nel browser"; Flags: nowait postinstall skipifsilent shellexec

[UninstallRun]
; Ferma servizio
Filename: "net"; Parameters: "stop {#MyAppServiceName}"; RunOnceId: "StopService"; Flags: runhidden waituntilterminated

; Rimuovi servizio
Filename: "{app}\python\python.exe"; Parameters: """{app}\DBLogiX_Service.py"" remove"; RunOnceId: "RemoveService"; Flags: runhidden waituntilterminated

; Rimuovi regole firewall
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""DBLogiX HTTP"""; RunOnceId: "RemoveFirewallHTTP"; Flags: runhidden waituntilterminated
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""DBLogiX HTTPS"""; RunOnceId: "RemoveFirewallHTTPS"; Flags: runhidden waituntilterminated

[Messages]
; Messaggi personalizzati in italiano
italian.WelcomeLabel2=Questo installer configurerà [name/ver] sul tuo computer.%n%nDBLogiX è un sistema di gestione completo che verrà installato come servizio Windows.%n%nSi raccomanda di chiudere tutte le altre applicazioni prima di continuare.
italian.FinishedHeadingLabel=Completamento installazione di [name]
italian.ClickFinish=Clicca Fine per completare l'installazione e avviare DBLogiX. 