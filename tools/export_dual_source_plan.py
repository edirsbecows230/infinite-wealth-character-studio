#!/usr/bin/env python3
"""Export the Ichiban/Kiryu/Both runtime selector plan."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
BASE_PLAN = PROJECT / "tools" / "reference" / \
    "npc_runtime_selector.generated.json"
OUTPUT = PROJECT / "data" / "dual_source_selector.generated.json"

sys.path.insert(0, str(PROJECT))
import y8_character_replacer as replacer  # noqa: E402


SOURCE_DEFS = {
    "ichiban": {"label": "Ichiban / 春日", "player": 4, "face_target": "ichiban"},
    "kiryu": {"label": "Kiryu / 桐生", "player": 1, "face_target": "kiryu"},
}

# Scene-specific Ichiban identities selected directly by scene_human_model.
# They are separate Character keys, not ordinary Costume variants, so they
# must participate in the same identity transaction as the three base keys.
# Tuple fields: (*character key, expected Character row, expected tops model).
ICHIBAN_SPECIAL_CONTEXTS = (
    (10513, 8282, "c_cm_x_ichiban_Is"),       # Dondoko Island neck light
    (19943, 8309, "c_cm_x_ichiban_date"),     # date scene variant 1
    (23390, 8367, "c_cm_x_ichiban_wk"),       # Chapter 1 Hello Work/ajito
    (28266, 8310, "c_cm_x_ichiban_date1"),    # date scene variant 2
)
EXPECTED_ROWS = {
    "ichiban": list(range(228, 295)),
    "kiryu": list(range(295, 356)),
}

# Extend the 40-target reference mapping. Each
# tuple is (id, label, Character Row, *character key, tops model, voicer).
# Judie is resolved through najimi_aloha_links row 46 -> najimi_045 ->
# najimi_list.character_id 13469, rather than inferred from appearance.
NEW_FEMALE_NPCS = (
    ("sujimon_queen", "[Sujimon League / 江湖宝贝联盟] Queen / 女王", 10396, 25979,
     "c_cw_x_queen", 1113),
    ("marilyn", "[Substory 15 / 支线15] Marilyn / 玛丽琳", 9800, 25128,
     "c_cw_x_onepieceA", 1215),
    ("marian", "[Substory 35 / 支线35] Marian / 玛丽亚娜", 9813, 26197,
     "c_cw_x_SH31_marian", 695),
    ("mao", "[Substory 9 / 支线9] Mao / 玛奥", 9804, 25046,
     "c_cw_x_SH29_mao", 0),
    ("hitomi_hamabe", "[Substory 14 / 支线14] Hitomi Hamabe / 滨边瞳", 9774, 26195,
     "c_cw_x_SH16_hamabe", 696),
    ("kiana", "[Substory 12 / 支线12] Kiana / 绮亚娜（草裙舞者）", 9816, 23500,
     "c_cw_x_hura", 410),
    ("julie", "[Named NPC / 具名NPC] Julie / 茱莉（武器工坊）", 9821, 28060,
     "c_cw_x_SH58_julie", 788),
    ("judie", "[ALOHA LINKs] Judie / 朱迪", 9712, 13469,
     "c_cw_t_swimA", 963),
    ("seiryo_student_a", "[Yokohama / 横滨] Seiryo High Candidate A / 诚稜高中女学生候选 A",
     9930, 10455, "c_cw_t_SstudentS", 202),
    ("seiryo_student_b", "[Yokohama / 横滨] Seiryo High Candidate B / 诚稜高中女学生候选 B",
     9931, 10456, "c_cw_t_SstudentS", 204),
    ("hawaii_woman_surfer", "[Hawaii / 夏威夷] Woman Surfer / 女冲浪者",
     9973, 23216, "c_cw_t_swimB", 925),
    ("hawaii_woman_runner", "[Hawaii Runner A / 跑步女性A] White/American Candidate / 白人候选",
     9956, 23214, "c_cw_t_camisoleA", 58),
    ("hawaii_woman_runner_b", "[Hawaii Runner B / 跑步女性B] Comparison Candidate / 对照候选",
     9957, 23215, "c_cw_t_camisoleA", 59),
    ("hawaii_woman_american_dress", "[Hawaii / 夏威夷] American Woman — Dress / 美国女性·连衣裙",
     9480, 22681, "c_cw_x_dressB", 955),
    ("hawaii_woman_american_tanktop", "[Hawaii / 夏威夷] American Woman — Tank Top / 美国女性·背心",
     9486, 22687, "c_cw_t_tanktop", 955),
    ("hawaii_woman_polynesian_cutsew", "[Hawaii / 夏威夷] Polynesian Woman — Casual / 波利尼西亚女性·休闲装",
     9552, 22723, "c_cw_t_cutsewA", 962),
    ("hawaii_woman_japanese_aloha", "[Hawaii / 夏威夷] Japanese Tourist — Aloha / 日裔游客·Aloha",
     9630, 22789, "c_cw_t_alohaA", 955),
    ("hawaii_woman_japanese_swim", "[Hawaii / 夏威夷] Japanese Woman — Swimsuit / 日裔女性·泳装",
     9588, 22753, "c_cw_t_swimA", 956),
    ("hawaii_woman_polynesian_swim", "[Hawaii / 夏威夷] Polynesian Woman — Swimsuit / 波利尼西亚女性·泳装",
     9583, 22748, "c_cw_t_swimA", 956),
)

# Additional Character identities that are visual states of one curated NPC.
# Tuple fields: (id, label, Character Row, *character key, tops model, voicer).
FIXED_NPC_EXTRA_VARIANTS = {
    "mao": (
        ("tiara", "Tiara / 戴冠", 9805, 25047, "c_cw_x_SH29_mao", 0),
    ),
    "hitomi_hamabe": (
        ("mud", "Mud / 沾泥", 9775, 26196, "c_cw_x_SH16_hamabe", 696),
    ),
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def context_entries(character, key_positions, face_target):
    entries = {}
    for row in range(character.row_count):
        if character.val(row, "face_target") != face_target or \
           character.val(row, "main_chara") != 1:
            continue
        key = character.val(row, "*character")
        if key is None or key in entries:
            continue
        position = key_positions.get(key)
        if position is None:
            raise SystemExit(f"{face_target}: key {key} has no sorted-index position")
        entries[key] = {
            "key": key,
            "position": position,
            "original_row": struct.unpack_from(
                "<I", character.buf, replacer.MAPPING_OFF + position * 4)[0],
        }
    return sorted(entries.values(), key=lambda item: item["position"])


def original_records(costume, rows):
    return [{
        "row": row,
        "costume": costume.val(row, "**costume"),
        "original_character": costume.val(row, "character"),
        "original_character_hawaii": costume.val(row, "character_hawaii"),
    } for row in rows]


def target_source_records(overrides, standard_key, regional_base,
                          normalize_fallback):
    records = []
    for row, costume_id, category, character, hawaii in overrides:
        if normalize_fallback and (character, hawaii) == regional_base:
            character, hawaii = standard_key, standard_key
        records.append({
            "row": row,
            "costume": costume_id,
            "category": category,
            "target_character": character,
            "target_character_hawaii": hawaii,
        })
    records.sort(key=lambda item: item["row"])
    return records


def build_fixed_npc_target(character, sources, definition):
    target_id, label, row, expected_key, expected_model, expected_voicer = definition
    described = replacer.describe_row(character, row)
    if described["character"] != expected_key or described["model"] != expected_model or \
       described["voicer"] != expected_voicer or described["adv_model_id"] in (None, 0):
        raise SystemExit(
            f"{target_id}: Character metadata drift row={row} "
            f"key={described['character']} model={described['model']!r} "
            f"voice={described['voicer']}")

    source_plans = {}
    for source_id, source in sources.items():
        records = [{
            "row": item["row"],
            "costume": item["costume"],
            "category": "npc_fixed_identity",
            "target_character": expected_key,
            "target_character_hawaii": expected_key,
        } for item in source["source_records"]]
        source_plans[source_id] = {
            "records": records,
            "category_counts": {"npc_fixed_identity": len(records)},
            "fallback_policy": "fixed NPC identity in both region columns",
        }

    fixed_variants = [{
        "id": f"pair_{expected_key}_{expected_key}",
        "label": f"Default / 默认模型 — {expected_model} ({expected_key}/{expected_key})",
        "source_costume": None,
        "category": "default",
        "character": expected_key,
        "character_hawaii": expected_key,
        "variant_key": expected_key,
        "character_row": row,
        "model": expected_model,
    }]
    for variant_id, variant_label, variant_row, variant_key, variant_model, variant_voice \
            in FIXED_NPC_EXTRA_VARIANTS.get(target_id, ()):
        variant = replacer.describe_row(character, variant_row)
        if variant["character"] != variant_key or variant["model"] != variant_model or \
           variant["voicer"] != variant_voice or variant["adv_model_id"] in (None, 0):
            raise SystemExit(
                f"{target_id}/{variant_id}: Character metadata drift row={variant_row} "
                f"key={variant['character']} model={variant['model']!r} "
                f"voice={variant['voicer']}")
        fixed_variants.append({
            "id": f"pair_{variant_key}_{variant_key}",
            "label": f"{variant_label} — {variant_model} ({variant_key}/{variant_key})",
            "source_costume": None,
            "category": variant_id,
            "character": variant_key,
            "character_hawaii": variant_key,
            "variant_key": variant_key,
            "character_row": variant_row,
            "model": variant_model,
        })

    return {
        "id": target_id,
        "label": label,
        "category": "female_npc_expansion",
        "character_row": row,
        "character": expected_key,
        "adv_model_id": described["adv_model_id"],
        "model": expected_model,
        "face_target": described["face_target"],
        "voicer": expected_voicer,
        "voice_status": "known Character DB voicer",
        "player_slot": None,
        "base_character": expected_key,
        "base_character_hawaii": expected_key,
        "category_counts": {"npc_fixed_identity": sources["ichiban"]["row_count"]},
        "fixed_variants": fixed_variants,
        "validation": "curated original Character DB row/model/voicer assertion",
        "source_plans": source_plans,
        "standard_character": expected_key,
        "standard_character_hawaii": expected_key,
        "regional_base_character": expected_key,
        "regional_base_character_hawaii": expected_key,
        "kiryu_target_slot": None,
    }


def build_document() -> dict:
    base = json.loads(BASE_PLAN.read_text(encoding="utf-8"))
    if base.get("schema") != "y8.runtime_unified_selector.v2" or \
       len(base.get("targets", [])) != 40:
        raise SystemExit("40-target reference plan is missing or changed")

    character = replacer.load_char()
    costume = replacer.RowTable(replacer.COSTUME_BIN, replacer.CC_FIELDS)
    key_positions = replacer.build_key_pos_map(character)
    key_model = replacer.build_key_model(character)
    rpg_names = replacer.parse_row_names(Path(replacer.RPG_COSTUME_BIN).read_bytes())

    sources = {}
    all_context_keys = set()
    for source_id, definition in SOURCE_DEFS.items():
        rows = [row for row in range(costume.row_count)
                if costume.val(row, "*player") == definition["player"]]
        if rows != EXPECTED_ROWS[source_id]:
            raise SystemExit(f"{source_id}: unexpected Costume rows {rows}")
        if source_id == "ichiban":
            entries = []
            for item in base["context_entries"]:
                position = item["position"]
                entries.append({
                    "key": item["key"],
                    "position": position,
                    "original_row": struct.unpack_from(
                        "<I", character.buf,
                        replacer.MAPPING_OFF + position * 4)[0],
                })
            existing_keys = {item["key"] for item in entries}
            for key, expected_row, expected_model in ICHIBAN_SPECIAL_CONTEXTS:
                if key in existing_keys:
                    raise SystemExit(f"ichiban: special context key {key} already exists")
                position = key_positions.get(key)
                if position is None:
                    raise SystemExit(f"ichiban: special context key {key} has no position")
                original_row = struct.unpack_from(
                    "<I", character.buf,
                    replacer.MAPPING_OFF + position * 4)[0]
                described = replacer.describe_row(character, original_row)
                if original_row != expected_row or described["character"] != key or \
                   described["model"] != expected_model or \
                   described["face_target"] != "ichiban" or \
                   described["main_chara"] != 1:
                    raise SystemExit(
                        f"ichiban: special context drift key={key} row={original_row} "
                        f"model={described['model']!r} face={described['face_target']!r} "
                        f"main={described['main_chara']}")
                entries.append({
                    "key": key,
                    "position": position,
                    "original_row": original_row,
                })
            entries.sort(key=lambda item: item["position"])
        else:
            entries = context_entries(character, key_positions, definition["face_target"])
        expected_keys = 7 if source_id == "ichiban" else 94
        if len(entries) != expected_keys:
            raise SystemExit(
                f"{source_id}: expected {expected_keys} context keys, got {len(entries)}")
        overlap = all_context_keys.intersection(item["key"] for item in entries)
        if overlap:
            raise SystemExit(f"source context key overlap: {sorted(overlap)}")
        all_context_keys.update(item["key"] for item in entries)
        sources[source_id] = {
            "id": source_id,
            **definition,
            "row_count": len(rows),
            "context_entries": entries,
            "source_records": original_records(costume, rows),
        }

    targets = []
    for existing in base["targets"]:
        row = existing["character_row"]
        target = replacer.describe_row(character, row)
        if target["character"] != existing["character"]:
            raise SystemExit(f"{existing['id']}: target Character Row drift")
        standard_key = target["character"]
        source_plans = {
            "ichiban": {
                "records": existing["records"],
                "category_counts": existing["category_counts"],
                "fallback_policy": "proven Mod v2.3 regional base",
            }
        }

        target_slot, regional_base, kiryu_overrides = replacer.build_costume_overrides(
            character, costume, key_model, rpg_names, target,
            source_slot=SOURCE_DEFS["kiryu"]["player"], source_name="kiryu")
        if sorted(item[0] for item in kiryu_overrides) != EXPECTED_ROWS["kiryu"]:
            raise SystemExit(f"{existing['id']}: Kiryu plan does not cover 61 rows")
        kiryu_records = target_source_records(
            kiryu_overrides, standard_key, regional_base, normalize_fallback=True)
        source_plans["kiryu"] = {
            "records": kiryu_records,
            "category_counts": dict(Counter(item[2] for item in kiryu_overrides)),
            "fallback_policy": "canonical target row key in both region columns",
        }

        copied = dict(existing)
        copied.pop("records", None)
        fixed_variants = []
        for variant in existing["fixed_variants"]:
            variant_key = variant["character"] or variant["character_hawaii"]
            position = key_positions.get(variant_key)
            if position is None:
                raise SystemExit(
                    f"{existing['id']}: fixed variant key {variant_key} has no sorted-index position")
            variant_row = struct.unpack_from(
                "<I", character.buf, replacer.MAPPING_OFF + position * 4)[0]
            if variant_row < 0 or variant_row >= character.row_count:
                raise SystemExit(
                    f"{existing['id']}: invalid fixed variant row {variant_row} for key {variant_key}")
            described = replacer.describe_row(character, variant_row)
            if described["character"] != variant_key:
                raise SystemExit(
                    f"{existing['id']}: fixed variant key/row mismatch {variant_key}/{variant_row}")
            copied_variant = dict(variant)
            copied_variant["variant_key"] = variant_key
            copied_variant["character_row"] = variant_row
            fixed_variants.append(copied_variant)
        copied["fixed_variants"] = fixed_variants
        copied["source_plans"] = source_plans
        copied["standard_character"] = standard_key
        copied["standard_character_hawaii"] = standard_key
        copied["regional_base_character"] = existing["base_character"]
        copied["regional_base_character_hawaii"] = existing["base_character_hawaii"]
        copied["kiryu_target_slot"] = target_slot
        targets.append(copied)

    for definition in NEW_FEMALE_NPCS:
        targets.append(build_fixed_npc_target(character, sources, definition))

    ids = [target["id"] for target in targets]
    rows = [target["character_row"] for target in targets]
    if len(ids) != len(set(ids)) or len(rows) != len(set(rows)):
        raise SystemExit("duplicate selector id or Character Row")

    target_counts = dict(base["target_counts"])
    target_counts["female_npc_expansion"] = len(NEW_FEMALE_NPCS)
    target_counts["total"] = len(targets)

    return {
        "schema": "y8.runtime_dual_source_selector.v2",
        "source": {
            "base_plan": BASE_PLAN.name,
            "base_plan_sha256": sha256(BASE_PLAN.read_bytes()),
            "rule_engine": "y8_character_replacer.py::build_costume_overrides",
            "character_sha256": sha256(character.buf),
            "costume_sha256": sha256(costume.buf),
        },
        "source_order": ["ichiban", "kiryu"],
        "sources": sources,
        "target_counts": target_counts,
        "targets": targets,
        "transaction_sizes": {
            "ichiban": 7 + 67 * 2,
            "kiryu": 94 + 61 * 2,
            "both": 101 + 128 * 2,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    text = json.dumps(build_document(), ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != text:
            raise SystemExit("dual-source selector plan is stale; run exporter without --check")
        print(f"OK: dual-source plan is current (2 sources x {len(NEW_FEMALE_NPCS) + 40} targets)")
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {OUTPUT}: 2 sources x {len(NEW_FEMALE_NPCS) + 40} targets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
