#!/usr/bin/env bash
# Local Linux PyInstaller smoke build for dxf2ifc.
# Validates that build/dxf2ifc.spec is well-formed; the resulting ELF is
# only useful for local sanity checking — Windows .exe ships from CI.
# Usage: DXF2IFC_VERSION=0.1.0 ./scripts/build_exe.sh

set -euo pipefail

VERSION="${DXF2IFC_VERSION:-$(grep -oE '__version__\s*=\s*"[^"]+"' src/dxf2ifc/_version.py | head -n1 | sed -E 's/.*"([^"]+)".*/\1/')}"

echo "Building dxf2ifc smoke binary version ${VERSION}..."

uv sync --extra dev --extra gui
uv run pyinstaller build/dxf2ifc.spec --clean --noconfirm

SOURCE="dist/dxf2ifc"
TARGET="dist/dxf2ifc-${VERSION}"

if [[ ! -f "${SOURCE}" ]]; then
    echo "PyInstaller did not produce ${SOURCE}" >&2
    exit 1
fi

cp "${SOURCE}" "${TARGET}"

if command -v sha256sum >/dev/null 2>&1; then
    HASH=$(sha256sum "${TARGET}" | awk '{print $1}')
elif command -v shasum >/dev/null 2>&1; then
    HASH=$(shasum -a 256 "${TARGET}" | awk '{print $1}')
else
    echo "no sha256sum/shasum on PATH" >&2
    exit 1
fi

echo "Built  : ${TARGET}"
echo "SHA256 : ${HASH}"
echo "${HASH}  $(basename "${TARGET}")" > "${TARGET}.sha256"
