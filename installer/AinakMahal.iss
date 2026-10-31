#define MyAppName "Ainak Mahal"
#ifndef MyAppVersion
#define MyAppVersion "2.0.1"
#endif
#ifndef MyFileVersion
#define MyFileVersion "2.0.1.0"
#endif
#ifndef MyBuildId
#define MyBuildId "manual"
#endif
#define MyAppExeName "AinakMahal.exe"
[Setup]
AppId={{F5BDB79A-A4E8-44EF-90CB-9160F5D0E4A2}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=Ahsan Iftikhar
VersionInfoCompany=Ahsan Iftikhar
VersionInfoVersion={#MyFileVersion}
VersionInfoProductVersion={#MyFileVersion}
VersionInfoTextVersion={#MyFileVersion}
VersionInfoProductTextVersion={#MyAppVersion} (build {#MyBuildId})
DefaultDirName={code:InstallPath}
DefaultGroupName=Ainak Mahal
OutputDir=..\output
OutputBaseFilename=AinakMahal_Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
WizardStyle=modern
SetupIconFile=..\assets\brand\ainak-mahal.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Uninstallable=not IsSmokeTest
CreateUninstallRegKey=not IsSmokeTest
[Files]
Source: "..\dist\AinakMahal\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{autoprograms}\Ainak Mahal"; Filename: "{app}\{#MyAppExeName}"; Check: not IsSmokeTest
Name: "{autoprograms}\Ainak Mahal Recovery"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--restore"; Check: not IsSmokeTest
Name: "{autoprograms}\Ainak Mahal Operator Guide"; Filename: "{app}\_internal\docs\OPERATOR_GUIDE.html"; Check: not IsSmokeTest
Name: "{autodesktop}\Ainak Mahal"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; Check: not IsSmokeTest
[Tasks]
Name: "desktopicon"; Description: "Create desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: checkedonce
[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Ainak Mahal"; Flags: nowait postinstall skipifsilent

[Code]
function IsSmokeTest: Boolean;
begin
  Result := ExpandConstant('{param:SMOKETEST|0}') = '1';
end;

function InstallPath(Param: String): String;
begin
  if IsSmokeTest then
    Result := ExpandConstant('{param:DIR|{tmp}\AinakMahalSmoke}')
  else
    Result := ExpandConstant('{localappdata}\Programs\Ainak Mahal');
end;
