from __future__ import annotations

import os
import re
import traceback
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt, QTimer, Signal, QSize
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
    "picker_title": ("Character Finder", "角色查找器"),
    "picker_search": ("AND search: name, alias, model, face, hair, key, 0x key, row...", "多关键词 AND 搜索：名字、别名、模型、脸、发型、Key、0x Key、行..."),
    "favorites": ("Favorites", "收藏"),
    "same_face": ("Same Face", "相同脸型"),
    "same_hair": ("Same Hair", "相同发型"),
    "same_model": ("Same Model", "相同模型"),
    "clear_filter": ("Clear Filter", "清除筛选"),
    "alias": ("Alias", "用户别名"),
    "edit_alias": ("Add/Edit Alias", "添加 / 编辑别名"),
    "alias_hint": ("Local label only; original IDs and model codes stay visible.", "仅保存为本地别名；原始 ID 与模型代码仍然保留。"),
    "alias_placeholder": ("e.g. Karen UFO / Blue dress girl", "例如 Karen UFO / 蓝裙女孩"),
    "delete_alias": ("Delete Alias", "删除别名"),
    "save_alias": ("Save Alias", "保存别名"),
    "favorite_add": ("☆ Add Favorite", "☆ 加入收藏"),
    "favorite_remove": ("★ Remove Favorite", "★ 取消收藏"),
    "previous": ("Previous", "上一个"),
    "next": ("Next", "下一个"),
    "candidate_position": ("Candidate {current} / {total}", "候选 {current} / {total}"),
    "result_count": ("{matched} / {total} matches", "匹配 {matched} / {total}"),
    "similar_filter": ("{field}: {value}", "{field}：{value}"),
    "finder_browse_hint": ("Browsing only selects a candidate. Use the slot Apply button to change the game.", "浏览只选择候选；需回到槽位点击应用，才会修改游戏。"),
    "anonymous_female": ("Female NPC #{key}", "女性 NPC #{key}"),
    "anonymous_male": ("Male NPC #{key}", "男性 NPC #{key}"),
    "field_model": ("MODEL", "模型"),
    "field_face": ("FACE", "脸型"),
    "field_hair": ("HAIR", "发型"),
    "field_row_key": ("ROW / KEY", "行 / KEY"),
    "field_voice": ("VOICE / ADV", "语音 / ADV"),
    "field_id": ("TARGET ID", "目标 ID"),
    "field_region": ("REGION", "地区"),
    "field_group": ("CATALOG GROUP", "目录分组"),
    "default_variant": ("Default appearance", "默认外观"),
    "finder_save_error": ("Could not save local Finder preferences: {error}", "无法保存本地查找器配置：{error}"),
    "finder_load_error": ("Local Finder configuration could not be read; started with empty preferences.", "本地查找器配置无法读取，已使用空配置启动。"),
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

