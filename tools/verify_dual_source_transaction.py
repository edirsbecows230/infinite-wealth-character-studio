#!/usr/bin/env python3
"""Transaction and failure-injection checks requiring local game database inputs."""

from __future__ import annotations

import json
import struct
import sys
import copy
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
PLAN_PATH = PROJECT / "data" / "dual_source_selector.generated.json"
CATALOG_PATH = PROJECT / "data" / "female_npc_catalog.generated.json"

sys.path.insert(0, str(PROJECT))
import y8_character_replacer as replacer  # noqa: E402


Address = tuple[str, int, int]
Operation = tuple[str, int, int, int]


def read_buffer(buffer: bytes | bytearray, offset: int, size: int) -> int:
    return struct.unpack_from("<H" if size == 2 else "<I", buffer, offset)[0]


def source_selected(source_id: str, source_mode: str) -> bool:
    return source_mode == "both" or source_mode == source_id


def targets_by_id(plan: dict) -> dict[str, dict]:
    return {target["id"]: target for target in plan["targets"]}


def source_rows(source: dict) -> list[dict]:
    return sorted(source["source_records"], key=lambda item: item["row"])


def relevant_addresses(plan: dict, character, costume) -> list[Address]:
    result: list[Address] = []
    for source_id in plan["source_order"]:
        source = plan["sources"][source_id]
        for record in source_rows(source):
            base = costume.row_offsets[record["row"]]
            result.extend((("costume", base + 4, 2), ("costume", base + 6, 2)))
    for source_id in plan["source_order"]:
        source = plan["sources"][source_id]
        for entry in source["context_entries"]:
            result.append(("character", replacer.MAPPING_OFF + entry["position"] * 4, 4))
    assert len(result) == 353
    assert len(result) == len(set(result))
    return result


def initial_state(plan: dict, character, costume) -> dict[Address, int]:
    buffers = {"character": character.buf, "costume": costume.buf}
    return {
        address: read_buffer(buffers[address[0]], address[1], address[2])
        for address in relevant_addresses(plan, character, costume)
    }


def selections(plan: dict) -> list[tuple[str, str, str, int | None]]:
    result = []
    for source_mode in ("ichiban", "kiryu", "both"):
        for target in plan["targets"]:
            result.append((source_mode, target["id"], "context_matched", None))
            result.append((source_mode, target["id"], "default_only", None))
            for index, _variant in enumerate(target["fixed_variants"]):
                result.append((source_mode, target["id"], "fixed_variant", index))
    return result


def expected_pair(target: dict, source_id: str, row: int,
                  mode: str, variant_index: int | None) -> tuple[int, int]:
    if target.get("fixedNpc"):
        return target["standard_character"], target["standard_character_hawaii"]
    if mode == "default_only":
        return target["standard_character"], target["standard_character_hawaii"]
    if mode == "fixed_variant":
        assert variant_index is not None
        variant = target["fixed_variants"][variant_index]
        key = variant["character"] or variant["character_hawaii"]
        assert key
        return key, key
    records = {
        item["row"]: item for item in target["source_plans"][source_id]["records"]
    }
    item = records[row]
    return item["target_character"], item["target_character_hawaii"]


def operations(plan: dict, selection, backup: dict[Address, int], costume) -> list[Operation]:
    source_mode, target_id, mode, variant_index = selection
    target = targets_by_id(plan)[target_id]
    result: list[Operation] = []
    for source_id in plan["source_order"]:
        source = plan["sources"][source_id]
        for record in source_rows(source):
            row = record["row"]
            base = costume.row_offsets[row]
            character_address = ("costume", base + 4, 2)
            hawaii_address = ("costume", base + 6, 2)
            if source_selected(source_id, source_mode):
                pair = expected_pair(target, source_id, row, mode, variant_index)
            else:
                pair = backup[character_address], backup[hawaii_address]
            result.extend(((*character_address, pair[0]), (*hawaii_address, pair[1])))
    for source_id in plan["source_order"]:
        source = plan["sources"][source_id]
        for entry in source["context_entries"]:
            address = ("character", replacer.MAPPING_OFF + entry["position"] * 4, 4)
            if source_selected(source_id, source_mode):
                if mode == "fixed_variant":
                    assert variant_index is not None
                    value = target["fixed_variants"][variant_index]["character_row"]
                else:
                    value = target["character_row"]
            else:
                value = backup[address]
            result.append((*address, value))
    assert len(result) == 353
    return result


