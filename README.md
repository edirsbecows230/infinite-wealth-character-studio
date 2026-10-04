# Infinite Wealth Character Studio

Standalone application for Like a Dragon: Infinite Wealth on Windows. Includes a separate **v1.3.0-rc1 Cheat Engine table**.

**Latest released version: [v0.8.0](https://github.com/edirsbecows230/infinite-wealth-character-studio/releases/tag/v0.8.0)**

## Released features (v0.8.0)

- Ten independently selectable source slots: Ichiban, Kiryu, Nanba, Adachi, Zhao, Joongi, Tomizawa, Saeko, Chitose and Seonhee.
- Searchable bilingual UI, grouped named characters, fixed model variants and restore controls.
- 47 curated targets, including Jo Amon, Jiro Amon, Kazuya Amon and Sango Amon; 404 female and 4,742 male NPC candidates.
- Character Finder with multi-keyword AND search, exact face/hair/model filters, local favorites and aliases, and Previous/Next browsing.
- 25 named side-story/activity characters with 40 selectable appearances, including Karen and Susumu Gondawara. Search their English, Japanese or Chinese display names in Named Side or All. See [Character Finder](app/CHARACTER_FINDER.md).
- Validated memory writes, readback, rollback attempts and restoration of saved state.

Party members use Character identity mappings. Ichiban and Kiryu additionally use Costume table mappings; party support does not imply identical costume behavior for every character. The complete source plan covers 574 identity mappings and 128 costume rows (830 identity/costume values). Optional voice overrides have separate backup handling.

The CT remains a two-protagonist selector. Use the standalone application for ten-slot replacement.

**The 25 newly added named characters and their appearances have not been tested in game.** Identity/model mappings were checked against source data, and offline tests passed; animation, expression and special-context appearance compatibility remain unverified.

**新增的 25 个具名角色及其造型尚未经过游戏内实机测试。** 身份与模型映射已核对、离线测试已通过，但动画、表情及特殊场景造型的兼容性仍待验证。中文姓名是界面译名，不代表官方译名。

The existing **v0.7.0 Release binary does not include Character Finder or Named Side presets**. Download v0.8.0 for these features. The CT remains an optional legacy version and is unchanged.

## Run

Download the standalone executable from a release package and launch it after loading a game save. Choose a source slot, select a target, enable the desired slots, and apply. Models may need a menu refresh, map transition or save reload to update.

Restore Original Models writes built-in original values. Restore Launch Backup restores the snapshot captured at first Apply and preserves pre-existing changes present in that snapshot. Game updates or conflicting mods may invalidate the expected memory layout.

Known footstep sound issues remain. Model replacement does not guarantee matching footsteps, animations or expressions for every target. No game files are permanently modified.

## Source and build

- `app/`: standalone source, build script and tests.
- `data/`: standalone runtime catalogs and minimal costume labels.
- `ct/`: CT Lua source, builder and CT-specific catalogs.
- `artifacts/`: reference CT and checksum.

See [BUILDING.md](BUILDING.md), [DATA.md](DATA.md) and [THIRD_PARTY.md](THIRD_PARTY.md).

No extracted binary game databases, models, textures, audio or saves are distributed. No project-wide reuse license has been selected; third-party components and game-derived data retain their respective rights.
