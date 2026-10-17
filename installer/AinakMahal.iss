#define MyAppName "Ainak Mahal"
#define MyAppVersion "0.9.0-beta"
#define MyAppExeName "AinakMahal.exe"
[Setup]
AppId={{F5BDB79A-A4E8-44EF-90CB-9160F5D0E4A2}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\Ainak Mahal
DefaultGroupName=Ainak Mahal
OutputDir=..\output
OutputBaseFilename=AinakMahal_Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
[Files]
Source: "..\dist\AinakMahal\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{autoprograms}\Ainak Mahal"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Ainak Mahal"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
[Tasks]
Name: "desktopicon"; Description: "Create desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: checkedonce
[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Ainak Mahal"; Flags: nowait postinstall skipifsilent
