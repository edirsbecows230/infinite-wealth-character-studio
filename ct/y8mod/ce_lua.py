"""Single Cheat Engine Lua syntax validator for CT/trainer builders."""

from __future__ import annotations

import ctypes
import os
from pathlib import Path

from .errors import ValidationError


CE_LUA_ENV = "CE_LUA_DLL"
DEFAULT_CANDIDATES = (
    Path(r"C:\Program Files\Cheat Engine\lua53-64.dll"),
    Path(r"C:\Program Files\Cheat Engine 7.5\lua53-64.dll"),
    Path(r"C:\Program Files\Cheat Engine 7.6\lua53-64.dll"),
    Path(r"C:\Program Files\Cheat Engine 7.7\lua53-64.dll"),
)


def find_ce_lua() -> Path | None:
    configured = os.environ.get(CE_LUA_ENV)
    candidates = (Path(configured), *DEFAULT_CANDIDATES) if configured else DEFAULT_CANDIDATES
    return next((path.resolve() for path in candidates if path.is_file()), None)


def compile_ce_lua(
    lua_source: str,
    *,
    chunk_name: str,
    required: bool = False,
) -> str:
    """Return ``checked`` or ``skipped``; never report a silent success.

    Release/check mode passes ``required=True`` so a missing CE Lua runtime is
    a validation failure. Development generation may skip it, but callers must
    display the returned status.
    """
    dll_path = find_ce_lua()
    if dll_path is None:
        if required:
            raise ValidationError(
                f"CE Lua validation required but lua53-64.dll was not found; "
                f"set {CE_LUA_ENV} to its full path")
        return "skipped"

    try:
        dll = ctypes.WinDLL(str(dll_path))
    except (AttributeError, OSError) as exc:
        raise ValidationError(f"cannot load CE Lua runtime {dll_path}: {exc}") from exc
    dll.luaL_newstate.restype = ctypes.c_void_p
    dll.luaL_loadbufferx.argtypes = [
        ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t,
        ctypes.c_char_p, ctypes.c_char_p,
    ]
    dll.luaL_loadbufferx.restype = ctypes.c_int
    dll.lua_tolstring.argtypes = [
        ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_size_t),
    ]
    dll.lua_tolstring.restype = ctypes.c_char_p
    dll.lua_close.argtypes = [ctypes.c_void_p]
    state = dll.luaL_newstate()
    if not state:
        raise ValidationError("CE Lua luaL_newstate failed")
    raw = lua_source.encode("utf-8")
    try:
        result = dll.luaL_loadbufferx(
            state, raw, len(raw), chunk_name.encode("utf-8"), None)
        if result:
            size = ctypes.c_size_t()
            message = dll.lua_tolstring(state, -1, ctypes.byref(size))
            text = message[:size.value].decode("utf-8", "replace") if message else str(result)
            raise ValidationError("CE Lua compile failed: " + text)
    finally:
        dll.lua_close(state)
    return "checked"

