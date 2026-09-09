#!/usr/bin/env python3
"""Build the Character Studio dual-protagonist Character + Costume selector CT."""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from y8mod.ce_lua import compile_ce_lua  # noqa: E402
SOURCE = HERE / "y8_dual_source_selector.lua"
PLAN = HERE / "data" / "dual_source_selector.generated.json"
CATALOG = HERE / "data" / "female_npc_catalog.generated.json"
MALE_CATALOG = HERE / "data" / "male_npc_catalog.generated.json"
COSTUME_METADATA = HERE.parent / "data" / "costume_vanilla_rpg_costume.json"
OUTPUT = HERE.parent / "artifacts" / "LikeADragon8_InfiniteWealth_Character_Studio_v1.3.0-rc1.CT"


def lua_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def plan_lua(document: dict, catalog: dict, male_catalog: dict,
             costume_metadata: dict) -> str:
    lines = [
        "_G.Y8_PHASE17_DUAL_PLAN = {",
        f"  schema = {lua_string(document['schema'])},",
        "  sourceOrder = {",
    ]
    for source_id in document["source_order"]:
        lines.append(f"    {lua_string(source_id)},")
    lines.extend(("  },", "  sources = {"))
    for source_id in document["source_order"]:
        source = document["sources"][source_id]
        lines.extend((
            f"    [{lua_string(source_id)}] = {{",
            f"      id = {lua_string(source_id)},",
            f"      label = {lua_string(source['label'])},",
            f"      player = {source['player']},",
            f"      rowCount = {source['row_count']},",
            "      contextEntries = {",
        ))
        for entry in source["context_entries"]:
            lines.append(
                "        {{ key={key}, position={position}, originalRow={original_row} }},".format(
                    **entry
                )
            )
        lines.extend(("      },", "      records = {"))
        for record in source["source_records"]:
            lines.append(
                "        [{row}] = {{ costume={costume}, originalCharacter={original_character}, "
                "originalHawaii={original_character_hawaii} }},".format(**record)
            )
        lines.extend(("      },", "    },"))
    lines.extend(("  },", "  targetOrder = {"))
    for target in document["targets"]:
        lines.append(f"    {lua_string(target['id'])},")
    lines.extend(("  },", "  targets = {"))
    for target in document["targets"]:
        lines.extend((
            f"    [{lua_string(target['id'])}] = {{",
            f"      id = {lua_string(target['id'])},",
            f"      label = {lua_string(target['label'])},",
            f"      targetRow = {target['character_row']},",
            f"      standardCharacter = {target['standard_character']},",
            f"      standardHawaii = {target['standard_character_hawaii']},",
            "      sourcePlans = {",
        ))
        for source_id in document["source_order"]:
            source_plan = target["source_plans"][source_id]
            lines.extend((
                f"        [{lua_string(source_id)}] = {{",
                "          records = {",
            ))
            for record in source_plan["records"]:
                lines.append(
                    "            [{row}] = {{ targetCharacter={target_character}, "
                    "targetHawaii={target_character_hawaii} }},".format(**record)
                )
            lines.extend(("          },", "        },"))
        lines.extend(("      },", "      variants = {"))
        for variant in target["fixed_variants"]:
            costume_id = variant.get("source_costume")
            wrapper = costume_metadata.get(str(costume_id), {}) if costume_id is not None else {}
            costume_key, fields = next(iter(wrapper.items())) if wrapper else ("", {})
            lines.append(
                "        {{ id={id}, label={label}, character={character}, "
                "hawaii={character_hawaii}, variantKey={variant_key}, "
                "characterRow={character_row}, model={model}, sourceCostume={source_costume}, "
                "costumeKey={costume_key}, costumeName={costume_name} }},".format(
                    id=lua_string(variant["id"]),
                    label=lua_string(variant["label"]),
                    character=variant["character"],
                    character_hawaii=variant["character_hawaii"],
                    variant_key=variant["variant_key"],
                    character_row=variant["character_row"],
                    model=lua_string(variant["model"] or ""),
                    source_costume="nil" if costume_id is None else int(costume_id),
                    costume_key=lua_string(costume_key),
                    costume_name=lua_string(fields.get("name", "")),
                )
            )
        lines.extend(("      },", "    },"))
    lines.extend(("  },", "  labTargetOrder = {"))
    # Amon clan targets are real Character Identity rows, not lab catalog
    # placeholders, so they go into the curated targetOrder below.
    for entry in catalog["entries"]:
        lines.append(f"    {lua_string(entry['id'])},")
    lines.extend(("  },", "  labTargets = {"))
    for entry in catalog["entries"]:
        label = "[Unverified Female NPC / 未确认女性NPC] " + entry["label"]
        variant_label = (
            f"Catalog key {entry['character_key']} / 目录模型 — "
            f"{entry['tops_model']}")
        lines.extend((
            f"    [{lua_string(entry['id'])}] = {{",
            f"      id = {lua_string(entry['id'])},",
            f"      label = {lua_string(label)},",
            f"      targetRow = {entry['character_row']},",
            f"      standardCharacter = {entry['character_key']},",
            f"      standardHawaii = {entry['character_key']},",
            "      fixedNpc = true,",
            f"      catalogGroup = {lua_string('; '.join(entry['groups']))},",
            f"      faceModel = {lua_string(entry['face_model'])},",
            f"      hairModel = {lua_string(entry['hair_model'])},",
            f"      topsModel = {lua_string(entry['tops_model'])},",
            f"      voicer = {entry['voicer']},",
            "      variants = {",
            "        { id=%s, label=%s, character=%d, hawaii=%d, "
            "variantKey=%d, characterRow=%d, model=%s }," % (
                lua_string(f"catalog_{entry['character_key']}"),
                lua_string(variant_label),
                entry["character_key"], entry["character_key"],
                entry["character_key"], entry["character_row"],
                lua_string(entry["tops_model"]),
            ),
            "      },",
            "    },",
        ))
    lines.extend(("  },", "  maleTargetOrder = {"))
    for entry in male_catalog["entries"]:
        lines.append(f"    {lua_string(entry['id'])},")
    lines.extend(("  },", "  maleTargets = {"))
    for entry in male_catalog["entries"]:
        label = "[Male NPC / 男性NPC] " + entry["label"]
        variant_label = f"Catalog key {entry['character_key']} — {entry['tops_model']}"
        lines.extend((
            f"    [{lua_string(entry['id'])}] = {{",
            f"      id = {lua_string(entry['id'])},",
            f"      label = {lua_string(label)},",
            f"      targetRow = {entry['character_row']},",
            f"      standardCharacter = {entry['character_key']},",
            f"      standardHawaii = {entry['character_key']},",
            "      fixedNpc = true,",
            f"      catalogGroup = {lua_string('; '.join(entry['groups']))},",
            f"      faceModel = {lua_string(entry['face_model'])},",
            f"      hairModel = {lua_string(entry['hair_model'])},",
            f"      topsModel = {lua_string(entry['tops_model'])},",
            f"      voicer = {entry['voicer']},",
            "      variants = {",
            "        { id=%s, label=%s, character=%d, hawaii=%d, variantKey=%d, characterRow=%d, model=%s }," % (
                lua_string(f"catalog_{entry['character_key']}"), lua_string(variant_label),
                entry["character_key"], entry["character_key"], entry["character_key"],
                entry["character_row"], lua_string(entry["tops_model"])),
            "      },", "    },",
        ))
    lines.extend(("  },", "}", ""))
    return "\n".join(lines)


