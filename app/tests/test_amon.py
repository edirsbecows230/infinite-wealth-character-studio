from __future__ import annotations

import json
import unittest
from pathlib import Path

from y8trainer.data import DataRepository
from y8trainer.engine import TrainerEngine, SlotSelection
from test_engine import FakeMemory


class AmonTests(unittest.TestCase):
    def test_amon_metadata_matches_ct_reference(self):
        root = Path(__file__).resolve().parents[2]
        ct = json.loads((root / "ct/data/dual_source_selector.generated.json").read_text(encoding="utf-8"))
        app = json.loads((root / "data/multi_source_selector.generated.json").read_text(encoding="utf-8"))
        expected = {x["id"]: x for x in ct["targets"] if x["id"].startswith("amon_")}
        actual = {x["id"]: x for x in app["targets"] if x["id"].startswith("amon_")}
        self.assertEqual(set(expected), {"amon_jou", "amon_jiro", "amon_kazuya", "amon_sango"})
        self.assertEqual(actual, expected)

    def test_four_amon_targets_all_ten_slots_and_modes_restore(self):
        repo = DataRepository()
        for target_id in ("amon_jou", "amon_jiro", "amon_kazuya", "amon_sango"):
            target = repo.targets[target_id]
            for source in repo.source_order:
                for mode in ("default_only", "context_matched", "fixed_variant"):
                    with self.subTest(target=target_id, source=source, mode=mode):
                        memory = FakeMemory(repo)
                        engine = TrainerEngine(repo, memory)
                        self.assertTrue(engine.validate_all().ok)
                        source_data = repo.sources[source]
                        addresses = [engine.character.mapping + e["position"] * 4 for e in source_data["context_entries"]]
                        original = [memory.read_u32(a) for a in addresses]
                        result = engine.apply({source: SlotSelection(target_id, mode, 0 if mode == "fixed_variant" else None)})
                        self.assertTrue(result.ok, result.message)
                        row = target["variants"][0]["character_row"] if mode == "fixed_variant" else target["target_row"]
                        self.assertEqual([memory.read_u32(a) for a in addresses], [row] * len(addresses))
                        restored = engine.restore("Amon matrix test")
                        self.assertTrue(restored.ok, restored.message)
                        self.assertEqual([memory.read_u32(a) for a in addresses], original)

    def test_different_amon_targets_can_share_one_transaction(self):
        repo = DataRepository()
        memory = FakeMemory(repo)
        engine = TrainerEngine(repo, memory)
        targets = ["amon_jou", "amon_jiro", "amon_kazuya", "amon_sango"]
        slots = {source: SlotSelection(targets[i % 4], "default_only") for i, source in enumerate(repo.source_order)}
        result = engine.apply(slots)
        self.assertTrue(result.ok, result.message)
        for source, selection in slots.items():
            for entry in repo.sources[source]["context_entries"]:
                self.assertEqual(memory.read_u32(engine.character.mapping + entry["position"] * 4), repo.targets[selection.target_id]["target_row"])
        restored = engine.restore("Amon mixed restore")
        self.assertTrue(restored.ok, restored.message)
