"""Normalize canonical names and their alternate manuscript forms."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable


def parse_entity_aliases(value: str | list[str] | tuple[str, ...] | None) -> list[str]:
    if isinstance(value, (list, tuple)):
        raw_aliases = value
    elif isinstance(value, str):
        text = value.strip()
        try:
            decoded = json.loads(text)
        except json.JSONDecodeError:
            decoded = None
        if isinstance(decoded, list):
            raw_aliases = decoded
        elif isinstance(decoded, dict):
            raw_aliases = [
                alias.get("name", "")
                for alias in decoded.values()
                if isinstance(alias, dict)
            ] or list(decoded.values())
        else:
            raw_aliases = re.split(r"[,;\n|]+", text)
    else:
        raw_aliases = []

    aliases: list[str] = []
    seen: set[str] = set()
    for raw_alias in raw_aliases:
        alias = str(raw_alias).strip().strip("\"'“”‘’")
        key = alias.casefold()
        if alias and key not in seen:
            seen.add(key)
            aliases.append(alias)
    return aliases


def entity_name_forms(name: str, aliases: str | list[str] | tuple[str, ...] | None) -> list[str]:
    forms = [name.strip()] if name and name.strip() else []
    forms.extend(parse_entity_aliases(aliases))
    seen: set[str] = set()
    unique_forms = []
    for form in forms:
        key = form.casefold()
        if key not in seen:
            seen.add(key)
            unique_forms.append(form)
    return unique_forms


def serialize_entity_aliases(aliases: Iterable[str]) -> str:
    return json.dumps(parse_entity_aliases(list(aliases)), ensure_ascii=False)


def text_mentions_entity(text: str, name: str, aliases: str | list[str] | tuple[str, ...] | None) -> bool:
    return any(
        re.search(r"(?<!\w)" + re.escape(form) + r"(?!\w)", text, re.IGNORECASE)
        for form in entity_name_forms(name, aliases)
    )
