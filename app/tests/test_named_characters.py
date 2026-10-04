import tempfile
import unittest
from pathlib import Path

from y8trainer.data import DataRepository
from y8trainer.engine import SlotSelection, TrainerEngine
from y8trainer.finder_state import FinderUserState
from test_engine import FakeMemory


class NamedSideCharacterTests(unittest.TestCase):
    def setUp(self):
        self.repo = DataRepository()

    def test_separate_identity_category_and_original_counts(self):
        self.assertEqual((self.repo.summary.curated, self.repo.summary.female,
                          self.repo.summary.male, self.repo.summary.named), (47, 404, 4742, 25))
        self.assertEqual(self.repo.summary.total, 5218)
        self.assertEqual(sum(len(self.repo.targets[x]["variants"]) for x in self.repo.named_ids), 40)
        self.assertFalse(set(self.repo.named_ids) & set(self.repo.curated_ids))

    def test_real_names_localizations_and_substory_search_without_user_alias(self):
        for query, target in [("Karen UFO", "side_karen"), ("カレン 23397", "side_karen"),
                              ("Susumu Gondawara", "side_gondawara"), ("权田原组长", "side_gondawara"),
                              ("沖田博士", "side_okita"), ("チャーリー", "side_charlie"),
                              ("豆岡", "side_mameoka"), ("澤井", "side_sawai")]:
            with self.subTest(query=query):
                self.assertEqual(self.repo.find_targets(query), [target])
        self.assertEqual(self.repo.find_targets("Karen not_a_real_token"), [])

    def test_primary_and_variant_keys_hex_rows_models_search_one_identity(self):
        for query, target in [("0x5B65 9771", "side_karen"), ("22834 2528", "side_gondawara"),
                              ("0x5932 c_ca_x_SH15_gondawara", "side_gondawara"),
                              ("21896 c_ca_x_SH37_mameoka_sit", "side_mameoka"),
                              ("21939 2661", "side_sawai")]:
            with self.subTest(query=query):
                self.assertEqual(self.repo.find_targets(query), [target])

    def test_default_appearance_avoids_special_contexts(self):
        expected = {"side_karen": (23397, 9771), "side_gondawara": (22833, 2527),
                    "side_okita": (23107, 2509), "side_charlie": (23009, 2582),
                    "side_mameoka": (25095, 2635), "side_sawai": (23492, 2656)}
        for tid, pair in expected.items():
            t = self.repo.targets[tid]
            self.assertEqual((t["standard_character"], t["target_row"]), pair)
            self.assertEqual((t["variants"][0]["character"], t["variants"][0]["character_row"]), pair)
            self.assertEqual(t["standard_hawaii"], pair[0])

    def test_same_face_uses_named_primary_and_preserves_variant_identity(self):
        self.assertEqual(self.repo.related_targets("side_karen", "face_model"), ["side_karen"])
        self.assertEqual(self.repo.targets["side_gondawara"]["face_model"], "c_ca_f_SH15_gondawara")
        self.assertTrue(all(v["face_model"] == "c_ca_f_SH15_gondawara"
                            for v in self.repo.targets["side_gondawara"]["variants"]))

    def test_named_favorites_aliases_are_user_overlays(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "finder.json"
            state = FinderUserState(path)
            state.set_favorite("side_gondawara", True)
            state.set_alias("side_gondawara", "My suit candidate")
            repo = DataRepository(FinderUserState(path))
            self.assertEqual(repo.ids_for_kind("favorites"), ["side_gondawara"])
            self.assertEqual(repo.find_targets("my suit candidate"), ["side_gondawara"])
            self.assertEqual(repo.find_targets("Gondawara"), ["side_gondawara"])

    def test_all_named_identities_every_variant_apply_and_restore_existing_transaction(self):
        for tid in self.repo.named_ids:
            for index, variant in enumerate(self.repo.targets[tid]["variants"]):
                with self.subTest(tid=tid, variant=index):
                    memory = FakeMemory(self.repo)
                    original = {base: bytes(data) for base, data in memory.segments.items()}
                    engine = TrainerEngine(self.repo, memory)
                    result = engine.apply({"ichiban": SlotSelection(tid, "fixed_variant", index)})
                    self.assertTrue(result.ok, result.message)
                    for sid, source in self.repo.sources.items():
                        for entry in source["context_entries"]:
                            address = engine.character.mapping + entry["position"] * 4
                            self.assertEqual(memory.read_u32(address), variant["character_row"] if sid == "ichiban" else entry["original_row"])
                    for item in engine.active_selection.slots.values():
                        self.assertEqual(item.variant_index, index)
                    self.assertTrue(engine.restore("named variant test").ok)
                    self.assertEqual({base: bytes(data) for base, data in memory.segments.items()}, original)

    def test_expanded_names_and_reviewed_default_keys(self):
        expected = [
            ("ace", "Ace", "艾斯", 25957), ("aina", "Aina", "艾娜", 26192),
            ("alohappy", "Alo-Happy", "阿罗哈皮", 28062),
            ("bony_kashiwa", "Bony Kashiwa", "邦尼柏", 23481),
            ("danny", "Danny", "丹尼", 25224),
            ("elizabeth", "Elizabeth", "伊丽莎白", 23498),
            ("ikari", "Ikari", "猪狩", 6212), ("jack", "Jack", "杰克", 25961),
            ("james", "James", "詹姆斯", 25127), ("joker", "Joker", "小丑", 25965),
            ("king", "King", "国王", 25969),
            ("machiko", "Machiko-san", "真知子", 13943),
            ("matt_tropico", "Matt Tropico", "马特·特罗皮科", 28040),
            ("nathan", "Nathan", "内森", 25126), ("onishi", "Onishi", "大西", 12616),
            ("raymond", "Raymond", "雷蒙德", 28065),
            ("yasuda", "Ringmaster Yasuda", "安田团长", 25054),
            ("thomas", "Thomas", "托马斯", 23007), ("tony", "Tony", "托尼", 25052),
        ]
        for slug, en, zh, key in expected:
            tid = "side_" + slug
            with self.subTest(tid=tid):
                target = self.repo.targets[tid]
                self.assertEqual(target["standard_character"], key)
                self.assertEqual(target["variants"][0]["character"], key)
                self.assertIn(tid, self.repo.find_targets(en, "named"))
                self.assertEqual(self.repo.find_targets(zh, "named"), [tid])
                self.assertEqual(self.repo.find_targets(f"{en} {key}", "named"), [tid])
                self.assertTrue(target["confirmed_identity"])

    def test_expanded_japanese_names_and_variant_searches(self):
        for query, tid in [("アイナ 7052", "side_aina"),
                           ("エリザベス 28063", "side_elizabeth"),
                           ("猪狩 26901", "side_ikari"),
                           ("レイモンド 28066", "side_raymond"),
                           ("トーマス 23008", "side_thomas"),
                           ("True Ace", "side_ace")]:
            with self.subTest(query=query):
                self.assertEqual(self.repo.find_targets(query, "named"), [tid])

    def test_named_write_failure_rolls_back_existing_transaction(self):
        memory = FakeMemory(self.repo)
        original = {base: bytes(data) for base, data in memory.segments.items()}
        memory.fail_on_write_number = 3
        engine = TrainerEngine(self.repo, memory)
        result = engine.apply({"kiryu": SlotSelection("side_gondawara", "fixed_variant", 1)})
        self.assertFalse(result.ok)
        self.assertEqual({base: bytes(data) for base, data in memory.segments.items()}, original)


if __name__ == "__main__":
    unittest.main()
