from __future__ import annotations

import os
import time
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
from y8trainer.engine import OperationResult, TrainerEngine
from y8trainer.ui import (
    MainWindow,
    TargetPickerDialog,
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


if __name__ == "__main__":
    unittest.main()
