# Character Finder / 角色查找器

Open the Finder from a standalone source slot's **Select Character** button. Categories include Curated, Named Side, Female NPC, Male NPC, All and Favorites. Choosing a candidate configures that slot; browsing and navigation never modify game memory.

在独立程序角色槽位中点击“更换目标角色”打开查找器。分类包含精选、具名支线、女性 NPC、男性 NPC、全部角色和收藏。选择候选只配置槽位；浏览、上一个/下一个和搜索均不修改游戏内存。

Use **Back** in the Finder's top bar to return without choosing a character, including when a search has no results. The bottom Cancel button remains available.

点击查找器顶部“返回”即可退出，不必选择角色，搜索无结果时也可返回。底部仍保留“取消”按钮。

## Named Side Characters (v0.8.0)

Standalone v0.8.0 includes 25 reviewed named identities, including Karen, Gondawara, Professor Okita, Charlie, Mameoka and Sawai. Choose **Named Side** or **All** to search their names, Japanese names and documented aliases, such as `Karen UFO` or `Susumu Gondawara`. The older v0.7.0 executable does not include these features.

**All 25 newly added named characters and their appearances remain untested in game.** Static identity/model checks and offline transaction tests do not establish gameplay compatibility. / **新增的 25 个具名角色及其造型均尚未实机测试。** 静态映射核验与离线事务测试不等于游戏内兼容性验证。

These 25 identities expose 40 Character-key appearances; alternate appearances remain variants of the same identity. Selecting a new named identity starts at its standard appearance. In the source slot, choose another appearance from the existing fixed-variant selector and click Apply explicitly. Alternate appearance keys, hex keys, rows and model fields also find the owning identity; searching does not automatically select a variant. Similarity filters compare the identity's default model/face/hair fields.

The reviewed overlay lives in `app/data/named_side_characters.json`, with upstream hashes and evidence references. Existing generated catalogs are unchanged. Favorites and custom aliases use the same local user configuration as other targets. Empty face/hair fields are retained; no anonymous NPC names are invented. Special-context variants still need gameplay compatibility testing.

All named entries have Chinese display labels, including 卡伦、权田原组长、冲田博士、查理、豆冈、泽井. These are application localization labels, not a claim of official Chinese spellings. English/Japanese identity names and technical identifiers remain searchable.

独立程序 v0.8.0 包含 25 个经静态证据审核的身份，包括 Karen、Gondawara、Professor Okita、Charlie、Mameoka、Sawai。在“具名支线”或“全部角色”中可搜索姓名、日文名及已记录别名，例如 `Karen UFO`、`Susumu Gondawara`、`权田原组长`。旧版 v0.7.0 EXE 不包含这些新增内容。

25 个人物共保留 40 个造型 key；换到一个新的具名人物时默认使用标准造型，在槽位的固定造型下拉框中可切换其他变体，再显式点击应用。搜索其他造型的 key、十六进制 key、row 或 model 仍返回该人物，不会自动选择变体。相似角色过滤比较默认造型的 model/face/hair。新增数据位于 `app/data/named_side_characters.json`，包含原始数据 hash 和证据引用，不修改现有 generated catalogs。收藏/用户别名沿用本地配置；特殊场景变体仍需游戏内兼容性测试。

The expanded presets cover the following additional side-story/activity characters. Identity evidence comes from named speaker/voice links or explicit named activity-to-Character references, not face similarity. Defaults avoid seated, undressed and weather-specific appearances where a normal appearance exists. Static mappings are checked; the new appearances have not been tested in game.

新增预设覆盖下列支线/活动人物。身份依据为具名对话/语音关联或活动表中明确的姓名 → Character 引用，不根据相同脸型推断。存在普通造型时，默认避开坐姿、无衣和特殊天气造型。模型映射已经静态核对，新增造型尚未实机测试。

| Name / 姓名 | Default key / 默认 key | Other appearance keys / 其他造型 |
| --- | --- | --- |
| Ace / 艾斯 | 25957 | — |
| Aina / 艾娜 | 26192 | 7052 |
| Alo-Happy / 阿罗哈皮 | 28062 | — |
| Bony Kashiwa / 邦尼柏 | 23481 | — |
| Danny / 丹尼 | 25224 | — |
| Elizabeth / 伊丽莎白 | 23498 | 28063 |
| Ikari / 猪狩 | 6212 | 26901 |
| Jack / 杰克 | 25961 | — |
| James / 詹姆斯 | 25127 | — |
| Joker / 小丑 | 25965 | — |
| King / 国王 | 25969 | — |
| Machiko-san / 真知子 | 13943 | — |
| Matt Tropico / 马特·特罗皮科 | 28040 | — |
| Nathan / 内森 | 25126 | — |
| Onishi / 大西 | 12616 | — |
| Raymond / 雷蒙德 | 28065 | 28066 |
| Ringmaster Yasuda / 安田团长 | 25054 | — |
| Thomas / 托马斯 | 23007 | 23008 |
| Tony / 托尼 | 25052 | — |

