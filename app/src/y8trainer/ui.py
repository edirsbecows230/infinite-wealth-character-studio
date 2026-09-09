from __future__ import annotations

import os
import re
import traceback
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QCloseEvent, QFont, QFontDatabase, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QListWidgetItem,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    Action,
    BodyLabel,
    CaptionLabel,
    CheckBox,
    ComboBox,
    FluentIcon as FIF,
    FluentWindow,
    HorizontalSeparator,
    InfoBadge,
    InfoBar,
    InfoBarPosition,
    InfoLevel,
    LineEdit,
    ListWidget,
    MessageBox,
    MessageBoxBase,
    Pivot,
    PrimaryDropDownPushButton,
    PrimaryPushButton,
    PushButton,
    RoundMenu,
    SearchLineEdit,
    SegmentedWidget,
    SimpleCardWidget,
    SmoothScrollArea,
    StrongBodyLabel,
    SubtitleLabel,
    Theme,
    TitleLabel,
    TransparentPushButton,
    setTheme,
    setThemeColor,
)

from .data import DataRepository
from .engine import OperationResult, SlotSelection, TrainerEngine


TEXT = {
    "app_title": (
        "Like a Dragon: Infinite Wealth — Character Studio",
        "如龙8 无尽财富 · 角色模型工坊",
    ),
    "app_badge": ("v0.7.0 Public Edition", "v0.7.0 公开版"),
    "subtitle": (
        "Real-time 10-slot character model & costume changer with multi-source support",
        "多角色实时模型与服装替换工具 · 10 槽位独立配置 · 即改即用",
    ),
    "waiting": ("WAITING FOR GAME", "等待游戏启动"),
    "scanning": ("SCANNING DATABASES", "正在定位数据库"),
    "ready": ("READY", "已就绪"),
    "applied": ("APPLIED & VERIFIED", "已应用并验证"),
    "error": ("ACTION REQUIRED", "需要处理"),
    "ichiban": ("ICHI / ICHIBAN", "春日"),
    "kiryu": ("KIRYU", "桐生"),
    "nanba": ("NANBA", "难波"),
    "adachi": ("ADACHI", "足立"),
    "chou": ("ZHAO", "赵"),
    "jyungi": ("JOON-GI HAN", "韩俊基"),
    "tomizawa": ("TOMIZAWA", "富泽"),
    "saeko": ("SAEKO", "纱荣子"),
    "chitose": ("CHITOSE", "千岁"),
    "sonhi": ("SEONHEE", "胜熙"),
    "slot_active": ("ACTIVE SLOT", "参与本次替换"),
    "slot_backup": ("RESTORE TO BACKUP", "保持首次备份"),
    "character": ("Target Character", "目标角色"),
    "choose": ("Select Character", "更换目标角色"),
    "outfit": ("Outfit Behavior", "服装行为"),
    "variant": ("Fixed Outfit", "固定服装"),
    "context": ("Context Matched (Recommended)", "场景匹配（推荐 · 全自动跟随场景换装）"),
    "default": ("Default Outfit Everywhere", "默认服装（始终保持标准常服）"),
    "fixed": ("Fixed Specific Outfit Variant", "固定指定服装（锁定特定 DLC/职业外观）"),
    "model": ("MODEL", "模型"),
    "row_key": ("ROW / KEY", "行 / KEY"),
    "voice": ("VOICE", "语音"),
    "apply": ("Apply Selected Slots", "应用所选角色槽位"),
    "apply_hint": (
        "Auto backup → Write all selected sources → Verify readback → Auto rollback on error",
        "自动备份 → 写入全部所选来源 → 逐项回读校验 → 失败自动回滚",
    ),
    "restore": ("Restore Original Models", "恢复游戏原版模型"),
    "reconnect": ("Scan & Reconnect", "重新连接扫描"),
    "custom": ("Custom Character Key Direct Inject", "自定义 Character Key 直填导入"),
    "custom_hint": ("Decimal (e.g. 23404) or Hex (e.g. 0x5B6C)", "十进制（如 23404）或十六进制（如 0x5B6C）"),
    "custom_slot": ("Target Slot", "目标槽位"),
    "use_custom": ("Set to Target Slot", "导入至所选槽位"),
    "details": ("Diagnostics & Advanced Tools", "诊断与底层工具"),
    "hide_details": ("Hide Diagnostics", "收起诊断工具"),
    "db_wait": ("Database addresses will appear after game connection.", "连接游戏后将在此显示数据库与内存基址。"),
    "vanilla": ("Restore Launch Backup", "恢复本次启动前状态"),
    "vanilla_hint": (
        "Restores memory to the snapshot taken on first Apply. Preserves pre-existing CT/file mods.",
        "恢复至首次「应用」时截取的内存快照。若启动前已加载 CT 或文件 Mod，将保留原有修改。",
    ),
    "original_confirm_title": ("Restore Original Game Models?", "恢复游戏原版模型？"),
    "original_confirm_body": (
        "This writes embedded original values for all configured sources. Existing free-roam actors refresh after reloading a save or changing maps.",
        "这会向所有配置槽位写入游戏内置的原版原始数值。场景中已生成的自由探索角色需读档或切图后刷新生效。",
    ),
    "safety": (
        "Reopen in-game menus to refresh UI. Reload a save or change maps for free-roam models.",
        "游戏内菜单需重新打开刷新；自由探索角色模型需读档或切换地图刷新。",
    ),
    "picker_title": ("Choose Target Character", "选择目标角色"),
    "picker_search": ("Search name, model code (c_cw_...), key, row, voice...", "搜索角色名、模型代码 (c_cw_...)、Key、行、语音..."),
    "curated": ("Curated Characters", "精选角色"),
    "female": ("Female NPCs", "女性 NPC"),
    "male": ("Male NPCs", "男性 NPC"),
    "all": ("All Characters", "全部角色"),
    "select": ("Select This Character", "选择此角色"),
    "cancel": ("Cancel", "取消"),
    "no_results": ("No matching characters found", "未找到匹配的角色"),
    "select_all": ("Select All", "全部勾选"),
    "deselect_all": ("Deselect All", "全部取消"),
    "reset_defaults": ("Reset Mappings", "恢复默认映射"),
    "presets": ("Quick Presets", "预设方案"),
    "preset_default": ("Reset Default Roster", "默认推荐阵容"),
    "preset_all_on": ("Enable All Slots", "启用全部 10 槽位"),
    "preset_dual": ("Protagonists Only (Ichiban & Kiryu)", "仅替换双主角（春日 & 桐生）"),
    "selected_slots_summary": ("{count}/10 Slots Active", "已选 {count}/10 个槽位"),
    "model_inspector": ("Model Specifications", "模型参数规格"),
    "variants_title": ("Available Outfits & Variants", "包含服装变体"),
    "close_title": ("Choose Restore Target on Exit", "退出前选择恢复目标"),
    "close_body": (
        "The game is still running with active replacements. Choose whether to restore original game models, restore launch-state backup, or leave active.",
        "游戏仍在运行且当前有模型替换处于生效状态。请选择退出时的处理方式：",
    ),
    "close_body_modified_backup": (
        "The initial launch backup was already modified by other tools. Choose original models to write clean vanilla values.",
        "检测到首次应用快照本身已被修改。若想彻底还原，请选择恢复原版模型。",
    ),
    "restore_exit": ("Original Models & Exit", "恢复原版并退出"),
    "session_exit": ("Launch State & Exit", "恢复启动前快照并退出"),
    "keep_exit": ("Keep Active & Exit", "保持替换生效并退出"),
}


def tx(key: str, language: str) -> str:
    pair = TEXT.get(key, (key, key))
    return pair[0] if language == "en" else pair[1]


