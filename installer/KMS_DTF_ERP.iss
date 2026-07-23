#define MyAppName "KMS DTF ERP"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "KMS"
#define MyAppExeName "KMS_DTF_ERP.exe"

[Setup]
AppId={{D9DAE29C-732A-4B83-8B46-887A69ED80FD}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\KMS DTF ERP
DefaultGroupName=KMS DTF ERP
OutputDir=..\installer-output
OutputBaseFilename=KMS-DTF-ERP-Setup-1.0.0
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
UninstallDisplayName={#MyAppName}

[Files]
Source: "..\dist\KMS_DTF_ERP\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\KMS DTF ERP"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\KMS DTF ERP"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch KMS DTF ERP"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
begin
  { Stable AppId upgrades in place; runtime data stays outside {app}. }
  Result := True;
end;
