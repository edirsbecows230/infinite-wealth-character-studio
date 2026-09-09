# Data inputs

The committed JSON files contain game-derived identifiers, model names, table positions, original values and labels needed by the selectors. No model, texture, audio, save or binary game database is included. Costume metadata is reduced to the table ID, row count, row keys and display names used by the application and CT builder.

The optional scripts under `tools/` document catalog and mapping generation. They are not required for application or CT builds. Their local inputs are not distributed:

- `local/game_data/extracted_full/`: original Character, Model, Costume and RPG Costume ARMP tables from a separately obtained game installation.
- `local/character_npc_npc_list.bin.json`: NPC table JSON export for female/male catalog generation.
- `tools/reference/npc_runtime_selector.generated.json`: committed reference mapping consumed by the plan exporter.

Run plan export before catalog exports. The repository does not include a complete extraction/conversion toolchain; optional regeneration is not a turnkey workflow. The legacy helper's optional portrait extraction requires `y8_par_extract.py`, which is not supplied and is not needed by the runtime application or CT builder. Generated CSVs are optional inspection outputs and are ignored by Git.

`tools/verify_dual_source_transaction.py` also requires the local binary game databases. It is separate from the self-contained 22-test application suite.
