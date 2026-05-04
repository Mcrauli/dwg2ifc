# PyInstaller Win32 VSVersionInfo for dxf2ifc.
# Loaded by EXE(version='build/version_info.py', ...).
# Keep in sync with src/dxf2ifc/_version.py — bump both when releasing.

VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=(0, 1, 3, 0),
        prodvers=(0, 1, 3, 0),
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
                        StringStruct("CompanyName", "Radika Oy"),
                        StringStruct("FileDescription", "dxf2ifc DXF to IFC 4 converter"),
                        StringStruct("FileVersion", "0.1.3a1"),
                        StringStruct("InternalName", "dxf2ifc"),
                        StringStruct(
                            "LegalCopyright", "(c) 2026 Lauri Rekola, Radika Oy. MIT licence."
                        ),
                        StringStruct("OriginalFilename", "dxf2ifc.exe"),
                        StringStruct("ProductName", "dxf2ifc"),
                        StringStruct("ProductVersion", "0.1.3a1"),
                    ],
                )
            ]
        ),
        VarFileInfo([VarStruct("Translation", [1033, 1200])]),
    ],
)
