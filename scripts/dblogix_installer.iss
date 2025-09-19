[Setup]
AppName=DBLogiX
AppVersion=2.0.0
AppPublisher=DBLogiX Development Team
AppPublisherURL=https://github.com/dblogix
AppSupportURL=https://github.com/dblogix/support
AppUpdatesURL=https://github.com/dblogix/releases
DefaultDirName={autopf32}\DBLogiX
DefaultGroupName=DBLogiX
AllowNoIcons=yes
OutputDir=..\installer_output
OutputBaseFilename=DBLogiX_Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin
WizardStyle=modern
SetupIconFile=..\build\favicon.ico
UninstallDisplayIcon={app}\favicon.ico
DisableProgramGroupPage=yes
DisableReadyPage=no
DisableWelcomePage=no
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayName=DBLogiX Task Management System

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[Files]
Source: "..\build\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\DBLogiX Web App"; Filename: "https://192.168.1.26:5000"; IconFilename: "{app}\favicon.ico"; Comment: "Open DBLogiX Web Application"
Name: "{commondesktop}\DBLogiX"; Filename: "https://192.168.1.26:5000"; IconFilename: "{app}\favicon.ico"; Comment: "Open DBLogiX Web Application"; Tasks: desktopicon
Name: "{group}\Start DBLogiX Service"; Filename: "net"; Parameters: "start DBLogiXService"; Comment: "Start DBLogiX Service manually"
Name: "{group}\Stop DBLogiX Service"; Filename: "net"; Parameters: "stop DBLogiXService"; Comment: "Stop DBLogiX Service"
Name: "{group}\Service Manager"; Filename: "services.msc"; Comment: "Open Windows Services Manager"
Name: "{group}\Uninstall DBLogiX"; Filename: "{uninstallexe}"; Comment: "Uninstall DBLogiX completely"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked
Name: "installservice"; Description: "Install and start Windows Service (recommended)"; GroupDescription: "Service Options:"; Flags: checkedonce
Name: "firewallrules"; Description: "Create firewall rules for DBLogiX (recommended)"; GroupDescription: "Network Options:"; Flags: checkedonce

[Run]
Filename: "netsh"; Parameters: "advfirewall firewall add rule name=""DBLogiX HTTP"" dir=in action=allow protocol=TCP localport=5000"; StatusMsg: "Creating HTTP firewall rule..."; Tasks: firewallrules; Flags: runhidden
Filename: "netsh"; Parameters: "advfirewall firewall add rule name=""DBLogiX HTTPS"" dir=in action=allow protocol=TCP localport=5000"; StatusMsg: "Creating HTTPS firewall rule..."; Tasks: firewallrules; Flags: runhidden
Filename: "{app}\python\python.exe"; Parameters: """{app}\DBLogiX_Service.py"" install"; WorkingDir: "{app}"; StatusMsg: "Installing Windows Service..."; Tasks: installservice; Flags: runhidden
Filename: "sc"; Parameters: "start DBLogiXService"; StatusMsg: "Starting DBLogiX Service..."; Tasks: installservice; Flags: runhidden
Filename: "https://192.168.1.26:5000"; Description: "Open DBLogiX Web Application"; Flags: postinstall shellexec nowait; Check: ServiceRunning

[UninstallRun]
Filename: "sc"; Parameters: "stop DBLogiXService"; RunOnceId: "StopService"; Flags: runhidden
Filename: "timeout"; Parameters: "/t 3"; RunOnceId: "WaitStop"; Flags: runhidden
Filename: "sc"; Parameters: "delete DBLogiXService"; RunOnceId: "DeleteService"; Flags: runhidden
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""DBLogiX HTTP"""; RunOnceId: "RemoveFirewallHTTP"; Flags: runhidden
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""DBLogiX HTTPS"""; RunOnceId: "RemoveFirewallHTTPS"; Flags: runhidden
Filename: "taskkill"; Parameters: "/F /IM python.exe /T"; RunOnceId: "KillPython"; Flags: runhidden

[UninstallDelete]
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\__pycache__"
Type: filesandordirs; Name: "{app}\app\__pycache__"
Type: filesandordirs; Name: "{app}\modules\__pycache__"
Type: filesandordirs; Name: "{app}\services\__pycache__"
Type: files; Name: "{app}\*.pyc"
Type: files; Name: "{app}\*.pyo"
Type: files; Name: "{app}\*.log"

[Code]
function ServiceRunning: Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('sc', 'query DBLogiXService', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  LocalIP: String;
begin
  if CurStep = ssPostInstall then
  begin
    LocalIP := '192.168.1.26';
    Log('DBLogiX installation completed');
    MsgBox('🎉 DBLogiX Installation Completed Successfully!' + #13#10 + #13#10 +
           '🌐 Web Application URL:' + #13#10 +
           '    https://' + LocalIP + ':5000' + #13#10 + #13#10 +
           '⚙️ Windows Service: DBLogiXService' + #13#10 +
           '   • Starts automatically with Windows' + #13#10 +
           '   • Manage via services.msc' + #13#10 + #13#10 +
           '🔧 Installation Directory:' + #13#10 +
           '    ' + ExpandConstant('{app}') + #13#10 + #13#10 +
           '✅ Your task management system is ready!', mbInformation, MB_OK);
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  Result := '';
  NeedsRestart := False;
  
  // Stop existing service if running
  if Exec('sc', 'query DBLogiXService', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0) then
  begin
    Exec('sc', 'stop DBLogiXService', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Sleep(2000);
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    // Final cleanup
    if MsgBox('Do you want to remove all user data and logs?' + #13#10 +
              'This will permanently delete all configuration files, logs, and user data.',
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      DelTree(ExpandConstant('{app}'), True, True, True);
    end;
    
    MsgBox('DBLogiX has been completely uninstalled.' + #13#10 +
           'Thank you for using DBLogiX!', mbInformation, MB_OK);
  end;
end;