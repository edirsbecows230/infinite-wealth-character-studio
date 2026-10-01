# Character Finder / 角色查找器

Open the Finder from a standalone source slot's **Select Character** button. The existing Curated, Female NPC, Male NPC and All categories are joined by Favorites. Choosing a candidate configures that slot; browsing and navigation never modify game memory.

在独立程序角色槽位中点击“更换目标角色”打开查找器。原有精选、女性 NPC、男性 NPC、全部角色分类之外，新增“收藏”。选择候选只配置槽位；浏览、上一个/下一个和搜索均不修改游戏内存。

## Search

Space-separated keywords use case-insensitive AND matching. Every keyword must occur, but keywords can match different fields. Examples: `c_w_f 023`, `hair 17`, `karen cw`, `12345 face_xxx`. The last two can use a user alias for an otherwise anonymous NPC; they are not built-in identity assignments.

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
