#define MyAppName "Gloorbot Worker"
#ifndef MyAppVersion
#define MyAppVersion "0.0.0"
#endif
#define MyAppExeName "GloorbotWorker.exe"    

[Setup]
AppId={{6A7B5D5A-69F2-4E6B-9B23-0B7C9E1A5531}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\GloorbotWorker
DisableDirPage=yes
DisableProgramGroupPage=yes
OutputDir=..\dist-installer
OutputBaseFilename=WorkerSetup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64
SetupIconFile=..\gloorbot.ico
CloseApplications=yes
RestartApplications=no
DirExistsWarning=no
UninstallDisplayIcon={app}\gloorbot.ico

[InstallDelete]
Type: filesandordirs; Name: "{localappdata}\GloorbotWorker"; Tasks: fullclean
Type: filesandordirs; Name: "{localappdata}\GloorbotWorkerData"; Tasks: fullclean

[Files]
Source: "..\dist\GloorbotWorker\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "..\gloorbot.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{userdesktop}\Gloorbot Worker"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\gloorbot.ico"

[Tasks]
Name: fullclean; Description: "Remove old profile folders"; GroupDescription: "Clean-up:"; Flags: checked

[Run]
Filename: "{app}\{#MyAppExeName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\GloorbotWorker"
Type: filesandordirs; Name: "{localappdata}\GloorbotWorkerData"

[UninstallRun]
Filename: "{cmd}"; Parameters: "/C taskkill /F /T /IM GloorbotWorker.exe"; Flags: runhidden
