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

#ifndef AppNumericVersion
  ; VersionInfoVersion requires pure-numeric X.Y.Z.W. Default is the
  ; placeholder used when ISCC runs without /DAppNumericVersion (manual
  ; runs); build_installer.ps1 always passes the real value derived
  ; from AppVersion stripped of its PEP 440 alpha suffix.
  #define AppNumericVersion "0.0.0.0"
#endif

[Setup]
; Stable AppId — required for upgrade/uninstall identity. Do not change.
AppId={{B1F1E1E2-3A8C-4F7D-9C61-2A6F1E5F3B2A}
AppName=dxf2ifc
AppVersion={#AppVersion}
AppVerName=dxf2ifc {#AppVersion}
AppPublisher=Lauri Rekola
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
VersionInfoVersion={#AppNumericVersion}
VersionInfoCompany=Lauri Rekola
VersionInfoDescription=dxf2ifc DXF to IFC 4 converter installer
VersionInfoProductName=dxf2ifc
VersionInfoProductVersion={#AppNumericVersion}
VersionInfoProductTextVersion={#AppVersion}
VersionInfoCopyright=(c) 2026 Lauri Rekola
#ifdef IconFile
SetupIconFile={#IconFile}
#endif

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "finnish"; MessagesFile: "compiler:Languages\Finnish.isl"

[Tasks]
; Desktop icon checkbox is ticked by default — colleague-feedback
; (2026-05-05) showed that the previous opt-in flow left users with no
; quick launcher and they assumed the install had failed. Users who
; don't want the icon can still untick during setup.
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

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
