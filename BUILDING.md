# Building v0.7.0

Windows x64, Python 3.12. Commands below run from the repository root in PowerShell. The validation build used Python 3.12.3, PySide6 6.9.2, PySide6-Fluent-Widgets 1.11.2, PyInstaller 6.21.0 and Pillow 12.0.0.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r app\requirements-build.txt
$env:PYTHONPATH = "$PWD\app\src"
.\.venv\Scripts\python.exe -m y8trainer.app
```

Offline tests:

```powershell
$env:PYTHONPATH = "$PWD\app\src"
.\.venv\Scripts\python.exe -m unittest discover -s app\tests -v
```

Build executable:

```powershell
.\.venv\Scripts\python.exe app\build_release.py
```

Output: `app/release/InfiniteWealthCharacterStudio_v0.7.0.exe` and SHA-256. All required data is embedded. Builds do not require game files. PyInstaller output is not guaranteed to have identical bytes between builds. Direct dependency constraints are listed in `app/requirements-build.txt`; transitive packages are not fully locked.

Build the separate CT:

```powershell
.\.venv\Scripts\python.exe ct\build_ct.py
```

Output is under `artifacts/`. Optional CE Lua syntax validation uses an installed compatible `lua53-64.dll`; set `CE_LUA_DLL` if it is not found automatically. `--check` requires Lua validation and compares the existing artifact without rewriting it.

A non-connecting UI preview is available with `python -m y8trainer.app --preview`; `--screenshot preview.png` renders a preview and exits without connecting to the game.