Unresolved homonyms, generic role-only NPC labels and animals are excluded. This list is not an exhaustive list of all side-story characters. / 同名存疑、仅有职务称谓的 NPC 和动物不在本次新增范围；这不是所有支线角色的完整名单。

## Search

Space-separated keywords use case-insensitive AND matching within the chosen category. Every keyword must occur, but keywords can match different fields. Examples: `c_w_f 023`, `hair 17`, `karen cw`, `12345 face_xxx`. Anonymous NPCs can also be searched using a custom local alias; aliases do not establish official identities.

Search covers both languages in original display labels, target ID, model, face, hair, decimal key, hexadecimal key (`12345` / `0x3039`), row, voice, region, catalog group, existing search metadata and the user alias. Numeric queries remain substring matches across searchable fields. Empty search shows all candidates in the chosen category.

空格分隔的关键词全部匹配才显示，忽略大小写，各词可以匹配不同字段。支持原始中英文名称、目标 ID、模型、脸型、发型、十进制/十六进制 Key、行、语音、地区、目录分组、原有搜索信息和用户别名。数值搜索仍采用字段中的子串匹配。

## Similar candidates

**Same Face**, **Same Hair** and **Same Model** search the entire catalog using exact, case-insensitive field equality. Empty face/hair disables its button. Same Model uses the exact model code, without inferred families or story identities. These actions clear the search text, switch to All and install a visible similarity filter. Further keywords refine the result; Clear Filter removes the similarity constraint and keywords. Switching categories can intersect the similarity filter with Favorites or another category.

相同脸型、发型和模型按字段值精确筛选整个目录，不推断剧情身份。点击时清空关键词、切换到全部角色，并显示筛选条件；随后输入关键词可继续细分，清除筛选可解除条件。字段为空时对应按钮禁用。

## Favorites and aliases

Each target can be starred and given one free-text alias (up to 256 characters in the editor). Save edits the alias; Delete Alias removes it. An alias is an overlay: the original target ID, model, face/hair, row/key and voice remain available in the inspector. Anonymous results use NPC + key identifiers rather than invented names, with visible model and face/hair codes. Tooltips expose the complete result text and target ID.

Normal application startup loads `character_finder.json` from Qt's `QStandardPaths.AppDataLocation`. On Windows, with the application's standard identity, this is:

```text
%APPDATA%\Infinite Wealth Modding\Infinite Wealth Character Studio\character_finder.json
```

Missing files start empty. Invalid/unreadable JSON starts with empty preferences and a Finder notice. Invalid records and IDs absent from the current catalog are ignored. Saving writes a temporary file in the same directory, flushes it and atomically replaces the old file; failed saves keep the old file and in-memory preferences and display an error. Bundled catalogs are never edited. Temporary custom-key favorites only appear while that target exists in the current repository; the key must still be re-resolved in a new game session.

收藏和别名存放在上述用户目录下的 JSON，与打包目录分开。缺失文件正常启动，损坏或无法读取时以空配置启动并提示；失效目标被忽略。保存采用同目录临时文件和原子替换，失败时保留旧状态并显示错误。

## Browsing and game application

Previous / Next and the list's Up / Down keys move within matching results; the ordinal shows the current candidate and total. The inspector scrolls vertically at smaller supported window sizes. Selection returns to the slot editor. Apply there uses the existing `TrainerEngine` transaction.

There is no in-Finder game Preview button. The current transaction owns all ten slots and restores omitted slots, so applying a one-slot selection could change other active slots. A genuinely isolated preview needs additional transaction semantics and is deferred. No memory layout or transaction-writing code is changed by the Finder.

上一个/下一个以及列表方向键用于逐项浏览，显示当前序号和总数。窗口较小时 inspector 可纵向滚动。回到槽位后再点击应用，沿用现有事务机制。查找器内暂不提供游戏预览：现有事务会恢复未选槽位，直接提交一个槽位可能改变其他已应用角色。

The Cheat Engine version remains legacy/optional and does not gain Finder features.
