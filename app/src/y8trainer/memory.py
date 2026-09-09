from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import os
import struct
from collections.abc import Iterator


PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_OPERATION = 0x0008
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_ACCESS = (
    PROCESS_QUERY_INFORMATION | PROCESS_VM_OPERATION | PROCESS_VM_READ | PROCESS_VM_WRITE
)

TH32CS_SNAPPROCESS = 0x00000002
MEM_COMMIT = 0x1000
PAGE_NOACCESS = 0x01
PAGE_READONLY = 0x02
PAGE_READWRITE = 0x04
PAGE_WRITECOPY = 0x08
PAGE_EXECUTE = 0x10
PAGE_EXECUTE_READ = 0x20
PAGE_EXECUTE_READWRITE = 0x40
PAGE_EXECUTE_WRITECOPY = 0x80
PAGE_GUARD = 0x100
NONEXEC_READABLE = {PAGE_READONLY, PAGE_READWRITE, PAGE_WRITECOPY}
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
WAIT_TIMEOUT = 0x00000102

ARMP_PREFIX = bytes.fromhex(
    "61 72 6D 70 00 00 00 00 00 00 02 00 00 00 00 00"
)

# The current Steam build's runtime allocator has produced these same bases
# across every captured process. They are hints only: strict structural
# validation still runs before any write, and targeted/full scans remain as
# fallbacks when ASLR, a patch, or a different build relocates either table.
KNOWN_ARMP_BASE_HINTS = {
    10646: (0x252B60000,),
    61: (0x1D38115C0,),
}


class MemoryAccessError(RuntimeError):
    pass


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD),
        ("cntUsage", wt.DWORD),
        ("th32ProcessID", wt.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wt.DWORD),
        ("cntThreads", wt.DWORD),
        ("th32ParentProcessID", wt.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wt.DWORD),
        ("szExeFile", wt.WCHAR * 260),
    ]


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wt.DWORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wt.DWORD),
        ("Protect", wt.DWORD),
        ("Type", wt.DWORD),
    ]


