from __future__ import annotations

import json
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any

from contract_forge.models import Requirement


TYPE_NAMES = {
    "STRING", "INT64", "FLOAT64", "NUMERIC", "BIGNUMERIC", "BOOLEAN", "DATE",
    "DATETIME", "TIME", "TIMESTAMP", "BYTES", "JSON", "GEOGRAPHY"
}


def _ascii(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c))


def slugify_identifier(value: str) -> str:
    value = _ascii(value).strip().lower()
    value = re.sub(r"[^a-z0-9_-]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_-")
    if value and not value[0].isalpha():
        value = f"p_{value}"
    return value


class HeuristicResolver:
    """Cheap deterministic normalization before any LLM call."""

    def extract(
        self,
        text: str,
        requirements: list[Requirement],
        contract: dict[str, Any],
        *,
        allow_plain_fallback: bool,
    ) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for req in requirements:
            value = self._for_requirement(text, req, contract, allow_plain_fallback=allow_plain_fallback)
            if value is not None:
                values[req.path] = value
        return values

    def _for_requirement(
        self,
        text: str,
        req: Requirement,
        contract: dict[str, Any],
        *,
        allow_plain_fallback: bool,
    ) -> Any | None:
        stripped = text.strip()
        path = req.path

        if req.reason == "source_system":
            return self._fuzzy_choice(stripped, [str(v) for v in (req.allowed_values or [])])

        if path == "metadata.id":
            m = re.search(r"(?:pipeline|id|nazwa)\s*[:=]?\s*([A-Za-z0-9_-]{3,})", stripped, re.I)
            if m:
                return slugify_identifier(m.group(1))
            if allow_plain_fallback and len(stripped.split()) <= 4:
                candidate = slugify_identifier(stripped)
                return candidate or None

        if path == "metadata.owner":
            email = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", stripped)
            if email:
                return email.group(0)
            m = re.search(r"(?:owner|właściciel|wlasciciel|zespół|zespol)\s*[:=]?\s*(.+)$", stripped, re.I)
            if m:
                return m.group(1).strip()
            if allow_plain_fallback and stripped:
                return stripped

        if path.endswith(".uri"):
            uri = re.search(r"\b(?:gs|s3|https?|file)://\S+", stripped)
            if uri:
                return uri.group(0).rstrip(",;")
            if allow_plain_fallback and re.match(r"^(?:gs|s3|https?|file)://", stripped):
                return stripped

        if path == "source.columns":
            parsed = self._parse_columns(stripped, contract.get("source", {}).get("sourceType"))
            if parsed:
                return parsed

        if req.allowed_values:
            choice = self._fuzzy_choice(stripped, [str(v) for v in req.allowed_values])
            if choice is not None:
                return choice

        typ = req.value_schema.get("type")
        if typ == "boolean":
            low = _ascii(stripped).lower()
            if low in {"tak", "yes", "true", "1"}:
                return True
            if low in {"nie", "no", "false", "0"}:
                return False
        if typ == "integer" and re.fullmatch(r"-?\d+", stripped):
            return int(stripped)
        if typ == "string" and allow_plain_fallback and stripped:
            return stripped
        return None

    @staticmethod
    def _fuzzy_choice(value: str, choices: list[str]) -> str | None:
        if not choices:
            return None
        norm = _ascii(value).lower().strip()
        # Try tokens too, so "to będzie roket" still resolves.
        candidates = [norm] + re.findall(r"[a-z0-9_-]+", norm)
        best: tuple[float, str] | None = None
        for candidate in candidates:
            for choice in choices:
                score = SequenceMatcher(None, candidate, _ascii(choice).lower()).ratio()
                if candidate == _ascii(choice).lower():
                    score = 1.0
                if best is None or score > best[0]:
                    best = (score, choice)
        return best[1] if best and best[0] >= 0.72 else None

    def _parse_columns(self, text: str, source_type: str | None) -> list[dict[str, Any]] | None:
        # First accept proper JSON pasted from docs/tools.
        try:
            raw = json.loads(text)
            if isinstance(raw, dict) and "columns" in raw:
                raw = raw["columns"]
            if isinstance(raw, list) and all(isinstance(x, dict) for x in raw):
                return raw
        except json.JSONDecodeError:
            pass

        # Normalize SQL-like comma lists into one record per line only if commas appear to separate columns.
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if len(lines) == 1 and "," in lines[0]:
            # Fixed width often uses commas inside a single column record; detect 4-tuples first.
            chunks = [c.strip() for c in lines[0].split(",") if c.strip()]
            if source_type == "fixed_width" and len(chunks) == 4:
                lines = [lines[0]]
            else:
                lines = chunks

        parsed: list[dict[str, Any]] = []
        for line in lines:
            line = line.strip().rstrip(",;")
            if not line:
                continue
            col = self._parse_fixed_width_line(line) if source_type == "fixed_width" else self._parse_regular_line(line)
            if col is None:
                return None
            parsed.append(col)
        return parsed or None

    @staticmethod
    def _parse_regular_line(line: str) -> dict[str, Any] | None:
        cleaned = line.replace(":", " ").replace("|", " ")
        tokens = [t for t in re.split(r"\s+", cleaned) if t]
        if len(tokens) < 2:
            return None
        name = tokens[0].strip('"`[]')
        dtype = tokens[1].upper().replace("INTEGER", "INT64").replace("VARCHAR", "STRING").replace("TEXT", "STRING")
        if dtype not in TYPE_NAMES:
            return None
        low = " ".join(tokens[2:]).lower()
        nullable = not ("not null" in low or "required" in low or "non-null" in low)
        return {"name": name, "dataType": dtype, "nullable": nullable}

    @staticmethod
    def _parse_fixed_width_line(line: str) -> dict[str, Any] | None:
        cleaned = line.replace(":", " ").replace("|", " ").replace(",", " ")
        tokens = [t for t in re.split(r"\s+", cleaned) if t]
        if len(tokens) < 4:
            return None
        name = tokens[0].strip('"`[]')
        dtype_idx = next((i for i, t in enumerate(tokens[1:], 1) if t.upper() in TYPE_NAMES), None)
        ints = [(i, int(t)) for i, t in enumerate(tokens[1:], 1) if re.fullmatch(r"\d+", t)]
        if dtype_idx is None or len(ints) < 2:
            return None
        start, end = ints[0][1], ints[1][1]
        dtype = tokens[dtype_idx].upper()
        nullable = "not null" not in line.lower() and "required" not in line.lower()
        return {"name": name, "start": start, "end": end, "dataType": dtype, "nullable": nullable}
