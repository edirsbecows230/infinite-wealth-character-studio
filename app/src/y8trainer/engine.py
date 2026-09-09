from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .data import DataRepository
from .memory import MemoryAccessError, NativeProcessMemory


GAME_PROCESS = "likeadragon8.exe"
CHARACTER_ROWS = 10646
CHARACTER_COLUMNS = 22
CHARACTER_DB_ID = 0x4A6
COSTUME_OUTER_ROWS = 61
COSTUME_ROWS = 539
COSTUME_COLUMNS = 7
COSTUME_TABLE_ID = 0x1279
COSTUME_STORAGE_MODE = 1
COSTUME_STRIDE = 16


class TrainerError(RuntimeError):
    pass


@dataclass
class CharacterLayout:
    base: int
    inner: int
    key_array: int
    mapping: int


@dataclass
class SourceCostumeState:
    source_rows: int = 0
    actual: dict[int, tuple[int, int]] = field(default_factory=dict)
    state: str = "unknown_or_other_mod"
    transaction_safe: bool = False


@dataclass
class CostumeLayout:
    base: int
    inner: int
    row_offset_table: int
    row_offsets: list[int]
    sources: dict[str, SourceCostumeState]
    source_rows: int
    transaction_safe: bool
    unknown_details: list[str]


@dataclass(frozen=True)
class SlotSelection:
    target_id: str
    mode: str
    variant_index: int | None = None


@dataclass(frozen=True)
class MultiSelection:
    """Independent configuration for either or both protagonist source slots."""

    slots: dict[str, SlotSelection]


@dataclass
class IdentityBackup:
    source_id: str
    key: int
    address: int
    value: int


@dataclass
class CostumeBackup:
    source_id: str
    row: int
    costume: int
    character_address: int
    hawaii_address: int
    character: int
    hawaii: int


@dataclass
class Snapshot:
    pid: int
    character_base: int
    costume_base: int
    identity: list[IdentityBackup]
    costume: list[CostumeBackup]


@dataclass(frozen=True)
class OperationResult:
    ok: bool
    message: str


def _make_logger() -> logging.Logger:
    logger = logging.getLogger("y8trainer")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    log_path = Path(os.environ.get("TEMP") or os.environ.get("TMP") or ".") / "Y8CharacterSelector.log"
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s"))
    logger.addHandler(handler)
    return logger