def independent_operations(plan: dict, slots: dict[str, tuple[str, str, int | None]],
                           backup: dict[Address, int], costume) -> list[Operation]:
    """Build the v1.2 transaction where each protagonist owns its own selection."""
    target_map = targets_by_id(plan)
    result: list[Operation] = []
    for source_id in plan["source_order"]:
        source = plan["sources"][source_id]
        slot = slots.get(source_id)
        for record in source_rows(source):
            base = costume.row_offsets[record["row"]]
            character_address = ("costume", base + 4, 2)
            hawaii_address = ("costume", base + 6, 2)
            if slot:
                target_id, mode, variant_index = slot
                pair = expected_pair(
                    target_map[target_id], source_id, record["row"], mode, variant_index
                )
            else:
                pair = backup[character_address], backup[hawaii_address]
            result.extend(((*character_address, pair[0]), (*hawaii_address, pair[1])))
    for source_id in plan["source_order"]:
        source = plan["sources"][source_id]
        slot = slots.get(source_id)
        for entry in source["context_entries"]:
            address = (
                "character", replacer.MAPPING_OFF + entry["position"] * 4, 4
            )
            if slot:
                target_id, mode, variant_index = slot
                target = target_map[target_id]
                value = (
                    target["fixed_variants"][variant_index]["character_row"]
                    if mode == "fixed_variant" else target["character_row"]
                )
            else:
                value = backup[address]
            result.append((*address, value))
    assert len(result) == 353
    return result


def vanilla_operations(plan: dict, costume) -> list[Operation]:
    result: list[Operation] = []
    for source_id in plan["source_order"]:
        source = plan["sources"][source_id]
        for record in source_rows(source):
            base = costume.row_offsets[record["row"]]
            result.extend((
                ("costume", base + 4, 2, record["original_character"]),
                ("costume", base + 6, 2, record["original_character_hawaii"]),
            ))
    for source_id in plan["source_order"]:
        for entry in plan["sources"][source_id]["context_entries"]:
            result.append(("character", replacer.MAPPING_OFF + entry["position"] * 4,
                           4, entry["original_row"]))
    assert len(result) == 353
    return result


def apply_ops(state: dict[Address, int], ops: list[Operation], stop_before: int | None = None) -> None:
    for index, (which, offset, size, value) in enumerate(ops):
        if stop_before is not None and index == stop_before:
            return
        state[(which, offset, size)] = value


def verify_ops(state: dict[Address, int], ops: list[Operation]) -> None:
    for which, offset, size, value in ops:
        actual = state[(which, offset, size)]
        assert actual == value, (which, hex(offset), actual, value)


def addresses_for_source(plan: dict, source_id: str, costume) -> set[Address]:
    source = plan["sources"][source_id]
    result: set[Address] = set()
    for record in source_rows(source):
        base = costume.row_offsets[record["row"]]
        result.update((("costume", base + 4, 2), ("costume", base + 6, 2)))
    for entry in source["context_entries"]:
        result.add(("character", replacer.MAPPING_OFF + entry["position"] * 4, 4))
    return result


