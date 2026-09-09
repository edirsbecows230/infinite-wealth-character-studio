from __future__ import annotations

import struct
import unittest

from y8trainer.data import DataRepository
from y8trainer.engine import (
    CHARACTER_ROWS,
    COSTUME_OUTER_ROWS,
    COSTUME_ROWS,
    SlotSelection,
    TrainerEngine,
)
from y8trainer.memory import MemoryAccessError


CHAR_BASE = 0x10000000
COSTUME_BASE = 0x20000000


class FakeMemory:
    def __init__(self, repository: DataRepository) -> None:
        self.repository = repository
        self.pid = 4242
        self.handle = True
        self.segments = {
            CHAR_BASE: bytearray(0x22000),
            COSTUME_BASE: bytearray(0x8000),
        }
        self.write_count = 0
        self.scan_count = 0
        self.fail_on_write_number: int | None = None
        self.fail_on_write_numbers: set[int] = set()
        self._build_character()
        self._build_costume()

    def _segment(self, address: int, size: int) -> tuple[bytearray, int]:
        for base, data in self.segments.items():
            offset = address - base
            if 0 <= offset and offset + size <= len(data):
                return data, offset
        raise RuntimeError(f"unmapped fake address 0x{address:X} + {size}")

    def _put(self, base: int, offset: int, data: bytes) -> None:
        segment = self.segments[base]
        segment[offset:offset + len(data)] = data

    def _u16(self, base: int, offset: int, value: int) -> None:
        self._put(base, offset, struct.pack("<H", value))

    def _u32(self, base: int, offset: int, value: int) -> None:
        self._put(base, offset, struct.pack("<I", value))

    def _header(self, base: int, inner: int, outer_rows: int) -> None:
        self._put(base, 0, b"armp")
        self._put(base, 0x0A, b"\x02")
        self._u32(base, 0x10, inner)
        self._u32(base, 0x20, outer_rows)
        self._u32(base, 0x24, 3)

    def _build_character(self) -> None:
        inner = 0x18000
        key_offset = 0x1000
        mapping_offset = 0xC000
        self._header(CHAR_BASE, inner, CHARACTER_ROWS)
        self._u32(CHAR_BASE, inner, CHARACTER_ROWS)
        self._u32(CHAR_BASE, inner + 0x04, 22)
        self._u32(CHAR_BASE, inner + 0x20, 0x800004A6)
        self._u32(CHAR_BASE, inner - 0x10, key_offset)
        self._u32(CHAR_BASE, inner - 0x08, mapping_offset)
        for source_id in self.repository.source_order:
            source = self.repository.sources[source_id]
            for entry in source["context_entries"]:
                self._u32(CHAR_BASE, key_offset + entry["position"] * 4, entry["key"])
                self._u32(CHAR_BASE, mapping_offset + entry["position"] * 4, entry["original_row"])

    def _build_costume(self) -> None:
        inner = 0x1000
        rows_start = 0x2000
        table = 0x6000
        self._header(COSTUME_BASE, inner, COSTUME_OUTER_ROWS)
        self._u32(COSTUME_BASE, inner, COSTUME_ROWS)
        self._u32(COSTUME_BASE, inner + 0x04, 7)
        self._u32(COSTUME_BASE, inner + 0x1C, table)
        self._u32(COSTUME_BASE, inner + 0x20, (0xC1 << 24) | 0x1279)
        for row in range(COSTUME_ROWS):
            offset = rows_start + row * 16
            self._u32(COSTUME_BASE, table + row * 4, offset)
            self._u16(COSTUME_BASE, offset, 0xFFFE)
            self._u16(COSTUME_BASE, offset + 0x02, 0)
            self._u16(COSTUME_BASE, offset + 0x04, 1)
            self._u16(COSTUME_BASE, offset + 0x06, 1)
        for source_id in self.repository.source_order:
            source = self.repository.sources[source_id]
            for row, record in source["records"].items():
                offset = rows_start + row * 16
                self._u16(COSTUME_BASE, offset, source["player"])
                self._u16(COSTUME_BASE, offset + 0x02, record["costume"])
                self._u16(COSTUME_BASE, offset + 0x04, record["original_character"])
                self._u16(COSTUME_BASE, offset + 0x06, record["original_hawaii"])

    def find_pid(self, _name: str) -> int | None:
        return self.pid

    def open(self, pid: int) -> None:
        if pid != self.pid:
            raise RuntimeError("wrong pid")
        self.handle = True

    def close(self) -> None:
        self.handle = False

    def scan_armp_headers(self, outer_rows: set[int]) -> dict[int, list[int]]:
        self.scan_count += 1
        result = {value: [] for value in outer_rows}
        result[CHARACTER_ROWS] = [CHAR_BASE]
        result[COSTUME_OUTER_ROWS] = [COSTUME_BASE]
        return result

    def read(self, address: int, size: int) -> bytes:
        data, offset = self._segment(address, size)
        return bytes(data[offset:offset + size])

    def write(self, address: int, value: bytes) -> None:
        self.write_count += 1
        if self.fail_on_write_number == self.write_count or self.write_count in self.fail_on_write_numbers:
            self.fail_on_write_number = None
            self.fail_on_write_numbers.discard(self.write_count)
            raise MemoryAccessError("injected write failure")
        data, offset = self._segment(address, len(value))
        data[offset:offset + len(value)] = value

    def read_u16(self, address: int) -> int:
        return struct.unpack("<H", self.read(address, 2))[0]

    def read_u32(self, address: int) -> int:
        return struct.unpack("<I", self.read(address, 4))[0]

    def write_u16(self, address: int, value: int) -> None:
        self.write(address, struct.pack("<H", value))

    def write_u32(self, address: int, value: int) -> None:
        self.write(address, struct.pack("<I", value))


class EngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repository = DataRepository()

    def setUp(self) -> None:
        self.memory = FakeMemory(self.repository)
        self.engine = TrainerEngine(self.repository, self.memory)

    def test_catalog_and_transaction_counts(self) -> None:
        self.assertEqual(self.repository.summary.curated, 59)
        self.assertEqual(self.repository.summary.female, 404)
        self.assertEqual(self.repository.summary.male, 4742)
        self.assertEqual(
            sum(len(source["context_entries"]) for source in self.repository.sources.values()), 101
        )

    def test_ichiban_scene_specific_contexts_are_covered(self) -> None:
        entries = {
            entry["key"]: (entry["position"], entry["original_row"])
            for entry in self.repository.sources["ichiban"]["context_entries"]
        }
        self.assertEqual(entries[10513], (1168, 8282))
        self.assertEqual(entries[19943], (5245, 8309))
        self.assertEqual(entries[23390], (6266, 8367))
        self.assertEqual(entries[28266], (10560, 8310))
        self.assertEqual(
            sum(len(source["records"]) for source in self.repository.sources.values()), 128
        )

    def test_validate_synthetic_runtime_layout(self) -> None:
        result = self.engine.validate_all()
        self.assertTrue(result.ok, result.message)
        status = self.engine.status_snapshot()
        self.assertEqual(status["states"], {"ichiban": "original", "kiryu": "original"})

    def test_first_apply_revalidates_cached_bases_without_second_full_scan(self) -> None:
        self.assertTrue(self.engine.validate_all().ok)
        self.assertEqual(self.memory.scan_count, 1)
        target_id = self.repository.curated_ids[0]
        result = self.engine.apply({"ichiban": SlotSelection(target_id, "default_only")})
        self.assertTrue(result.ok, result.message)
        self.assertEqual(self.memory.scan_count, 1)

    def test_independent_dual_targets_apply_and_restore(self) -> None:
        first_id, second_id = self.repository.curated_ids[:2]
        self.assertNotEqual(first_id, second_id)
        result = self.engine.apply({
            "ichiban": SlotSelection(first_id, "context_matched"),
            "kiryu": SlotSelection(second_id, "default_only"),
        })
        self.assertTrue(result.ok, result.message)
        self.assertTrue(self.engine.active)
        selection = self.engine.active_selection
        self.assertIsNotNone(selection)
        self.assertEqual(selection.slots["ichiban"].target_id, first_id)
        self.assertEqual(selection.slots["kiryu"].target_id, second_id)
        self.engine._verify_selection(selection, self.engine.backup)

        restored = self.engine.restore("unit test")
        self.assertTrue(restored.ok, restored.message)
        self.assertFalse(self.engine.active)
        layout = self.engine.validate_costume_db(COSTUME_BASE)
        self.assertEqual(layout.sources["ichiban"].state, "original")
        self.assertEqual(layout.sources["kiryu"].state, "original")

    def test_restore_game_original_does_not_reapply_a_modded_launch_snapshot(self) -> None:
        first_id, second_id = self.repository.curated_ids[:2]
        seeded = self.engine.apply({
            "ichiban": SlotSelection(first_id, "context_matched"),
        })
        self.assertTrue(seeded.ok, seeded.message)

        # Simulate opening the standalone tool while an earlier CT/tool
        # replacement is already loaded into the game database.
        restarted = TrainerEngine(self.repository, self.memory)
        changed = restarted.apply({
            "ichiban": SlotSelection(second_id, "default_only"),
        })
        self.assertTrue(changed.ok, changed.message)
        self.assertFalse(restarted.backup_is_vanilla())

        restored = restarted.restore_game_original("unit test")
        self.assertTrue(restored.ok, restored.message)
        self.assertIsNone(restarted.backup_is_vanilla())
        layout = restarted.validate_costume_db(COSTUME_BASE)
        self.assertEqual(layout.sources["ichiban"].state, "original")
        self.assertEqual(layout.sources["kiryu"].state, "original")

    def test_single_source_restores_other_source_to_first_backup(self) -> None:
        first_id, second_id = self.repository.curated_ids[:2]
        applied = self.engine.apply({
            "ichiban": SlotSelection(first_id, "default_only"),
            "kiryu": SlotSelection(second_id, "context_matched"),
        })
        self.assertTrue(applied.ok, applied.message)
        switched = self.engine.apply({
            "ichiban": SlotSelection(second_id, "default_only"),
        })
        self.assertTrue(switched.ok, switched.message)
        self.engine._verify_selection(self.engine.active_selection, self.engine.backup)
        source = self.repository.sources["kiryu"]
        for entry in source["context_entries"]:
            actual = self.memory.read_u32(self.engine.character.mapping + entry["position"] * 4)
            self.assertEqual(actual, entry["original_row"])

    def test_fixed_variant_uses_variant_identity_row_for_each_slot(self) -> None:
        targets = [
            self.repository.targets[target_id]
            for target_id in self.repository.curated_ids
            if len(self.repository.targets[target_id]["variants"]) >= 2
        ]
        left, right = targets[:2]
        result = self.engine.apply({
            "ichiban": SlotSelection(left["id"], "fixed_variant", 1),
            "kiryu": SlotSelection(right["id"], "fixed_variant", 1),
        })
        self.assertTrue(result.ok, result.message)
        for source_id, target in (("ichiban", left), ("kiryu", right)):
            expected_row = target["variants"][1]["character_row"]
            for entry in self.repository.sources[source_id]["context_entries"]:
                actual = self.memory.read_u32(self.engine.character.mapping + entry["position"] * 4)
                self.assertEqual(actual, expected_row)

    def test_injected_write_failure_rolls_back_first_transaction(self) -> None:
        target_id = self.repository.curated_ids[0]
        self.memory.fail_on_write_number = 11
        result = self.engine.apply({"ichiban": SlotSelection(target_id, "default_only")})
        self.assertFalse(result.ok)
        self.assertFalse(self.engine.active)
        layout = self.engine.validate_costume_db(COSTUME_BASE)
        self.assertEqual(layout.sources["ichiban"].state, "original")
        self.assertEqual(layout.sources["kiryu"].state, "original")

    def test_write_and_rollback_failure_requires_recovery(self) -> None:
        target_id = self.repository.curated_ids[0]
        self.memory.fail_on_write_numbers = {11, 12}
        result = self.engine.apply({"ichiban": SlotSelection(target_id, "default_only")})
        self.assertFalse(result.ok)
        self.assertTrue(self.engine.recovery_required)
        self.assertTrue(self.engine.active)
        blocked = self.engine.apply({"ichiban": SlotSelection(target_id, "default_only")})
        self.assertFalse(blocked.ok)
        self.assertIn("Restore is required", blocked.message)
        restored = self.engine.restore("recovery test")
        self.assertTrue(restored.ok, restored.message)
        self.assertFalse(self.engine.active)

    def test_restore_uses_snapshot_when_layout_cache_was_cleared(self) -> None:
        target_id = self.repository.curated_ids[0]
        result = self.engine.apply({"ichiban": SlotSelection(target_id, "default_only")})
        self.assertTrue(result.ok, result.message)
        self.engine.character = None
        self.engine.costume = None
        restored = self.engine.restore("cache cleared")
        self.assertTrue(restored.ok, restored.message)

    def test_custom_target_is_invalidated_across_pid_change(self) -> None:
        self.assertTrue(self.engine.validate_all().ok)
        target = self.repository.register_custom(1234, 8000, self.engine.pid)
        self.memory.pid = 5252
        lifecycle = self.engine.refresh_process_lifecycle()
        self.assertFalse(lifecycle.ok)
        self.assertIsNone(target["resolved_pid"])
        result = self.engine.apply({"ichiban": SlotSelection(target["id"], "fixed_variant", 0)})
        self.assertFalse(result.ok)
        self.assertIn("old game process", result.message)


if __name__ == "__main__":
    unittest.main()
