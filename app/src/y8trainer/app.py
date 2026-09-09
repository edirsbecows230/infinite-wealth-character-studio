from __future__ import annotations

import argparse
import os
import sys
import traceback
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Like a Dragon: Infinite Wealth character and costume changer"
    )
    parser.add_argument("--preview", action="store_true", help="show the UI without connecting to the game")
    parser.add_argument("--screenshot", type=Path, help="render a UI preview to a PNG and exit")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.screenshot:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QMessageBox

    from y8trainer.data import DataRepository
    from y8trainer.engine import TrainerEngine
    from y8trainer.ui import MainWindow, apply_application_style, make_app_icon

    app = QApplication(sys.argv[:1])
    app.setApplicationName("Infinite Wealth Character Studio")
    app.setOrganizationName("Infinite Wealth Modding")
    app.setWindowIcon(make_app_icon())
    apply_application_style(app)

    try:
        repository = DataRepository()
        engine = TrainerEngine(repository)
        window = MainWindow(repository, engine, preview=args.preview or bool(args.screenshot))
        window.show()
        if args.screenshot:
            output = args.screenshot.resolve()
            output.parent.mkdir(parents=True, exist_ok=True)

            def capture() -> None:
                window.grab().save(str(output), "PNG")
                window.close()
                app.quit()

            QTimer.singleShot(650, capture)
        return app.exec()
    except Exception as exc:
        details = traceback.format_exc()
        if args.screenshot:
            print(details, file=sys.stderr)
        else:
            QMessageBox.critical(
                None, "Infinite Wealth Character Studio", f"{exc}\n\n{details}"
            )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
