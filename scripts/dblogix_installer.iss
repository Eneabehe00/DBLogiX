[Setup]
AppName=DBLogiX
AppVersion=1.0
AppPublisher=DBLogiX Team
AppPublisherURL=https://dblogix.com
DefaultDirName={autopf}\DBLogiX
DefaultGroupName=DBLogiX
OutputDir=..\installer_output
OutputBaseFilename=DBLogiX_Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin
SetupIconFile=..\static\favicon.ico
WizardStyle=modern
UninstallDisplayIcon={app}\favicon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[Files]
Source: "..\build\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\static\favicon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\DBLogiX"; Filename: "https://localhost:5000"; IconFilename: "{app}\favicon.ico"; Comment: "Open DBLogiX Web Application"
Name: "{group}\DBLogiX (Manual Start)"; Filename: "{app}\start_dblogix.bat"; WorkingDir: "{app}"; IconFilename: "{app}\favicon.ico"; Comment: "Start DBLogiX manually (for debugging)"
Name: "{group}\Service Control\Install Service"; Filename: "{app}\install_service.bat"; WorkingDir: "{app}"; Comment: "Install DBLogiX Windows Service"
Name: "{group}\Service Control\Uninstall Service"; Filename: "{app}\uninstall_service.bat"; WorkingDir: "{app}"; Comment: "Uninstall DBLogiX Windows Service"
Name: "{group}\Service Control\Start Service"; Filename: "net"; Parameters: "start DBLogiXEmbedded"; Comment: "Start DBLogiX Service"
Name: "{group}\Service Control\Stop Service"; Filename: "net"; Parameters: "stop DBLogiXEmbedded"; Comment: "Stop DBLogiX Service"
Name: "{group}\Service Control\Service Status"; Filename: "{app}\status_service.bat"; WorkingDir: "{app}"; Comment: "Check DBLogiX Service Status"
Name: "{group}\Service Control\View Service Logs"; Filename: "{app}\view_service_logs.bat"; WorkingDir: "{app}"; Comment: "View DBLogiX Service Logs"
Name: "{group}\Service Control\Debug Launcher"; Filename: "{app}\debug_launcher.bat"; WorkingDir: "{app}"; Comment: "Debug DBLogiX Launcher (troubleshooting)"
Name: "{group}\{cm:UninstallProgram,DBLogiX}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\DBLogiX"; Filename: "https://localhost:5000"; Tasks: desktopicon; IconFilename: "{app}\favicon.ico"; Comment: "Open DBLogiX Web Application"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "installservice"; Description: "Install Windows Service"; GroupDescription: "Service Options"; Flags: checkedonce
Name: "startservice"; Description: "Start Windows Service automatically"; GroupDescription: "Service Options"; Flags: checkedonce
Name: "configurefirewall"; Description: "Configure Windows Firewall"; GroupDescription: "Security Options"; Flags: checkedonce
Name: "openbrowser"; Description: "Open DBLogiX in browser after installation"; GroupDescription: "Launch Options"; Flags: checkedonce

[Run]
Filename: "{app}\python\python.exe"; Parameters: """DBLogiX_Service.py"" install"; WorkingDir: "{app}"; StatusMsg: "Installing Windows Service..."; Tasks: installservice; Flags: runhidden
Filename: "net"; Parameters: "start DBLogiXEmbedded"; StatusMsg: "Starting DBLogiX Service..."; Tasks: startservice; Flags: runhidden waituntilterminated
Filename: "netsh"; Parameters: "advfirewall firewall add rule name=""DBLogiX HTTP"" dir=in action=allow protocol=TCP localport=5000 enable=yes"; StatusMsg: "Configuring Firewall..."; Tasks: configurefirewall; Flags: runhidden
Filename: "netsh"; Parameters: "advfirewall firewall add rule name=""DBLogiX HTTPS"" dir=in action=allow protocol=TCP localport=5000 enable=yes"; StatusMsg: "Configuring Firewall..."; Tasks: configurefirewall; Flags: runhidden
Filename: "timeout"; Parameters: "/t 5 /nobreak"; StatusMsg: "Waiting for service to start..."; Tasks: openbrowser; Flags: runhidden waituntilterminated
Filename: "https://localhost:5000"; StatusMsg: "Opening DBLogiX in browser..."; Tasks: openbrowser; Flags: shellexec postinstall skipifsilent

[UninstallRun]
Filename: "net"; Parameters: "stop DBLogiXEmbedded"; StatusMsg: "Stopping Service..."; Flags: runhidden
Filename: "{app}\python\python.exe"; Parameters: """DBLogiX_Service.py"" remove"; WorkingDir: "{app}"; StatusMsg: "Removing Windows Service..."; Flags: runhidden
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""DBLogiX HTTP"""; StatusMsg: "Removing Firewall Rules..."; Flags: runhidden
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""DBLogiX HTTPS"""; StatusMsg: "Removing Firewall Rules..."; Flags: runhidden

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    MsgBox('Installation completed successfully!' + #13#10 + 
           'You can start DBLogiX from the Start Menu or Desktop icon.' + #13#10 +
           'Access the web interface at: https://localhost:5000', mbInformation, MB_OK);
  end;
end;