def validate_plan(document: dict) -> None:
    if document.get("schema") != "y8.runtime_dual_source_selector.v2":
        raise ValueError("unexpected dual-source plan schema")
    if document.get("source_order") != ["ichiban", "kiryu"]:
        raise ValueError("dual-source order must be Ichiban, Kiryu")
    if len(document.get("targets", [])) != 63:
        raise ValueError("curated selector requires 63 targets including Queen, both runners, and Amon clan")
    expected = {"ichiban": (7, 67), "kiryu": (94, 61)}
    positions: set[int] = set()
    for source_id, (entry_count, row_count) in expected.items():
        source = document["sources"][source_id]
        if len(source["context_entries"]) != entry_count:
            raise ValueError(f"{source_id} Character entry count mismatch")
        if len(source["source_records"]) != row_count or source["row_count"] != row_count:
            raise ValueError(f"{source_id} Costume row count mismatch")
        for entry in source["context_entries"]:
            position = entry["position"]
            if position in positions:
                raise ValueError(f"duplicate Character mapping position {position}")
            positions.add(position)
    if len(positions) != 101:
        raise ValueError("dual-source Character mapping union must contain 101 entries")
    for target in document["targets"]:
        for source_id, (_, row_count) in expected.items():
            if len(target["source_plans"][source_id]["records"]) != row_count:
                raise ValueError(f"{target['id']}/{source_id} target plan row count mismatch")
        if not target.get("fixed_variants"):
            raise ValueError(f"{target['id']} has no fixed variant")
        for variant in target["fixed_variants"]:
            if not variant.get("variant_key") or variant.get("character_row") is None:
                raise ValueError(f"{target['id']} has an unresolved fixed variant")
    sizes = document.get("transaction_sizes", {})
    if sizes != {"ichiban": 141, "kiryu": 216, "both": 357}:
        raise ValueError(f"unexpected transaction sizes: {sizes!r}")


