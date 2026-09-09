#!/usr/bin/env python3
"""Generate the shared, compact male NPC comparison catalog.

The catalog is presentation data for both the original CT and the standalone
trainer.  Entries are intentionally marked unverified: NPC-pool membership
proves a usable model identity, not a public-facing character name.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
NPC_LIST_JSON = PROJECT / "local" / "character_npc_npc_list.bin.json"
CURATED_PLAN = PROJECT / "data" / "dual_source_selector.generated.json"
OUTPUT_JSON = PROJECT / "data" / "male_npc_catalog.generated.json"
OUTPUT_CSV = PROJECT / "data" / "male_npc_catalog.generated.csv"

sys.path.insert(0, str(PROJECT))
import y8_character_replacer as replacer  # noqa: E402


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def nested_ids(record: dict) -> list[int]:
    table = record.get("character_id_table")
    if not isinstance(table, dict):
        return []
    result = []
    for index in range(table.get("ROW_COUNT", 0)):
        wrapped = table.get(str(index), {})
        cell = next(iter(wrapped.values()), {})
        value = cell.get("1")
        if isinstance(value, int) and value:
            result.append(value)
    return result


def selected_group(_group: str, record: dict) -> bool:
    return record.get("reARMP_isValid") == "1" and record.get("sex") == 1


def region_for(groups: list[str]) -> str:
    lowered = [item.lower() for item in groups]
    if any(item.startswith(("h_", "hw_")) for item in lowered):
        return "hawaii"
    if any(item.startswith(("k_", "kb_")) for item in lowered):
        return "kamurocho"
    if any(item.startswith(("y_", "i_", "hs_")) for item in lowered):
        return "yokohama"
    return "other"


def build_document() -> dict:
    npc = json.loads(NPC_LIST_JSON.read_text(encoding="utf-8"))
    character = replacer.load_char()
    model = replacer.load_model()
    key_to_row = {
        character.val(row, "*character"): row for row in range(character.row_count)
    }
    model_by_key = {}
    for row in range(model.row_count):
        key = model.val(row, "*model")
        if key is not None and key not in model_by_key:
            model_by_key[key] = {
                "model_row": row,
                "face_model": model.val(row, "face_model") or "",
                "hair_model": model.val(row, "hair_model") or "",
                "tops_model": model.val(row, "tops_model") or "",
            }

    curated_keys = set()
    if CURATED_PLAN.exists():
        plan = json.loads(CURATED_PLAN.read_text(encoding="utf-8"))
        curated_keys.update(
            target.get("character") for target in plan.get("targets", [])
            if isinstance(target.get("character"), int)
        )

    candidates: dict[int, dict] = {}
    for index in range(npc["ROW_COUNT"]):
        wrapped = npc[str(index)]
        group = next(iter(wrapped))
        record = wrapped[group]
        if not selected_group(group, record):
            continue
        for slot, character_key in enumerate(nested_ids(record), 1):
            row = key_to_row.get(character_key)
            if row is None or character_key in curated_keys:
                continue
            adv_model_id = character.val(row, "adv_model_id")
            model_info = model_by_key.get(adv_model_id)
            if not model_info:
                continue
            item = candidates.get(character_key)
            if item is None:
                item = {
                    "id": f"male_lab_{character_key}",
                    "character_key": character_key,
                    "character_row": row,
                    "adv_model_id": adv_model_id,
                    **model_info,
                    "voicer": character.val(row, "voicer"),
                    "groups": [],
                    "confirmed_identity": False,
                }
                candidates[character_key] = item
            reference = f"{group}[{slot}]"
            if reference not in item["groups"]:
                item["groups"].append(reference)

    entries = sorted(candidates.values(), key=lambda item: (
        region_for(item["groups"]), item["groups"][0], item["character_key"]))
    counts: dict[str, int] = {}
    for item in entries:
        item["region"] = region_for(item["groups"])
        counts[item["region"]] = counts.get(item["region"], 0) + 1
        item["label"] = (
            f"[{item['region']}] {item['groups'][0]} | {item['tops_model']} | "
            f"{item['face_model']} / {item['hair_model']} | "
            f"key {item['character_key']} row {item['character_row']}")

    return {
        "schema": "y8.male_npc_catalog.v1",
        "source": {
            "npc_list_json": NPC_LIST_JSON.name,
            "npc_list_sha256": sha256(NPC_LIST_JSON.read_bytes()),
            "character_sha256": sha256(character.buf),
            "model_sha256": sha256(model.buf),
            "selection": "all valid sex=1 character_npc_npc_list groups",
        },
        "count": len(entries),
        "region_counts": counts,
        "entries": entries,
    }


def csv_text(document: dict) -> str:
    output = io.StringIO(newline="")
    fields = [
        "id", "region", "character_key", "character_row", "adv_model_id",
        "model_row", "face_model", "hair_model", "tops_model", "voicer",
        "groups", "confirmed_identity",
    ]
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for item in document["entries"]:
        row = {field: item[field] for field in fields}
        row["groups"] = ";".join(item["groups"])
        writer.writerow(row)
    return output.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    document = build_document()
    json_output = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    table_output = csv_text(document)
    if args.check:
        if not OUTPUT_JSON.exists() or OUTPUT_JSON.read_text(encoding="utf-8") != json_output:
            raise SystemExit("male NPC JSON catalog is stale")
        if not OUTPUT_CSV.exists() or OUTPUT_CSV.read_text(encoding="utf-8-sig") != table_output:
            raise SystemExit("male NPC CSV catalog is stale")
        print(f"OK: male NPC catalog is current ({document['count']} candidates)")
        return 0
    OUTPUT_JSON.write_text(json_output, encoding="utf-8", newline="\n")
    OUTPUT_CSV.write_text(table_output, encoding="utf-8-sig", newline="")
    print(f"Wrote male NPC catalog: {document['count']} candidates")
    print("Regions:", document["region_counts"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