if os.name == "nt":
    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
    _k32.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
    _k32.Process32FirstW.restype = wt.BOOL
    _k32.Process32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    _k32.Process32NextW.restype = wt.BOOL
    _k32.Process32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    _k32.OpenProcess.restype = wt.HANDLE
    _k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
    _k32.CloseHandle.restype = wt.BOOL
    _k32.CloseHandle.argtypes = [wt.HANDLE]
    _k32.ReadProcessMemory.restype = wt.BOOL
    _k32.ReadProcessMemory.argtypes = [
        wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    _k32.WriteProcessMemory.restype = wt.BOOL
    _k32.WriteProcessMemory.argtypes = [
        wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    _k32.VirtualQueryEx.restype = ctypes.c_size_t
    _k32.VirtualQueryEx.argtypes = [
        wt.HANDLE, ctypes.c_void_p, ctypes.POINTER(MEMORY_BASIC_INFORMATION),
        ctypes.c_size_t,
    ]
    _k32.WaitForSingleObject.restype = wt.DWORD
    _k32.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
else:  # pragma: no cover - release is Windows-only
    _k32 = None


def _last_error(context: str) -> MemoryAccessError:
    code = ctypes.get_last_error()
    message = ctypes.FormatError(code).strip() if code else "unknown Windows error"
    return MemoryAccessError(f"{context}: {message} (WinError {code})")


class NativeProcessMemory:
    """Minimal, debugger-free Windows process memory backend."""

    def __init__(self) -> None:
        if _k32 is None:
            raise OSError("The native trainer only runs on Windows")
        self.handle: int | None = None
        self.pid: int | None = None

    @staticmethod
    def find_pid(exe_name: str) -> int | None:
        snapshot = _k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if not snapshot or int(snapshot) == INVALID_HANDLE_VALUE:
            return None
        try:
            entry = PROCESSENTRY32W()
            entry.dwSize = ctypes.sizeof(entry)
            if not _k32.Process32FirstW(snapshot, ctypes.byref(entry)):
                return None
            wanted = exe_name.casefold()
            while True:
                if entry.szExeFile.casefold() == wanted:
                    return int(entry.th32ProcessID)
                if not _k32.Process32NextW(snapshot, ctypes.byref(entry)):
                    return None
        finally:
            _k32.CloseHandle(snapshot)

    def open(self, pid: int) -> None:
        if self.pid == pid and self.handle and self.is_handle_alive():
            return
        self.close()
        handle = _k32.OpenProcess(PROCESS_ACCESS, False, pid)
        if not handle:
            raise _last_error(
                f"Unable to open likeadragon8.exe PID {pid}; run the trainer at the same privilege level as the game"
            )
        self.handle = int(handle)
        self.pid = int(pid)

    def close(self) -> None:
        if self.handle:
            _k32.CloseHandle(self.handle)
        self.handle = None
        self.pid = None

    def is_handle_alive(self) -> bool:
        return bool(self.handle) and _k32.WaitForSingleObject(self.handle, 0) == WAIT_TIMEOUT

    def is_alive(self, pid: int | None = None) -> bool:
        wanted = self.pid if pid is None else pid
        return bool(wanted) and self.find_pid("likeadragon8.exe") == wanted

    def _require_handle(self) -> int:
        if not self.handle:
            raise MemoryAccessError("game process is not open")
        return self.handle

    def read(self, address: int, size: int) -> bytes:
        handle = self._require_handle()
        if address < 0x10000 or size < 0:
            raise MemoryAccessError(f"invalid read 0x{address:X} + {size}")
        buffer = ctypes.create_string_buffer(size)
        received = ctypes.c_size_t()
        ok = _k32.ReadProcessMemory(
            handle, ctypes.c_void_p(address), buffer, size, ctypes.byref(received)
        )
        if not ok or received.value != size:
            raise _last_error(f"ReadProcessMemory 0x{address:X} + {size}")
        return buffer.raw

    def try_read(self, address: int, size: int) -> bytes | None:
        try:
            return self.read(address, size)
        except MemoryAccessError:
            return None

    def write(self, address: int, data: bytes) -> None:
        handle = self._require_handle()
        if address < 0x10000 or not data:
            raise MemoryAccessError(f"invalid write 0x{address:X} + {len(data)}")
        buffer = ctypes.create_string_buffer(data, len(data))
        written = ctypes.c_size_t()
        ok = _k32.WriteProcessMemory(
            handle, ctypes.c_void_p(address), buffer, len(data), ctypes.byref(written)
        )
        if not ok or written.value != len(data):
            raise _last_error(f"WriteProcessMemory 0x{address:X} + {len(data)}")

    def read_u16(self, address: int) -> int:
        return struct.unpack("<H", self.read(address, 2))[0]

    def read_u32(self, address: int) -> int:
        return struct.unpack("<I", self.read(address, 4))[0]

    def write_u16(self, address: int, value: int) -> None:
        self.write(address, struct.pack("<H", value))

    def write_u32(self, address: int, value: int) -> None:
        self.write(address, struct.pack("<I", value))

    def iter_readable_regions(
        self,
        maximum: int = 0x7FFFFFFFFFFF,
        private_only: bool = False,
    ) -> Iterator[tuple[int, int]]:
        handle = self._require_handle()
        address = 0
        info = MEMORY_BASIC_INFORMATION()
        while address < maximum:
            result = _k32.VirtualQueryEx(
                handle, ctypes.c_void_p(address), ctypes.byref(info), ctypes.sizeof(info)
            )
            if not result:
                return
            base = int(info.BaseAddress or 0)
            region_size = int(info.RegionSize or 0)
            if region_size <= 0:
                return
            protect = int(info.Protect)
            if (
                int(info.State) == MEM_COMMIT
                and not (protect & PAGE_GUARD)
                and (protect & 0xFF) in NONEXEC_READABLE
                and (not private_only or int(info.Type) == 0x20000)
            ):
                yield base, region_size
            next_address = base + region_size
            if next_address <= address:
                return
            address = next_address

    def scan_armp_headers(self, outer_rows: set[int]) -> dict[int, list[int]]:
        """Probe validated build hints, then scan the low private game heap.

        Both target tables currently live below 0x400000000 in private RW
        memory. Restricting the compatibility scan to that range reduces the
        search set from roughly 10.5 GiB to roughly 1 GiB. The engine still
        falls back to `scan_armp_headers_full` if validation finds no block.
        """
        matches = {row_count: [] for row_count in outer_rows}
        seen: set[int] = set()
        for row_count in outer_rows:
            for address in KNOWN_ARMP_BASE_HINTS.get(row_count, ()):
                header = self.try_read(address, 40)
                if header is not None:
                    self._collect_armp_headers(header, address, matches, seen)
        if all(matches[row_count] for row_count in outer_rows):
            return matches
        return self._scan_regions(
            outer_rows,
            self.iter_readable_regions(maximum=0x400000000, private_only=True),
        )

    def _scan_regions(
        self,
        outer_rows: set[int],
        regions: Iterator[tuple[int, int]],
    ) -> dict[int, list[int]]:
        matches = {row_count: [] for row_count in outer_rows}
        seen: set[int] = set()
        overlap = 39
        for region_base, region_size in regions:
            cursor = region_base
            region_end = min(region_base + region_size, 0x7FFFFFFFFFFF)
            carry = b""
            while cursor < region_end:
                chunk_size = min(0x800000, region_end - cursor)
                chunk = self.try_read(cursor, chunk_size)
                if chunk is None:
                    break
                data = carry + chunk
                self._collect_armp_headers(data, cursor - len(carry), matches, seen)
                carry = data[-overlap:] if len(data) >= overlap else data
                cursor += chunk_size
        return matches

    @staticmethod
    def _collect_armp_headers(
        data: bytes,
        data_base: int,
        matches: dict[int, list[int]],
        seen: set[int],
    ) -> None:
        search_at = 0
        while True:
            found = data.find(ARMP_PREFIX, search_at)
            if found < 0:
                return
            address = data_base + found
            header = data[found:found + 40]
            if address not in seen and len(header) == 40 and header[20:32] == b"\0" * 12:
                row_count = int.from_bytes(header[32:36], "little")
                columns = int.from_bytes(header[36:40], "little")
                if row_count in matches and columns == 3:
                    matches[row_count].append(address)
                    seen.add(address)
            search_at = found + 1

    def scan_armp_headers_full(self, outer_rows: set[int]) -> dict[int, list[int]]:
        """Compatibility fallback that scans every non-executable readable byte."""
        return self._scan_regions(outer_rows, self.iter_readable_regions())

    def __enter__(self) -> "NativeProcessMemory":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
