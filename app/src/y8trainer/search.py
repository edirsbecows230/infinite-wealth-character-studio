"""Case-insensitive AND search and exact appearance indexes, independent of Qt."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable
from typing import Any


RELATED_FIELDS = ("face_model", "hair_model", "model")


def query_tokens(query: str) -> tuple[str, ...]:
    tokens = []
    for token in query.casefold().split():
        if token.startswith("0x"):
            try:
                token = hex(int(token, 16))
            except ValueError:
                pass
        tokens.append(token)
    return tuple(tokens)


def searchable_text(target: dict[str, Any]) -> str:
    fields = [
        target.get(name) for name in (
            "label", "id", "model", "face_model", "hair_model", "target_row",
            "standard_character", "voicer", "region", "catalog_group", "search_text",
        )
    ]
    key = target.get("standard_character")
    if isinstance(key, int):
        fields.append(hex(key))
    return " ".join(str(x) for x in fields if x is not None).casefold()


class CharacterSearchIndex:
    def __init__(self, targets: Iterable[dict[str, Any]]) -> None:
        self.text: dict[str, str] = {}
        self.related: dict[str, dict[str, set[str]]] = {
            name: defaultdict(set) for name in RELATED_FIELDS
        }
        for target in targets:
            self.add(target)

    def add(self, target: dict[str, Any]) -> None:
        target_id = target["id"]
        self.text[target_id] = searchable_text(target)
        for name in RELATED_FIELDS:
            value = str(target.get(name) or "").casefold()
            if value:
                self.related[name][value].add(target_id)

    def matching_ids(
        self, target_ids: Iterable[str], query: str = "",
        alias: Callable[[str], str] = lambda _: "",
        related: tuple[str, str] | None = None,
    ) -> list[str]:
        tokens = query_tokens(query)
        allowed = None
        if related is not None:
            field, value = related
            allowed = self.related.get(field, {}).get(value.casefold(), set()) if value else set()
        result = []
        for target_id in target_ids:
            if target_id not in self.text or (allowed is not None and target_id not in allowed):
                continue
            if tokens:
                haystack = self.text[target_id] + " " + alias(target_id).casefold()
                if not all(token in haystack for token in tokens):
                    continue
            result.append(target_id)
        return result