class TrainerEngine:
    """Port of the RC1 transaction core using only Win32 process APIs.

    Unlike the CT, a selection is a map keyed by source id. This allows
    Ichiban and Kiryu to receive different targets, outfits, and variants in
    the same verified 357-cell transaction.
    """

    def __init__(self, repository: DataRepository, memory: Any | None = None) -> None:
        self.repository = repository
        self.memory = memory or NativeProcessMemory()
        self.log = _make_logger()
        self.lock = threading.RLock()
        self.pid: int | None = None
        self.character: CharacterLayout | None = None
        self.costume: CostumeLayout | None = None
        self.backup: Snapshot | None = None
        self.active_selection: MultiSelection | None = None
        self.recovery_required = False
        self.last_message = "waiting for game"

    @property
    def active(self) -> bool:
        return self.backup is not None and (
            self.active_selection is not None or self.recovery_required
        )

    @property
    def connected(self) -> bool:
        return bool(self.pid and self.character and self.costume)

    def _set_message(self, message: str) -> None:
        self.last_message = message
        self.log.info(message)

    def _clear_process_state(self, reason: str) -> None:
        old_pid = self.pid
        self.log.info(
            "PROCESS_END old_pid=%s reason=%s active=%s backup=%s",
            old_pid, reason, self.active, self.backup is not None,
        )
        self.pid = None
        self.character = None
        self.costume = None
        self.backup = None
        self.active_selection = None
        self.recovery_required = False
        self.repository.invalidate_custom_targets()
        self.memory.close()

    def process_is_running(self) -> bool:
        return self.memory.find_pid(GAME_PROCESS) is not None

    def refresh_process_lifecycle(self) -> OperationResult:
        """Cheap poll used by the UI; database scans are performed separately."""
        with self.lock:
            current = self.memory.find_pid(GAME_PROCESS)
            if current is None:
                if self.pid is not None:
                    self._clear_process_state("process exited")
                return OperationResult(False, "likeadragon8.exe is not running")
            if self.pid is not None and current != self.pid:
                self._clear_process_state(f"PID changed to {current}")
            if self.pid == current and self.connected:
                return OperationResult(True, "game and databases are ready")
            return OperationResult(False, f"game PID {current} found; databases not connected")

    def _read_common_header(self, base: int, outer_rows: int) -> int:
        if base < 0x10000:
            raise TrainerError("invalid database base")
        header = self.memory.read(base, 0x28)
        if header[0:4] != b"armp":
            raise TrainerError("ARMP magic mismatch")
        if header[0x0A] != 2:
            raise TrainerError("ARMP version mismatch")
        rows = int.from_bytes(header[0x20:0x24], "little")
        columns = int.from_bytes(header[0x24:0x28], "little")
        if rows != outer_rows or columns != 3:
            raise TrainerError(f"outer layout mismatch rows={rows} columns={columns}")
        inner_offset = int.from_bytes(header[0x10:0x14], "little")
        if not 0x100 <= inner_offset <= 0x2000000:
            raise TrainerError(f"invalid inner offset {inner_offset}")
        return inner_offset

    def validate_character_db(self, base: int) -> CharacterLayout:
        inner_offset = self._read_common_header(base, CHARACTER_ROWS)
        rows = self.memory.read_u32(base + inner_offset)
        columns = self.memory.read_u32(base + inner_offset + 0x04)
        runtime_id = self.memory.read_u32(base + inner_offset + 0x20)
        database_id = runtime_id & 0x7FFFFFFF
        if rows != CHARACTER_ROWS or columns != CHARACTER_COLUMNS or database_id != CHARACTER_DB_ID:
            raise TrainerError(
                "Character inner mismatch "
                f"rows={rows} columns={columns} runtime_id=0x{runtime_id:X} normalized=0x{database_id:X}"
            )
        key_offset = self.memory.read_u32(base + inner_offset - 0x10)
        mapping_offset = self.memory.read_u32(base + inner_offset - 0x08)
        if not key_offset or not mapping_offset or key_offset >= inner_offset or mapping_offset >= inner_offset:
            raise TrainerError("invalid Character sorted-index offsets")
        seen_positions: set[int] = set()
        for source_id in self.repository.source_order:
            source = self.repository.sources[source_id]
            for entry in source["context_entries"]:
                position = entry["position"]
                if position in seen_positions:
                    raise TrainerError(f"duplicate Character mapping position {position}")
                seen_positions.add(position)
                key = self.memory.read_u32(base + key_offset + position * 4)
                row = self.memory.read_u32(base + mapping_offset + position * 4)
                if key != entry["key"] or not 0 <= row < CHARACTER_ROWS:
                    raise TrainerError(
                        f"Character key/mapping mismatch source={source_id} "
                        f"key={entry['key']} value={key} row={row}"
                    )
        return CharacterLayout(
            base=base,
            inner=base + inner_offset,
            key_array=base + key_offset,
            mapping=base + mapping_offset,
        )

    @staticmethod
    def _fixed_variant_pair(variant: dict[str, Any] | None) -> tuple[int, int] | None:
        if not variant:
            return None
        key = int(variant.get("character") or variant.get("hawaii") or 0)
        if key <= 0:
            return None
        return key, key

    def _target_matches(
        self,
        source_id: str,
        actual: dict[int, tuple[int, int]],
        target: dict[str, Any],
        mode: str,
        variant: dict[str, Any] | None,
    ) -> bool:
        source = self.repository.sources[source_id]
        source_plan = target.get("source_plans", {}).get(source_id)
        if not target["fixed_npc"] and source_plan is None:
            return False
        for row in source["sorted_rows"]:
            if target["fixed_npc"]:
                expected = (target["standard_character"], target["standard_hawaii"])
            elif mode == "context_matched":
                expected = source_plan.get(row)
            elif mode == "default_only":
                expected = (target["standard_character"], target["standard_hawaii"])
            else:
                expected = self._fixed_variant_pair(variant)
            if expected is None:
                return False
            pair = actual.get(row)
            matches = pair == expected
            # Accept the legacy v0.1.0 fixed pair before replacing it.
            if not matches and mode == "fixed_variant" and variant and pair:
                matches = pair == (variant["character"], variant["hawaii"])
            if not matches:
                return False
        return True

    def validate_costume_db(self, base: int) -> CostumeLayout:
        inner_offset = self._read_common_header(base, COSTUME_OUTER_ROWS)
        rows = self.memory.read_u32(base + inner_offset)
        columns = self.memory.read_u32(base + inner_offset + 0x04)
        packed = self.memory.read_u32(base + inner_offset + 0x20)
        table_id = packed & 0xFFFFFF
        storage_mode = ((packed >> 24) & 0xFF) & 0x01
        if (
            rows != COSTUME_ROWS
            or columns != COSTUME_COLUMNS
            or table_id != COSTUME_TABLE_ID
            or storage_mode != COSTUME_STORAGE_MODE
        ):
            raise TrainerError(
                "Costume inner mismatch "
                f"rows={rows} columns={columns} packed=0x{packed:X} "
                f"table_id=0x{table_id:X} storage={storage_mode}"
            )

        row_table_offset = self.memory.read_u32(base + inner_offset + 0x1C)
        if not inner_offset < row_table_offset <= 0x2000000:
            raise TrainerError(f"invalid Costume row-offset table {row_table_offset}")
        row_offsets: list[int] = []
        previous: int | None = None
        for row in range(COSTUME_ROWS):
            offset = self.memory.read_u32(base + row_table_offset + row * 4)
            if not inner_offset < offset < row_table_offset:
                raise TrainerError(f"invalid Costume row offset row={row} value=0x{offset:X}")
            if previous is not None and offset - previous != COSTUME_STRIDE:
                raise TrainerError(
                    f"Costume stride mismatch row={row} previous=0x{previous:X} current=0x{offset:X}"
                )
            row_offsets.append(offset)
            previous = offset

        player_to_source = {
            self.repository.sources[source_id]["player"]: source_id
            for source_id in self.repository.source_order
        }
        states = {source_id: SourceCostumeState() for source_id in self.repository.source_order}
        seen_rows = {source_id: set() for source_id in self.repository.source_order}
        for row, offset in enumerate(row_offsets):
            row_address = base + offset
            player = self.memory.read_u16(row_address)
            costume = self.memory.read_u16(row_address + 0x02)
            character = self.memory.read_u16(row_address + 0x04)
            hawaii = self.memory.read_u16(row_address + 0x06)
            source_id = player_to_source.get(player)
            if source_id is None:
                continue
            source = self.repository.sources[source_id]
            expected = source["records"].get(row)
            if expected is None:
                raise TrainerError(f"unexpected source row source={source_id} row={row}")
            if costume != expected["costume"]:
                raise TrainerError(
                    f"costume mismatch source={source_id} row={row} "
                    f"expected={expected['costume']} actual={costume}"
                )
            state = states[source_id]
            state.source_rows += 1
            state.actual[row] = (character, hawaii)
            seen_rows[source_id].add(row)

        unknown: list[str] = []
        total_source_rows = 0
        all_safe = True
        for source_id in self.repository.source_order:
            source = self.repository.sources[source_id]
            state = states[source_id]
            total_source_rows += state.source_rows
            if state.source_rows != source["row_count"]:
                raise TrainerError(
                    f"source row count mismatch source={source_id} "
                    f"expected={source['row_count']} actual={state.source_rows}"
                )
            missing = set(source["records"]) - seen_rows[source_id]
            if missing:
                raise TrainerError(f"missing planned source row source={source_id} row={min(missing)}")

            original = all(
                state.actual[row]
                == (expected["original_character"], expected["original_hawaii"])
                for row, expected in source["records"].items()
            )
            if original:
                state.state = "original"
                state.transaction_safe = True
            else:
                for target_id in self.repository.curated_ids:
                    target = self.repository.targets[target_id]
                    if self._target_matches(source_id, state.actual, target, "context_matched", None):
                        state.state = f"{target_id}/context_matched"
                        state.transaction_safe = True
                        break
                    if self._target_matches(source_id, state.actual, target, "default_only", None):
                        state.state = f"{target_id}/default_only"
                        state.transaction_safe = True
                        break
                    for index, variant in enumerate(target["variants"]):
                        if self._target_matches(source_id, state.actual, target, "fixed_variant", variant):
                            state.state = f"{target_id}/fixed_variant/{index}"
                            state.transaction_safe = True
                            break
                    if state.transaction_safe:
                        break

            if not state.transaction_safe:
                fixed_key: int | None = None
                uniform = True
                for row in source["sorted_rows"]:
                    pair = state.actual[row]
                    if pair[0] == 0 or pair[0] != pair[1]:
                        uniform = False
                        break
                    if fixed_key is None:
                        fixed_key = pair[0]
                    elif pair[0] != fixed_key:
                        uniform = False
                        break
                if uniform and fixed_key is not None:
                    state.state = f"uniform_fixed_key/{fixed_key}"
                    state.transaction_safe = True

            if not state.transaction_safe:
                all_safe = False
                for row in source["sorted_rows"]:
                    if len(unknown) >= 12:
                        break
                    pair = state.actual[row]
                    unknown.append(f"{source_id}/row{row}={pair[0]},{pair[1]}")

        return CostumeLayout(
            base=base,
            inner=base + inner_offset,
            row_offset_table=base + row_table_offset,
            row_offsets=row_offsets,
            sources=states,
            source_rows=total_source_rows,
            transaction_safe=all_safe,
            unknown_details=unknown,
        )

    def _unique_validated(self, candidates: list[int], label: str, validator: Any) -> Any:
        valid: list[Any] = []
        for base in candidates:
            try:
                valid.append(validator(base))
            except (TrainerError, MemoryAccessError) as exc:
                self.log.info("REJECT label=%s hit=0x%X reason=%s", label, base, exc)
        if not valid:
            raise TrainerError(f"no validated {label} block")
        if len(valid) > 1:
            bases = ", ".join(f"0x{item.base:X}" for item in valid)
            raise TrainerError(f"multiple validated {label} blocks: {bases}")
        return valid[0]

    def validate_all(self) -> OperationResult:
        with self.lock:
            try:
                pid = self.memory.find_pid(GAME_PROCESS)
                if pid is None:
                    raise TrainerError("likeadragon8.exe is not running")
                if self.pid is not None and self.pid != pid:
                    self._clear_process_state(f"new PID {pid}")
                self.memory.open(pid)
                self.pid = pid
                candidates = self.memory.scan_armp_headers({CHARACTER_ROWS, COSTUME_OUTER_ROWS})
                self.log.info(
                    "FAST_SCAN character_hits=%d costume_hits=%d",
                    len(candidates[CHARACTER_ROWS]), len(candidates[COSTUME_OUTER_ROWS]),
                )
                try:
                    character = self._unique_validated(
                        candidates[CHARACTER_ROWS], "character_character_data", self.validate_character_db
                    )
                    costume = self._unique_validated(
                        candidates[COSTUME_OUTER_ROWS], "character_costume", self.validate_costume_db
                    )
                except TrainerError as fast_error:
                    full_scan = getattr(self.memory, "scan_armp_headers_full", None)
                    if not callable(full_scan):
                        raise
                    self.log.info("FAST_SCAN_FALLBACK reason=%s", fast_error)
                    candidates = full_scan({CHARACTER_ROWS, COSTUME_OUTER_ROWS})
                    self.log.info(
                        "FULL_SCAN character_hits=%d costume_hits=%d",
                        len(candidates[CHARACTER_ROWS]), len(candidates[COSTUME_OUTER_ROWS]),
                    )
                    character = self._unique_validated(
                        candidates[CHARACTER_ROWS], "character_character_data", self.validate_character_db
                    )
                    costume = self._unique_validated(
                        candidates[COSTUME_OUTER_ROWS], "character_costume", self.validate_costume_db
                    )
                self.character = character
                self.costume = costume
                states = ", ".join(
                    f"{source_id}={costume.sources[source_id].state}"
                    for source_id in self.repository.source_order
                )
                warning = "" if costume.transaction_safe else " | source state is not transaction-safe"
                message = (
                    f"READY | PID {pid} | Character 0x{character.base:X} | "
                    f"Costume 0x{costume.base:X} | {states}{warning}"
                )
                self._set_message(message)
                if costume.unknown_details:
                    self.log.info("UNKNOWN %s", "; ".join(costume.unknown_details))
                return OperationResult(True, message)
            except (TrainerError, MemoryAccessError, OSError) as exc:
                self.character = None
                self.costume = None
                message = str(exc)
                self._set_message(f"CONNECT ERROR: {message}")
                return OperationResult(False, message)

    def revalidate_cached_layouts(self) -> OperationResult:
        """Strictly revalidate already located bases without a full memory scan."""
        with self.lock:
            try:
                if not self.pid or not self.character or not self.costume:
                    raise TrainerError("database layout cache is missing")
                if self.memory.find_pid(GAME_PROCESS) != self.pid:
                    raise TrainerError("game process changed")
                old_mapping = self.character.mapping
                old_row_table = self.costume.row_offset_table
                character = self.validate_character_db(self.character.base)
                costume = self.validate_costume_db(self.costume.base)
                if character.mapping != old_mapping or costume.row_offset_table != old_row_table:
                    raise TrainerError("validated runtime table layout changed")
                self.character = character
                self.costume = costume
                message = (
                    f"READY | PID {self.pid} | Character 0x{character.base:X} | "
                    f"Costume 0x{costume.base:X} | cached layout revalidated"
                )
                self._set_message(message)
                return OperationResult(True, message)
            except Exception as exc:
                message = str(exc)
                self._set_message(f"REVALIDATE ERROR: {message}")
                return OperationResult(False, message)

    def prepare_custom_target(self, value: str) -> tuple[OperationResult, dict[str, Any] | None]:
        with self.lock:
            text = str(value or "").strip()
            try:
                key = int(text, 16) if text.lower().startswith("0x") else int(text, 10)
            except ValueError:
                return OperationResult(False, "请输入正十进制或十六进制 Character key"), None
            if not 0 < key <= 0xFFFF:
                return OperationResult(False, "Character key 必须在 1..65535（Costume u16）范围内"), None
            source_keys = {
                entry["key"]
                for source in self.repository.sources.values()
                for entry in source["context_entries"]
            }
            if key in source_keys:
                return OperationResult(False, "这是主角上下文 key，请输入目标 *character key"), None
            if not self.character:
                result = self.validate_all()
                if not result.ok:
                    return result, None
            assert self.character is not None
            try:
                layout = self.validate_character_db(self.character.base)
                low, high = 0, CHARACTER_ROWS - 1
                position: int | None = None
                while low <= high:
                    middle = (low + high) // 2
                    candidate = self.memory.read_u32(layout.key_array + middle * 4)
                    if candidate == key:
                        position = middle
                        break
                    if candidate < key:
                        low = middle + 1
                    else:
                        high = middle - 1
                if position is None:
                    raise TrainerError(f"Character key not found: {key}")
                row = self.memory.read_u32(layout.mapping + position * 4)
                if not 0 <= row < CHARACTER_ROWS:
                    raise TrainerError(f"invalid Character row for key {key}")
                target = self.repository.register_custom(key, row, self.pid)
                message = f"CUSTOM TARGET READY | key {key} → row {row}"
                self._set_message(message)
                return OperationResult(True, message), target
            except (TrainerError, MemoryAccessError) as exc:
                return OperationResult(False, str(exc)), None

    def _normalize_selection(self, slots: dict[str, SlotSelection]) -> MultiSelection:
        if not slots:
            raise TrainerError("at least one protagonist slot must be configured")
        normalized: dict[str, SlotSelection] = {}
        for source_id, slot in slots.items():
            if source_id not in self.repository.source_order:
                raise TrainerError(f"unsupported source {source_id}")
            target = self.repository.get_target(slot.target_id)
            if target is None:
                raise TrainerError(f"unknown target {slot.target_id}")
            if target.get("kind") == "custom" and (
                not target.get("resolved_pid") or target.get("resolved_pid") != self.pid
            ):
                raise TrainerError(
                    f"custom key target for {source_id} belongs to an old game process; resolve it again"
                )
            for field in ("standard_character", "standard_hawaii"):
                if not 0 < int(target[field]) <= 0xFFFF:
                    raise TrainerError(f"target {field} is outside the Costume u16 range")
            mode = slot.mode
            variant_index = slot.variant_index
            if target["fixed_npc"]:
                mode = "fixed_variant"
                variant_index = 0
            if mode not in {"context_matched", "default_only", "fixed_variant"}:
                raise TrainerError(f"unsupported outfit mode {mode}")
            if mode == "fixed_variant":
                if variant_index is None or not 0 <= variant_index < len(target["variants"]):
                    raise TrainerError(f"invalid fixed variant for {source_id}")
                if target["variants"][variant_index].get("character_row") is None:
                    raise TrainerError(f"fixed variant has no Character row for {source_id}")
                pair = self._fixed_variant_pair(target["variants"][variant_index])
                if pair is None or any(not 0 < value <= 0xFFFF for value in pair):
                    raise TrainerError(f"fixed variant is outside the Costume u16 range for {source_id}")
            normalized[source_id] = SlotSelection(slot.target_id, mode, variant_index)
        return MultiSelection(normalized)

    def _capture_snapshot(self) -> Snapshot:
        if not self.pid or not self.character or not self.costume:
            raise TrainerError("databases are not connected")
        identity: list[IdentityBackup] = []
        costume_items: list[CostumeBackup] = []
        for source_id in self.repository.source_order:
            source = self.repository.sources[source_id]
            for entry in source["context_entries"]:
                address = self.character.mapping + entry["position"] * 4
                identity.append(IdentityBackup(
                    source_id, entry["key"], address, self.memory.read_u32(address)
                ))
            for row in source["sorted_rows"]:
                expected = source["records"][row]
                row_address = self.costume.base + self.costume.row_offsets[row]
                costume_items.append(CostumeBackup(
                    source_id=source_id,
                    row=row,
                    costume=expected["costume"],
                    character_address=row_address + 0x04,
                    hawaii_address=row_address + 0x06,
                    character=self.memory.read_u16(row_address + 0x04),
                    hawaii=self.memory.read_u16(row_address + 0x06),
                ))
        if len(identity) != 101 or len(costume_items) != 128:
            raise TrainerError(
                f"dual snapshot count mismatch identity={len(identity)} costume={len(costume_items)}"
            )
        return Snapshot(
            pid=self.pid,
            character_base=self.character.base,
            costume_base=self.costume.base,
            identity=identity,
            costume=costume_items,
        )

    @staticmethod
    def _backup_identity(snapshot: Snapshot, source_id: str, key: int) -> int:
        for item in snapshot.identity:
            if item.source_id == source_id and item.key == key:
                return item.value
        raise TrainerError(f"missing identity backup source={source_id} key={key}")

    @staticmethod
    def _backup_costume(snapshot: Snapshot, source_id: str, row: int) -> tuple[int, int]:
        for item in snapshot.costume:
            if item.source_id == source_id and item.row == row:
                return item.character, item.hawaii
        raise TrainerError(f"missing Costume backup source={source_id} row={row}")

    def _snapshot_is_vanilla(self, snapshot: Snapshot) -> bool:
        """Return whether a captured runtime snapshot matches the embedded game values."""
        identity = {
            (item.source_id, item.key): item.value for item in snapshot.identity
        }
        costume = {
            (item.source_id, item.row): (item.character, item.hawaii)
            for item in snapshot.costume
        }
        for source_id in self.repository.source_order:
            source = self.repository.sources[source_id]
            for entry in source["context_entries"]:
                if identity.get((source_id, entry["key"])) != entry["original_row"]:
                    return False
            for row in source["sorted_rows"]:
                record = source["records"][row]
                expected = (record["original_character"], record["original_hawaii"])
                if costume.get((source_id, row)) != expected:
                    return False
        return True

    def backup_is_vanilla(self) -> bool | None:
        """Describe the first-Apply snapshot without touching the game process."""
        with self.lock:
            if self.backup is None:
                return None
            return self._snapshot_is_vanilla(self.backup)

    def _expected_identity(
        self, selection: MultiSelection, source_id: str, entry: dict[str, int], backup: Snapshot
    ) -> int:
        slot = selection.slots.get(source_id)
        if slot is None:
            return self._backup_identity(backup, source_id, entry["key"])
        target = self.repository.targets[slot.target_id]
        if slot.mode == "fixed_variant":
            assert slot.variant_index is not None
            return int(target["variants"][slot.variant_index]["character_row"])
        return int(target["target_row"])

    def _expected_costume(
        self, selection: MultiSelection, source_id: str, row: int, backup: Snapshot
    ) -> tuple[int, int]:
        slot = selection.slots.get(source_id)
        if slot is None:
            return self._backup_costume(backup, source_id, row)
        target = self.repository.targets[slot.target_id]
        if target["fixed_npc"]:
            return target["standard_character"], target["standard_hawaii"]
        if slot.mode == "default_only":
            return target["standard_character"], target["standard_hawaii"]
        if slot.mode == "fixed_variant":
            assert slot.variant_index is not None
            pair = self._fixed_variant_pair(target["variants"][slot.variant_index])
            if pair is None:
                raise TrainerError(f"invalid fixed variant target={slot.target_id}")
            return pair
        pair = target["source_plans"].get(source_id, {}).get(row)
        if pair is None:
            raise TrainerError(f"missing context-matched pair target={slot.target_id} source={source_id} row={row}")
        return pair

    def _verify_selection(self, selection: MultiSelection, backup: Snapshot) -> None:
        assert self.character and self.costume
        for source_id in self.repository.source_order:
            source = self.repository.sources[source_id]
            for entry in source["context_entries"]:
                expected = self._expected_identity(selection, source_id, entry, backup)
                actual = self.memory.read_u32(self.character.mapping + entry["position"] * 4)
                if actual != expected:
                    raise TrainerError(
                        f"identity verification failed source={source_id} key={entry['key']} "
                        f"expected={expected} actual={actual}"
                    )
            for row in source["sorted_rows"]:
                expected = self._expected_costume(selection, source_id, row, backup)
                row_address = self.costume.base + self.costume.row_offsets[row]
                actual = (
                    self.memory.read_u16(row_address + 0x04),
                    self.memory.read_u16(row_address + 0x06),
                )
                if actual != expected:
                    raise TrainerError(
                        f"Costume verification failed source={source_id} row={row} "
                        f"expected={expected[0]},{expected[1]} actual={actual[0]},{actual[1]}"
                    )

    def _write_selection(self, selection: MultiSelection, backup: Snapshot) -> None:
        assert self.character and self.costume
        # Preserve the CT's proven write order: all Costume cells, then identity mappings.
        for source_id in self.repository.source_order:
            source = self.repository.sources[source_id]
            for row in source["sorted_rows"]:
                character, hawaii = self._expected_costume(selection, source_id, row, backup)
                row_address = self.costume.base + self.costume.row_offsets[row]
                self.memory.write_u16(row_address + 0x04, character)
                self.memory.write_u16(row_address + 0x06, hawaii)
        for source_id in self.repository.source_order:
            source = self.repository.sources[source_id]
            for entry in source["context_entries"]:
                expected = self._expected_identity(selection, source_id, entry, backup)
                self.memory.write_u32(self.character.mapping + entry["position"] * 4, expected)
        self._verify_selection(selection, backup)

    def _validate_backup_bases(self, snapshot: Snapshot) -> None:
        current_pid = self.memory.find_pid(GAME_PROCESS)
        if current_pid != snapshot.pid:
            raise TrainerError("game process changed")
        character = self.validate_character_db(snapshot.character_base)
        costume = self.validate_costume_db(snapshot.costume_base)
        identity_addresses = {
            (item.source_id, item.key): item.address for item in snapshot.identity
        }
        costume_addresses = {
            (item.source_id, item.row): (item.character_address, item.hawaii_address)
            for item in snapshot.costume
        }
        for source_id in self.repository.source_order:
            source = self.repository.sources[source_id]
            for entry in source["context_entries"]:
                expected = character.mapping + entry["position"] * 4
                if identity_addresses.get((source_id, entry["key"])) != expected:
                    raise TrainerError("validated Character mapping layout changed")
            for row in source["sorted_rows"]:
                row_address = costume.base + costume.row_offsets[row]
                if costume_addresses.get((source_id, row)) != (row_address + 0x04, row_address + 0x06):
                    raise TrainerError("validated Costume row layout changed")
        self.pid = snapshot.pid
        self.character = character
        self.costume = costume

    def _restore_snapshot(self, snapshot: Snapshot) -> None:
        self._validate_backup_bases(snapshot)
        for item in snapshot.costume:
            self.memory.write_u16(item.character_address, item.character)
            self.memory.write_u16(item.hawaii_address, item.hawaii)
        for item in snapshot.identity:
            self.memory.write_u32(item.address, item.value)
        for item in snapshot.costume:
            actual = (
                self.memory.read_u16(item.character_address),
                self.memory.read_u16(item.hawaii_address),
            )
            if actual != (item.character, item.hawaii):
                raise TrainerError(f"restore verification failed Costume row={item.row}")
        for item in snapshot.identity:
            if self.memory.read_u32(item.address) != item.value:
                raise TrainerError(f"restore verification failed identity key={item.key}")

    def apply(self, slots: dict[str, SlotSelection]) -> OperationResult:
        with self.lock:
            try:
                if self.recovery_required:
                    raise TrainerError(
                        "the previous write and rollback were both incomplete; Restore is required before another Apply"
                    )
                selection = self._normalize_selection(slots)
                was_active = self.active
                prior_selection = self.active_selection
                if not was_active:
                    located = self.revalidate_cached_layouts() if self.connected else self.validate_all()
                    # A live table can relocate after a load. Fall back to one
                    # full scan only when the cached bases no longer validate.
                    if not located.ok:
                        located = self.validate_all()
                    if not located.ok:
                        raise TrainerError(located.message)
                    assert self.costume is not None
                    if not self.costume.transaction_safe:
                        states = ", ".join(
                            f"{source_id}={self.costume.sources[source_id].state}"
                            for source_id in self.repository.source_order
                        )
                        raise TrainerError(f"refusing first write: Costume states are {states}")
                    original = self._capture_snapshot()
                    rollback = original
                    self.log.info(
                        "BACKUP pid=%d identity=%d costume_rows=%d dual_source=true",
                        original.pid, len(original.identity), len(original.costume),
                    )
                else:
                    assert self.backup is not None and self.active_selection is not None
                    self._validate_backup_bases(self.backup)
                    self._verify_selection(self.active_selection, self.backup)
                    original = self.backup
                    rollback = self._capture_snapshot()

                try:
                    self._write_selection(selection, original)
                except Exception as write_error:
                    try:
                        self._restore_snapshot(rollback)
                    except Exception as rollback_error:
                        self.backup = original
                        self.active_selection = None
                        self.recovery_required = True
                        raise TrainerError(
                            f"write failed: {write_error}; rollback also failed: {rollback_error}"
                        ) from rollback_error
                    self.backup = original if was_active else None
                    self.active_selection = prior_selection if was_active else None
                    self.recovery_required = False
                    raise TrainerError(f"write failed; pre-switch state restored: {write_error}") from write_error

                self.backup = original
                self.active_selection = selection
                self.recovery_required = False
                summary = []
                for source_id in self.repository.source_order:
                    slot = selection.slots.get(source_id)
                    if slot:
                        target = self.repository.targets[slot.target_id]
                        summary.append(f"{source_id}→{target['label']} [{slot.mode}]")
                    else:
                        summary.append(f"{source_id}→backup")
                message = "APPLIED & VERIFIED | " + " | ".join(summary)
                self._set_message(message)
                self.log.info(
                    "APPLY slots=%s identity=101 costume_rows=128 verified=true",
                    {key: vars(value) for key, value in selection.slots.items()},
                )
                return OperationResult(True, message)
            except Exception as exc:
                message = str(exc)
                self._set_message(f"APPLY ERROR: {message}")
                return OperationResult(False, message)

    def restore(self, reason: str = "user") -> OperationResult:
        with self.lock:
            if self.backup is None:
                self.active_selection = None
                self.recovery_required = False
                return OperationResult(True, "nothing to restore")
            if self.memory.find_pid(GAME_PROCESS) != self.backup.pid:
                self.log.info(
                    "RESTORE_SKIPPED old_pid=%s new_pid=%s reason=%s",
                    self.backup.pid, self.memory.find_pid(GAME_PROCESS), reason,
                )
                self._clear_process_state("stale PID during Restore")
                return OperationResult(True, "old game process ended; stale backup discarded")
            try:
                snapshot = self.backup
                self._restore_snapshot(snapshot)
                self.log.info(
                    "RESTORE reason=%s identity=%d costume_rows=%d verified=true",
                    reason, len(snapshot.identity), len(snapshot.costume),
                )
                self.backup = None
                self.active_selection = None
                self.recovery_required = False
                message = "RESTORED & VERIFIED | both protagonist sources returned to the first backup"
                self._set_message(message)
                return OperationResult(True, message)
            except Exception as exc:
                self.recovery_required = True
                message = str(exc)
                self._set_message(f"RESTORE CRITICAL: {message}")
                return OperationResult(False, message)

    def _write_vanilla(self) -> None:
        assert self.character and self.costume
        for source_id in self.repository.source_order:
            source = self.repository.sources[source_id]
            for row in source["sorted_rows"]:
                expected = source["records"][row]
                row_address = self.costume.base + self.costume.row_offsets[row]
                self.memory.write_u16(row_address + 0x04, expected["original_character"])
                self.memory.write_u16(row_address + 0x06, expected["original_hawaii"])
        for source_id in self.repository.source_order:
            source = self.repository.sources[source_id]
            for entry in source["context_entries"]:
                self.memory.write_u32(
                    self.character.mapping + entry["position"] * 4, entry["original_row"]
                )
        for source_id in self.repository.source_order:
            source = self.repository.sources[source_id]
            for row in source["sorted_rows"]:
                expected = source["records"][row]
                row_address = self.costume.base + self.costume.row_offsets[row]
                actual = (
                    self.memory.read_u16(row_address + 0x04),
                    self.memory.read_u16(row_address + 0x06),
                )
                vanilla = (expected["original_character"], expected["original_hawaii"])
                if actual != vanilla:
                    raise TrainerError(f"vanilla Costume verification failed source={source_id} row={row}")
            for entry in source["context_entries"]:
                actual = self.memory.read_u32(self.character.mapping + entry["position"] * 4)
                if actual != entry["original_row"]:
                    raise TrainerError(f"vanilla identity verification failed key={entry['key']}")

    def force_vanilla_reset(self, reason: str = "user") -> OperationResult:
        with self.lock:
            located = self.validate_all()
            if not located.ok:
                return located
            try:
                rollback = self._capture_snapshot()
                try:
                    self._write_vanilla()
                except (TrainerError, MemoryAccessError) as write_error:
                    try:
                        self._restore_snapshot(rollback)
                    except (TrainerError, MemoryAccessError) as rollback_error:
                        raise TrainerError(
                            f"vanilla reset failed: {write_error}; rollback failed: {rollback_error}"
                        ) from rollback_error
                    raise TrainerError(f"vanilla reset failed; previous state restored: {write_error}")
                self.backup = None
                self.active_selection = None
                self.recovery_required = False
                message = "VANILLA RESET COMPLETE | 101 identity mappings + 128 Costume rows verified"
                self._set_message(message)
                self.log.info("VANILLA_RESET reason=%s verified=true", reason)
                return OperationResult(True, message)
            except Exception as exc:
                message = str(exc)
                self._set_message(f"RESET CRITICAL: {message}")
                return OperationResult(False, message)

    def restore_game_original(self, reason: str = "user") -> OperationResult:
        """Restore embedded game values, using the snapshot only when it is already vanilla."""
        with self.lock:
            if self.backup is not None and self._snapshot_is_vanilla(self.backup):
                return self.restore(reason)
            return self.force_vanilla_reset(reason)

    def status_snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                "pid": self.pid,
                "connected": self.connected,
                "active": self.active,
                "recovery_required": self.recovery_required,
                "backup": self.backup is not None,
                "backup_is_vanilla": self.backup_is_vanilla(),
                "character_base": self.character.base if self.character else None,
                "costume_base": self.costume.base if self.costume else None,
                "states": {
                    source_id: self.costume.sources[source_id].state
                    for source_id in self.repository.source_order
                } if self.costume else {},
                "message": self.last_message,
            }

    def close(self) -> None:
        with self.lock:
            self.memory.close()
            self.pid = None
            self.character = None
            self.costume = None
            self.backup = None
            self.active_selection = None
            self.recovery_required = False
