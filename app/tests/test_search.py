from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from y8trainer.data import DataRepository
from y8trainer.finder_state import FinderUserState
from y8trainer.search import CharacterSearchIndex


class SearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.targets = [
            {"id": "npc_a", "label": "NPC", "model": "c_w_f_023_blue",
             "face_model": "face_xxx", "hair_model": "hair_17", "standard_character": 12345,
             "target_row": 9988, "voicer": 1122, "region": "Hawaii", "catalog_group": "cw street"},
            {"id": "npc_b", "label": "NPC", "model": "c_w_f_024_red",
             "face_model": "face_xxx", "hair_model": "hair_18", "standard_character": 12346},
            {"id": "named", "label": "Karen / 卡伦", "model": "c_named", "face_model": "",
             "hair_model": "", "standard_character": 22},
        ]
        cls.index = CharacterSearchIndex(cls.targets)

    def find(self, text, **kwargs):
        return self.index.matching_ids([t["id"] for t in self.targets], text, **kwargs)

    def test_multiple_tokens_match_across_fields_and_require_all(self):
        self.assertEqual(self.find("c_w_f 023"), ["npc_a"])
        self.assertEqual(self.find("HAIR 17"), ["npc_a"])
        self.assertEqual(self.find("12345 face_xxx"), ["npc_a"])
        self.assertEqual(self.find("023 missing"), [])

    def test_model_and_target_id(self):
        self.assertEqual(self.find("024_red"), ["npc_b"])
        self.assertEqual(self.find("npc_b"), ["npc_b"])

    def test_decimal_and_hex_key(self):
        self.assertEqual(self.find("12345"), ["npc_a"])
        self.assertEqual(self.find("0x3039"), ["npc_a"])
        self.assertEqual(self.find("0X03039"), ["npc_a"])

    def test_face_hair_row_voice_region_group_and_name(self):
        for text, expected in (("face_xxx", ["npc_a", "npc_b"]), ("hair_17", ["npc_a"]),
                               ("9988", ["npc_a"]), ("1122", ["npc_a"]),
                               ("hawaii cw", ["npc_a"]), ("卡伦", ["named"])):
            with self.subTest(text=text):
                self.assertEqual(self.find(text), expected)

    def test_alias_participates_in_and_search(self):
        alias = lambda target_id: "Karen UFO" if target_id == "npc_a" else ""
        self.assertEqual(self.find("karen cw", alias=alias), ["npc_a"])
        self.assertEqual(self.find("ufo 0x3039", alias=alias), ["npc_a"])
        self.assertEqual(self.find("ufo hair_18", alias=alias), [])

    def test_similarity_is_exact_and_search_can_refine_it(self):
        self.assertEqual(self.find("", related=("face_model", "FACE_XXX")), ["npc_a", "npc_b"])
        self.assertEqual(self.find("024", related=("face_model", "face_xxx")), ["npc_b"])
        self.assertEqual(self.find("", related=("hair_model", "hair_17")), ["npc_a"])
        self.assertEqual(self.find("", related=("model", "c_w_f_023_blue")), ["npc_a"])
        self.assertEqual(self.find("", related=("face_model", "face_x")), [])
        self.assertEqual(self.find("", related=("face_model", "")), [])

    def test_empty_search_and_no_overlay_keep_order(self):
        self.assertEqual(self.find("  \t"), ["npc_a", "npc_b", "named"])
        self.assertEqual(self.index.matching_ids(["missing", "npc_b", "npc_a"]), ["npc_b", "npc_a"])


class FinderPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "nested" / "character_finder.json"

    def test_missing_file_is_normal(self):
        state = FinderUserState(self.path)
        self.assertEqual(state.favorites, set())
        self.assertEqual(state.aliases, {})
        self.assertEqual(state.load_error, "")
        self.assertFalse(self.path.exists())

    def test_favorite_survives_restart_and_can_be_removed(self):
        state = FinderUserState(self.path)
        self.assertTrue(state.set_favorite("chitose", True))
        state = FinderUserState(self.path)
        self.assertTrue(state.is_favorite("chitose"))
        self.assertTrue(state.set_favorite("chitose", False))
        self.assertFalse(FinderUserState(self.path).is_favorite("chitose"))

    def test_alias_survives_restart_can_edit_and_delete(self):
        state = FinderUserState(self.path)
        self.assertTrue(state.set_alias("chitose", " 蓝裙女孩 Karen UFO "))
        state = FinderUserState(self.path)
        self.assertEqual(state.alias("chitose"), "蓝裙女孩 Karen UFO")
        self.assertTrue(state.set_alias("chitose", "Pretty NPC"))
        self.assertEqual(FinderUserState(self.path).alias("chitose"), "Pretty NPC")
        self.assertTrue(state.set_alias("chitose", ""))
        self.assertEqual(FinderUserState(self.path).alias("chitose"), "")

    def test_corrupt_configuration_cannot_prevent_catalog_loading(self):
        self.path.parent.mkdir()
        for text in ("{broken", "[]", '{"schema":99}', "\ud800"):
            with self.subTest(text=repr(text)):
                self.path.write_bytes(text.encode("utf-8", errors="surrogatepass"))
                state = FinderUserState(self.path)
                self.assertTrue(state.load_error)
                repo = DataRepository(state)
                self.assertEqual(len(repo.ids_for_kind("all")), 5218)

    def test_invalid_records_and_disappeared_targets_are_ignored(self):
        self.path.parent.mkdir()
        self.path.write_text(json.dumps({"favorites": ["chitose", "gone", 1],
                                        "aliases": {"gone": "Gone alias fixture", "chitose": "UFO", "bad": []}}))
        repo = DataRepository(FinderUserState(self.path))
        self.assertEqual(repo.ids_for_kind("favorites"), ["chitose"])
        self.assertIn("chitose", repo.find_targets("UFO"))
        self.assertEqual(repo.find_targets("Gone alias fixture"), [])

    def test_failed_atomic_replace_preserves_previous_file_and_memory(self):
        state = FinderUserState(self.path)
        self.assertTrue(state.set_alias("chitose", "Original"))
        original = self.path.read_bytes()
        with patch("y8trainer.finder_state.os.replace", side_effect=PermissionError("locked")):
            self.assertFalse(state.set_alias("chitose", "Changed"))
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(state.alias("chitose"), "Original")
        self.assertTrue(state.last_error)
        self.assertEqual(list(self.path.parent.glob("*.tmp")), [])

    def test_catalog_has_no_user_fields_and_baseline_categories_are_unchanged(self):
        repo = DataRepository()
        self.assertEqual(repo.summary.curated, 47)
        self.assertEqual(repo.summary.female, 404)
        self.assertEqual(repo.summary.male, 4742)
        self.assertEqual(repo.ids_for_kind("favorites"), [])
        self.assertIn("chitose", repo.find_targets("0x5B6C"))
        before = dict(repo.targets["chitose"])
        repo.user_state.set_alias("chitose", "Karen UFO")
        repo.user_state.set_favorite("chitose", True)
        self.assertEqual(repo.targets["chitose"], before)

    def test_custom_target_added_to_search_and_favorites_without_catalog_copy(self):
        repo = DataRepository()
        target = repo.register_custom(1234, 8000, 5252)
        self.assertEqual(repo.find_targets("0x4d2 8000"), [target["id"]])
        repo.user_state.set_favorite(target["id"], True)
        self.assertEqual(repo.ids_for_kind("favorites"), [target["id"]])
