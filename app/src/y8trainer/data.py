from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


PLAN_FILE = "dual_source_selector.generated.json"
FEMALE_FILE = "female_npc_catalog.generated.json"
MALE_FILE = "male_npc_catalog.generated.json"
COSTUME_FILE = "costume_vanilla_rpg_costume.json"


def _data_directories() -> Iterable[Path]:
    override = os.environ.get("Y8_TRAINER_DATA_DIR")
    if override:
        yield Path(override)
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle:
        yield Path(bundle) / "data"
    here = Path(__file__).resolve()
    yield here.parents[2] / "data"
    yield here.parents[3] / "data"


def resolve_data_file(name: str) -> Path:
    checked: list[str] = []
    for directory in _data_directories():
        candidate = directory / name
        checked.append(str(candidate))
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Could not find {name}; checked: {', '.join(checked)}")


def _load_json(name: str) -> dict[str, Any]:
    return json.loads(resolve_data_file(name).read_text(encoding="utf-8"))


@dataclass(frozen=True)
class CatalogSummary:
    curated: int
    female: int
    male: int

    @property
    def total(self) -> int:
        return self.curated + self.female + self.male


class DataRepository:
    """Loads and normalizes the generated CT plan into runtime-friendly maps."""

    def __init__(self) -> None:
        document = _load_json(PLAN_FILE)
        female = _load_json(FEMALE_FILE)
        male = _load_json(MALE_FILE)
        costumes = _load_json(COSTUME_FILE)
        self._validate(document, female, male, costumes)

        self.schema = document["schema"]
        self.costumes = self._normalize_costumes(costumes)
        self.source_order: list[str] = list(document["source_order"])
        self.sources = {
            source_id: self._normalize_source(document["sources"][source_id])
            for source_id in self.source_order
        }

        self.curated_ids: list[str] = []
        self.female_ids: list[str] = []
        self.male_ids: list[str] = []
        self.custom_ids: set[str] = set()
        self.targets: dict[str, dict[str, Any]] = {}

        for raw in document["targets"]:
            target = self._normalize_curated(raw)
            if target["id"] in self.targets:
                raise ValueError(f"duplicate target id {target['id']}")
            self.targets[target["id"]] = target
            self.curated_ids.append(target["id"])
        for raw in female["entries"]:
            target = self._normalize_catalog(raw, "female")
            if target["id"] in self.targets:
                raise ValueError(f"duplicate target id {target['id']}")
            self.targets[target["id"]] = target
            self.female_ids.append(target["id"])
        for raw in male["entries"]:
            target = self._normalize_catalog(raw, "male")
            if target["id"] in self.targets:
                raise ValueError(f"duplicate target id {target['id']}")
            self.targets[target["id"]] = target
            self.male_ids.append(target["id"])

        self.summary = CatalogSummary(
            curated=len(self.curated_ids),
            female=len(self.female_ids),
            male=len(self.male_ids),
        )
        self._validate_runtime_invariants()

    @staticmethod
    def _validate(
        document: dict[str, Any],
        female: dict[str, Any],
        male: dict[str, Any],
        costumes: dict[str, Any],
    ) -> None:
        if document.get("schema") != "y8.runtime_dual_source_selector.v2":
            raise ValueError("unsupported dual-source selector plan")
        if document.get("source_order") != ["ichiban", "kiryu"]:
            raise ValueError("the generated plan must contain Ichiban and Kiryu in order")
        if len(document.get("targets", [])) != 59:
            raise ValueError("curated target count mismatch")
        if female.get("schema") != "y8.female_npc_catalog.v1" or female.get("count") != len(female.get("entries", [])):
            raise ValueError("female NPC catalog is missing or stale")
        if male.get("schema") != "y8.male_npc_catalog.v1" or male.get("count") != len(male.get("entries", [])):
            raise ValueError("male NPC catalog is missing or stale")
        if costumes.get("TABLE_ID") != 3536 or costumes.get("ROW_COUNT") != 480:
            raise ValueError("RPG Costume metadata is missing or stale")
        tx = document.get("transaction_sizes", {})
        if tx.get("ichiban") != 141 or tx.get("kiryu") != 216 or tx.get("both") != 357:
            raise ValueError("transaction size mismatch")

    @staticmethod
    def _normalize_costumes(raw: dict[str, Any]) -> dict[int, dict[str, str]]:
        costumes: dict[int, dict[str, str]] = {}
        for key, wrapper in raw.items():
            if not key.isdigit() or not isinstance(wrapper, dict) or not wrapper:
                continue
            row_name, fields = next(iter(wrapper.items()))
            costume_id = int(key)
            costumes[costume_id] = {
                "key": str(row_name or ""),
                "name": str(fields.get("name") or row_name or f"Costume {costume_id}"),
            }
        if len(costumes) != 480:
            raise ValueError(f"RPG Costume metadata row mismatch: {len(costumes)}")
        return costumes

    @staticmethod
    def _normalize_source(raw: dict[str, Any]) -> dict[str, Any]:
        records = {
            int(item["row"]): {
                "costume": int(item["costume"]),
                "original_character": int(item["original_character"]),
                "original_hawaii": int(item["original_character_hawaii"]),
            }
            for item in raw["source_records"]
        }
        return {
            "id": raw["id"],
            "label": raw["label"],
            "player": int(raw["player"]),
            "row_count": int(raw["row_count"]),
            "context_entries": [
                {
                    "key": int(item["key"]),
                    "position": int(item["position"]),
                    "original_row": int(item["original_row"]),
                }
                for item in raw["context_entries"]
            ],
            "records": records,
            "sorted_rows": sorted(records),
        }

    def _normalize_curated(self, raw: dict[str, Any]) -> dict[str, Any]:
        source_plans: dict[str, dict[int, tuple[int, int]]] = {}
        for source_id, plan in raw["source_plans"].items():
            source_plans[source_id] = {
                int(item["row"]): (
                    int(item["target_character"]),
                    int(item["target_character_hawaii"]),
                )
                for item in plan["records"]
            }
        variants = []
        for item in raw.get("fixed_variants", []):
            source_costume = item.get("source_costume")
            costume_id = int(source_costume) if source_costume is not None else None
            costume = self.costumes.get(costume_id, {}) if costume_id is not None else {}
            variants.append({
                "id": item["id"],
                "label": item["label"],
                "character": int(item["character"]),
                "hawaii": int(item["character_hawaii"]),
                "variant_key": int(item["variant_key"]),
                "character_row": int(item["character_row"]),
                "model": item.get("model") or "",
                "source_costume": costume_id,
                "costume_key": costume.get("key", ""),
                "costume_name": costume.get("name", ""),
                "costume_category": item.get("category") or "",
            })
        return {
            "id": raw["id"],
            "label": raw["label"],
            "kind": "curated",
            "target_row": int(raw["character_row"]),
            "standard_character": int(raw["standard_character"]),
            "standard_hawaii": int(raw["standard_character_hawaii"]),
            "model": raw.get("model") or "",
            "face_model": "",
            "hair_model": "",
            "voicer": raw.get("voicer"),
            "fixed_npc": False,
            "source_plans": source_plans,
            "variants": variants,
            "search_text": " ".join(
                str(value) for value in (
                    raw["id"], raw["label"], raw.get("model", ""),
                    raw.get("character", ""), raw.get("voicer", ""),
                )
            ).lower(),
        }

    @staticmethod
    def _normalize_catalog(raw: dict[str, Any], kind: str) -> dict[str, Any]:
        key = int(raw["character_key"])
        row = int(raw["character_row"])
        region = raw.get("region") or ""
        prefix = "[Female NPC / 女性 NPC]" if kind == "female" else "[Male NPC / 男性 NPC]"
        label = f"{prefix} {raw['label']}"
        target = {
            "id": raw["id"],
            "label": label,
            "kind": kind,
            "target_row": row,
            "standard_character": key,
            "standard_hawaii": key,
            "model": raw.get("tops_model") or "",
            "face_model": raw.get("face_model") or "",
            "hair_model": raw.get("hair_model") or "",
            "voicer": raw.get("voicer"),
            "fixed_npc": True,
            "source_plans": {},
            "catalog_group": "; ".join(raw.get("groups", [])),
            "region": region,
            "confirmed_identity": bool(raw.get("confirmed_identity")),
            "variants": [{
                "id": f"catalog_{key}",
                "label": f"Catalog key {key} / 目录模型 — {raw.get('tops_model') or 'unknown'}",
                "character": key,
                "hawaii": key,
                "variant_key": key,
                "character_row": row,
                "model": raw.get("tops_model") or "",
            }],
        }
        target["search_text"] = " ".join(
            str(value) for value in (
                target["id"], label, key, row, target["model"], target["face_model"],
                target["hair_model"], target.get("catalog_group", ""), region,
                target.get("voicer", ""),
            )
        ).lower()
        return target

    def ids_for_kind(self, kind: str) -> list[str]:
        if kind == "curated":
            return self.curated_ids
        if kind == "female":
            return self.female_ids
        if kind == "male":
            return self.male_ids
        if kind == "all":
            return self.curated_ids + self.female_ids + self.male_ids
        return []

    def get_target(self, target_id: str) -> dict[str, Any] | None:
        return self.targets.get(target_id)

    def _validate_runtime_invariants(self) -> None:
        positions: set[int] = set()
        costume_rows: set[int] = set()
        identity_count = 0
        costume_count = 0
        for source_id in self.source_order:
            source = self.sources[source_id]
            if len(source["records"]) != source["row_count"]:
                raise ValueError(f"source record count mismatch: {source_id}")
            for entry in source["context_entries"]:
                if not 0 <= entry["position"] < 10646 or not 0 <= entry["original_row"] < 10646:
                    raise ValueError(f"Character entry out of range: {source_id}")
                if entry["position"] in positions:
                    raise ValueError(f"duplicate Character position {entry['position']}")
                positions.add(entry["position"])
                identity_count += 1
            for row, record in source["records"].items():
                if not 0 <= row < 539 or row in costume_rows:
                    raise ValueError(f"invalid/duplicate Costume row {row}")
                costume_rows.add(row)
                costume_count += 1
                for field in ("original_character", "original_hawaii"):
                    if not 0 <= record[field] <= 0xFFFF:
                        raise ValueError(f"Costume {field} out of u16 range")
        if identity_count != 101 or costume_count != 128:
            raise ValueError(
                f"computed transaction count mismatch identity={identity_count} costume={costume_count}"
            )

        for target_id, target in self.targets.items():
            if not 0 <= target["target_row"] < 10646:
                raise ValueError(f"target row out of range: {target_id}")
            for field in ("standard_character", "standard_hawaii"):
                if not 0 < target[field] <= 0xFFFF:
                    raise ValueError(f"target {field} out of u16 range: {target_id}")
            for variant in target["variants"]:
                if not 0 <= variant["character_row"] < 10646:
                    raise ValueError(f"variant row out of range: {target_id}")
                for field in ("character", "hawaii"):
                    if not 0 <= variant[field] <= 0xFFFF:
                        raise ValueError(f"variant {field} out of u16 range: {target_id}")
            if not target["fixed_npc"]:
                for source_id in self.source_order:
                    plan = target["source_plans"].get(source_id)
                    expected_rows = set(self.sources[source_id]["records"])
                    if plan is None or set(plan) != expected_rows:
                        raise ValueError(f"incomplete source plan target={target_id} source={source_id}")
                    if any(not 0 <= value <= 0xFFFF for pair in plan.values() for value in pair):
                        raise ValueError(f"source plan value out of u16 range: {target_id}")

    def register_custom(self, key: int, row: int, pid: int) -> dict[str, Any]:
        target_id = f"custom_key_{key}"
        target = {
            "id": target_id,
            "label": f"[Custom Key / 自定义] key {key} → row {row}",
            "kind": "custom",
            "target_row": row,
            "standard_character": key,
            "standard_hawaii": key,
            "model": "custom",
            "face_model": "",
            "hair_model": "",
            "voicer": None,
            "fixed_npc": True,
            "resolved_pid": pid,
            "source_plans": {},
            "variants": [{
                "id": target_id,
                "label": f"Custom key {key} / 自定义 key {key}",
                "character": key,
                "hawaii": key,
                "variant_key": key,
                "character_row": row,
                "model": "custom",
            }],
            "search_text": f"custom key {key} row {row} 自定义",
        }
        self.targets[target_id] = target
        self.custom_ids.add(target_id)
        return target

    def invalidate_custom_targets(self) -> None:
        for target_id in self.custom_ids:
            target = self.targets.get(target_id)
            if target is not None:
                target["resolved_pid"] = None
