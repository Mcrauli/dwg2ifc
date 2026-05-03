; Inno Setup script for dxf2ifc.
;
; Compiled by `scripts/build_installer.ps1` after PyInstaller has produced
; `dist/dxf2ifc.exe`. The driver script passes paths and version through
; /D defines so the .iss does not hardcode any absolute path.
;
; Manual build:
;   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" ^
;     /DAppVersion=0.1.0 ^
;     /DSourceExe=C:\path\to\dist\dxf2ifc.exe ^
;     /DLicensesFile=C:\path\to\dist\LICENSES.md ^
;     /DOutputDir=C:\path\to\dist ^
;     build\installer.iss

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

#ifndef SourceExe
  #define SourceExe "..\dist\dxf2ifc.exe"
#endif

#ifndef LicensesFile
  #define LicensesFile "..\dist\LICENSES.md"
#endif

#ifndef OutputDir
  #define OutputDir "..\dist"
#endif

[Setup]
; Stable AppId — required for upgrade/uninstall identity. Do not change.
AppId={{B1F1E1E2-3A8C-4F7D-9C61-2A6F1E5F3B2A}
AppName=dxf2ifc
AppVersion={#AppVersion}
AppVerName=dxf2ifc {#AppVersion}
AppPublisher=Radika Oy
AppPublisherURL=https://github.com/Mcrauli/dxf2ifc
AppSupportURL=https://github.com/Mcrauli/dxf2ifc/issues
AppUpdatesURL=https://github.com/Mcrauli/dxf2ifc/releases
DefaultDirName={autopf}\dxf2ifc
DefaultGroupName=dxf2ifc
DisableProgramGroupPage=yes
DisableDirPage=auto
; Per-user install by default → no UAC prompt → less SmartScreen friction.
; User can elevate to all-users via dialog if they want Program Files install.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog commandline
OutputDir={#OutputDir}
OutputBaseFilename=dxf2ifc-Setup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName=dxf2ifc {#AppVersion}
UninstallDisplayIcon={app}\dxf2ifc.exe
VersionInfoVersion={#AppVersion}.0
VersionInfoCompany=Radika Oy
VersionInfoDescription=dxf2ifc DXF to IFC 4 converter installer
VersionInfoProductName=dxf2ifc
VersionInfoProductVersion={#AppVersion}
VersionInfoCopyright=(c) 2026 Lauri Rekola, Radika Oy. MIT licence.
#ifdef IconFile
SetupIconFile={#IconFile}
#endif

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "finnish"; MessagesFile: "compiler:Languages\Finnish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourceExe}"; DestDir: "{app}"; DestName: "dxf2ifc.exe"; Flags: ignoreversion
Source: "{#LicensesFile}"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{autoprograms}\dxf2ifc"; Filename: "{app}\dxf2ifc.exe"
Name: "{autodesktop}\dxf2ifc"; Filename: "{app}\dxf2ifc.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\dxf2ifc.exe"; Description: "{cm:LaunchProgram,dxf2ifc}"; Flags: nowait postinstall skipifsilent
