[Setup]
AppId={{62FE2191-7EA4-49C1-B09A-14066B1B015A}
AppName=MOOVE RECOVERY
AppVersion=0.1.0
AppPublisher=DAX
DefaultDirName={localappdata}\Programs\MooveRecovery
DefaultGroupName=MOOVE RECOVERY
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist\installer
OutputBaseFilename=MOOVE_RECOVERY_Setup_0.1.0
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\MooveRecovery.exe
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; Flags: unchecked

[Files]
Source: "..\dist\MooveRecovery\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\MOOVE RECOVERY"; Filename: "{app}\MooveRecovery.exe"
Name: "{userdesktop}\MOOVE RECOVERY"; Filename: "{app}\MooveRecovery.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\MooveRecovery.exe"; Description: "Abrir MOOVE RECOVERY"; Flags: nowait postinstall skipifsilent
