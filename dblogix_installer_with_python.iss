;******************************************************************************
; DBLogiX Installer Script per InnoSetup - CON PYTHON EMBEDDABLE INCLUSO
; Questo script crea un installer Windows per DBLogiX con Python Embeddable incluso
;******************************************************************************

#define MyAppName "DBLogiX"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "DBLogiX Team"
#define MyAppURL "https://github.com/dblogix/dblogix"
#define MyAppExeName "DBLogiX.exe"
#define MyServiceName "DBLogiX"

[Setup]
; Informazioni base dell'applicazione
AppId={{A1B2C3D4-E5F6-7890-ABCD-123456789ABC}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=
InfoBeforeFile=
InfoAfterFile=
OutputDir=installer_output
OutputBaseFilename=DBLogiX_Setup_WithPython_{#MyAppVersion}
SetupIconFile=
Compression=lzma
SolidCompression=yes
WizardStyle=modern

; Privilegi amministratore richiesti
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; Architettura supportata
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1
Name: "firewall"; Description: "Configura automaticamente il Firewall Windows"; GroupDescription: "Configurazione Sistema";
Name: "autostart"; Description: "Avvia automaticamente il servizio all'avvio del sistema"; GroupDescription: "Configurazione Sistema";

[Files]
; File principali dell'applicazione
Source: "dist\DBLogiX\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Python Embeddable incluso
Source: "python_embedded\python\*"; DestDir: "{app}\python"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "https://localhost:5000"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\Gestione Servizio {#MyAppName}"; Filename: "{cmd}"; Parameters: "/c cd ""{app}"" && ""{app}\python\python.exe"" dblogix_service.py status && pause"; WorkingDir: "{app}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 21
Name: "{group}\Stop Servizio {#MyAppName}"; Filename: "{cmd}"; Parameters: "/c cd ""{app}"" && ""{app}\python\python.exe"" dblogix_service.py stop && pause"; WorkingDir: "{app}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 27
Name: "{group}\Start Servizio {#MyAppName}"; Filename: "{cmd}"; Parameters: "/c cd ""{app}"" && ""{app}\python\python.exe"" dblogix_service.py start && pause"; WorkingDir: "{app}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 22
Name: "{group}\Logs {#MyAppName}"; Filename: "{app}\logs"; IconFilename: "{sys}\shell32.dll"; IconIndex: 126
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "https://localhost:5000"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "https://localhost:5000"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
; Installa e configura il servizio (usando Python embeddable)
Filename: "{cmd}"; Parameters: "/c cd ""{app}"" && ""{app}\python\python.exe"" dblogix_service.py install"; StatusMsg: "Installazione servizio Windows..."; Flags: runhidden waituntilterminated
Filename: "{cmd}"; Parameters: "/c cd ""{app}"" && ""{app}\python\python.exe"" dblogix_service.py firewall"; StatusMsg: "Configurazione firewall..."; Flags: runhidden waituntilterminated; Tasks: firewall
Filename: "{cmd}"; Parameters: "/c cd ""{app}"" && ""{app}\python\python.exe"" dblogix_service.py start"; StatusMsg: "Avvio servizio DBLogiX..."; Flags: runhidden waituntilterminated; Tasks: autostart
; Apri il browser alla fine dell'installazione
Filename: "https://localhost:5000"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent shellexec; Check: IsServiceRunning

[UninstallRun]
; Ferma e disinstalla il servizio durante la disinstallazione (usando Python embeddable)
Filename: "{cmd}"; Parameters: "/c cd ""{app}"" && ""{app}\python\python.exe"" dblogix_service.py stop"; Flags: runhidden waituntilterminated; RunOnceId: "StopService"
Filename: "{cmd}"; Parameters: "/c cd ""{app}"" && ""{app}\python\python.exe"" dblogix_service.py uninstall"; Flags: runhidden waituntilterminated; RunOnceId: "UninstallService"

[UninstallDelete]
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\cert.pem"
Type: filesandordirs; Name: "{app}\key.pem"
Type: filesandordirs; Name: "{app}\python"

[Code]
function IsEmbeddedPythonAvailable(): Boolean;
begin
  Result := FileExists(ExpandConstant('{app}\python\python.exe'));
end;

function IsServiceRunning(): Boolean;
var
  ResultCode: Integer;
begin
  Result := False;
  if IsEmbeddedPythonAvailable() then
  begin
    Exec('cmd', '/c cd "' + ExpandConstant('{app}') + '" && "' + ExpandConstant('{app}') + '\python\python.exe" dblogix_service.py status | findstr "RUNNING"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Result := (ResultCode = 0);
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    // Genera i certificati SSL se non esistono (usando Python embeddable)
    if IsEmbeddedPythonAvailable() then
    begin
      if not FileExists(ExpandConstant('{app}\cert.pem')) then
      begin
        Exec('cmd', '/c cd "' + ExpandConstant('{app}') + '" && "' + ExpandConstant('{app}') + '\python\python.exe" generate_certs.py', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      end;
    end;
  end;
end;

[Messages]
; Messaggi personalizzati in italiano
italian.BeveledLabel=DBLogiX - Sistema di gestione database (con Python incluso)
italian.SetupAppTitle=Installazione {#MyAppName}
italian.SetupWindowTitle=Installazione {#MyAppName} {#MyAppVersion}
italian.WelcomeLabel1=Benvenuto nell'installazione di [name]
italian.WelcomeLabel2=Questo programma installerà [name/ver] sul tuo computer come servizio Windows.%n%nQuesta versione include Python Embeddable, quindi non è necessario installare Python separatamente.%n%nL'applicazione sarà accessibile tramite browser web all'indirizzo https://localhost:5000%n%nÈ consigliabile chiudere tutte le altre applicazioni prima di continuare.

; Messaggi personalizzati in inglese  
english.BeveledLabel=DBLogiX - Database Management System (with Python included)
english.SetupAppTitle={#MyAppName} Setup
english.SetupWindowTitle={#MyAppName} {#MyAppVersion} Setup
english.WelcomeLabel1=Welcome to the [name] Setup Wizard
english.WelcomeLabel2=This will install [name/ver] on your computer as a Windows service.%n%nThis version includes Python Embeddable, so you don't need to install Python separately.%n%nThe application will be accessible through web browser at https://localhost:5000%n%nIt is recommended that you close all other applications before continuing.

[CustomMessages]
; Messaggi personalizzati
italian.LaunchProgram=Apri %1 nel browser
english.LaunchProgram=Launch %1 in browser 