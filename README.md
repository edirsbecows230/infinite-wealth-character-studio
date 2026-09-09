# Infinite Wealth Character Studio

Runtime character and costume selector for Like a Dragon: Infinite Wealth on Windows.

- Standalone application: **v0.4.0-alpha5** (Python / PySide6).
- Cheat Engine table: **v1.2.1-rc1** (Lua).

Select separate character models and costume variants for Ichiban and Kiryu. The tool validates the runtime tables, backs up affected values, reads back writes and attempts rollback on failure. A complete dual-source transaction covers 101 identity mappings and 128 costume rows (357 values).

## Source layout

- `app/`: desktop application, build script and offline tests.
- `ct/`: Cheat Engine Lua source, table builder and Lua syntax validator.
- `data/`: required character catalogs, transaction plans and minimal costume labels.
- `tools/`: optional data preparation and transaction verification scripts.
- `artifacts/`: reference CT and its SHA-256 checksum.

See [BUILDING.md](BUILDING.md) for setup, tests and builds, and [DATA.md](DATA.md) for data provenance.

## Usage and limitations

Start the game and load a save, then start the application. Select models and costumes for the active protagonist slots and apply. Reopening menus, changing maps or reloading a save may be needed to refresh models. Use Restore First Backup before closing. Force Vanilla Reset overwrites affected modded values and should be used only for recovery.

The application targets `likeadragon8.exe` through Windows process memory APIs. Game updates can invalidate table assumptions. Offline tests do not establish compatibility with every game version or validate every NPC appearance.

## Release correspondence

Reference CT SHA-256: `03FEC6764C589ACFF4B0B01BB05D8D327AD5B6B0393540FBCFB070F64BB52A7C`.

Previously recorded EXE SHA-256: `2D653A8DEAAED665EDDB7C9ED3A013D63530AE77F0FF48B8DB097B89D463DE2E`. The EXE is not included. This source distribution reorganizes paths and reduces unused data fields; a new executable build will have a different hash. The historical EXE-to-source correspondence has not been independently established by this reorganization.

## Licensing

No project-wide reuse license has been selected. Public source availability alone is not a grant of permission to redistribute or relicense it. Third-party dependencies retain their own licenses; game-derived identifiers and labels are not claimed as original project assets. See [THIRD_PARTY.md](THIRD_PARTY.md).
