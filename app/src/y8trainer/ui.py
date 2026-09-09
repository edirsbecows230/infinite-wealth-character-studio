from __future__ import annotations

import re
import traceback
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QCloseEvent, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QListWidgetItem,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CheckBox,
    ComboBox,
    FluentIcon as FIF,
    FluentWindow,
    HorizontalSeparator,
    InfoBadge,
    InfoLevel,
    LineEdit,
    ListWidget,
    MessageBox,
    MessageBoxBase,
    Pivot,
    PrimaryPushButton,
    PushButton,
    SearchLineEdit,
    SimpleCardWidget,
    SmoothScrollArea,
    StrongBodyLabel,
    SubtitleLabel,
    Theme,
    TitleLabel,
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
    "subtitle": (
        "Real-time protagonist model & costume changer with dual-slot support",
        "双主角实时模型与服装替换工具 · 即改即用",
    ),
    "waiting": ("WAITING FOR GAME", "等待游戏启动"),
    "scanning": ("SCANNING DATABASES", "正在定位数据库"),
    "ready": ("READY", "已就绪"),
    "applied": ("APPLIED & VERIFIED", "已应用并验证"),
    "error": ("ACTION REQUIRED", "需要处理"),
    "mode_title": ("Replacement layout", "替换布局"),
    "mode_hint": (
        "Independent mode lets both protagonists use different models in the same party.",
        "分别设置可让同一队伍中的两位主角使用不同模型。",
    ),
    "only_ichiban": ("Ichiban only", "仅春日"),
    "only_kiryu": ("Kiryu only", "仅桐生"),
    "independent": ("Independent dual slots", "双主角分别设置"),
    "ichiban": ("ICHI / ICHIBAN", "春日 · ICHI"),
    "kiryu": ("KIRYU", "桐生 · KIRYU"),
    "slot_active": ("ACTIVE SLOT", "参与本次替换"),
    "slot_backup": ("RESTORE TO BACKUP", "保持首次备份"),
    "character": ("Character", "角色"),
    "choose": ("Choose character", "选择角色"),
    "outfit": ("Outfit behavior", "服装行为"),
    "variant": ("Fixed outfit", "固定服装"),
    "context": ("Context matched · Recommended", "场景匹配 · 推荐"),
    "default": ("Default outfit everywhere", "始终使用默认服装"),
    "fixed": ("One fixed outfit variant", "固定指定服装"),
    "model": ("MODEL", "模型"),
    "row_key": ("ROW / KEY", "行 / KEY"),
    "voice": ("VOICE", "语音"),
    "apply": ("Apply selected protagonists", "应用所选主角"),
    "apply_hint": (
        "Backs up → writes 357 cells → reads every cell back → rolls back on failure",
        "自动备份 → 写入 357 项 → 逐项回读 → 失败自动回滚",
    ),
    "restore": ("Restore original game models", "恢复游戏原版模型"),
    "reconnect": ("Reconnect", "重新连接"),
    "custom": ("Custom character key", "自定义 Character key"),
    "custom_hint": ("Decimal or 0x hexadecimal", "十进制或 0x 十六进制"),
    "use_ichi": ("Use for Ichiban", "用于春日"),
    "use_kiryu": ("Use for Kiryu", "用于桐生"),
    "details": ("Diagnostics & recovery", "诊断与恢复工具"),
    "hide_details": ("Hide diagnostics", "收起诊断工具"),
    "db_wait": ("Database addresses will appear after connection.", "连接后将在此显示数据库地址。"),
    "vanilla": ("Restore launch-state backup", "恢复本次启动前状态"),
    "vanilla_hint": (
        "The first-Apply snapshot preserves values already changed by a CT or file Mod, so it may still be a replacement.",
        "首次应用快照会保留启动前已有的 CT 或文件 Mod 值，因此恢复后仍可能是替换模型。",
    ),
    "original_confirm_title": ("Restore original game models?", "恢复游戏原版模型？"),
    "original_confirm_body": (
        "This writes the embedded original values for both protagonists and can overwrite currently loaded file-Mod values. Existing free-roam actors refresh after a save reload or map change.",
        "这会向两个主角源写入内置原版值，并可能覆盖当前加载的文件 Mod 值。自由探索中已经生成的角色需读档或切图后刷新。",
    ),
    "safety": (
        "Reopen menus to refresh. Reload a save or change maps for free-roam models.",
        "菜单需重新打开刷新；自由探索模型需读档或切换地图刷新。",
    ),
    "picker_title": ("Choose a character", "选择角色"),
    "picker_search": ("Search name, model, key, row, voice…", "搜索名称、模型、key、行、语音…"),
    "curated": ("Curated · 59", "精选 · 59"),
    "female": ("Female NPC · 404", "女性 NPC · 404"),
    "male": ("Male NPC · 4,742", "男性 NPC · 4,742"),
    "all": ("All · 5,205", "全部 · 5,205"),
    "select": ("Select character", "选择此角色"),
    "cancel": ("Cancel", "取消"),
    "no_results": ("No matching characters", "没有匹配的角色"),
    "close_title": ("Choose restore target", "选择退出前恢复目标"),
    "close_body": (
        "The game is still running with an active replacement. Original values restore the game models; launch state may already contain a CT/file Mod replacement. Existing free-roam actors refresh after a save reload or map change.",
        "游戏仍在运行且替换处于活动状态。恢复原版会写回游戏内置值；启动前状态可能已经包含 CT/文件 Mod 替换。自由探索角色需读档或切图后刷新。",
    ),
    "close_body_modified_backup": (
        "The first-Apply backup was already modified, so restoring launch state will keep a replacement. Choose original models to write the embedded game values. Existing free-roam actors refresh after a save reload or map change.",
        "检测到首次应用备份本身已经被修改；恢复启动前状态仍会保留替换模型。若要回到原角色，请选择恢复原版。自由探索角色需读档或切图后刷新。",
    ),
    "restore_exit": ("Original models & exit", "恢复原版并退出"),
    "session_exit": ("Launch state & exit", "恢复启动前状态并退出"),
    "keep_exit": ("Leave active and exit", "保持替换并退出"),
}