def parse_label_category_and_name(text: str, language: str) -> tuple[str, str]:
    """Extract category badge and clean name from raw label string."""
    text = str(text or "")
    match = re.match(r"^\[([^\]]+)\]\s*(.*)$", text)
    if match:
        head, rest = match.groups()
        head_parts = re.split(r"\s*/\s*", head, maxsplit=1)
        localized_cat = head_parts[0] if language == "en" or len(head_parts) == 1 else head_parts[1]
        name_parts = re.split(r"\s*/\s*", rest, maxsplit=1)
        if len(name_parts) == 2 and " — " not in rest and " | " not in rest:
            localized_name = name_parts[0] if language == "en" else name_parts[1]
        else:
            localized_name = rest
        return localized_cat.strip(), localized_name.strip()
    if " — " in text:
        prefix, suffix = text.split(" — ", 1)
        parts = re.split(r"\s*/\s*", prefix, maxsplit=1)
        loc = parts[0] if language == "en" or len(parts) == 1 else parts[1]
        return "", f"{loc} — {suffix}".strip()
    return "", text.strip()


def display_label(text: str, language: str) -> str:
    """Render bilingual CT labels into the selected language."""
    cat, name = parse_label_category_and_name(text, language)
    if cat:
        return f"[{cat}] {name}"
    return name


COSTUME_GROUP_LABELS = {
    "host": ("Host", "男公关"),
    "dancer": ("Breaker", "街舞者"),
    "cook": ("Chef", "厨师"),
    "idol": ("Idol", "偶像"),
    "queen": ("Night Queen", "夜之女王"),
    "kunoichi": ("Kunoichi", "女忍者"),
    "samurai": ("Samurai", "武士"),
    "actionstar": ("Action Star", "动作巨星"),
    "marine": ("Aquanaut", "海洋潜水员"),
    "footballer": ("Linebacker", "橄榄球员"),
    "western": ("Desperado", "西部枪手"),
    "firedancer": ("Pyrodancer", "火焰舞者"),
    "housekeeper": ("Housekeeper", "家政管家"),
    "tropicaldancer": ("Geodancer", "热带舞者"),
    "tennis": ("Tennis Ace", "网球高手"),
}

COSTUME_NAME_ZH = {
    "Normal": "标准款",
    "Pattern A": "配色 A",
    "Pattern B": "配色 B",
    "Normal Swimsuit": "标准泳装",
    "Hawaii Outfit": "夏威夷常服",
    "Yokohama Outfit": "横滨常服",
}

COSTUME_DETAIL_ZH = {
    "88Tees Shirt": "88Tees T恤",
    "AWAKE": "AWAKE 演出服",
    "Akira Nishikiyama (Yakuza 0)": "锦山彰（如龙 0）",
    "Casino Attire": "赌场服",
    "Chitose": "千岁套装",
    "Classic Saeko": "经典纱荣子套装",
    "Daigo Dojima": "堂岛大吾套装",
    "Date Outfit": "约会装",
    "Dragon of Dojima": "堂岛之龙",
    "Gaiden TGS Shirt": "《外传》TGS T恤",
    "Go for Victory Shirt": "必胜 T恤",
    "Gold Swimsuit": "金色泳装",
    "Goro Majima": "真岛吾朗套装",
    "Goro Majima (Yakuza 0)": "真岛吾朗（如龙 0）",
    "Hamako": "滨子套装",
    "Haruka Sawamura": "泽村遥套装",
    "Hero": "勇者套装",
    "Hero of Yokohama Shirt": "横滨勇者 T恤",
    "Hostess": "女公关装",
    "Ichiban Kasuga": "春日一番套装",
    "Infinite Wealth TGS Shirt": "《无限财富》TGS T恤",
    "Joongi": "韩俊基套装",
    "Joongi (Yakuza 6)": "韩俊基（如龙 6）",
    "Judgement": "审判套装",
    "Kaoru Sayama": "狭山薰套装",
    "Kazuma Kiryu (Yakuza 0)": "桐生一马（如龙 0）",
    "Lawson Exclusive Shirt": "罗森限定 T恤",
    "Legendary Dragon Shirt": "传说之龙 T恤",
    "Makoto Date": "伊达真套装",
    "Nanba": "难波套装",
    "Ono Michio": "小野道夫套装",
    "Pixel Shirt": "像素 T恤",
    "Resurrected Dragon": "复活之龙套装",
    "Robo Michio": "机器小野道夫套装",
    "Ryuji Goda": "乡田龙司套装",
    "Security Detail": "安保人员装",
    "Seonhee": "善熙套装",
    "Shun Akiyama": "秋山骏套装",
    "Taiga Saejima": "冴岛大河套装",
    "Tasty Swimsuit": "趣味泳装",
    "Team Kasuga Pixel Shirt": "春日队像素 T恤",
    "Team Kiryu Pixel Shirt": "桐生队像素 T恤",
    "Tech Inspector": "技术检查员装",
    "Tomizawa": "富泽套装",
    "Traditional Swimsuit": "传统泳装",
    "Waitress Attire": "女服务员装",
    "White Matsumoto Shave Ice Shirt": "松本刨冰白色 T恤",
    "Zhao": "赵套装",
}


def _costume_name_zh(name: str, costume_key: str) -> str:
    hair = ""
    if name.endswith(" (Short Hair)"):
        name = name.removesuffix(" (Short Hair)")
        hair = "（短发）"
    elif "_amikomi" in costume_key:
        hair = "（编发）"
    if name.startswith("Special Outfit: "):
        detail = name.removeprefix("Special Outfit: ")
        translated = COSTUME_DETAIL_ZH.get(detail, detail)
        return f"特别服装：{translated}{hair}"
    return f"{COSTUME_NAME_ZH.get(name, name)}{hair}"


def costume_variant_label(variant: dict[str, Any], language: str) -> str:
    """Build a readable outfit label while keeping model codes clean."""
    costume_id = variant.get("source_costume")
    costume_key = str(variant.get("costume_key") or "")
    name = str(variant.get("costume_name") or "")
    if costume_id is None or not name:
        raw_label = str(variant.get("label") or "")
        if raw_label.startswith("Default /"):
            return "Default outfit" if language == "en" else "默认服装"
        return display_label(raw_label, language)

    group = next(
        (labels for prefix, labels in COSTUME_GROUP_LABELS.items()
         if costume_key == prefix or costume_key.startswith(prefix + "_")),
        None,
    )
    if language == "en":
        readable = f"{group[0]} · {name}" if group else name
        return f"{readable}  (costume {costume_id})"
    readable = _costume_name_zh(name, costume_key)
    if group:
        readable = f"{group[1]} · {readable}"
    return f"{readable}（服装 {costume_id}）"


def make_app_icon(size: int = 64) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#00B4D8"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(2, 2, size - 4, size - 4, size * 0.24, size * 0.24)
    painter.setPen(QColor("#FFFFFF"))
    font = QFont("Segoe UI", int(size * 0.28), QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "IW")
    painter.end()
    return QIcon(pixmap)


# =========================================================================
# StudioCard (Flawless Anti-Aliased Custom Dark Card with Zero White Edges)
# =========================================================================

class StudioCard(SimpleCardWidget):
    """Custom antialiased card widget with smooth borders and zero corner artifacts."""
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        bg_color: QColor | None = None,
        border_color: QColor | None = None,
        radius: int = 10,
    ) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.custom_bg = bg_color or QColor("#1E1E24")
        self.custom_border = border_color or QColor(255, 255, 255, 20)
        self.setBorderRadius(radius)

    def paintEvent(self, e) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.borderRadius
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.setPen(self.custom_border)
        painter.setBrush(self.custom_bg)
        painter.drawRoundedRect(rect, r, r)


# =========================================================================
# Target Picker Dialog (Overhauled with Segmented Nav & Rich Inspector)
# =========================================================================

