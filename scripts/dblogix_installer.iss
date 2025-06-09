;******************************************************************************
; DBLogiX Installer Script per InnoSetup
; Questo script crea un installer Windows per DBLogiX con configurazione automatica
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
OutputBaseFilename=DBLogiX_Setup_{#MyAppVersion}
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
; Nota: aggiungi qui altri file se necessario

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "https://localhost:5000"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\Gestione Servizio {#MyAppName}"; Filename: "{cmd}"; Parameters: "/c cd ""{app}"" && python dblogix_service.py status && pause"; WorkingDir: "{app}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 21
Name: "{group}\Stop Servizio {#MyAppName}"; Filename: "{cmd}"; Parameters: "/c cd ""{app}"" && python dblogix_service.py stop && pause"; WorkingDir: "{app}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 27
Name: "{group}\Start Servizio {#MyAppName}"; Filename: "{cmd}"; Parameters: "/c cd ""{app}"" && python dblogix_service.py start && pause"; WorkingDir: "{app}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 22
Name: "{group}\Logs {#MyAppName}"; Filename: "{app}\logs"; IconFilename: "{sys}\shell32.dll"; IconIndex: 126
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "https://localhost:5000"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "https://localhost:5000"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
; Installa e configura il servizio
Filename: "{cmd}"; Parameters: "/c cd ""{app}"" && python dblogix_service.py install"; StatusMsg: "Installazione servizio Windows..."; Flags: runhidden waituntilterminated; Check: ShouldInstallService
Filename: "{cmd}"; Parameters: "/c cd ""{app}"" && python dblogix_service.py firewall"; StatusMsg: "Configurazione firewall..."; Flags: runhidden waituntilterminated; Tasks: firewall
Filename: "{cmd}"; Parameters: "/c cd ""{app}"" && python dblogix_service.py start"; StatusMsg: "Avvio servizio DBLogiX..."; Flags: runhidden waituntilterminated; Tasks: autostart
; Apri il browser alla fine dell'installazione
Filename: "https://localhost:5000"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent shellexec; Check: IsServiceRunning

[UninstallRun]
; Ferma e disinstalla il servizio durante la disinstallazione
Filename: "{cmd}"; Parameters: "/c cd ""{app}"" && python dblogix_service.py stop"; Flags: runhidden waituntilterminated; RunOnceId: "StopService"
Filename: "{cmd}"; Parameters: "/c cd ""{app}"" && python dblogix_service.py uninstall"; Flags: runhidden waituntilterminated; RunOnceId: "UninstallService"

[UninstallDelete]
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\cert.pem"
Type: filesandordirs; Name: "{app}\key.pem"

[Code]
var
  PythonPage: TInputOptionWizardPage;
  PythonPath: String;

function IsPythonInstalled(): Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('python', '--version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

function GetPythonPath(): String;
var
  TempFile: String;
  Lines: TArrayOfString;
  ResultCode: Integer;
begin
  Result := '';
  TempFile := ExpandConstant('{tmp}\python_path.txt');
  if Exec('cmd', '/c python -c "import sys; print(sys.executable)" > "' + TempFile + '"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    if LoadStringsFromFile(TempFile, Lines) and (GetArrayLength(Lines) > 0) then
      Result := Trim(Lines[0]);
    DeleteFile(TempFile);
  end;
end;

procedure InitializeWizard;
begin
  PythonPage := CreateInputOptionPage(wpWelcome,
    'Controllo Python', 'Verifico l''installazione di Python sul sistema',
    'DBLogiX richiede Python 3.8 o superiore per funzionare correttamente.',
    True, False);
  PythonPage.Add('Python è installato e configurato correttamente');
  PythonPage.Add('Python non è installato o non è accessibile');
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  ErrorCode: Integer;
begin
  Result := True;
  
  if CurPageID = PythonPage.ID then
  begin
    if IsPythonInstalled() then
    begin
      PythonPath := GetPythonPath();
      PythonPage.SelectedValueIndex := 0;
      Log('Python trovato in: ' + PythonPath);
    end
    else
    begin
      PythonPage.SelectedValueIndex := 1;
      if MsgBox('Python non è installato o non è accessibile dal PATH di sistema.' + #13#10 + 
                'DBLogiX richiede Python 3.8 o superiore per funzionare.' + #13#10 + #13#10 +
                'Vuoi continuare comunque? (Dovrai installare Python manualmente)',
                mbConfirmation, MB_YESNO) = IDNO then
      begin
        Result := False;
      end;
    end;
  end;
end;

function ShouldInstallService(): Boolean;
begin
  Result := IsPythonInstalled();
end;

function IsServiceRunning(): Boolean;
var
  ResultCode: Integer;
begin
  Result := False;
  if IsPythonInstalled() then
  begin
    Exec('cmd', '/c cd "' + ExpandConstant('{app}') + '" && python dblogix_service.py status | findstr "RUNNING"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Result := (ResultCode = 0);
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    // Genera i certificati SSL se non esistono
    if IsPythonInstalled() then
    begin
      if not FileExists(ExpandConstant('{app}\cert.pem')) then
      begin
        Exec('cmd', '/c cd "' + ExpandConstant('{app}') + '" && python generate_certs.py', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      end;
    end;
  end;
end;

[Messages]
; Messaggi personalizzati in italiano
italian.BeveledLabel=DBLogiX - Sistema di gestione database
italian.SetupAppTitle=Installazione {#MyAppName}
italian.SetupWindowTitle=Installazione {#MyAppName} {#MyAppVersion}
italian.WelcomeLabel1=Benvenuto nell'installazione di [name]
italian.WelcomeLabel2=Questo programma installerà [name/ver] sul tuo computer come servizio Windows.%n%nL'applicazione sarà accessibile tramite browser web all'indirizzo https://localhost:5000%n%nÈ consigliabile chiudere tutte le altre applicazioni prima di continuare.

; Messaggi personalizzati in inglese  
english.BeveledLabel=DBLogiX - Database Management System
english.SetupAppTitle={#MyAppName} Setup
english.SetupWindowTitle={#MyAppName} {#MyAppVersion} Setup
english.WelcomeLabel1=Welcome to the [name] Setup Wizard
english.WelcomeLabel2=This will install [name/ver] on your computer as a Windows service.%n%nThe application will be accessible through web browser at https://localhost:5000%n%nIt is recommended that you close all other applications before continuing.

[CustomMessages]
; Messaggi personalizzati
italian.LaunchProgram=Apri %1 nel browser
english.LaunchProgram=Launch %1 in browser 