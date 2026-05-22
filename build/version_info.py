# PyInstaller Win32 VSVersionInfo for dwg2ifc.
# Loaded by EXE(version='build/version_info.py', ...).
# Keep in sync with src/dwg2ifc/_version.py — bump both when releasing.

VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=(0, 3, 0, 0),
        prodvers=(0, 3, 0, 0),
        mask=0x3F,
        flags=0x0,
        OS=0x40004,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0),
    ),
    kids=[
        StringFileInfo(
            [
                StringTable(
                    "040904B0",
                    [
                        StringStruct("CompanyName", "Lauri Rekola"),
                        StringStruct("FileDescription", "dwg2ifc DWG/DXF to IFC 4 converter"),
                        StringStruct("FileVersion", "0.3.0a12"),
                        StringStruct("InternalName", "dwg2ifc"),
                        StringStruct(
                            "LegalCopyright", "(c) 2026 Lauri Rekola"
                        ),
                        StringStruct("OriginalFilename", "dwg2ifc.exe"),
                        StringStruct("ProductName", "dwg2ifc"),
                        StringStruct("ProductVersion", "0.3.0a12"),
                    ],
                )
            ]
        ),
        VarFileInfo([VarStruct("Translation", [1033, 1200])]),
    ],
)