def combined_lua() -> str:
    document = json.loads(PLAN.read_text(encoding="utf-8"))
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    male_catalog = json.loads(MALE_CATALOG.read_text(encoding="utf-8"))
    costume_metadata = json.loads(COSTUME_METADATA.read_text(encoding="utf-8"))
    validate_plan(document)
    if catalog.get("schema") != "y8.female_npc_catalog.v1" or \
       catalog.get("count") != len(catalog.get("entries", [])) or \
       catalog.get("count", 0) < 300:
        raise ValueError("missing/invalid female NPC lab catalog")
    if male_catalog.get("schema") != "y8.male_npc_catalog.v1" or \
       male_catalog.get("count") != len(male_catalog.get("entries", [])) or \
       male_catalog.get("count", 0) < 4000:
        raise ValueError("missing/invalid male NPC lab catalog")
    if costume_metadata.get("TABLE_ID") != 3536 or costume_metadata.get("ROW_COUNT") != 480:
        raise ValueError("missing/invalid RPG Costume metadata")
    source = SOURCE.read_text(encoding="utf-8")
    for banned in ("autoAssemble", "debug_setBreakpoint", "debug_removeBreakpoint"):
        if banned in source:
            raise ValueError(f"dual-source source contains banned API: {banned}")
    for required in (
        "function S.apply", "function S.applySlots", "function S.restore", "function S.showSelector",
        "writeInteger", "writeSmallInteger", "restoreSnapshot",
        "verifySelection", "forceResetToVanilla", "verifyVanilla",
    ):
        if required not in source:
            raise ValueError(f"dual-source source is missing required primitive: {required}")
    return plan_lua(document, catalog, male_catalog, costume_metadata) + source.rstrip() + "\n"


def build_text(lua: str) -> str:
    open_script = '''[ENABLE]
{$lua}
if syntaxcheck then return end
local ok, err = Y8Phase17.showSelector()
if not ok then error(err) end
{$asm}

[DISABLE]
{$lua}
if syntaxcheck then return end
{$asm}'''
    validate_script = '''[ENABLE]
{$lua}
if syntaxcheck then return end
local ok, err = Y8Phase17.validateAll()
if not ok then error(err) end
{$asm}

[DISABLE]
{$lua}
if syntaxcheck then return end
{$asm}'''
    restore_script = '''[ENABLE]
{$lua}
if syntaxcheck then return end
local ok, err = Y8Phase17.restore("CT Restore entry")
if not ok then error(err) end
{$asm}

[DISABLE]
{$lua}
if syntaxcheck then return end
{$asm}'''
    reset_script = '''[ENABLE]
{$lua}
if syntaxcheck then return end
local ok, err = Y8Phase17.forceResetToVanilla("manual CT emergency reset")
if not ok then error(err) end
{$asm}

[DISABLE]
{$lua}
if syntaxcheck then return end
{$asm}'''
    return f'''<?xml version="1.0" encoding="utf-8"?>
<CheatTable CheatEngineTableVersion="45">
  <CheatEntries>
    <CheatEntry>
      <ID>1900</ID>
      <Description>"Like a Dragon: Infinite Wealth Character Studio v1.2.1-rc1 / 如龙8 无尽财富角色模型工坊"</Description>
      <Options moHideChildren="1"/>
      <GroupHeader>1</GroupHeader>
      <CheatEntries>
        <CheatEntry>
          <ID>1901</ID>
          <Description>"Open Character &amp; Costume Selector / 打开角色与服装选择器"</Description>
          <VariableType>Auto Assembler Script</VariableType>
          <AssemblerScript><![CDATA[{open_script}]]></AssemblerScript>
        </CheatEntry>
        <CheatEntry>
          <ID>1902</ID>
          <Description>"Validate Runtime Databases (Read Only) / 验证运行时数据库（只读）"</Description>
          <VariableType>Auto Assembler Script</VariableType>
          <AssemblerScript><![CDATA[{validate_script}]]></AssemblerScript>
        </CheatEntry>
        <CheatEntry>
          <ID>1903</ID>
          <Description>"Restore State Saved at First Apply / 恢复首次应用前状态"</Description>
          <VariableType>Auto Assembler Script</VariableType>
          <AssemblerScript><![CDATA[{restore_script}]]></AssemblerScript>
        </CheatEntry>
        <CheatEntry>
          <ID>1904</ID>
          <Description>"EMERGENCY ONLY: Force Vanilla Reset (May Override File Mods) / 紧急原版重置"</Description>
          <VariableType>Auto Assembler Script</VariableType>
          <AssemblerScript><![CDATA[{reset_script}]]></AssemblerScript>
        </CheatEntry>
      </CheatEntries>
    </CheatEntry>
  </CheatEntries>
  <UserdefinedSymbols/>
  <LuaScript><![CDATA[
{lua}]]></LuaScript>
</CheatTable>
'''


def compile_with_ce_lua(lua_source: str, *, required: bool = False) -> str:
    return compile_ce_lua(
        lua_source, chunk_name="phase1_7_dual_source", required=required)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    lua = combined_lua()
    ce_lua_status = compile_with_ce_lua(lua, required=args.check)
    text = build_text(lua)
    ET.fromstring(text)
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != text:
            raise SystemExit("Character Studio dual-source CT is stale; run builder without --check")
        print("OK: Character Studio dual-source CT is current and self-contained; "
              f"CE Lua validation={ce_lua_status.upper()}")
        return 0
    OUTPUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {OUTPUT} ({len(text.encode('utf-8'))} bytes)")
    print(f"CE Lua validation={ce_lua_status.upper()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
