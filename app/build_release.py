#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from PyInstaller.__main__ import run as pyinstaller_run


HERE = Path(__file__).resolve().parent
SRC = HERE / "src"
ENTRY = SRC / "y8trainer" / "app.py"
SHARED = HERE.parent / "data"
PLAN = SHARED / "multi_source_selector.generated.json"
COSTUME_METADATA = HERE.parent / "data" / "costume_vanilla_rpg_costume.json"
BUILD = HERE / "build"
RELEASE = HERE / "release"
ICON = BUILD / "infinite_wealth_fluent.ico"
NAME = "InfiniteWealthCharacterStudio_v0.7.0"


def make_icon() -> None:
    BUILD.mkdir(parents=True, exist_ok=True)
    size = 256
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (3, 3, size - 4, size - 4), radius=64,
        fill=(58, 122, 254, 255), outline=(118, 160, 255, 255), width=5,
    )
    try:
        font = ImageFont.truetype("segoeuib.ttf", 88)
    except OSError:
        font = ImageFont.load_default()
    box = draw.textbbox((0, 0), "IW", font=font)
    x = (size - (box[2] - box[0])) / 2
    y = (size - (box[3] - box[1])) / 2 - box[1]
    draw.text((x, y), "IW", font=font, fill=(255, 255, 255, 255))
    buffer = io.BytesIO()
    image.save(
        buffer, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48),
                                     (64, 64), (128, 128), (256, 256)]
    )
    ICON.write_bytes(buffer.getvalue())


def main() -> int:
    required = [
        PLAN,
        SHARED / "female_npc_catalog.generated.json",
        SHARED / "male_npc_catalog.generated.json",
        COSTUME_METADATA,
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit("Missing generated data: " + ", ".join(missing))
    # Reuse a valid generated icon. This also avoids rewriting a file that a
    # previous Windows Explorer/PyInstaller process may still have open.
    if not ICON.is_file() or ICON.stat().st_size < 1024:
        make_icon()
    RELEASE.mkdir(parents=True, exist_ok=True)
    # Keep generated build metadata isolated from older builds. On Windows an
    # Explorer/AV scan can retain a handle to a previous .spec or analysis
    # artifact and make an otherwise clean rebuild fail with PermissionError.
    work = BUILD / f"pyinstaller_{NAME}"
    spec = BUILD / f"spec_{NAME}"
    work.mkdir(parents=True, exist_ok=True)
    spec.mkdir(parents=True, exist_ok=True)

    args = [
        str(ENTRY),
        "--name", NAME,
        "--onefile",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--icon", str(ICON),
        "--paths", str(SRC),
        "--distpath", str(RELEASE),
        "--workpath", str(work),
        "--specpath", str(spec),
        "--add-data", f"{required[0]};data",
        "--add-data", f"{required[1]};data",
        "--add-data", f"{required[2]};data",
        "--add-data", f"{required[3]};data",
        "--exclude-module", "PySide6.QtWebEngineCore",
        "--exclude-module", "PySide6.QtWebEngineWidgets",
        "--exclude-module", "PySide6.QtQml",
        "--exclude-module", "PySide6.QtQuick",
        "--exclude-module", "PySide6.QtPdf",
        "--exclude-module", "PySide6.QtPdfWidgets",
        # The lite QFluentWidgets build probes this optional AcrylicLabel
        # helper inside a guarded import. It pulls NumPy/SciPy/Pillow even
        # though this application never uses image blur. Excluding it keeps
        # the documented fallback and avoids a large, fragile dependency tree.
        "--exclude-module", "qfluentwidgets.common.image_utils",
    ]
    pyinstaller_run(args)

    executable = RELEASE / f"{NAME}.exe"
    if not executable.is_file():
        raise SystemExit(f"PyInstaller did not create {executable}")
    digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    (RELEASE / f"{NAME}.sha256.txt").write_text(
        f"{digest}  {executable.name}\n", encoding="ascii", newline="\n"
    )
    print(f"Built {executable} ({executable.stat().st_size:,} bytes)")
    print(f"SHA-256 {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