class AliasDialog(MessageBoxBase):
    def __init__(self, alias: str, language: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.title = SubtitleLabel(tx("edit_alias", language))
        self.help = BodyLabel(tx("alias_hint", language))
        self.help.setWordWrap(True)
        self.editor = LineEdit()
        self.editor.setMaxLength(256)
        self.editor.setPlaceholderText(tx("alias_placeholder", language))
        self.editor.setText(alias)
        self.delete_button = PushButton(tx("delete_alias", language))
        self.delete_button.clicked.connect(self._delete)
        self.viewLayout.addWidget(self.title)
        self.viewLayout.addWidget(self.help)
        self.viewLayout.addWidget(self.editor)
        self.viewLayout.addWidget(self.delete_button)
        self.yesButton.setText(tx("save_alias", language))
        self.cancelButton.setText(tx("cancel", language))
        self.widget.setMinimumWidth(360)

    def _delete(self) -> None:
        self.editor.clear()
        self.accept()


class TargetPickerDialog(MessageBoxBase):
    """Character Finder: browsing and user overlays only; no game writes."""
    def __init__(self, repository: DataRepository, language: str,
                 current_id: str | None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.repository = repository
        self.language = language
        self.selected_id = current_id
        self.related_filter: tuple[str, str] | None = None
        self._row_text: dict[str, str] = {}
        host_width = parent.width() if parent is not None else 1280
        host_height = parent.height() if parent is not None else 850
        self.widget.setFixedSize(max(680, min(1180, host_width - 48)),
                                 max(480, min(820, host_height - 48)))
        self.setMaskColor(QColor(0, 0, 0, 160))
        self.widget.setStyleSheet("""
            QFrame#widget { background-color: #1A1A1E;
                border: 1px solid rgba(255,255,255,0.12); border-radius: 10px; }
            QFrame#buttonGroup { background-color: #222228;
                border-top: 1px solid rgba(255,255,255,0.08); }
        """)
        self.choose = self.yesButton
        self.choose.setText(tx("select", language))
        self.cancelButton.setText(tx("cancel", language))
        title_row = QHBoxLayout()
        self.title_label = TitleLabel(tx("picker_title", language))
        self.count_badge = CaptionLabel()
        title_row.addWidget(self.title_label)
        title_row.addWidget(self.count_badge)
        title_row.addStretch(1)
        self.clear_filter_button = PushButton(tx("clear_filter", language))
        title_row.addWidget(self.clear_filter_button)
        self.viewLayout.addLayout(title_row)

        self.segmented = SegmentedWidget()
        for key in ("curated", "female", "male", "all", "favorites"):
            self.segmented.addItem(routeKey=key, text=tx(key, language),
                onClick=lambda _, k=key: self._on_kind_changed(k))
        self.current_kind = "curated"
        self.segmented.setCurrentItem("curated")
        self.viewLayout.addWidget(self.segmented)
        search_row = QHBoxLayout()
        self.search = SearchLineEdit()
        self.search.setPlaceholderText(tx("picker_search", language))
        self.search.setClearButtonEnabled(True)
        self.search.setFixedHeight(36)
        self.result_stat = CaptionLabel()
        search_row.addWidget(self.search, 1)
        search_row.addWidget(self.result_stat)
        self.viewLayout.addLayout(search_row)
        self.filter_label = CaptionLabel()
        self.filter_label.setWordWrap(True)
        self.filter_label.hide()
        self.viewLayout.addWidget(self.filter_label)

        body = QHBoxLayout()
        body.setSpacing(12)
        list_column = QVBoxLayout()
        self.list = ListWidget()
        self.list.setUniformItemSizes(True)
        self.list.setMinimumWidth(290)
        list_column.addWidget(self.list, 1)
        navigation = QHBoxLayout()
        self.previous_button = PushButton(tx("previous", language))
        self.next_button = PushButton(tx("next", language))
        self.candidate_position = CaptionLabel()
        navigation.addWidget(self.previous_button)
        navigation.addWidget(self.candidate_position, 1, Qt.AlignmentFlag.AlignCenter)
        navigation.addWidget(self.next_button)
        list_column.addLayout(navigation)
        body.addLayout(list_column, 3)

        self.inspector_scroll = SmoothScrollArea()
        self.inspector_scroll.setWidgetResizable(True)
        self.inspector_scroll.setMinimumWidth(330)
        self.inspector_scroll.setStyleSheet("QScrollArea {background: transparent; border: none;}")
        self.inspector_card = StudioCard(bg_color=QColor("#202025"),
            border_color=QColor(255, 255, 255, 20), radius=8)
        detail = QVBoxLayout(self.inspector_card)
        detail.setContentsMargins(14, 12, 14, 12)
        detail.setSpacing(8)
        self.detail_cat_tag = CaptionLabel()
        self.detail_name = SubtitleLabel()
        self.detail_name.setWordWrap(True)
        self.detail_name.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        detail.addWidget(self.detail_cat_tag)
        detail.addWidget(self.detail_name)
        self.favorite_button = PushButton()
        self.alias_button = PushButton(tx("edit_alias", language))
        overlay_row = QHBoxLayout()
        overlay_row.addWidget(self.favorite_button)
        overlay_row.addWidget(self.alias_button)
        detail.addLayout(overlay_row)
        self.alias_label = CaptionLabel()
        self.alias_label.setWordWrap(True)
        self.alias_label.setTextFormat(Qt.TextFormat.PlainText)
        self.alias_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        detail.addWidget(self.alias_label)
        detail.addWidget(HorizontalSeparator())
        similarity_row = QGridLayout()
        self.same_face_button = PushButton(tx("same_face", language))
        self.same_hair_button = PushButton(tx("same_hair", language))
        self.same_model_button = PushButton(tx("same_model", language))
        similarity_row.addWidget(self.same_face_button, 0, 0)
        similarity_row.addWidget(self.same_hair_button, 0, 1)
        similarity_row.addWidget(self.same_model_button, 1, 0, 1, 2)
        detail.addLayout(similarity_row)
        detail.addWidget(StrongBodyLabel(tx("model_inspector", language)))
        self.specs_grid = QGridLayout()
        self.spec_labels = {}
        for row, field in enumerate(("model", "face", "hair", "row_key", "voice", "id", "region", "group")):
            value = CaptionLabel()
            value.setWordWrap(True)
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            value.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            value.setStyleSheet("color: #E2E2E8; font-size: 12px; font-family: 'Consolas', 'Segoe UI', monospace;")
            self.spec_labels[field] = value
            self.specs_grid.addWidget(CaptionLabel(tx("field_" + field, language)), row, 0)
            self.specs_grid.addWidget(value, row, 1)
        self.specs_grid.setColumnStretch(1, 1)
        detail.addLayout(self.specs_grid)
        self.lbl_main_model = self.spec_labels["model"]
        self.lbl_face_model = self.spec_labels["face"]
        self.lbl_hair_model = self.spec_labels["hair"]
        self.lbl_row_key = self.spec_labels["row_key"]
        self.lbl_voice = self.spec_labels["voice"]
        self.variants_header = StrongBodyLabel(tx("variants_title", language))
        detail.addWidget(self.variants_header)
        self.variants_list = ListWidget()
        self.variants_list.setMinimumHeight(100)
        self.variants_list.setMaximumHeight(150)
        detail.addWidget(self.variants_list)
        detail.addStretch(1)
        self.inspector_scroll.setWidget(self.inspector_card)
        body.addWidget(self.inspector_scroll, 2)
        self.viewLayout.addLayout(body, 1)
        self.browse_hint = CaptionLabel(tx("finder_browse_hint", language))
        self.browse_hint.setWordWrap(True)
        self.viewLayout.addWidget(self.browse_hint)
        self.state_feedback = CaptionLabel()
        self.state_feedback.setWordWrap(True)
        self.state_feedback.setTextFormat(Qt.TextFormat.PlainText)
        if repository.user_state.load_error:
            self.state_feedback.setText(tx("finder_load_error", language))
        else:
            self.state_feedback.hide()
        self.viewLayout.addWidget(self.state_feedback)

        self.filter_timer = QTimer(self)
        self.filter_timer.setSingleShot(True)
        self.filter_timer.setInterval(120)
        self.filter_timer.timeout.connect(self._populate)
        self.search.textChanged.connect(lambda: self.filter_timer.start())
        self.list.currentItemChanged.connect(self._show_details)
        self.list.itemDoubleClicked.connect(lambda _: self._accept())
        self.choose.clicked.connect(self._accept)
        self.cancelButton.clicked.connect(self.reject)
        self.previous_button.clicked.connect(lambda: self._move_candidate(-1))
        self.next_button.clicked.connect(lambda: self._move_candidate(1))
        self.clear_filter_button.clicked.connect(self._clear_filter)
        self.favorite_button.clicked.connect(self._toggle_favorite)
        self.alias_button.clicked.connect(self._edit_alias)
        for button, field in ((self.same_face_button, "face_model"),
                              (self.same_hair_button, "hair_model"),
                              (self.same_model_button, "model")):
            button.clicked.connect(lambda _, field=field: self._find_similar(field))
        self._populate()

    def _on_kind_changed(self, kind: str) -> None:
        self.current_kind = kind
        self._populate()

    def _current_id(self) -> str | None:
        item = self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def _name(self, target: dict[str, Any]) -> tuple[str, str]:
        cat, name = parse_label_category_and_name(target["label"], self.language)
        if target["kind"] in ("female", "male") and not target.get("confirmed_identity"):
            name = tx("anonymous_" + target["kind"], self.language).format(key=target["standard_character"])
        return cat, name

    def _item_text(self, target_id: str) -> str:
        if target_id not in self._row_text:
            target = self.repository.targets[target_id]
            cat, name = self._name(target)
            self._row_text[target_id] = (
                name + "\n" + tx("field_model", self.language) + ": " + (target.get("model") or "—")
                + "\n" + tx("field_face", self.language) + ": " + (target.get("face_model") or "—")
                + "  ·  " + tx("field_hair", self.language) + ": " + (target.get("hair_model") or "—")
                + "\n" + tx("field_row_key", self.language) + f": {target['target_row']} / {target['standard_character']} (0x{target['standard_character']:X})"
            )
        text = self._row_text[target_id]
        alias = self.repository.user_state.alias(target_id)
        if alias:
            text = alias + "  ·  " + text
        if self.repository.user_state.is_favorite(target_id):
            text = "★ " + text
        return text

    def _populate(self) -> None:
        self.filter_timer.stop()
        current_id = self._current_id() or self.selected_id
        matched = self.repository.find_targets(self.search.text(), self.current_kind, self.related_filter)
        total = len(self.repository.ids_for_kind(self.current_kind))
        self.list.blockSignals(True)
        self.list.setUpdatesEnabled(False)
        try:
            self.list.clear()
            self.list.addItems([self._item_text(target_id) for target_id in matched])
            current_row = 0
            for row, target_id in enumerate(matched):
                item = self.list.item(row)
                item.setData(Qt.ItemDataRole.UserRole, target_id)
                item.setSizeHint(QSize(0, 84))
                item.setToolTip(item.text() + "\n" + tx("field_id", self.language) + ": " + target_id)
                if target_id == current_id:
                    current_row = row
            if matched:
                self.list.setCurrentRow(current_row)
                self.list.scrollToItem(self.list.currentItem())
        finally:
            self.list.setUpdatesEnabled(True)
            self.list.blockSignals(False)
        self.result_stat.setText(tx("result_count", self.language).format(matched=f"{len(matched):,}", total=f"{total:,}"))
        for kind in ("curated", "female", "male", "all", "favorites"):
            self.segmented.setItemText(kind, f"{tx(kind, self.language)} · {len(self.repository.ids_for_kind(kind)):,}")
        self.choose.setEnabled(bool(matched))
        self._show_details(self.list.currentItem(), None)

    def _show_details(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        target = self.repository.targets[current.data(Qt.ItemDataRole.UserRole)] if current else None
        if target is None:
            self.detail_cat_tag.hide()
            self.detail_name.setText(tx("no_results", self.language))
            for label in self.spec_labels.values():
                label.setText("—")
            self.alias_label.clear()
            self.variants_list.clear()
        else:
            cat, name = self._name(target)
            self.detail_cat_tag.setText(cat)
            self.detail_cat_tag.setVisible(bool(cat))
            self.detail_name.setText(name)
            alias = self.repository.user_state.alias(target["id"])
            self.alias_label.setText(tx("alias", self.language) + ": " + (alias or "—"))
            values = {
                "model": target.get("model"), "face": target.get("face_model"),
                "hair": target.get("hair_model"), "id": target["id"],
                "row_key": f"{target['target_row']} / {target['standard_character']} (0x{target['standard_character']:X})",
                "voice": f"{target.get('voicer') if target.get('voicer') is not None else '—'} / {target.get('adv_model_id') or '—'}",
                "region": target.get("region"), "group": target.get("catalog_group"),
            }
            for field, label in self.spec_labels.items():
                label.setText(str(values[field] or "—"))
            self.variants_list.clear()
            self.variants_list.addItems([costume_variant_label(v, self.language) for v in target.get("variants", [])]
                or [tx("default_variant", self.language)])
        favorite = bool(target and self.repository.user_state.is_favorite(target["id"]))
        self.favorite_button.setText(tx("favorite_remove" if favorite else "favorite_add", self.language))
        self.favorite_button.setEnabled(target is not None)
        self.alias_button.setEnabled(target is not None)
        for button, field in ((self.same_face_button, "face_model"), (self.same_hair_button, "hair_model"), (self.same_model_button, "model")):
            button.setEnabled(bool(target and target.get(field)))
        row = self.list.currentRow()
        count = self.list.count()
        self.candidate_position.setText(tx("candidate_position", self.language).format(current=row + 1 if count else 0, total=count))
        self.previous_button.setEnabled(row > 0)
        self.next_button.setEnabled(0 <= row < count - 1)

    def _move_candidate(self, step: int) -> None:
        row = self.list.currentRow() + step
        if 0 <= row < self.list.count():
            self.list.setCurrentRow(row)
            self.list.scrollToItem(self.list.currentItem())

    def _find_similar(self, field: str) -> None:
        target_id = self._current_id()
        if target_id is None:
            return
        value = self.repository.targets[target_id].get(field)
        if not value:
            return
        self.related_filter = (field, str(value))
        self.search.blockSignals(True)
        self.search.clear()
        self.search.blockSignals(False)
        self.current_kind = "all"
        self.segmented.setCurrentItem("all")
        label = {"face_model": "same_face", "hair_model": "same_hair", "model": "same_model"}[field]
        self.filter_label.setText(tx("similar_filter", self.language).format(field=tx(label, self.language), value=value))
        self.filter_label.show()
        self._populate()

    def _clear_filter(self) -> None:
        self.related_filter = None
        self.filter_label.hide()
        self.search.clear()
        self._populate()

    def _save_feedback(self, success: bool) -> None:
        if not success:
            self.state_feedback.setText(tx("finder_save_error", self.language).format(error=self.repository.user_state.last_error))
            self.state_feedback.show()
        else:
            self.state_feedback.clear()
            self.state_feedback.hide()

    def _toggle_favorite(self) -> None:
        target_id = self._current_id()
        if target_id is not None:
            self._save_feedback(self.repository.user_state.set_favorite(target_id,
                not self.repository.user_state.is_favorite(target_id)))
            self._populate()

    def _edit_alias(self) -> None:
        target_id = self._current_id()
        if target_id is None:
            return
        dialog = AliasDialog(self.repository.user_state.alias(target_id), self.language, self)
        if dialog.exec() == AliasDialog.DialogCode.Accepted:
            self.save_alias(target_id, dialog.editor.text())

    def save_alias(self, target_id: str, alias: str) -> None:
        if target_id in self.repository.targets:
            self._save_feedback(self.repository.user_state.set_alias(target_id, alias))
            self._populate()

    def _accept(self) -> None:
        target_id = self._current_id()
        if target_id is not None:
            self.selected_id = target_id
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