class TargetPickerDialog(MessageBoxBase):
    def __init__(
        self,
        repository: DataRepository,
        language: str,
        current_id: str | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.repository = repository
        self.language = language
        self.selected_id: str | None = current_id

        host_width = parent.width() if parent is not None else 1280
        host_height = parent.height() if parent is not None else 800
        dialog_width = max(860, min(1180, host_width - 48))
        dialog_height = max(560, min(760, host_height - 48))
        self.widget.setFixedSize(dialog_width, dialog_height)
        self.setMaskColor(QColor(0, 0, 0, 160))
        self.widget.setStyleSheet("""
            QFrame#widget {
                background-color: #1A1A1E;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 10px;
            }
            QFrame#buttonGroup {
                background-color: #222228;
                border-top: 1px solid rgba(255, 255, 255, 0.08);
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
        """)

        self.yesButton.setText(tx("select", language))
        self.cancelButton.setText(tx("cancel", language))
        self.choose = self.yesButton

        # Title Row
        title_row = QHBoxLayout()
        self.title_label = TitleLabel(tx("picker_title", language))
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #FFFFFF;")
        self.count_badge = CaptionLabel()
        self.count_badge.setStyleSheet("color: #00B4D8; font-weight: bold; font-size: 13px;")
        title_row.addWidget(self.title_label)
        title_row.addSpacing(10)
        title_row.addWidget(self.count_badge)
        title_row.addStretch(1)
        self.viewLayout.addLayout(title_row)

        # Top Segmented Category Bar
        self.segmented = SegmentedWidget()
        kind_counts = {
            "curated": len(repository.curated_ids),
            "female": len(repository.female_ids),
            "male": len(repository.male_ids),
            "all": len(repository.targets),
        }
        for key in ("curated", "female", "male", "all"):
            label = f"{tx(key, language)} · {kind_counts[key]:,}"
            self.segmented.addItem(routeKey=key, text=label, onClick=lambda _, k=key: self._on_kind_changed(k))
        self.current_kind = "curated"
        self.segmented.setCurrentItem("curated")
        self.viewLayout.addWidget(self.segmented)

        # Search Bar
        search_row = QHBoxLayout()
        self.search = SearchLineEdit()
        self.search.setPlaceholderText(tx("picker_search", language))
        self.search.setClearButtonEnabled(True)
        self.search.setFixedHeight(36)
        self.result_stat = CaptionLabel()
        self.result_stat.setStyleSheet("color: #8E8E93; font-size: 12px;")
        search_row.addWidget(self.search, 1)
        search_row.addWidget(self.result_stat)
        self.viewLayout.addLayout(search_row)

        # Split Body (List + Rich Inspector)
        body = QHBoxLayout()
        body.setSpacing(14)

        # Left List Widget
        self.list = ListWidget()
        self.list.setUniformItemSizes(True)
        self.list.setMinimumWidth(480)
        body.addWidget(self.list, 3)

        # Right Inspector Card (StudioCard - No White Edges)
        self.inspector_card = StudioCard(bg_color=QColor("#202025"), border_color=QColor(255, 255, 255, 20), radius=8)
        detail_layout = QVBoxLayout(self.inspector_card)
        detail_layout.setContentsMargins(18, 16, 18, 16)
        detail_layout.setSpacing(10)

        # Inspector Header
        self.detail_cat_tag = CaptionLabel()
        self.detail_cat_tag.setStyleSheet("""
            background-color: rgba(0, 180, 216, 0.15);
            color: #38BDF8;
            border: 1px solid rgba(0, 180, 216, 0.3);
            border-radius: 4px;
            padding: 2px 8px;
            font-weight: bold;
            font-size: 11px;
        """)
        self.detail_name = SubtitleLabel()
        self.detail_name.setWordWrap(True)
        self.detail_name.setStyleSheet("font-size: 17px; font-weight: bold; color: #FFFFFF;")

        name_box = QVBoxLayout()
        name_box.setSpacing(4)
        name_box.addWidget(self.detail_cat_tag)
        name_box.addWidget(self.detail_name)
        detail_layout.addLayout(name_box)

        detail_layout.addWidget(HorizontalSeparator())

        # Model Specs Section
        specs_header = StrongBodyLabel(tx("model_inspector", language))
        specs_header.setStyleSheet("color: #A1A1AA; font-size: 12px; font-weight: bold;")
        detail_layout.addWidget(specs_header)

        self.specs_grid = QGridLayout()
        self.specs_grid.setHorizontalSpacing(10)
        self.specs_grid.setVerticalSpacing(4)

        self.lbl_main_model = CaptionLabel()
        self.lbl_face_model = CaptionLabel()
        self.lbl_row_key = CaptionLabel()
        self.lbl_voice = CaptionLabel()
        for lbl in (self.lbl_main_model, self.lbl_face_model, self.lbl_row_key, self.lbl_voice):
            lbl.setStyleSheet("color: #E2E2E8; font-size: 12px; font-family: 'Consolas', 'Segoe UI', monospace;")

        self.specs_grid.addWidget(CaptionLabel("MODEL:"), 0, 0)
        self.specs_grid.addWidget(self.lbl_main_model, 0, 1)
        self.specs_grid.addWidget(CaptionLabel("FACE/HAIR:"), 1, 0)
        self.specs_grid.addWidget(self.lbl_face_model, 1, 1)
        self.specs_grid.addWidget(CaptionLabel("ROW / KEY:"), 2, 0)
        self.specs_grid.addWidget(self.lbl_row_key, 2, 1)
        self.specs_grid.addWidget(CaptionLabel("VOICE:"), 3, 0)
        self.specs_grid.addWidget(self.lbl_voice, 3, 1)
        detail_layout.addLayout(self.specs_grid)

        detail_layout.addWidget(HorizontalSeparator())

        # Variants List Section
        self.variants_header = StrongBodyLabel(tx("variants_title", language))
        self.variants_header.setStyleSheet("color: #A1A1AA; font-size: 12px; font-weight: bold;")
        detail_layout.addWidget(self.variants_header)

        self.variants_list = ListWidget()
        detail_layout.addWidget(self.variants_list, 1)

        body.addWidget(self.inspector_card, 2)
        self.viewLayout.addLayout(body, 1)

        # Filter Debounce Timer
        self.filter_timer = QTimer(self)
        self.filter_timer.setSingleShot(True)
        self.filter_timer.setInterval(120)
        self.filter_timer.timeout.connect(self._populate)

        self.search.textChanged.connect(lambda: self.filter_timer.start())
        self.list.currentItemChanged.connect(self._show_details)
        self.list.itemDoubleClicked.connect(lambda _: self._accept())
        self.choose.clicked.connect(self._accept)
        self.cancelButton.clicked.connect(self.reject)

        self._populate()

    def _on_kind_changed(self, kind: str) -> None:
        self.current_kind = kind
        self._populate()

    def _populate(self) -> None:
        kind = self.current_kind or "curated"
        query = self.search.text().strip().lower()
        current = self.selected_id
        self.list.clear()
        selected_item: QListWidgetItem | None = None
        target_ids = self.repository.ids_for_kind(kind)
        total_in_kind = len(target_ids)
        matched_count = 0

        for target_id in target_ids:
            target = self.repository.targets[target_id]
            if query and query not in target["search_text"]:
                continue
            matched_count += 1
            cat, name = parse_label_category_and_name(target["label"], self.language)
            display_text = f"[{cat}] {name}" if cat else name
            model_hint = target.get("model") or ""
            if model_hint:
                item_text = f"{display_text}  ·  {model_hint}"
            else:
                item_text = display_text

            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, target_id)
            item.setToolTip(f"{target['label']}\nModel: {target.get('model') or '—'}\nRow: {target['target_row']} / Key: {target['standard_character']}")
            self.list.addItem(item)
            if target_id == current:
                selected_item = item

        if query:
            self.result_stat.setText(f"{matched_count:,} / {total_in_kind:,}")
        else:
            self.result_stat.setText(f"{total_in_kind:,}")

        if selected_item:
            self.list.setCurrentItem(selected_item)
            self.list.scrollToItem(selected_item)
        elif self.list.count():
            self.list.setCurrentRow(0)
        else:
            self.detail_cat_tag.hide()
            self.detail_name.setText(tx("no_results", self.language))
            self.lbl_main_model.setText("—")
            self.lbl_face_model.setText("—")
            self.lbl_row_key.setText("—")
            self.lbl_voice.setText("—")
            self.variants_list.clear()

        self.choose.setEnabled(self.list.count() > 0)

    def _show_details(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        if not current:
            return
        target_id = current.data(Qt.ItemDataRole.UserRole)
        target = self.repository.targets[target_id]
        cat, name = parse_label_category_and_name(target["label"], self.language)

        if cat:
            self.detail_cat_tag.setText(cat)
            self.detail_cat_tag.show()
        else:
            self.detail_cat_tag.hide()

        self.detail_name.setText(name)
        self.lbl_main_model.setText(target.get("model") or "—")
        face_hair = " / ".join(filter(None, [target.get("face_model"), target.get("hair_model")])) or "—"
        self.lbl_face_model.setText(face_hair)
        self.lbl_row_key.setText(f"{target['target_row']} / {target['standard_character']} (0x{target['standard_character']:X})")
        voice_str = str(target.get("voicer")) if target.get("voicer") is not None else "—"
        self.lbl_voice.setText(f"{voice_str}  ·  ADV {target.get('adv_model_id') or '—'}")

        self.variants_list.clear()
        for variant in target.get("variants", []):
            label = costume_variant_label(variant, self.language)
            self.variants_list.addItem(label)

        if not target.get("variants"):
            self.variants_list.addItem("（默认外观 / Default Only）" if self.language == "zh" else "(Default Only)")

    def _accept(self) -> None:
        item = self.list.currentItem()
        if item:
            self.selected_id = item.data(Qt.ItemDataRole.UserRole)
            self.accept()


# =========================================================================
# Source Card (Slot Editor with Clean StudioCard Base)
# =========================================================================

class SourceCard(StudioCard):
    changed = Signal()

    def __init__(
        self,
        source_id: str,
        repository: DataRepository,
        language: str,
        initial_target: str,
        parent: QWidget | None = None,
        *,
        included: bool = True,
    ) -> None:
        super().__init__(parent, bg_color=QColor("#1E1E24"), border_color=QColor(255, 255, 255, 20), radius=10)
        self.source_id = source_id
        self.repository = repository
        self.language = language
        self.target_id = initial_target if initial_target in repository.targets else repository.curated_ids[0]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 22)
        layout.setSpacing(14)

        # Card Header: Slot Badge + Slot Name + Active Switch
        header = QHBoxLayout()
        header.setSpacing(10)

        source_number = self.repository.source_order.index(self.source_id) + 1
        self.step_badge = CaptionLabel(f"SLOT {source_number:02d}")
        self.step_badge.setStyleSheet("""
            background-color: #00B4D8;
            color: #FFFFFF;
            font-weight: bold;
            font-size: 11px;
            border-radius: 4px;
            padding: 3px 8px;
        """)
        self.title = SubtitleLabel(tx(self.source_id, language))
        self.title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFFFFF;")

        header.addWidget(self.step_badge)
        header.addWidget(self.title)
        header.addStretch(1)

        self.include = CheckBox()
        self.include.setChecked(included)
        self.include.setStyleSheet("font-weight: 600; font-size: 13px; color: #E2E2E8;")
        self.include.toggled.connect(self._on_include_toggled)
        header.addWidget(self.include)
        layout.addLayout(header)

        layout.addWidget(HorizontalSeparator())

        # Hero Target Character Card Box (StudioCard - No White Edges)
        self.target_box = StudioCard(self, bg_color=QColor("#26262D"), border_color=QColor(255, 255, 255, 24), radius=8)
        target_layout = QHBoxLayout(self.target_box)
        target_layout.setContentsMargins(18, 14, 18, 14)
        target_layout.setSpacing(16)

        target_info = QVBoxLayout()
        target_info.setSpacing(4)

        tag_row = QHBoxLayout()
        tag_row.setSpacing(8)
        self.target_category = CaptionLabel()
        self.target_category.setStyleSheet("""
            background-color: rgba(0, 180, 216, 0.2);
            color: #38BDF8;
            border: 1px solid rgba(0, 180, 216, 0.4);
            border-radius: 4px;
            padding: 2px 6px;
            font-weight: bold;
            font-size: 11px;
        """)
        self.target_caption = CaptionLabel(tx("character", language))
        self.target_caption.setStyleSheet("color: #8E8E93; font-size: 11px;")
        tag_row.addWidget(self.target_category)
        tag_row.addWidget(self.target_caption)
        tag_row.addStretch(1)
        target_info.addLayout(tag_row)

        self.target_name = SubtitleLabel()
        self.target_name.setStyleSheet("font-size: 20px; font-weight: bold; color: #FFFFFF;")
        target_info.addWidget(self.target_name)

        self.technical = CaptionLabel()
        self.technical.setStyleSheet("color: #A1A1AA; font-size: 12px; font-family: 'Consolas', 'Segoe UI', monospace;")
        self.technical.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        target_info.addWidget(self.technical)

        target_layout.addLayout(target_info, 1)

        self.choose = PrimaryPushButton(FIF.PEOPLE, tx("choose", language))
        self.choose.setMinimumWidth(160)
        self.choose.setFixedHeight(40)
        target_layout.addWidget(self.choose)

        layout.addWidget(self.target_box)

        # Outfit / Costume Configuration Section
        outfit_group = QVBoxLayout()
        outfit_group.setSpacing(10)

        combos = QGridLayout()
        combos.setHorizontalSpacing(16)
        combos.setVerticalSpacing(10)

        self.mode_caption = StrongBodyLabel()
        self.mode_caption.setStyleSheet("color: #E2E2E8; font-size: 13px;")
        self.variant_caption = StrongBodyLabel()
        self.variant_caption.setStyleSheet("color: #E2E2E8; font-size: 13px;")

        self.mode = ComboBox()
        self.variant = ComboBox()
        self.mode.setFixedHeight(36)
        self.variant.setFixedHeight(36)
        self.mode.setMinimumWidth(380)

        combos.addWidget(self.mode_caption, 0, 0)
        combos.addWidget(self.mode, 0, 1)
        combos.addWidget(self.variant_caption, 1, 0)
        combos.addWidget(self.variant, 1, 1)
        combos.setColumnStretch(1, 1)
        outfit_group.addLayout(combos)

        self.variant_detail = CaptionLabel()
        self.variant_detail.setStyleSheet("color: #38BDF8; font-size: 12px; font-family: 'Consolas', 'Segoe UI', monospace;")
        self.variant_detail.setWordWrap(True)
        outfit_group.addWidget(self.variant_detail)

        self.outfit_note = CaptionLabel()
        self.outfit_note.setStyleSheet("color: #8E8E93; font-size: 12px;")
        self.outfit_note.setWordWrap(True)
        outfit_group.addWidget(self.outfit_note)

        layout.addLayout(outfit_group)
        layout.addStretch(1)

        self.choose.clicked.connect(self._choose_target)
        self.mode.currentIndexChanged.connect(self._mode_changed)
        self.variant.currentIndexChanged.connect(self._refresh_variant_detail)
        self.variant.currentIndexChanged.connect(self.changed)

        self.retranslate(language)
        self._set_target(self.target_id)

    def _on_include_toggled(self) -> None:
        self.changed.emit()

    def retranslate(self, language: str) -> None:
        self.language = language
        self.title.setText(tx(self.source_id, language))
        self.target_caption.setText(tx("character", language))
        self.mode_caption.setText(tx("outfit", language))
        self.variant_caption.setText(tx("variant", language))
        self.choose.setText(tx("choose", language))
        self.include.setText(tx("slot_active", language))

        source_number = self.repository.source_order.index(self.source_id) + 1
        self.step_badge.setText(f"SLOT {source_number:02d}")

        self.outfit_note.setText(
            "Context matched follows in-game costume scenes (roam / battle / story). Fixed outfit forces a specific variant row."
            if language == "en"
            else "「场景匹配」会全自动跟随游戏探索、战斗、过场等服装场景；「固定服装」会把模型与身份映射强行锁定至该 variant。"
        )
        current_mode = self.mode.currentData()
        self.mode.blockSignals(True)
        self.mode.clear()
        for key, mode_id in (
            ("context", "context_matched"),
            ("default", "default_only"),
            ("fixed", "fixed_variant"),
        ):
            self.mode.addItem(tx(key, language), userData=mode_id)
        index = self.mode.findData(current_mode or "context_matched")
        self.mode.setCurrentIndex(max(0, index))
        self.mode.blockSignals(False)
        self._refresh_target_text()
        self._refresh_variants()

    def set_slot_active(self, active: bool) -> None:
        self.include.setChecked(active)

    def is_included(self) -> bool:
        return self.include.isChecked()

    def _choose_target(self) -> None:
        dialog = TargetPickerDialog(
            self.repository, self.language, self.target_id, self.window()
        )
        if dialog.exec() == TargetPickerDialog.DialogCode.Accepted and dialog.selected_id:
            self._set_target(dialog.selected_id)

    def _set_target(self, target_id: str) -> None:
        self.target_id = target_id
        target = self.repository.targets[target_id]
        if target["fixed_npc"]:
            self.mode.setCurrentIndex(self.mode.findData("fixed_variant"))
            self.mode.setEnabled(False)
        else:
            self.mode.setEnabled(True)
        self._refresh_target_text()
        self._refresh_variants()
        self.changed.emit()

    def set_target(self, target_id: str) -> None:
        if target_id in self.repository.targets:
            self._set_target(target_id)

    def _refresh_target_text(self) -> None:
        target = self.repository.targets[self.target_id]
        cat, name = parse_label_category_and_name(target["label"], self.language)
        if cat:
            self.target_category.setText(cat)
            self.target_category.show()
        else:
            self.target_category.hide()

        self.target_name.setText(name)
        voice = str(target.get("voicer")) if target.get("voicer") is not None else "—"
        model_str = target.get("model") or "—"
        self.technical.setText(
            f"MODEL: {model_str}    ·    ROW: {target['target_row']}    ·    KEY: {target['standard_character']} (0x{target['standard_character']:X})    ·    VOICE: {voice}"
        )

    def _refresh_variants(self) -> None:
        target = self.repository.targets[self.target_id]
        current = self.variant.currentData()
        self.variant.blockSignals(True)
        self.variant.clear()
        for index, variant in enumerate(target["variants"]):
            self.variant.addItem(
                costume_variant_label(variant, self.language), userData=index
            )
        if current is not None and 0 <= int(current) < self.variant.count():
            self.variant.setCurrentIndex(int(current))
        elif self.variant.count():
            self.variant.setCurrentIndex(0)
        self.variant.blockSignals(False)
        fixed = self.mode.currentData() == "fixed_variant"
        self.variant.setVisible(fixed)
        self.variant_caption.setVisible(fixed)
        self.variant.setEnabled(fixed)
        self.variant_detail.setVisible(fixed)
        self._refresh_variant_detail()

    def _refresh_variant_detail(self, _index: int | None = None) -> None:
        target = self.repository.targets[self.target_id]
        index = self.variant.currentData()
        if index is None or not 0 <= int(index) < len(target["variants"]):
            self.variant_detail.clear()
            self.variant.setToolTip("")
            return
        variant = target["variants"][int(index)]
        self.variant_detail.setText(
            f"MODEL: {variant.get('model') or '—'}    ·    KEY: {variant['variant_key']}    ·    Character Row: {variant['character_row']}"
        )
        self.variant.setToolTip(variant["label"])

    def _mode_changed(self) -> None:
        self._refresh_variants()
        self.changed.emit()

    def selection(self) -> SlotSelection:
        mode = self.mode.currentData() or "context_matched"
        variant = self.variant.currentData() if mode == "fixed_variant" else None
        return SlotSelection(self.target_id, mode, int(variant) if variant is not None else None)


