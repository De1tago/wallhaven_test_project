; Inno Setup script for Wallhaven Desktop Viewer (Windows)
; Установка: Program Files + ярлык в меню Пуск + запись в реестре (Параметры -> Приложения)
;
; 1. Скачай и установи Inno Setup: https://jrsoftware.org/isdl.php
; 2. Сначала собери exe: scripts\build-windows.bat  (результат: dist\wallhaven-viewer.exe)
; 3. Открой этот файл в Inno Setup и нажми "Compile", либо через командную строку:
;    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" windows-installer.iss

#define MyAppName "Wallhaven Desktop Viewer"
#define MyAppVersion "5.0.0"
#define MyAppPublisher "wallhaven_viewer"
#define MyAppExeName "wallhaven-viewer.exe"
#define MyAppURL "https://github.com/"

[Setup]
AppId={{C4F2A9E1-3B7D-4E5A-9C8B-1F2D3E4A5B6C}
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
OutputDir=installer
OutputBaseFilename=wallhaven-viewer-setup-{#MyAppVersion}
SetupIconFile=assets\app-icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
; Создаёт правильную запись в реестре (Параметры -> Приложения -> Установленные приложения)
CreateUninstallRegKey=yes
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; Дистрибутив PyInstaller (папка dist целиком)
Source: "dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Ярлык в меню Пуск
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
; Ярлык на рабочий стол (опционально)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительно:"

[Run]
; Запустить после установки (опционально)
; Filename: "{app}\{#MyAppExeName}"; Description: "Запустить приложение"; Flags: nowait postinstall skipifsilent
