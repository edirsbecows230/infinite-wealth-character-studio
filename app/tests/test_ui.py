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
from y8trainer.ui import MainWindow, apply_application_style, costume_variant_label


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

    def test_each_protagonist_keeps_an_independent_slot(self) -> None:
        both = self.window._collect_slots()
        self.assertEqual(set(both), {"ichiban", "kiryu"})
        self.assertNotEqual(both["ichiban"].target_id, both["kiryu"].target_id)

        self.window.kiryu_card.include.setChecked(False)
        one = self.window._collect_slots()
        self.assertEqual(set(one), {"ichiban"})

    def test_restore_actions_are_explicit(self) -> None:
        self.assertEqual(self.window.restore_button.text(), "恢复游戏原版模型")
        self.assertEqual(self.window.vanilla_button.text(), "恢复本次启动前状态")

    def test_product_name_and_value_focused_subtitle_are_bilingual(self) -> None:
        self.assertEqual(self.window.windowTitle(), "如龙8 无尽财富 · 角色模型工坊")
        self.assertEqual(self.window.app_title.text(), "如龙8 无尽财富 · 角色模型工坊")
        self.assertEqual(
            self.window.subtitle.text(),
            "双主角实时模型与服装替换工具 · 即改即用",
        )

        self.window.language_button.click()
        self.app.processEvents()
        self.assertEqual(
            self.window.windowTitle(),
            "Like a Dragon: Infinite Wealth — Character Studio",
        )
        self.assertEqual(
            self.window.subtitle.text(),
            "Real-time protagonist model & costume changer with dual-slot support",
        )

    def test_fluent_widget_mapping(self) -> None:
        self.assertIsInstance(self.window, FluentWindow)
        self.assertIsInstance(self.window.slot_pivot, Pivot)
        self.assertIsInstance(self.window.scroll_area, SmoothScrollArea)
        self.assertIsInstance(self.window.ichiban_card, SimpleCardWidget)
        self.assertIsInstance(self.window.ichiban_card.include, CheckBox)
        self.assertIsInstance(self.window.ichiban_card.mode, ComboBox)
        self.assertIsInstance(self.window.custom_input, LineEdit)
        self.assertIsInstance(self.window.restore_button, PushButton)
        self.assertIsInstance(self.window.apply_button, PrimaryPushButton)

    def test_pivot_switches_protagonist_editor(self) -> None:
        self.assertEqual(self.window.editor_stack.currentIndex(), 0)
        self.window.pivot_items["kiryu"].click()
        self.app.processEvents()
        self.assertEqual(self.window.editor_stack.currentIndex(), 1)

    def test_fixed_outfit_mode_reveals_variant_selector(self) -> None:
        card = self.window.ichiban_card
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
        card = self.window.ichiban_card
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

    def test_ui_source_has_no_custom_qss_hooks(self) -> None:
        source = Path(__file__).resolve().parents[1] / "src" / "y8trainer" / "ui.py"
        text = source.read_text(encoding="utf-8")
        self.assertNotIn("STYLE =", text)
        self.assertNotIn("setStyleSheet(", text)
        self.assertNotIn(".setProperty(", text)
        # FluentWindow requires one object name as its routing key. It is not
        # used for styling and is documented next to the call.
        self.assertEqual(text.count(".setObjectName("), 1)


if __name__ == "__main__":
    unittest.main()
