; Inno Setup script for dwg2ifc.
;
; Compiled by `scripts/build_installer.ps1` after PyInstaller has produced
; `dist/dwg2ifc.exe`. The driver script passes paths and version through
; /D defines so the .iss does not hardcode any absolute path.
;
; Manual build:
;   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" ^
;     /DAppVersion=0.1.0 ^
;     /DSourceExe=C:\path\to\dist\dwg2ifc.exe ^
;     /DLicensesFile=C:\path\to\dist\LICENSES.md ^
;     /DOutputDir=C:\path\to\dist ^
;     build\installer.iss

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

#ifndef SourceExe
  #define SourceExe "..\dist\dwg2ifc.exe"
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
; v0.3.0-alpha1 rebrand from dxf2ifc -> dwg2ifc bumped this to a new GUID so
; the new install lives alongside the legacy dxf2ifc one in Apps & Features
; (users can uninstall the dxf2ifc-named entry manually after the migration).
AppId={{2991C7F6-5C6D-4472-BF37-A9D9E4AE61AD}
AppName=dwg2ifc
AppVersion={#AppVersion}
AppVerName=dwg2ifc {#AppVersion}
AppPublisher=Lauri Rekola
AppPublisherURL=https://github.com/Mcrauli/dwg2ifc
AppSupportURL=https://github.com/Mcrauli/dwg2ifc/issues
AppUpdatesURL=https://github.com/Mcrauli/dwg2ifc/releases
DefaultDirName={autopf}\dwg2ifc
DefaultGroupName=dwg2ifc
DisableProgramGroupPage=yes
DisableDirPage=auto
; Per-user install by default → no UAC prompt → less SmartScreen friction.
; User can elevate to all-users via dialog if they want Program Files install.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog commandline
OutputDir={#OutputDir}
OutputBaseFilename=dwg2ifc-Setup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName=dwg2ifc {#AppVersion}
UninstallDisplayIcon={app}\dwg2ifc.exe
VersionInfoVersion={#AppNumericVersion}
VersionInfoCompany=Lauri Rekola
VersionInfoDescription=dwg2ifc DXF to IFC 4 converter installer
VersionInfoProductName=dwg2ifc
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
Source: "{#SourceExe}"; DestDir: "{app}"; DestName: "dwg2ifc.exe"; Flags: ignoreversion
Source: "{#LicensesFile}"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{autoprograms}\dwg2ifc"; Filename: "{app}\dwg2ifc.exe"
Name: "{autodesktop}\dwg2ifc"; Filename: "{app}\dwg2ifc.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\dwg2ifc.exe"; Description: "{cm:LaunchProgram,dwg2ifc}"; Flags: nowait postinstall skipifsilent
