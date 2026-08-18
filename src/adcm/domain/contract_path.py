from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_TOKEN_RE = re.compile(r"([^\.\[\]]+)|\[(\d+)\]")


@dataclass(frozen=True)
class PathToken:
    key: str | None = None
    index: int | None = None


class ContractPath:
    """Read/write concrete instance paths such as silver.tables[0].columns[2].name."""

    @staticmethod
    def parse(path: str) -> list[PathToken]:
        tokens: list[PathToken] = []
        for match in _TOKEN_RE.finditer(path):
            key, index = match.groups()
            tokens.append(PathToken(key=key) if key is not None else PathToken(index=int(index)))
        if not tokens:
            raise ValueError(f"Invalid contract path: {path!r}")
        return tokens

    @classmethod
    def write(cls, document: dict[str, Any], path: str, value: Any) -> None:
        tokens = cls.parse(path)
        current: Any = document

        for pos, token in enumerate(tokens):
            last = pos == len(tokens) - 1
            next_token = tokens[pos + 1] if not last else None

            if token.key is not None:
                if not isinstance(current, dict):
                    raise TypeError(f"Expected object while writing {path!r}")
                if last:
                    current[token.key] = value
                    return
                if token.key not in current or current[token.key] is None:
                    current[token.key] = [] if next_token and next_token.index is not None else {}
                current = current[token.key]
                continue

            if not isinstance(current, list):
                raise TypeError(f"Expected list while writing {path!r}")
            assert token.index is not None
            while len(current) <= token.index:
                # For an intermediate element of a list of objects, {} is intentional padding.
                # A schema-aware writer can later specialize scalar-list padding if needed.
                current.append({} if not last else None)
            if last:
                current[token.index] = value
                return
            if current[token.index] is None:
                current[token.index] = [] if next_token and next_token.index is not None else {}
            current = current[token.index]

    @classmethod
    def read(cls, document: dict[str, Any], path: str, default: Any = None) -> Any:
        current: Any = document
        try:
            for token in cls.parse(path):
                if token.key is not None:
                    current = current[token.key]
                else:
                    assert token.index is not None
                    current = current[token.index]
            return current
        except (KeyError, IndexError, TypeError):
            return default
