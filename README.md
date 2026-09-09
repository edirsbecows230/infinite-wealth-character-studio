# Infinite Wealth Character Studio

Standalone **v0.7.0** for Like a Dragon: Infinite Wealth on Windows. Includes a separate **v1.3.0-rc1 Cheat Engine table**.

## Features

- Ten independently selectable source slots: Ichiban, Kiryu, Nanba, Adachi, Zhao, Joongi, Tomizawa, Saeko, Chitose and Seonhee.
- Searchable bilingual UI, grouped named characters, fixed model variants and restore controls.
- 47 curated targets, including Jo Amon, Jiro Amon, Kazuya Amon and Sango Amon; 404 female and 4,742 male NPC candidates.
- Validated memory writes, readback, rollback attempts and restoration of saved state.

Party members use Character identity mappings. Ichiban and Kiryu additionally use Costume table mappings; party support does not imply identical costume behavior for every character. The complete source plan covers 574 identity mappings and 128 costume rows (830 identity/costume values). Optional voice overrides have separate backup handling.

The CT remains a two-protagonist selector. Use the standalone application for ten-slot replacement.

## Run

Download the standalone executable from a release package and launch it after loading a game save. Choose a source slot, select a target, enable the desired slots, and apply. Models may need a menu refresh, map transition or save reload to update.

Restore Original Models writes built-in original values. Restore Launch Backup restores the snapshot captured at first Apply and preserves pre-existing changes present in that snapshot. Game updates or conflicting mods may invalidate the expected memory layout.

## Source and build

- `app/`: standalone source, build script and tests.
- `data/`: standalone runtime catalogs and minimal costume labels.
- `ct/`: CT Lua source, builder and CT-specific catalogs.
- `artifacts/`: reference CT and checksum.

See [BUILDING.md](BUILDING.md), [DATA.md](DATA.md) and [THIRD_PARTY.md](THIRD_PARTY.md).

No extracted binary game databases, models, textures, audio or saves are distributed. No project-wide reuse license has been selected; third-party components and game-derived data retain their respective rights.
