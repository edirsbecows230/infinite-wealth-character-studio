from __future__ import annotations

import os
import time
import tempfile
from unittest.mock import patch
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from qfluentwidgets import (
    CheckBox,
    ComboBox,
    FluentWindow,
    LineEdit,
    Pivot,
    PrimaryPushButton,
    PushButton,
    SimpleCardWidget,
    SmoothScrollArea,
)

from y8trainer.data import DataRepository
from y8trainer.finder_state import FinderUserState
from y8trainer.engine import OperationResult, TrainerEngine
from y8trainer.ui import (
    MainWindow,
    TargetPickerDialog,
    AliasDialog,
    tx,
    apply_application_style,
    costume_variant_label,
)


class UiTaskLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        apply_application_style(cls.app)
        cls.repository = DataRepository()

    def setUp(self) -> None:
        self.engine = TrainerEngine(self.repository)
        self.window = MainWindow(self.repository, self.engine, preview=True)

    def tearDown(self) -> None:
        self.window.close()
        self.app.processEvents()

    def test_background_task_releases_busy_and_reenables_apply(self) -> None:
        results: list[OperationResult] = []
        for index in range(3):
            message = f"done-{index}"
            self.window._run(lambda message=message: OperationResult(True, message), results.append)
            self.assertTrue(self.window.busy)
            self.assertFalse(self.window.apply_button.isEnabled())

            deadline = time.monotonic() + 3.0
            while self.window.busy and time.monotonic() < deadline:
                self.app.processEvents()
                time.sleep(0.01)

            self.assertFalse(self.window.busy, "finished signal did not release the UI busy state")
            self.assertTrue(self.window.apply_button.isEnabled())
        self.assertEqual([item.message for item in results], ["done-0", "done-1", "done-2"])

    def test_each_character_keeps_an_independent_slot(self) -> None:
        for card in self.window.cards.values():
            card.include.setChecked(True)
        both = self.window._collect_slots()
        self.assertEqual(
            set(both),
            {"ichiban", "kiryu", "nanba", "adachi", "chou", "jyungi", "tomizawa", "saeko", "chitose", "sonhi"},
        )
        self.assertNotEqual(both["ichiban"].target_id, both["kiryu"].target_id)

        self.window.cards["kiryu"].include.setChecked(False)
        one = self.window._collect_slots()
        self.assertNotIn("kiryu", one)

    def test_only_current_slot_included_by_default(self) -> None:
        included = [source_id for source_id, card in self.window.cards.items() if card.is_included()]
        self.assertEqual(included, ["ichiban"])
        self.assertEqual(set(self.window._collect_slots()), {"ichiban"})

    def test_restore_actions_are_explicit(self) -> None:
        self.assertEqual(self.window.restore_button.text(), "恢复游戏原版模型")
        self.assertEqual(self.window.vanilla_button.text(), "恢复本次启动前状态")

    def test_chinese_pivot_labels_are_chinese_only(self) -> None:
        self.assertEqual(self.window.language, "zh")
        labels = [item.text() for item in self.window.slot_pivot.items.values()]
        expected_names = ["春日", "桐生", "难波", "足立", "赵", "韩俊基", "富泽", "纱荣子", "千岁", "胜熙"]
        for expected, label in zip(expected_names, labels):
            self.assertIn(expected, label)

    def test_product_name_and_value_focused_subtitle_are_bilingual(self) -> None:
        self.assertEqual(self.window.windowTitle(), "如龙8 无尽财富 · 角色模型工坊")
        self.assertEqual(self.window.app_title.text(), "如龙8 无尽财富 · 角色模型工坊")
        self.assertEqual(
            self.window.subtitle.text(),
            "多角色实时模型与服装替换工具 · 10 槽位独立配置 · 即改即用",
        )

        self.window.language_button.click()
        self.app.processEvents()
        self.assertEqual(
            self.window.windowTitle(),
            "Like a Dragon: Infinite Wealth — Character Studio",
        )
        self.assertEqual(
            self.window.subtitle.text(),
            "Real-time 10-slot character model & costume changer with multi-source support",
        )

    def test_fluent_widget_mapping(self) -> None:
        self.assertIsInstance(self.window, FluentWindow)
        self.assertIsInstance(self.window.slot_pivot, Pivot)
        self.assertIsInstance(self.window.scroll_area, SmoothScrollArea)
        self.assertGreater(len(self.window.cards), 2)
        for card in self.window.cards.values():
            self.assertIsInstance(card, SimpleCardWidget)
            self.assertIsInstance(card.include, CheckBox)
            self.assertIsInstance(card.mode, ComboBox)
        self.assertIsInstance(self.window.custom_input, LineEdit)
        self.assertIsInstance(self.window.restore_button, PushButton)
        self.assertIsInstance(self.window.apply_button, PrimaryPushButton)

    def test_pivot_switches_character_editor(self) -> None:
        self.assertEqual(self.window.editor_stack.currentIndex(), 0)
        self.window.pivot_items["nanba"].click()
        self.app.processEvents()
        self.assertEqual(self.window.editor_stack.currentIndex(), 2)

    def test_fixed_outfit_mode_reveals_variant_selector(self) -> None:
        card = self.window.cards["ichiban"]
        fixed_index = card.mode.findData("fixed_variant")
        self.assertGreaterEqual(fixed_index, 0)
        card.mode.setCurrentIndex(fixed_index)
        self.app.processEvents()

        self.assertEqual(card.mode.currentData(), "fixed_variant")
        self.assertFalse(card.variant.isHidden())
        self.assertFalse(card.variant_caption.isHidden())
        self.assertGreater(card.variant.count(), 0)
        self.assertIsInstance(card.variant.currentData(), int)

    def test_costume_metadata_produces_readable_bilingual_labels(self) -> None:
        self.assertEqual(len(self.repository.costumes), 480)
        host = next(
            item for item in self.repository.targets["adachi"]["variants"]
            if item.get("source_costume") == 91
        )
        majima = next(
            item for item in self.repository.targets["kiryu"]["variants"]
            if item.get("source_costume") == 271
        )
        self.assertEqual(costume_variant_label(host, "en"), "Host · Normal  (costume 91)")
        self.assertEqual(costume_variant_label(host, "zh"), "男公关 · 标准款（服装 91）")
        self.assertEqual(
            costume_variant_label(majima, "zh"),
            "特别服装：真岛吾朗套装（服装 271）",
        )
        self.assertNotIn(host["model"], costume_variant_label(host, "zh"))

    def test_selected_outfit_keeps_model_code_in_secondary_detail(self) -> None:
        card = self.window.cards["ichiban"]
        card.set_target("adachi")
        card.mode.setCurrentIndex(card.mode.findData("fixed_variant"))
        variant_index = next(
            index for index, item in enumerate(self.repository.targets["adachi"]["variants"])
            if item.get("source_costume") == 91
        )
        card.variant.setCurrentIndex(variant_index)
        self.app.processEvents()

        self.assertEqual(card.variant.currentText(), "男公关 · 标准款（服装 91）")
        self.assertIn("c_cm_x_job_02_adachi", card.variant_detail.text())

    def test_target_picker_keeps_last_row_inside_top_level_window(self) -> None:
        self.window.resize(1280, 720)
        self.window.show()
        self.app.processEvents()
        dialog = TargetPickerDialog(
            self.repository, "zh", "chitose", self.window)
        dialog.show()
        self.app.processEvents()

        self.assertLessEqual(dialog.widget.height(), self.window.height() - 48)
        dialog.segmented.setCurrentItem("curated")
        self.app.processEvents()
        scroll = dialog.list.verticalScrollBar()
        scroll.setValue(scroll.maximum())
        self.app.processEvents()
        last = dialog.list.item(dialog.list.count() - 1)
        self.assertTrue(
            dialog.list.viewport().rect().intersects(dialog.list.visualItemRect(last))
        )
        dialog.close()

    def test_ui_has_valid_routing_object_name(self) -> None:
        source = Path(__file__).resolve().parents[1] / "src" / "y8trainer" / "ui.py"
        text = source.read_text(encoding="utf-8")
        self.assertIn(".setObjectName(", text)


class CharacterFinderUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        apply_application_style(cls.app)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config = Path(self.temp.name) / "finder.json"
        self.repository = DataRepository(FinderUserState(self.config))
        self.engine = TrainerEngine(self.repository)
        self.window = MainWindow(self.repository, self.engine, preview=True)
        self.window.show()
        self.app.processEvents()
        self.dialog = TargetPickerDialog(self.repository, "zh", "chitose", self.window)
        self.dialog.show()
        self.app.processEvents()

    def tearDown(self):
        self.dialog.close()
        self.window.close()
        self.app.processEvents()

    def ids(self):
        from PySide6.QtCore import Qt
        return [self.dialog.list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.dialog.list.count())]

    def select_id(self, target_id):
        self.dialog.list.setCurrentRow(self.ids().index(target_id))
        self.app.processEvents()

    def test_ui_hex_key_and_multi_token_search(self):
        target = self.repository.targets["chitose"]
        self.dialog.search.setText(f"0x{target['standard_character']:X} chitose")
        self.dialog._populate()
        self.assertEqual(self.ids(), ["chitose"])
        self.assertIn("0x", self.dialog.lbl_row_key.text())
        self.dialog.search.setText("chitose not_a_real_token")
        self.dialog._populate()
        self.assertEqual(self.ids(), [])
        self.assertFalse(self.dialog.choose.isEnabled())
        self.assertFalse(self.dialog.next_button.isEnabled())
        self.assertFalse(self.dialog.favorite_button.isEnabled())

    def test_same_face_searches_entire_catalog_and_can_be_refined(self):
        target_id = next(x for x in self.repository.female_ids
                         if len(self.repository.related_targets(x, "face_model")) > 1)
        self.dialog.segmented.items["female"].click()
        self.select_id(target_id)
        face = self.repository.targets[target_id]["face_model"]
        self.dialog.same_face_button.click()
        self.assertEqual(self.dialog.current_kind, "all")
        self.assertEqual(set(self.ids()), set(self.repository.related_targets(target_id, "face_model")))
        self.assertTrue(all(self.repository.targets[x]["face_model"] == face for x in self.ids()))
        self.assertEqual(self.dialog.search.text(), "")
        self.dialog.search.setText(str(self.repository.targets[target_id]["standard_character"]))
        self.dialog._populate()
        self.assertIn(target_id, self.ids())
        self.dialog.clear_filter_button.click()
        self.assertIsNone(self.dialog.related_filter)
        self.assertEqual(self.dialog.list.count(), 5193)

    def test_same_hair_and_same_model_use_exact_indexes(self):
        self.dialog.segmented.items["female"].click()
        target_id = next(x for x in self.repository.female_ids if self.repository.targets[x]["hair_model"])
        self.select_id(target_id)
        self.dialog.same_hair_button.click()
        self.assertEqual(set(self.ids()), set(self.repository.related_targets(target_id, "hair_model")))
        self.select_id(target_id)
        self.dialog.same_model_button.click()
        self.assertEqual(set(self.ids()), set(self.repository.related_targets(target_id, "model")))

    def test_empty_face_hair_buttons_are_disabled(self):
        self.select_id("chitose")
        self.assertFalse(self.dialog.same_face_button.isEnabled())
        self.assertFalse(self.dialog.same_hair_button.isEnabled())
        self.assertTrue(self.dialog.same_model_button.isEnabled())

    def test_favorite_category_updates_and_persists(self):
        self.select_id("chitose")
        self.dialog.favorite_button.click()
        self.assertTrue(FinderUserState(self.config).is_favorite("chitose"))
        self.dialog.segmented.items["favorites"].click()
        self.assertEqual(self.ids(), ["chitose"])
        self.dialog.favorite_button.click()
        self.assertEqual(self.ids(), [])
        self.assertFalse(FinderUserState(self.config).is_favorite("chitose"))

    def test_alias_editor_save_delete_search_and_original_fields(self):
        self.select_id("chitose")
        alias_dialog = AliasDialog("", "zh", self.dialog)
        alias_dialog.editor.setText("Karen UFO")
        self.dialog.save_alias("chitose", alias_dialog.editor.text())
        self.assertEqual(FinderUserState(self.config).alias("chitose"), "Karen UFO")
        self.assertIn("Karen UFO", self.dialog.alias_label.text())
        self.assertEqual(self.dialog.spec_labels["id"].text(), "chitose")
        self.assertEqual(self.dialog.lbl_main_model.text(), self.repository.targets["chitose"]["model"])
        self.dialog.search.setText("karen chitose")
        self.dialog._populate()
        self.assertEqual(self.ids(), ["chitose"])
        alias_dialog.delete_button.click()
        self.assertEqual(alias_dialog.editor.text(), "")
        self.dialog.save_alias("chitose", alias_dialog.editor.text())
        self.assertEqual(FinderUserState(self.config).alias("chitose"), "")
        self.assertEqual(self.ids(), [])
        alias_dialog.close()

    def test_anonymous_rows_expose_model_face_hair_and_key(self):
        self.dialog.segmented.items["male"].click()
        target_id = self.ids()[0]
        target = self.repository.targets[target_id]
        text = self.dialog.list.item(0).text()
        self.assertIn(str(target["standard_character"]), text)
        self.assertIn(target["model"], text)
        self.assertIn(target["face_model"] or "—", text)
        self.assertIn(target["hair_model"] or "—", text)
        self.assertEqual(self.dialog.spec_labels["id"].text(), target_id)

    def test_alias_button_runs_fluent_editor_and_cancel_does_not_save(self):
        from PySide6.QtCore import QTimer
        self.select_id("chitose")

        def accept_editor():
            editor = next(x for x in reversed(self.dialog.findChildren(AliasDialog)) if x.isVisible())
            editor.editor.setText("Karen UFO")
            editor.yesButton.click()

        QTimer.singleShot(0, accept_editor)
        self.dialog.alias_button.click()
        self.assertEqual(self.repository.user_state.alias("chitose"), "Karen UFO")

        def cancel_editor():
            editor = next(x for x in reversed(self.dialog.findChildren(AliasDialog)) if x.isVisible())
            editor.editor.setText("Unsaved")
            editor.cancelButton.click()

        QTimer.singleShot(0, cancel_editor)
        self.dialog.alias_button.click()
        self.assertEqual(FinderUserState(self.config).alias("chitose"), "Karen UFO")

    def test_previous_next_and_selection_never_call_engine(self):
        with patch.object(self.engine, "apply") as apply, patch.object(self.engine.memory, "write") as write:
            self.dialog.list.setCurrentRow(0)
            self.dialog.next_button.click()
            self.assertEqual(self.dialog.list.currentRow(), 1)
            self.assertEqual(self.dialog.candidate_position.text(), tx("candidate_position", "zh").format(current=2, total=47))
            self.dialog.previous_button.click()
            self.assertEqual(self.dialog.list.currentRow(), 0)
            self.assertFalse(self.dialog.previous_button.isEnabled())
            self.dialog._accept()
            self.assertEqual(self.dialog.selected_id, self.ids()[0])
            apply.assert_not_called()
            write.assert_not_called()

    def test_search_debounce_and_all_results_fit_in_supported_window_sizes(self):
        self.dialog.close()
        for language in ("en", "zh"):
            for size in ((960, 720), (1160, 850), (1280, 720)):
                with self.subTest(language=language, size=size):
                    self.window.resize(*size)
                    self.app.processEvents()
                    dialog = TargetPickerDialog(self.repository, language, "chitose", self.window)
                    dialog.show()
                    dialog.segmented.items["all"].click()
                    self.app.processEvents()
                    self.assertLessEqual(dialog.widget.height(), self.window.height() - 48)
                    self.assertLessEqual(dialog.widget.width(), self.window.width() - 48)
                    self.assertLessEqual(dialog.inspector_scroll.horizontalScrollBar().maximum(), 0)
                    self.assertEqual(dialog.list.count(), 5193)
                    dialog.search.setText("0x5b6c chitose")
                    self.assertTrue(dialog.filter_timer.isActive())
                    deadline = time.monotonic() + 1.0
                    while dialog.filter_timer.isActive() and time.monotonic() < deadline:
                        self.app.processEvents()
                    self.assertEqual(dialog.list.count(), 1)
                    dialog.close()

    def test_save_failure_is_visible_and_does_not_lose_state(self):
        self.select_id("chitose")
        self.dialog.favorite_button.click()
        with patch("y8trainer.finder_state.os.replace", side_effect=PermissionError("locked")):
            self.dialog.favorite_button.click()
        self.assertTrue(self.repository.user_state.is_favorite("chitose"))
        self.assertFalse(self.dialog.state_feedback.isHidden())
        self.assertIn("locked", self.dialog.state_feedback.text())


if __name__ == "__main__":
    unittest.main()
