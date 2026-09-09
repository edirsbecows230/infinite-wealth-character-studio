# Building

Use Windows x64 and Python 3.12 (the historical build documentation specifies 3.12.3). Run commands from the repository root in PowerShell.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r app\requirements-build.txt
$env:PYTHONPATH = "$PWD\app\src"
.\.venv\Scripts\python.exe -m y8trainer.app
```

Offline tests (no running game required):

```powershell
$env:PYTHONPATH = "$PWD\app\src"
.\.venv\Scripts\python.exe -m unittest discover -s app\tests -v
```

Build the standalone executable:

```powershell
.\.venv\Scripts\python.exe app\build_release.py
```

Output: `app/release/InfiniteWealthCharacterStudio_v0.4.0-alpha5.exe` and checksum. PyInstaller output is not promised to be byte-reproducible. Direct dependency versions are listed in `app/requirements-build.txt`; Pillow has a minimum version and transitive dependencies are not locked.

Build the CT:

```powershell
.\.venv\Scripts\python.exe ct\build_ct.py
```

Output is written under `artifacts/`. A local Cheat Engine Lua DLL is optional for normal builds; missing validation is reported as skipped. Set `CE_LUA_DLL` to a compatible DLL path when needed. `ct/build_ct.py --check` requires the DLL and checks the existing artifact without rewriting it.

Both builds use committed data and require no extracted game files. Optional data regeneration has separate prerequisites in [DATA.md](DATA.md).