def tx(key: str, language: str) -> str:
    pair = TEXT[key]
    return pair[0] if language == "en" else pair[1]


def display_label(text: str, language: str) -> str:
    """Render the generated bilingual CT labels in one selected language."""
    text = str(text or "")
    match = re.match(r"^\[([^\]]+)\]\s*(.*)$", text)
    if match:
        head, rest = match.groups()
        parts = re.split(r"\s*/\s*", head, maxsplit=1)
        localized_head = parts[0] if language == "en" or len(parts) == 1 else parts[1]
        names = re.split(r"\s*/\s*", rest, maxsplit=1)
        if len(names) == 2 and " — " not in rest and " | " not in rest:
            rest = names[0] if language == "en" else names[1]
        return f"[{localized_head}] {rest}".strip()
    if " — " in text:
        prefix, suffix = text.split(" — ", 1)
        parts = re.split(r"\s*/\s*", prefix, maxsplit=1)
        if len(parts) == 2:
            return f"{parts[0] if language == 'en' else parts[1]} — {suffix}"
    return text


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
    """Build a readable outfit label while keeping model codes out of the primary text."""
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
    painter.setBrush(QColor("#3A7AFE"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(2, 2, size - 4, size - 4, size * 0.23, size * 0.23)
    painter.setPen(QColor("#FFFFFF"))
    font = QFont("Segoe UI", int(size * 0.28), QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "IW")
    painter.end()
    return QIcon(pixmap)


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
        self.widget.setMinimumSize(900, 650)
        self.yesButton.setText(tx("select", language))
        self.cancelButton.setText(tx("cancel", language))
        self.choose = self.yesButton

        title = TitleLabel()
        title.setText(tx("picker_title", language))
        self.viewLayout.addWidget(title)

        controls = QHBoxLayout()
        self.kind = ComboBox()
        for key in ("curated", "female", "male", "all"):
            self.kind.addItem(tx(key, language), userData=key)
        self.kind.setMinimumWidth(190)
        self.search = SearchLineEdit()
        self.search.setPlaceholderText(tx("picker_search", language))
        self.search.setClearButtonEnabled(True)
        controls.addWidget(self.kind)
        controls.addWidget(self.search, 1)
        self.viewLayout.addLayout(controls)

        body = QHBoxLayout()
        body.setSpacing(16)
        self.list = ListWidget()
        self.list.setUniformItemSizes(True)
        self.list.setMinimumWidth(500)
        body.addWidget(self.list, 3)

        details = SimpleCardWidget()
        detail_layout = QVBoxLayout(details)
        detail_layout.setContentsMargins(18, 18, 18, 18)
        detail_layout.setSpacing(10)
        self.detail_name = SubtitleLabel()
        self.detail_name.setWordWrap(True)
        self.detail_model = BodyLabel()
        self.detail_model.setWordWrap(True)
        self.detail_meta = CaptionLabel()
        self.detail_meta.setWordWrap(True)
        detail_layout.addWidget(self.detail_name)
        detail_layout.addWidget(self.detail_model)
        detail_layout.addWidget(self.detail_meta)
        detail_layout.addStretch(1)
        body.addWidget(details, 2)
        self.viewLayout.addLayout(body, 1)

        self.filter_timer = QTimer(self)
        self.filter_timer.setSingleShot(True)
        self.filter_timer.setInterval(140)
        self.filter_timer.timeout.connect(self._populate)
        self.kind.currentIndexChanged.connect(self._populate)
        self.search.textChanged.connect(lambda: self.filter_timer.start())
        self.list.currentItemChanged.connect(self._show_details)
        self.list.itemDoubleClicked.connect(lambda _: self._accept())
        self.choose.clicked.connect(self._accept)
        self.cancelButton.clicked.connect(self.reject)
        self._populate()

    def _populate(self) -> None:
        kind = self.kind.currentData() or "curated"
        query = self.search.text().strip().lower()
        current = self.selected_id
        self.list.clear()
        selected_item: QListWidgetItem | None = None
        for target_id in self.repository.ids_for_kind(kind):
            target = self.repository.targets[target_id]
            if query and query not in target["search_text"]:
                continue
            item = QListWidgetItem(display_label(target["label"], self.language))
            item.setData(Qt.ItemDataRole.UserRole, target_id)
            item.setToolTip(target["model"] or target["label"])
            self.list.addItem(item)
            if target_id == current:
                selected_item = item
        if selected_item:
            self.list.setCurrentItem(selected_item)
            self.list.scrollToItem(selected_item)
        elif self.list.count():
            self.list.setCurrentRow(0)
        else:
            self.detail_name.setText(tx("no_results", self.language))
            self.detail_model.clear()
            self.detail_meta.clear()
        self.choose.setEnabled(self.list.count() > 0)

    def _show_details(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        if not current:
            return
        target = self.repository.targets[current.data(Qt.ItemDataRole.UserRole)]
        self.detail_name.setText(display_label(target["label"], self.language))
        models = [target.get("model"), target.get("face_model"), target.get("hair_model")]
        self.detail_model.setText("\n".join(value for value in models if value) or "—")
        self.detail_meta.setText(
            f"row {target['target_row']}  ·  key {target['standard_character']}\n"
            f"voice {target.get('voicer') if target.get('voicer') is not None else '—'}  ·  "
            f"variants {len(target['variants'])}"
        )

    def _accept(self) -> None:
        item = self.list.currentItem()
        if item:
            self.selected_id = item.data(Qt.ItemDataRole.UserRole)
            self.accept()


class SourceCard(SimpleCardWidget):
    changed = Signal()

    def __init__(
        self,
        source_id: str,
        repository: DataRepository,
        language: str,
        initial_target: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.source_id = source_id
        self.repository = repository
        self.language = language
        self.target_id = initial_target if initial_target in repository.targets else repository.curated_ids[0]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 26)
        layout.setSpacing(14)

        header = QHBoxLayout()
        header_text = QVBoxLayout()
        header_text.setSpacing(3)
        self.step = CaptionLabel()
        self.title = SubtitleLabel()
        header_text.addWidget(self.step)
        header_text.addWidget(self.title)
        header.addLayout(header_text)
        header.addStretch(1)
        self.include = CheckBox()
        self.include.setChecked(True)
        self.include.toggled.connect(self.changed)
        header.addWidget(self.include)
        layout.addLayout(header)
        layout.addWidget(HorizontalSeparator())

        self.character_caption = StrongBodyLabel()
        layout.addWidget(self.character_caption)
        character_row = QHBoxLayout()
        character_row.setSpacing(14)
        self.target_name = SubtitleLabel()
        self.target_name.setWordWrap(True)
        self.target_name.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.choose = PushButton()
        self.choose.setMinimumWidth(140)
        character_row.addWidget(self.target_name, 1)
        character_row.addWidget(self.choose)
        layout.addLayout(character_row)

        self.technical = CaptionLabel()
        self.technical.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.technical.setWordWrap(True)
        layout.addWidget(self.technical)
        layout.addWidget(HorizontalSeparator())

        combos = QGridLayout()
        combos.setHorizontalSpacing(18)
        combos.setVerticalSpacing(10)
        self.mode_caption = BodyLabel()
        self.variant_caption = BodyLabel()
        self.mode = ComboBox()
        self.variant = ComboBox()
        self.variant_detail = CaptionLabel()
        self.variant_detail.setWordWrap(True)
        self.mode.setMinimumWidth(360)
        combos.addWidget(self.mode_caption, 0, 0)
        combos.addWidget(self.mode, 0, 1)
        combos.addWidget(self.variant_caption, 1, 0)
        combos.addWidget(self.variant, 1, 1)
        combos.setColumnStretch(1, 1)
        layout.addLayout(combos)
        layout.addWidget(self.variant_detail)

        self.outfit_note = CaptionLabel()
        self.outfit_note.setWordWrap(True)
        layout.addWidget(self.outfit_note)
        layout.addStretch(1)

        self.choose.clicked.connect(self._choose_target)
        self.mode.currentIndexChanged.connect(self._mode_changed)
        self.variant.currentIndexChanged.connect(self._refresh_variant_detail)
        self.variant.currentIndexChanged.connect(self.changed)
        self.retranslate(language)
        self._set_target(self.target_id)

    def retranslate(self, language: str) -> None:
        self.language = language
        self.title.setText(tx(self.source_id, language))
        self.character_caption.setText(tx("character", language))
        self.mode_caption.setText(tx("outfit", language))
        self.variant_caption.setText(tx("variant", language))
        self.choose.setText(tx("choose", language))
        self.include.setText("Include in next Apply" if language == "en" else "参与下次应用")
        self.step.setText(
            ("01  PROTAGONIST" if self.source_id == "ichiban" else "02  PROTAGONIST")
            if language == "en"
            else ("01  主角槽位" if self.source_id == "ichiban" else "02  主角槽位")
        )
        self.outfit_note.setText(
            "Context matched follows each gameplay costume context. Fixed outfit also redirects the identity row."
            if language == "en"
            else "场景匹配会跟随游戏服装场景；固定服装还会把身份映射指向该 variant 的 Character Row。"
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
        dialog = TargetPickerDialog(self.repository, self.language, self.target_id, self)
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
        self.target_name.setText(display_label(target["label"], self.language))
        voice = str(target.get("voicer")) if target.get("voicer") is not None else "—"
        self.technical.setText(
            f"{tx('model', self.language)}  {target.get('model') or '—'}    ·    "
            f"{tx('row_key', self.language)}  {target['target_row']} / {target['standard_character']}    ·    "
            f"{tx('voice', self.language)}  {voice}"
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
            f"{tx('model', self.language)}  {variant.get('model') or '—'}    ·    "
            f"KEY  {variant['variant_key']}    ·    Character Row  {variant['character_row']}"
        )
        self.variant.setToolTip(variant["label"])

    def _mode_changed(self) -> None:
        self._refresh_variants()
        self.changed.emit()

    def selection(self) -> SlotSelection:
        mode = self.mode.currentData() or "context_matched"
        variant = self.variant.currentData() if mode == "fixed_variant" else None
        return SlotSelection(self.target_id, mode, int(variant) if variant is not None else None)


class RestoreCloseDialog(MessageBoxBase):
    def __init__(self, language: str, body: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.choice = "original"
        self.widget.setMinimumWidth(880)

        title = SubtitleLabel()
        title.setText(tx("close_title", language))
        content = BodyLabel()
        content.setText(body)
        content.setWordWrap(True)
        self.viewLayout.addWidget(title)
        self.viewLayout.addWidget(content)

        self.yesButton.setText(tx("restore_exit", language))
        self.cancelButton.setText(tx("cancel", language))
        self.sessionButton = PushButton()
        self.sessionButton.setText(tx("session_exit", language))
        self.keepButton = PushButton()
        self.keepButton.setText(tx("keep_exit", language))
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
        self.resize(1120, 820)
        self.setMinimumSize(920, 690)
        self.setCustomBackgroundColor(QColor("#F3F3F3"), QColor("#202020"))
        self.setMicaEffectEnabled(True)
        # Qt's offscreen backend cannot render the Windows compositor Mica
        # surface. Disable it only for deterministic preview/test captures.
        if QApplication.platformName() == "offscreen":
            self.setMicaEffectEnabled(False)
        self._build_ui()
        self._retranslate()
        self._mode_changed()

        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(2200)
        self.poll_timer.timeout.connect(self._connection_tick)
        if preview:
            self._set_state("ready", "READY · 双槽位独立配置预览")
            self._update_db_details({
                "pid": 24816,
                "connected": True,
                "active": False,
                "backup": False,
                "backup_is_vanilla": None,
                "character_base": 0x252B60000,
                "costume_base": 0x1D38115C0,
                "states": {"ichiban": "original", "kiryu": "original"},
                "message": "Preview",
            })
        else:
            self.poll_timer.start()
            QTimer.singleShot(180, self._connection_tick)

    def _build_ui(self) -> None:
        self.interface = QWidget()
        # FluentWindow requires a unique route key for each sub-interface.
        # This object name is routing metadata, not a QSS styling hook.
        self.interface.setObjectName("characterStudioInterface")
        self.navigation_item = self.addSubInterface(
            self.interface, FIF.GAME, "Character Studio", isTransparent=False
        )
        # The editor has one workspace and uses Pivot for protagonist routing;
        # a one-item Fluent navigation rail would only duplicate that control.
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
        # QFluentWidgets applies transparency to the current child widget, so
        # this must be called after setWidget().
        self.scroll_area.enableTransparentBackground()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(30, 28, 30, 30)
        layout.setSpacing(16)

        hero = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(3)
        self.app_title = TitleLabel()
        self.subtitle = CaptionLabel()
        titles.addWidget(self.app_title)
        titles.addWidget(self.subtitle)
        hero.addLayout(titles)
        hero.addStretch(1)

        status_column = QVBoxLayout()
        status_column.setSpacing(5)
        status_top = QHBoxLayout()
        self.status = InfoBadge()
        self.status.setLevel(InfoLevel.ATTENTION)
        self.language_button = PushButton()
        self.language_button.setFixedWidth(54)
        status_top.addStretch(1)
        status_top.addWidget(self.status)
        status_top.addWidget(self.language_button)
        self.message = CaptionLabel()
        self.message.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.message.setMaximumWidth(530)
        status_column.addLayout(status_top)
        status_column.addWidget(self.message)
        hero.addLayout(status_column)
        layout.addLayout(hero)
        layout.addWidget(HorizontalSeparator())

        self.slot_pivot = Pivot()
        self.pivot_items = {
            "ichiban": self.slot_pivot.addItem(
                routeKey="ichibanSlot",
                text="Ichiban",
                onClick=lambda: self.editor_stack.setCurrentIndex(0),
            ),
            "kiryu": self.slot_pivot.addItem(
                routeKey="kiryuSlot",
                text="Kiryu",
                onClick=lambda: self.editor_stack.setCurrentIndex(1),
            ),
        }
        self.slot_pivot.setCurrentItem("ichibanSlot")
        layout.addWidget(self.slot_pivot)

        self.editor_stack = QStackedWidget()
        self.editor_stack.setMinimumHeight(410)
        self.ichiban_card = SourceCard("ichiban", self.repository, self.language, "chitose")
        self.kiryu_card = SourceCard("kiryu", self.repository, self.language, "kiryu")
        self.editor_stack.addWidget(self.ichiban_card)
        self.editor_stack.addWidget(self.kiryu_card)
        layout.addWidget(self.editor_stack, 1)

        layout.addWidget(HorizontalSeparator())
        action_row = QHBoxLayout()
        action_copy = QVBoxLayout()
        action_copy.setSpacing(3)
        self.apply_hint = CaptionLabel()
        self.safety = CaptionLabel()
        self.apply_hint.setWordWrap(True)
        self.safety.setWordWrap(True)
        action_copy.addWidget(self.apply_hint)
        action_copy.addWidget(self.safety)
        action_row.addLayout(action_copy, 1)
        self.restore_button = PushButton()
        self.restore_button.setMinimumWidth(190)
        self.apply_button = PrimaryPushButton()
        self.apply_button.setMinimumWidth(235)
        action_row.addWidget(self.restore_button)
        action_row.addWidget(self.apply_button)
        layout.addLayout(action_row)

        self.details_button = PushButton()
        self.details_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.details_button)

        self.details_panel = SimpleCardWidget()
        detail_layout = QVBoxLayout(self.details_panel)
        detail_layout.setContentsMargins(20, 18, 20, 18)
        detail_layout.setSpacing(13)
        custom_row = QHBoxLayout()
        self.custom_title = StrongBodyLabel()
        self.custom_input = LineEdit()
        self.custom_use_ichi = PushButton()
        self.custom_use_kiryu = PushButton()
        custom_row.addWidget(self.custom_title)
        custom_row.addWidget(self.custom_input, 1)
        custom_row.addWidget(self.custom_use_ichi)
        custom_row.addWidget(self.custom_use_kiryu)
        detail_layout.addLayout(custom_row)
        detail_layout.addWidget(HorizontalSeparator())

        recovery = QHBoxLayout()
        recovery_text = QVBoxLayout()
        recovery_text.setSpacing(4)
        self.db_info = BodyLabel()
        self.db_info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.vanilla_hint = CaptionLabel()
        self.vanilla_hint.setWordWrap(True)
        recovery_text.addWidget(self.db_info)
        recovery_text.addWidget(self.vanilla_hint)
        self.reconnect_button = PushButton()
        self.vanilla_button = PushButton()
        recovery.addLayout(recovery_text, 1)
        recovery.addWidget(self.reconnect_button)
        recovery.addWidget(self.vanilla_button)
        detail_layout.addLayout(recovery)
        self.details_panel.setVisible(False)
        layout.addWidget(self.details_panel)

        self.language_button.clicked.connect(self._toggle_language)
        self.apply_button.clicked.connect(self._apply)
        self.restore_button.clicked.connect(self._force_vanilla)
        self.reconnect_button.clicked.connect(self._connect_now)
        self.details_button.clicked.connect(self._toggle_details)
        self.custom_use_ichi.clicked.connect(lambda: self._resolve_custom("ichiban"))
        self.custom_use_kiryu.clicked.connect(lambda: self._resolve_custom("kiryu"))
        self.vanilla_button.clicked.connect(self._restore)
        self.ichiban_card.changed.connect(self._mode_changed)
        self.kiryu_card.changed.connect(self._mode_changed)

    def _retranslate(self) -> None:
        lang = self.language
        self.setWindowTitle(tx("app_title", lang))
        self.app_title.setText(tx("app_title", lang))
        self.subtitle.setText(tx("subtitle", lang))
        self.navigation_item.setText("Character Studio" if lang == "en" else "角色模型工坊")
        self.pivot_items["ichiban"].setText(tx("ichiban", lang))
        self.pivot_items["kiryu"].setText(tx("kiryu", lang))
        self.ichiban_card.retranslate(lang)
        self.kiryu_card.retranslate(lang)
        self.apply_hint.setText(tx("apply_hint", lang))
        self.safety.setText(tx("safety", lang))
        self.restore_button.setText(tx("restore", lang))
        self.reconnect_button.setText(tx("reconnect", lang))
        self.details_button.setText(tx("hide_details" if self.details_visible else "details", lang))
        self.custom_title.setText(tx("custom", lang))
        self.custom_input.setPlaceholderText(tx("custom_hint", lang))
        self.custom_use_ichi.setText(tx("use_ichi", lang))
        self.custom_use_kiryu.setText(tx("use_kiryu", lang))
        self.vanilla_button.setText(tx("vanilla", lang))
        self.vanilla_hint.setText(tx("vanilla_hint", lang))
        self.language_button.setText("中" if lang == "en" else "EN")
        self._mode_changed()
        if not self.engine.connected and not self.preview:
            self._set_state("waiting", tx("waiting", lang))

    def _toggle_language(self) -> None:
        self.language = "en" if self.language == "zh" else "zh"
        self._retranslate()
        self._mode_changed()

    def _current_mode(self) -> str:
        included = (self.ichiban_card.is_included(), self.kiryu_card.is_included())
        if included == (True, False):
            return "ichiban"
        if included == (False, True):
            return "kiryu"
        return "both" if any(included) else "none"

    def _mode_changed(self) -> None:
        count = int(self.ichiban_card.is_included()) + int(self.kiryu_card.is_included())
        if self.language == "en":
            self.apply_button.setText(f"Apply {count} protagonist{'s' if count != 1 else ''}")
        else:
            self.apply_button.setText(f"应用 {count} 个主角槽位")
        self.apply_button.setEnabled(not self.busy and count > 0)

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
        self.vanilla_button.setEnabled(not busy)
        self.custom_use_ichi.setEnabled(not busy)
        self.custom_use_kiryu.setEnabled(not busy)
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
        self._set_state("error", trace.splitlines()[-1] if trace else "Unexpected error")

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

    def _collect_slots(self) -> dict[str, SlotSelection]:
        slots: dict[str, SlotSelection] = {}
        if self.ichiban_card.is_included():
            slots["ichiban"] = self.ichiban_card.selection()
        if self.kiryu_card.is_included():
            slots["kiryu"] = self.kiryu_card.selection()
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

    def _toggle_details(self) -> None:
        self.details_visible = not self.details_visible
        self.details_panel.setVisible(self.details_visible)
        self.details_button.setText(tx("hide_details" if self.details_visible else "details", self.language))
        if self.details_visible:
            self._update_db_details(self.engine.status_snapshot())

    def _update_db_details(self, status: dict[str, Any]) -> None:
        if status.get("connected"):
            self.db_info.setText(
                f"PID {status['pid']}  ·  Character 0x{status['character_base']:X}  ·  "
                f"Costume 0x{status['costume_base']:X}\n"
                f"Ichiban: {status['states'].get('ichiban', '—')}  ·  "
                f"Kiryu: {status['states'].get('kiryu', '—')}  ·  "
                f"Backup: {'saved' if status.get('backup') else 'not saved'}"
            )
        else:
            self.db_info.setText(tx("db_wait", self.language))

    def _resolve_custom(self, source_id: str) -> None:
        value = self.custom_input.text()

        def done(payload: tuple[OperationResult, dict[str, Any] | None]) -> None:
            result, target = payload
            if result.ok and target:
                card = self.ichiban_card if source_id == "ichiban" else self.kiryu_card
                card.set_target(target["id"])
                self._set_state("ready", result.message)
            else:
                self._set_state("error", result.message)

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


def apply_application_style(app: QApplication) -> None:
    setTheme(Theme.DARK)
    setThemeColor(QColor("#3A7AFE"))