def main() -> int:
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    assert plan["schema"] == "y8.runtime_dual_source_selector.v2"
    assert len(plan["targets"]) == 59
    assert plan["target_counts"]["female_npc_expansion"] == 19
    expanded = targets_by_id(plan)
    assert (expanded["sujimon_queen"]["character_row"],
            expanded["sujimon_queen"]["character"],
            expanded["sujimon_queen"]["adv_model_id"],
            expanded["sujimon_queen"]["model"],
            expanded["sujimon_queen"]["voicer"]) == \
           (10396, 25979, 20553, "c_cw_x_queen", 1113)
    assert (expanded["hawaii_woman_runner"]["character_row"],
            expanded["hawaii_woman_runner"]["character"],
            expanded["hawaii_woman_runner"]["voicer"]) == (9956, 23214, 58)
    assert (expanded["hawaii_woman_runner_b"]["character_row"],
            expanded["hawaii_woman_runner_b"]["character"],
            expanded["hawaii_woman_runner_b"]["voicer"]) == (9957, 23215, 59)
    assert (expanded["marilyn"]["character_row"], expanded["marilyn"]["character"],
            expanded["marilyn"]["adv_model_id"], expanded["marilyn"]["model"],
            expanded["marilyn"]["voicer"]) == \
           (9800, 25128, 19702, "c_cw_x_onepieceA", 1215)
    assert (expanded["marian"]["character_row"], expanded["marian"]["character"],
            expanded["marian"]["adv_model_id"], expanded["marian"]["model"],
            expanded["marian"]["voicer"]) == \
           (9813, 26197, 20771, "c_cw_x_SH31_marian", 695)
    mao = expanded["mao"]
    assert (mao["character_row"], mao["character"], mao["adv_model_id"],
            mao["model"], mao["voicer"]) == \
           (9804, 25046, 19620, "c_cw_x_SH29_mao", 0)
    assert [(item["character_row"], item["variant_key"])
            for item in mao["fixed_variants"]] == [(9804, 25046), (9805, 25047)]
    hitomi = expanded["hitomi_hamabe"]
    assert (hitomi["character_row"], hitomi["character"], hitomi["adv_model_id"],
            hitomi["model"], hitomi["voicer"]) == \
           (9774, 26195, 20769, "c_cw_x_SH16_hamabe", 696)
    assert [(item["character_row"], item["variant_key"])
            for item in hitomi["fixed_variants"]] == [(9774, 26195), (9775, 26196)]
    assert (expanded["kiana"]["character_row"], expanded["kiana"]["character"],
            expanded["kiana"]["adv_model_id"], expanded["kiana"]["model"],
            expanded["kiana"]["voicer"]) == \
           (9816, 23500, 18074, "c_cw_x_hura", 410)
    assert (expanded["julie"]["character_row"], expanded["julie"]["character"],
            expanded["julie"]["voicer"]) == (9821, 28060, 788)
    assert (expanded["judie"]["character_row"], expanded["judie"]["character"],
            expanded["judie"]["voicer"]) == (9712, 13469, 963)
    assert (expanded["seiryo_student_a"]["character_row"],
            expanded["seiryo_student_b"]["character_row"]) == (9930, 9931)
    assert catalog["schema"] == "y8.female_npc_catalog.v1"
    assert catalog["count"] == len(catalog["entries"]) >= 300
    test_plan = copy.deepcopy(plan)
    for entry in catalog["entries"]:
        key = entry["character_key"]
        test_plan["targets"].append({
            "id": entry["id"],
            "character_row": entry["character_row"],
            "standard_character": key,
            "standard_character_hawaii": key,
            "fixedNpc": True,
            "fixed_variants": [{
                "character": key,
                "character_hawaii": key,
                "character_row": entry["character_row"],
            }],
        })

    character = replacer.load_char()
    costume = replacer.RowTable(replacer.COSTUME_BIN, replacer.CC_FIELDS)
    vanilla = initial_state(plan, character, costume)
    all_selections = selections(test_plan)

    # Every UI combination applies and verifies as one 353-write transaction,
    # then the first backup restores both sources exactly.
    for selection in all_selections:
        state = vanilla.copy()
        first_backup = state.copy()
        ops = operations(test_plan, selection, first_backup, costume)
        apply_ops(state, ops)
        verify_ops(state, ops)
        state = first_backup.copy()
        assert state == vanilla
    print(f"OK: {len(all_selections)} dual-source target/outfit combinations apply+restore")

    # One active transaction can switch through every source/target/outfit
    # combination while preserving the immutable first backup.
    state = vanilla.copy()
    first_backup = state.copy()
    for selection in all_selections:
        ops = operations(test_plan, selection, first_backup, costume)
        apply_ops(state, ops)
        verify_ops(state, ops)
    state = first_backup.copy()
    assert state == vanilla
    print(f"OK: continuous {len(all_selections)}-selection switch keeps one dual backup")

    # Source isolation: a one-source Apply restores the other protagonist to
    # the first backup; Both intentionally targets both.
    ichiban_addresses = addresses_for_source(plan, "ichiban", costume)
    kiryu_addresses = addresses_for_source(plan, "kiryu", costume)
    assert ichiban_addresses.isdisjoint(kiryu_addresses)
    state = vanilla.copy()
    first_backup = state.copy()
    apply_ops(state, operations(plan, ("both", "chitose", "context_matched", None),
                                first_backup, costume))
    apply_ops(state, operations(plan, ("ichiban", "kei", "default_only", None),
                                first_backup, costume))
    assert all(state[address] == first_backup[address] for address in kiryu_addresses)
    assert any(state[address] != first_backup[address] for address in ichiban_addresses)
    apply_ops(state, operations(plan, ("kiryu", "yamai", "context_matched", None),
                                first_backup, costume))
    assert all(state[address] == first_backup[address] for address in ichiban_addresses)
    assert any(state[address] != first_backup[address] for address in kiryu_addresses)
    apply_ops(state, operations(plan, ("both", "chitose", "default_only", None),
                                first_backup, costume))
    assert any(state[address] != first_backup[address] for address in ichiban_addresses)
    assert any(state[address] != first_backup[address] for address in kiryu_addresses)
    print("OK: Ichiban/Kiryu/Both source isolation and de-accumulation")

    # v1.2 independently targets each source in one verified 353-write
    # transaction. Omitting one slot restores that source to the first backup.
    independent = {
        "ichiban": ("chitose", "fixed_variant", 21),
        "kiryu": ("kiryu", "default_only", None),
    }
    state = vanilla.copy()
    first_backup = state.copy()
    independent_ops = independent_operations(plan, independent, first_backup, costume)
    apply_ops(state, independent_ops)
    verify_ops(state, independent_ops)
    assert any(state[address] != first_backup[address] for address in ichiban_addresses)
    assert any(state[address] != first_backup[address] for address in kiryu_addresses)
    assert state != first_backup

    ichiban_only_ops = independent_operations(
        plan, {"ichiban": ("adachi", "context_matched", None)},
        first_backup, costume,
    )
    apply_ops(state, ichiban_only_ops)
    verify_ops(state, ichiban_only_ops)
    assert all(state[address] == first_backup[address] for address in kiryu_addresses)
    assert any(state[address] != first_backup[address] for address in ichiban_addresses)
    print("OK: v1.2 independent Ichiban/Kiryu targets and omitted-slot restore")

    # Chitose Default Only is the proven standard visible default (23404), not
    # the Japan coat variant (18935), for both source tables.
    chitose = targets_by_id(plan)["chitose"]
    assert (chitose["standard_character"], chitose["standard_character_hawaii"]) == (23404, 23404)
    forced_swimsuit = expected_pair(chitose, "ichiban", 228, "fixed_variant", 21)
    assert forced_swimsuit == (6707, 6707)
    assert chitose["fixed_variants"][21]["character_row"] == 10069

    # Representative failure injection at every write index.  Rolling back the
    # immediate pre-switch snapshot must recover all 353 values exactly.
    representative = []
    target_map = targets_by_id(plan)
    for source_mode in ("ichiban", "kiryu", "both"):
        for target_id in ("chitose", "kei", "kiryu"):
            target = target_map[target_id]
            representative.extend((
                (source_mode, target_id, "context_matched", None),
                (source_mode, target_id, "default_only", None),
                (source_mode, target_id, "fixed_variant", 0),
                (source_mode, target_id, "fixed_variant", len(target["fixed_variants"]) - 1),
            ))

    state = vanilla.copy()
    first_backup = state.copy()
    apply_ops(state, operations(plan, ("both", "yamai", "context_matched", None),
                                first_backup, costume))
    failures = 0
    for selection in representative:
        ops = operations(plan, selection, first_backup, costume)
        for fail_at in range(len(ops)):
            trial = state.copy()
            pre_switch = trial.copy()
            apply_ops(trial, ops, stop_before=fail_at)
            trial = pre_switch.copy()
            assert trial == pre_switch, (selection, fail_at)
            failures += 1
    print(f"OK: {failures} injected dual-source write failures restore pre-switch state")

    # Emergency reset ignores the transaction backup and writes embedded
    # static Vanilla values for both sources.
    mixed = vanilla.copy()
    apply_ops(mixed, operations(plan, ("ichiban", "kei", "fixed_variant", 0),
                                vanilla, costume))
    apply_ops(mixed, operations(plan, ("kiryu", "chitose", "context_matched", None),
                                mixed.copy(), costume))
    reset_ops = vanilla_operations(plan, costume)
    apply_ops(mixed, reset_ops)
    verify_ops(mixed, reset_ops)
    assert mixed == vanilla
    print("OK: emergency reset restores static Vanilla for both sources")
    print("OK: dual transaction schedule = 256 u16 + 97 u32 = 353 writes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
