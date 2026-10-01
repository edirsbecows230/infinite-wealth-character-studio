"""User overlays for the Character Finder; never edits bundled catalogs."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


def default_state_path() -> Path:
    from PySide6.QtCore import QStandardPaths

    return Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)) / "character_finder.json"


class FinderUserState:
    """One free-text alias per target and favorites, saved with atomic replace.

    A None path is an in-memory store for tests and non-interactive callers.
    Unknown target IDs can remain on disk; the repository filters them out.
    """

    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self.favorites: set[str] = set()
        self.aliases: dict[str, str] = {}
        self.load_error = ""
        self.last_error = ""
        if path is not None:
            self._load()

    def _load(self) -> None:
        try:
            document = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(document, dict) or document.get("schema", 1) != 1:
                raise ValueError("unsupported Character Finder configuration")
            favorites = document.get("favorites", [])
            aliases = document.get("aliases", {})
            if isinstance(favorites, list):
                self.favorites = {x for x in favorites if isinstance(x, str)}
            if isinstance(aliases, dict):
                self.aliases = {
                    k: v.strip() for k, v in aliases.items()
                    if isinstance(k, str) and isinstance(v, str) and v.strip()
                }
        except FileNotFoundError:
            pass
        except (OSError, ValueError, UnicodeError) as exc:
            self.load_error = str(exc)

    def alias(self, target_id: str) -> str:
        return self.aliases.get(target_id, "")

    def is_favorite(self, target_id: str) -> bool:
        return target_id in self.favorites

    def set_favorite(self, target_id: str, enabled: bool) -> bool:
        favorites = self.favorites.copy()
        if enabled:
            favorites.add(target_id)
        else:
            favorites.discard(target_id)
        return self._commit(favorites, self.aliases.copy())

    def set_alias(self, target_id: str, alias: str) -> bool:
        aliases = self.aliases.copy()
        text = alias.strip()
        if text:
            aliases[target_id] = text
        else:
            aliases.pop(target_id, None)
        return self._commit(self.favorites.copy(), aliases)

    def _commit(self, favorites: set[str], aliases: dict[str, str]) -> bool:
        self.last_error = ""
        temporary: str | None = None
        try:
            if self.path is not None:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(
                    mode="w", encoding="utf-8", dir=self.path.parent,
                    prefix=self.path.name + ".", suffix=".tmp", delete=False,
                ) as stream:
                    temporary = stream.name
                    json.dump({"schema": 1, "favorites": sorted(favorites), "aliases": aliases},
                              stream, ensure_ascii=False, indent=2)
                    stream.write("\n")
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, self.path)
                temporary = None
            self.favorites = favorites
            self.aliases = aliases
            self.load_error = ""
            return True
        except OSError as exc:
            self.last_error = str(exc)
            return False
        finally:
            if temporary is not None:
                try:
                    Path(temporary).unlink(missing_ok=True)
                except OSError:
                    pass
