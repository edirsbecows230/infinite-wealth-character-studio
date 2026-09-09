# Release verification

Standalone: v0.7.0

EXE SHA-256: `8312b9f9e0e5512e6a5f81e79405a33d2011b927a5b4749069c0b82d426037e8`

CT: v1.3.0-rc1

CT SHA-256: `0c4212bb2ab7e59889c6eca0f7cd7be7126dbf5ec8c5449a007d62e1c62e1667`

- 32 offline tests passed, including all four Amon targets across ten source slots and three modes, mixed selections and restore checks.
- Standalone EXE built successfully and launched in non-connecting screenshot preview mode with exit code 0.
- All four embedded JSON files match the source distribution byte for byte.
- CT rebuilt with real CE Lua syntax validation and matches the existing v1.3.0-rc1 artifact byte for byte.
- The maintainer confirmed Amon gameplay testing in the CT. The newly built standalone EXE has not been tested in a running game in this release preparation.

Build environment: Python 3.12.3, PySide6 6.9.2, PySide6-Fluent-Widgets 1.11.2, PyInstaller 6.21.0, Pillow 12.0.0.