# =========================================================================
# Restore Close Dialog
# =========================================================================

class RestoreCloseDialog(MessageBoxBase):
    def __init__(self, language: str, body: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.choice = "original"
        self.widget.setMinimumWidth(840)
        self.setMaskColor(QColor(0, 0, 0, 160))
        self.widget.setStyleSheet("""
            QFrame#widget {
                background-color: #1A1A1E;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 10px;
            }
            QFrame#buttonGroup {
                background-color: #222228;
                border-top: 1px solid rgba(255, 255, 255, 0.08);
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
        """)

        title = SubtitleLabel(tx("close_title", language))
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFFFFF;")
        content = BodyLabel(body)
        content.setStyleSheet("font-size: 13px; color: #D0D0D8; line-height: 1.4;")
        content.setWordWrap(True)
        self.viewLayout.addWidget(title)
        self.viewLayout.addWidget(content)

        self.yesButton.setText(tx("restore_exit", language))
        self.cancelButton.setText(tx("cancel", language))
        self.sessionButton = PushButton(tx("session_exit", language))
        self.keepButton = PushButton(tx("keep_exit", language))
        self.buttonLayout.insertWidget(1, self.sessionButton)
        self.buttonLayout.insertWidget(2, self.keepButton)

        self.sessionButton.clicked.connect(self._choose_session)
        self.keepButton.clicked.connect(self._choose_keep)

    def _choose_session(self) -> None:
        self.choice = "session"
        self.accept()

    def _choose_keep(self) -> None:
        self.choice = "keep"
        self.accept()


# =========================================================================
# Main Window (Infinite Wealth Neon & Dark Glass Studio)
# =========================================================================

class MainWindow(FluentWindow):
    def __init__(
        self,
        repository: DataRepository,
        engine: TrainerEngine,
        preview: bool = False,
    ) -> None:
        super().__init__()
        self.repository = repository
        self.engine = engine
        self.language = "zh"
        self.preview = preview
        self.busy = False
        self.details_visible = False

        self.setWindowTitle(tx("app_title", self.language))
        self.setWindowIcon(make_app_icon())
        self.resize(1160, 850)
        self.setMinimumSize(960, 720)
        self.setCustomBackgroundColor(QColor("#18181C"), QColor("#141418"))
        self.setMicaEffectEnabled(True)
        if QApplication.platformName() == "offscreen":
            self.setMicaEffectEnabled(False)

        self._build_ui()
        self._retranslate()
        self._mode_changed()

        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(2200)
        self.poll_timer.timeout.connect(self._connection_tick)
        if preview:
            self._set_state("ready", "READY · 多角色独立配置预览")
            self._update_db_details({
                "pid": 24816,
                "connected": True,
                "active": False,
                "backup": False,
                "backup_is_vanilla": None,
                "character_base": 0x252B60000,
                "costume_base": 0x1D38115C0,
                "states": {
                    source_id: "original"
                    for source_id in self.repository.source_order
                },
                "message": "Preview Mode",
            })
        else:
            self.poll_timer.start()
            QTimer.singleShot(180, self._connection_tick)

    def _build_ui(self) -> None:
        self.interface = QWidget()
        self.interface.setObjectName("characterStudioInterface")
        self.navigation_item = self.addSubInterface(
            self.interface, FIF.GAME, "Character Studio", isTransparent=False
        )
        self.navigationInterface.panel.setMenuButtonVisible(False)
        self.navigationInterface.panel.setReturnButtonVisible(False)
        self.navigationInterface.hide()

        interface_layout = QVBoxLayout(self.interface)
        interface_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_area = SmoothScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        interface_layout.addWidget(self.scroll_area)

        content = QWidget()
        self.scroll_area.setWidget(content)
        self.scroll_area.enableTransparentBackground()

        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 22, 28, 26)
        layout.setSpacing(14)

        # Hero Header Card (StudioCard - Clean antialiasing, no white edges)
        hero_card = StudioCard(bg_color=QColor("#1E1E24"), border_color=QColor(255, 255, 255, 20), radius=10)
        hero_layout = QHBoxLayout(hero_card)
        hero_layout.setContentsMargins(20, 16, 20, 16)
        hero_layout.setSpacing(16)

        titles = QVBoxLayout()
        titles.setSpacing(4)

        title_top = QHBoxLayout()
        title_top.setSpacing(10)
        self.app_title = TitleLabel(tx("app_title", self.language))
        self.app_title.setStyleSheet("font-size: 22px; font-weight: bold; color: #FFFFFF;")
        self.edition_badge = CaptionLabel(tx("app_badge", self.language))
        self.edition_badge.setStyleSheet("""
            background-color: rgba(245, 158, 11, 0.2);
            color: #FBBF24;
            border: 1px solid rgba(245, 158, 11, 0.4);
            border-radius: 4px;
            padding: 2px 8px;
            font-weight: bold;
            font-size: 11px;
        """)
        title_top.addWidget(self.app_title)
        title_top.addWidget(self.edition_badge)
        title_top.addStretch(1)
        titles.addLayout(title_top)

        self.subtitle = CaptionLabel(tx("subtitle", self.language))
        self.subtitle.setStyleSheet("color: #8E8E93; font-size: 12px;")
        titles.addWidget(self.subtitle)
        hero_layout.addLayout(titles, 1)

        status_column = QVBoxLayout()
        status_column.setSpacing(6)
        status_top = QHBoxLayout()
        status_top.setSpacing(8)

        self.status = InfoBadge()
        self.status.setLevel(InfoLevel.ATTENTION)
        self.status.setStyleSheet("font-weight: bold; padding: 4px 10px; font-size: 12px;")

        self.reconnect_top_button = TransparentPushButton(FIF.SYNC, tx("reconnect", self.language))
        self.reconnect_top_button.clicked.connect(self._connect_now)

        self.language_button = PushButton("EN")
        self.language_button.setFixedWidth(64)
        self.language_button.setFixedHeight(32)
        self.language_button.clicked.connect(self._toggle_language)

        status_top.addStretch(1)
        status_top.addWidget(self.reconnect_top_button)
        status_top.addWidget(self.status)
        status_top.addWidget(self.language_button)
        status_column.addLayout(status_top)

        self.message = CaptionLabel()
        self.message.setStyleSheet("color: #A1A1AA; font-size: 12px;")
        self.message.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.message.setMaximumWidth(460)
        status_column.addWidget(self.message)

        hero_layout.addLayout(status_column)
        layout.addWidget(hero_card)

        # Batch Operations & Summary Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        self.select_all_btn = PushButton(FIF.CHECKBOX, tx("select_all", self.language))
        self.deselect_all_btn = PushButton(FIF.CANCEL, tx("deselect_all", self.language))
        self.reset_defaults_btn = PushButton(FIF.HISTORY, tx("reset_defaults", self.language))
        self.presets_btn = PrimaryDropDownPushButton(FIF.TILES, tx("presets", self.language))

        # Setup Presets Menu
        self.presets_menu = RoundMenu(parent=self)
        self.action_preset_default = Action(FIF.ACCEPT, tx("preset_default", self.language))
        self.action_preset_all = Action(FIF.PLAY, tx("preset_all_on", self.language))
        self.action_preset_dual = Action(FIF.PEOPLE, tx("preset_dual", self.language))

        self.presets_menu.addAction(self.action_preset_default)
        self.presets_menu.addAction(self.action_preset_all)
        self.presets_menu.addAction(self.action_preset_dual)
        self.presets_btn.setMenu(self.presets_menu)

        for btn in (self.select_all_btn, self.deselect_all_btn, self.reset_defaults_btn):
            btn.setFixedHeight(34)
            btn.setMinimumWidth(110)
        self.presets_btn.setFixedHeight(34)
        self.presets_btn.setMinimumWidth(130)

        toolbar.addWidget(self.select_all_btn)
        toolbar.addWidget(self.deselect_all_btn)
        toolbar.addWidget(self.reset_defaults_btn)
        toolbar.addWidget(self.presets_btn)
        toolbar.addStretch(1)

        self.slot_summary_badge = CaptionLabel()
        self.slot_summary_badge.setStyleSheet("""
            background-color: #23232A;
            color: #38BDF8;
            border: 1px solid rgba(0, 180, 216, 0.3);
            border-radius: 6px;
            padding: 5px 12px;
            font-weight: bold;
            font-size: 12px;
        """)
        toolbar.addWidget(self.slot_summary_badge)
        layout.addLayout(toolbar)

        # 10-Slot Navigation Pivot Bar
        self.slot_pivot = Pivot()
        self.pivot_items: dict[str, Any] = {}
        self.cards: dict[str, SourceCard] = {}
        self.slot_scroll = SmoothScrollArea()
        self.slot_scroll.setWidgetResizable(False)
        self.slot_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.slot_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.slot_scroll.setWidget(self.slot_pivot)
        self.slot_scroll.setFixedHeight(54)
        self.slot_scroll.setStyleSheet("""
            SmoothScrollArea {
                background: transparent;
                border: none;
            }
        """)
        layout.addWidget(self.slot_scroll)

        # Stacked Editor for 10 Slots
        self.editor_stack = QStackedWidget()
        self.editor_stack.setMinimumHeight(380)

        default_targets = {
            "ichiban": "chitose",
            "kiryu": "kiryu",
            "nanba": "chitose",
            "adachi": "joongi",
            "chou": "tomizawa",
            "jyungi": "adachi",
            "tomizawa": "zhao",
            "saeko": "nanba",
            "chitose": "seonhee",
            "sonhi": "chitose",
        }
        for index, source_id in enumerate(self.repository.source_order):
            route_key = f"{source_id}Slot"
            self.pivot_items[source_id] = self.slot_pivot.addItem(
                routeKey=route_key,
                text=tx(source_id, self.language),
                onClick=lambda checked=False, card_index=index: (
                    self.editor_stack.setCurrentIndex(card_index)
                ),
            )
            card = SourceCard(
                source_id,
                self.repository,
                self.language,
                default_targets.get(source_id, self.repository.curated_ids[0]),
                included=(source_id == "ichiban"),
            )
            self.cards[source_id] = card
            self.editor_stack.addWidget(card)
        self.slot_pivot.setCurrentItem("ichibanSlot")
        layout.addWidget(self.editor_stack, 1)

        # Bottom Action Bar (StudioCard - Clean antialiasing, no white edges)
        action_card = StudioCard(bg_color=QColor("#1E1E24"), border_color=QColor(255, 255, 255, 20), radius=10)
        action_layout = QHBoxLayout(action_card)
        action_layout.setContentsMargins(18, 14, 18, 14)
        action_layout.setSpacing(14)

        action_copy = QVBoxLayout()
        action_copy.setSpacing(3)
        self.apply_hint = CaptionLabel(tx("apply_hint", self.language))
        self.safety = CaptionLabel(tx("safety", self.language))
        self.apply_hint.setStyleSheet("color: #E2E2E8; font-size: 12px; font-weight: 500;")
        self.safety.setStyleSheet("color: #8E8E93; font-size: 11px;")
        self.apply_hint.setWordWrap(True)
        self.safety.setWordWrap(True)
        action_copy.addWidget(self.apply_hint)
        action_copy.addWidget(self.safety)
        action_layout.addLayout(action_copy, 1)

        self.restore_button = PushButton(FIF.CANCEL, tx("restore", self.language))
        self.restore_button.setMinimumWidth(190)
        self.restore_button.setFixedHeight(42)

        self.apply_button = PrimaryPushButton(FIF.ACCEPT, tx("apply", self.language))
        self.apply_button.setMinimumWidth(240)
        self.apply_button.setFixedHeight(42)
        action_layout.addWidget(self.restore_button)
        action_layout.addWidget(self.apply_button)
        layout.addWidget(action_card)

        # Diagnostics Toggle Button
        self.details_button = PushButton(FIF.SETTING, tx("details", self.language))
        self.details_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.details_button.setFixedHeight(34)
        layout.addWidget(self.details_button)

        # Collapsible Diagnostics & Power Tools Panel (StudioCard - Clean antialiasing, no white edges)
        self.details_panel = StudioCard(bg_color=QColor("#19191E"), border_color=QColor(255, 255, 255, 20), radius=10)
        detail_layout = QVBoxLayout(self.details_panel)
        detail_layout.setContentsMargins(18, 14, 18, 14)
        detail_layout.setSpacing(12)

        # Custom Key Inject Section
        custom_row = QHBoxLayout()
        custom_row.setSpacing(10)
        self.custom_title = StrongBodyLabel(tx("custom", self.language))
        self.custom_title.setStyleSheet("color: #E2E2E8; font-size: 12px;")
        self.custom_input = LineEdit()
        self.custom_input.setFixedHeight(32)
        self.custom_input.setPlaceholderText(tx("custom_hint", self.language))
        self.custom_slot = ComboBox()
        self.custom_slot.setFixedHeight(32)
        self.custom_slot.setMinimumWidth(110)
        self.custom_use_button = PushButton(FIF.ADD, tx("use_custom", self.language))
        self.custom_use_button.setFixedHeight(32)

        custom_row.addWidget(self.custom_title)
        custom_row.addWidget(self.custom_input, 1)
        custom_row.addWidget(self.custom_slot)
        custom_row.addWidget(self.custom_use_button)
        detail_layout.addLayout(custom_row)

        detail_layout.addWidget(HorizontalSeparator())

        # Memory & DB Diagnostics
        recovery = QHBoxLayout()
        recovery.setSpacing(12)
        recovery_text = QVBoxLayout()
        recovery_text.setSpacing(4)
        self.db_info = BodyLabel(tx("db_wait", self.language))
        self.db_info.setStyleSheet("color: #38BDF8; font-family: 'Consolas', 'Segoe UI', monospace; font-size: 12px;")
        self.db_info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.vanilla_hint = CaptionLabel(tx("vanilla_hint", self.language))
        self.vanilla_hint.setStyleSheet("color: #8E8E93; font-size: 11px;")
        self.vanilla_hint.setWordWrap(True)
        recovery_text.addWidget(self.db_info)
        recovery_text.addWidget(self.vanilla_hint)

        self.reconnect_button = PushButton(FIF.SYNC, tx("reconnect", self.language))
        self.vanilla_button = PushButton(FIF.HISTORY, tx("vanilla", self.language))
        self.reconnect_button.setFixedHeight(34)
        self.vanilla_button.setFixedHeight(34)

        recovery.addLayout(recovery_text, 1)
        recovery.addWidget(self.reconnect_button)
        recovery.addWidget(self.vanilla_button)
        detail_layout.addLayout(recovery)

        self.details_panel.setVisible(False)
        layout.addWidget(self.details_panel)

        # Wire Signals
        self.select_all_btn.clicked.connect(self._select_all_slots)
        self.deselect_all_btn.clicked.connect(self._deselect_all_slots)
        self.reset_defaults_btn.clicked.connect(self._reset_default_mappings)
        self.action_preset_default.triggered.connect(self._reset_default_mappings)
        self.action_preset_all.triggered.connect(self._select_all_slots)
        self.action_preset_dual.triggered.connect(self._preset_dual_slots)

        self.apply_button.clicked.connect(self._apply)
        self.restore_button.clicked.connect(self._force_vanilla)
        self.reconnect_button.clicked.connect(self._connect_now)
        self.details_button.clicked.connect(self._toggle_details)
        self.custom_use_button.clicked.connect(self._resolve_custom)
        self.vanilla_button.clicked.connect(self._restore)

        for card in self.cards.values():
            card.changed.connect(self._mode_changed)

    def _select_all_slots(self) -> None:
        for card in self.cards.values():
            card.set_slot_active(True)
        self._mode_changed()

    def _deselect_all_slots(self) -> None:
        for card in self.cards.values():
            card.set_slot_active(False)
        self._mode_changed()

    def _preset_dual_slots(self) -> None:
        for source_id, card in self.cards.items():
            card.set_slot_active(source_id in ("ichiban", "kiryu"))
        self._mode_changed()

    def _reset_default_mappings(self) -> None:
        default_targets = {
            "ichiban": "chitose",
            "kiryu": "kiryu",
            "nanba": "chitose",
            "adachi": "joongi",
            "chou": "tomizawa",
            "jyungi": "adachi",
            "tomizawa": "zhao",
            "saeko": "nanba",
            "chitose": "seonhee",
            "sonhi": "chitose",
        }
        for source_id, target_id in default_targets.items():
            if source_id in self.cards:
                self.cards[source_id].set_target(target_id)
                self.cards[source_id].set_slot_active(source_id == "ichiban")
        self._mode_changed()

    def _retranslate(self) -> None:
        lang = self.language
        self.setWindowTitle(tx("app_title", lang))
        self.app_title.setText(tx("app_title", lang))
        self.edition_badge.setText(tx("app_badge", lang))
        self.subtitle.setText(tx("subtitle", lang))
        self.navigation_item.setText("Character Studio" if lang == "en" else "角色模型工坊")

        self.select_all_btn.setText(tx("select_all", lang))
        self.deselect_all_btn.setText(tx("deselect_all", lang))
        self.reset_defaults_btn.setText(tx("reset_defaults", lang))
        self.presets_btn.setText(tx("presets", lang))
        self.action_preset_default.setText(tx("preset_default", lang))
        self.action_preset_all.setText(tx("preset_all_on", lang))
        self.action_preset_dual.setText(tx("preset_dual", lang))

        self.apply_hint.setText(tx("apply_hint", lang))
        self.safety.setText(tx("safety", lang))
        self.restore_button.setText(tx("restore", lang))
        self.reconnect_button.setText(tx("reconnect", lang))
        self.reconnect_top_button.setText(tx("reconnect", lang))
        self.details_button.setText(tx("hide_details" if self.details_visible else "details", lang))
        self.custom_title.setText(tx("custom", lang))
        self.custom_input.setPlaceholderText(tx("custom_hint", lang))

        current_slot = self.custom_slot.currentData()
        self.custom_slot.blockSignals(True)
        self.custom_slot.clear()
        for source_id in self.repository.source_order:
            self.custom_slot.addItem(tx(source_id, lang), userData=source_id)
        if current_slot:
            index = self.custom_slot.findData(current_slot)
            if index >= 0:
                self.custom_slot.setCurrentIndex(index)
        self.custom_slot.blockSignals(False)

        self.custom_use_button.setText(tx("use_custom", lang))
        self.vanilla_button.setText(tx("vanilla", lang))
        self.vanilla_hint.setText(tx("vanilla_hint", lang))
        self.language_button.setText("中" if lang == "en" else "EN")

        for source_id in self.repository.source_order:
            self.cards[source_id].retranslate(lang)

        self._refresh_slot_tabs()
        self._mode_changed()
        if not self.engine.connected and not self.preview:
            self._set_state("waiting", tx("waiting", lang))

    def _refresh_slot_tabs(self) -> None:
        lang = self.language
        for source_id in self.repository.source_order:
            card = self.cards[source_id]
            target = self.repository.targets[card.target_id]
            cat, target_name = parse_label_category_and_name(target["label"], lang)
            slot_name = tx(source_id, lang)
            active_mark = "●" if card.is_included() else "○"
            tab_text = f"{active_mark} {slot_name} · {target_name}"
            self.pivot_items[source_id].setText(tab_text)

        self.slot_pivot.setFixedHeight(54)
        natural_width = sum(item.sizeHint().width() for item in self.slot_pivot.items.values())
        self.slot_pivot.setMinimumWidth(max(320, natural_width + 40))
        self.slot_pivot.setMaximumWidth(max(320, natural_width + 40))

    def _toggle_language(self) -> None:
        self.language = "en" if self.language == "zh" else "zh"
        self._retranslate()

    def _mode_changed(self) -> None:
        count = sum(card.is_included() for card in self.cards.values())
        if self.language == "en":
            noun = "Slot" if count == 1 else "Slots"
            self.apply_button.setText(f"Apply {count} {noun}")
            self.slot_summary_badge.setText(f"{count}/10 Slots Active")
        else:
            self.apply_button.setText(f"应用 {count} 个角色槽位")
            self.slot_summary_badge.setText(f"已选 {count}/10 个槽位")

        self.apply_button.setEnabled(not self.busy and count > 0)
        self._refresh_slot_tabs()

    def _set_state(self, state: str, message: str) -> None:
        levels = {
            "waiting": InfoLevel.ATTENTION,
            "scanning": InfoLevel.INFOAMTION,
            "ready": InfoLevel.SUCCESS,
            "applied": InfoLevel.SUCCESS,
            "error": InfoLevel.ERROR,
        }
        key = state if state in levels else "error"
        self.status.setLevel(levels[key])
        self.status.setText(tx(key, self.language))
        self.message.setText(message)
        self.message.setToolTip(message)

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        self.restore_button.setEnabled(not busy)
        self.reconnect_button.setEnabled(not busy)
        self.reconnect_top_button.setEnabled(not busy)
        self.vanilla_button.setEnabled(not busy)
        self.custom_use_button.setEnabled(not busy)
        self.select_all_btn.setEnabled(not busy)
        self.deselect_all_btn.setEnabled(not busy)
        self.reset_defaults_btn.setEnabled(not busy)
        self.presets_btn.setEnabled(not busy)
        if busy:
            self.apply_button.setEnabled(False)
        else:
            self._mode_changed()

    def _run(self, function: Callable[[], Any], callback: Callable[[Any], None]) -> None:
        if self.busy:
            return
        self._set_busy(True)
        QTimer.singleShot(20, lambda: self._execute_task(function, callback))

    def _execute_task(self, function: Callable[[], Any], callback: Callable[[Any], None]) -> None:
        try:
            callback(function())
        except Exception:
            self._task_error(traceback.format_exc())
        finally:
            self._set_busy(False)

    def _task_error(self, trace: str) -> None:
        err_msg = trace.splitlines()[-1] if trace else "Unexpected error"
        self._set_state("error", err_msg)
        InfoBar.error(
            title=tx("error", self.language),
            content=err_msg,
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=4000,
            parent=self,
        )

    def _connection_tick(self) -> None:
        if self.busy or self.preview:
            return
        lifecycle = self.engine.refresh_process_lifecycle()
        if lifecycle.ok:
            self._set_state("applied" if self.engine.active else "ready", self.engine.last_message)
            self._update_db_details(self.engine.status_snapshot())
            return
        if not self.engine.process_is_running():
            self._set_state("waiting", tx("waiting", self.language))
            self._update_db_details(self.engine.status_snapshot())
            return
        self._connect_now()

    def _connect_now(self) -> None:
        if self.busy:
            return
        self._set_state("scanning", tx("scanning", self.language))
        self._run(self.engine.validate_all, self._connect_finished)

    def _connect_finished(self, result: OperationResult) -> None:
        self._set_state("ready" if result.ok else "error", result.message)
        self._update_db_details(self.engine.status_snapshot())
        if result.ok:
            InfoBar.success(
                title=tx("ready", self.language),
                content=result.message,
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2500,
                parent=self,
            )
        else:
            InfoBar.warning(
                title=tx("error", self.language),
                content=result.message,
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=4000,
                parent=self,
            )

    def _collect_slots(self) -> dict[str, SlotSelection]:
        slots: dict[str, SlotSelection] = {}
        for source_id, card in self.cards.items():
            if card.is_included():
                slots[source_id] = card.selection()
        return slots

    def _apply(self) -> None:
        slots = self._collect_slots()
        self._set_state("scanning", tx("scanning", self.language))
        self._run(lambda: self.engine.apply(slots), self._operation_finished)

    def _restore(self) -> None:
        self._run(lambda: self.engine.restore("Restore button"), self._operation_finished)

    def _operation_finished(self, result: OperationResult) -> None:
        state = "applied" if result.ok and self.engine.active else ("ready" if result.ok else "error")
        self._set_state(state, result.message)
        self._update_db_details(self.engine.status_snapshot())
        if result.ok:
            InfoBar.success(
                title=tx("applied", self.language) if self.engine.active else tx("ready", self.language),
                content=result.message,
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )
        else:
            InfoBar.error(
                title=tx("error", self.language),
                content=result.message,
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=4500,
                parent=self,
            )

    def _toggle_details(self) -> None:
        self.details_visible = not self.details_visible
        self.details_panel.setVisible(self.details_visible)
        self.details_button.setText(tx("hide_details" if self.details_visible else "details", self.language))
        if self.details_visible:
            self._update_db_details(self.engine.status_snapshot())

    def _update_db_details(self, status: dict[str, Any]) -> None:
        if status.get("connected"):
            char_base = f"0x{status['character_base']:X}" if status.get('character_base') else "—"
            cost_base = f"0x{status['costume_base']:X}" if status.get('costume_base') else "—"
            self.db_info.setText(
                f"PID: {status['pid']}    ·    Character Base: {char_base}    ·    Costume Base: {cost_base}\n"
                + "  ·  ".join(
                    f"{tx(source_id, self.language)}: {status.get('states', {}).get(source_id, '—')}"
                    for source_id in self.repository.source_order
                )
                + "\n"
                f"First Backup Snapshot: {'Saved (OK)' if status.get('backup') else 'Not created yet'}"
            )
        else:
            self.db_info.setText(tx("db_wait", self.language))

    def _resolve_custom(self) -> None:
        value = self.custom_input.text().strip()
        source_id = self.custom_slot.currentData()
        if not source_id:
            return

        def done(payload: tuple[OperationResult, dict[str, Any] | None]) -> None:
            result, target = payload
            if result.ok and target:
                card = self.cards[source_id]
                card.set_target(target["id"])
                self._set_state("ready", result.message)
                InfoBar.success(
                    title=tx("ready", self.language),
                    content=result.message,
                    orient=Qt.Orientation.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2500,
                    parent=self,
                )
            else:
                self._set_state("error", result.message)
                InfoBar.error(
                    title=tx("error", self.language),
                    content=result.message,
                    orient=Qt.Orientation.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=4000,
                    parent=self,
                )

        self._run(lambda: self.engine.prepare_custom_target(value), done)

    def _force_vanilla(self) -> None:
        box = MessageBox(
            tx("original_confirm_title", self.language),
            tx("original_confirm_body", self.language),
            self,
        )
        box.yesButton.setText(tx("restore", self.language))
        box.cancelButton.setText(tx("cancel", self.language))
        if box.exec() != MessageBox.DialogCode.Accepted:
            return
        self._run(
            lambda: self.engine.restore_game_original("Restore original button"),
            self._operation_finished,
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.preview or not self.engine.active:
            self.engine.close()
            event.accept()
            return
        body_key = (
            "close_body_modified_backup"
            if self.engine.backup_is_vanilla() is False
            else "close_body"
        )
        box = RestoreCloseDialog(self.language, tx(body_key, self.language), self)
        if box.exec() != RestoreCloseDialog.DialogCode.Accepted:
            event.ignore()
            return
        if box.choice == "original":
            result = self.engine.restore_game_original("window close: original")
            if not result.ok:
                error_box = MessageBox(tx("error", self.language), result.message, self)
                error_box.cancelButton.hide()
                error_box.exec()
                event.ignore()
                return
        elif box.choice == "session":
            result = self.engine.restore("window close: launch state")
            if not result.ok:
                error_box = MessageBox(tx("error", self.language), result.message, self)
                error_box.cancelButton.hide()
                error_box.exec()
                event.ignore()
                return
        elif box.choice != "keep":
            event.ignore()
            return
        self.engine.close()
        event.accept()


# =========================================================================
# Application Styling & High-DPI Font Configuration
# =========================================================================

def apply_application_style(app: QApplication) -> None:
    setTheme(Theme.DARK)
    setThemeColor(QColor("#00B4D8"))

    # Register High-Quality Fonts
    font_paths = [
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\msyhbd.ttc",
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf",
    ]
    for path in font_paths:
        if os.path.isfile(path):
            QFontDatabase.addApplicationFont(path)

    app_font = QFont("Microsoft YaHei UI", 9)
    app_font.setFamilies(["Microsoft YaHei UI", "Segoe UI", "PingFang SC", "sans-serif"])
    app.setFont(app_font)
