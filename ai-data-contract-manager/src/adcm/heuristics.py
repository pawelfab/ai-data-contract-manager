from __future__ import annotations

import json
import re
import unicodedata
from copy import deepcopy
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from .models import Requirement


def _ascii(value: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(character)
    )


def slugify_identifier(value: str) -> str:
    value = _ascii(value).strip().lower()
    value = re.sub(r"[^a-z0-9_-]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_-")
    if value and not value[0].isalpha():
        value = f"p_{value}"
    return value


@dataclass(frozen=True)
class StructuredParseResult:
    value: list[dict[str, Any]]
    missing: list[str]
    invalid: list[str]

    @property
    def complete(self) -> bool:
        return bool(self.value) and not self.missing and not self.invalid


class HeuristicResolver:
    """Cheap deterministic normalization before any LLM call."""

    def extract(
        self,
        text: str,
        requirements: list[Requirement],
        contract: dict[str, Any],
        *,
        allow_plain_fallback: bool,
        allow_structured: bool = True,
    ) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for requirement in requirements:
            structured = (
                self.parse_structured(text, requirement)
                if allow_structured
                else None
            )
            if structured is not None:
                if structured.complete:
                    values[requirement.path] = deepcopy(structured.value)
                continue
            value = self._for_requirement(
                text,
                requirement,
                contract,
                allow_plain_fallback=allow_plain_fallback,
            )
            if value is not None:
                values[requirement.path] = value
        return values

    def parse_structured(
        self,
        text: str,
        requirement: Requirement,
    ) -> StructuredParseResult | None:
        item_schema = self._array_object_item_schema(requirement)
        if item_schema is None:
            return None

        decoded = self._decode_json_records(text, requirement.path)
        if decoded is not None:
            return self._evaluate_records(decoded, item_schema)

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return None

        if len(lines) == 1 and "," in lines[0]:
            chunks = [chunk.strip() for chunk in lines[0].split(",") if chunk.strip()]
            chunk_results = [self._parse_text_record(chunk, item_schema) for chunk in chunks]
            if any(result is not None and result.complete for result in chunk_results):
                return self._combine_results(chunk_results)

            whole = self._parse_text_record(lines[0], item_schema)
            if whole is not None and whole.complete:
                return whole
            return self._combine_results(chunk_results)

        return self._combine_results(
            [self._parse_text_record(line, item_schema) for line in lines]
        )

    def merge_structured(
        self,
        existing: Any,
        incoming: StructuredParseResult,
        requirement: Requirement,
    ) -> StructuredParseResult:
        item_schema = self._array_object_item_schema(requirement)
        if item_schema is None:
            return incoming

        records = [
            deepcopy(record)
            for record in existing
            if isinstance(existing, list) and isinstance(record, dict)
        ] if isinstance(existing, list) else []
        identity = self._identity_property(item_schema)

        for new_record in incoming.value:
            match_index: int | None = None
            identity_value = new_record.get(identity) if identity else None
            if identity_value is not None:
                for index, current in enumerate(records):
                    if self._same_identity(current.get(identity), identity_value):
                        match_index = index
                        break
            if match_index is None:
                records.append(deepcopy(new_record))
            else:
                records[match_index].update(deepcopy(new_record))

        return self._evaluate_records(
            records,
            item_schema,
            additional_invalid=incoming.invalid,
        )

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
            return self._fuzzy_choice(
                stripped,
                [str(value) for value in (req.allowed_values or [])],
            )

        if path == "metadata.id":
            match = re.search(
                r"(?:pipeline|id|nazwa)\s*[:=]?\s*([A-Za-z0-9_-]{3,})",
                stripped,
                re.I,
            )
            if match:
                return slugify_identifier(match.group(1))
            if allow_plain_fallback and len(stripped.split()) <= 4:
                candidate = slugify_identifier(stripped)
                return candidate or None

        if path == "metadata.owner":
            email = re.search(
                r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
                stripped,
            )
            if email:
                return email.group(0)
            match = re.search(
                r"(?:owner|właściciel|wlasciciel|zespół|zespol)\s*[:=]?\s*(.+)$",
                stripped,
                re.I,
            )
            if match:
                return match.group(1).strip()
            if allow_plain_fallback and stripped:
                return stripped

        if path.endswith(".uri"):
            uri = re.search(r"\b(?:gs|s3|https?|file)://\S+", stripped)
            if uri:
                return uri.group(0).rstrip(",;")
            if allow_plain_fallback and re.match(
                r"^(?:gs|s3|https?|file)://",
                stripped,
            ):
                return stripped

        if req.allowed_values:
            choice = self._fuzzy_choice(
                stripped,
                [str(value) for value in req.allowed_values],
            )
            if choice is not None:
                return choice

        typ = req.value_schema.get("type")
        pattern = req.value_schema.get("pattern")
        description = _ascii(str(req.value_schema.get("description", ""))).lower()
        if typ == "string" and isinstance(pattern, str) and "cron" in description:
            try:
                if re.fullmatch(pattern, stripped) and self._unambiguous_pattern_value(
                    req,
                    stripped,
                ):
                    return stripped
            except re.error:
                # Forge remains responsible for schema correctness and validation.
                pass
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
    def _array_object_item_schema(
        requirement: Requirement,
    ) -> dict[str, Any] | None:
        schema = requirement.value_schema
        items = schema.get("items")
        if (
            schema.get("type") != "array"
            or not isinstance(items, dict)
            or items.get("type") != "object"
            or not isinstance(items.get("properties"), dict)
            or not isinstance(items.get("required"), list)
        ):
            return None
        return items

    @staticmethod
    def _decode_json_records(text: str, path: str) -> list[dict[str, Any]] | None:
        try:
            raw = json.loads(text)
        except json.JSONDecodeError:
            return None

        if isinstance(raw, dict):
            leaf = path.rsplit(".", 1)[-1]
            if isinstance(raw.get(leaf), list):
                raw = raw[leaf]
            elif len(raw) == 1 and isinstance(next(iter(raw.values())), list):
                raw = next(iter(raw.values()))
        if isinstance(raw, list) and all(isinstance(item, dict) for item in raw):
            return raw
        return None

    def _parse_text_record(
        self,
        line: str,
        item_schema: dict[str, Any],
    ) -> StructuredParseResult | None:
        cleaned = line.replace(":", " ").replace("|", " ").replace(",", " ")
        tokens = [token.strip('"`[]') for token in re.split(r"\s+", cleaned) if token]
        if not tokens:
            return None

        properties = item_schema["properties"]
        required = [name for name in item_schema["required"] if name in properties]
        identity = self._identity_property(item_schema)
        record: dict[str, Any] = {}
        used: set[int] = set()

        if identity:
            record[identity] = tokens[0]
            used.add(0)

        for name in required:
            if name == identity:
                continue
            found = self._find_token(tokens, used, properties[name])
            if found is not None:
                index, value = found
                used.add(index)
                record[name] = value

        if "nullable" in properties:
            low = _ascii(line).lower()
            if "not null" in low or "required" in low or "non-null" in low:
                record["nullable"] = False
            elif re.search(r"\bnullable\b", low):
                record["nullable"] = True

        evaluated = self._evaluate_records([record], item_schema)
        unused = [token for index, token in enumerate(tokens) if index not in used]
        invalid = list(evaluated.invalid)
        if unused:
            label = self._record_label(record, identity, 0)
            for missing in evaluated.missing:
                property_schema = properties.get(missing, {})
                if property_schema.get("enum"):
                    invalid.append(f"{label}.{missing}={unused[0]}")
                    break
        return StructuredParseResult(
            value=evaluated.value,
            missing=evaluated.missing,
            invalid=self._dedupe_strings(invalid),
        )

    @staticmethod
    def _find_token(
        tokens: list[str],
        used: set[int],
        property_schema: dict[str, Any],
    ) -> tuple[int, Any] | None:
        enum = property_schema.get("enum")
        if isinstance(enum, list):
            for index, token in enumerate(tokens):
                if index in used:
                    continue
                for choice in enum:
                    if str(token).casefold() == str(choice).casefold():
                        return index, deepcopy(choice)
            return None

        typ = property_schema.get("type")
        for index, token in enumerate(tokens):
            if index in used:
                continue
            if typ == "integer" and re.fullmatch(r"-?\d+", token):
                return index, int(token)
            if typ == "number" and re.fullmatch(r"-?(?:\d+(?:\.\d+)?|\.\d+)", token):
                return index, float(token)
            if typ == "boolean":
                low = _ascii(token).lower()
                if low in {"tak", "yes", "true", "1"}:
                    return index, True
                if low in {"nie", "no", "false", "0"}:
                    return index, False
            if typ == "string":
                return index, token
        return None

    def _evaluate_records(
        self,
        records: list[dict[str, Any]],
        item_schema: dict[str, Any],
        *,
        additional_invalid: list[str] | None = None,
    ) -> StructuredParseResult:
        properties = item_schema["properties"]
        required = [name for name in item_schema["required"] if name in properties]
        identity = self._identity_property(item_schema)
        normalized_records: list[dict[str, Any]] = []
        missing: list[str] = []
        invalid = list(additional_invalid or [])

        for index, record in enumerate(records):
            normalized: dict[str, Any] = {}
            label = self._record_label(record, identity, index)
            for name, value in record.items():
                property_schema = properties.get(name)
                if property_schema is None:
                    invalid.append(f"{label}.{name}={value}")
                    continue
                converted, valid = self._normalize_property(value, property_schema)
                if valid:
                    normalized[name] = converted
                else:
                    invalid.append(f"{label}.{name}={value}")
            for name in required:
                if name not in normalized:
                    missing.append(name)
            normalized_records.append(normalized)

        return StructuredParseResult(
            value=normalized_records,
            missing=self._dedupe_strings(missing),
            invalid=self._dedupe_strings(invalid),
        )

    @staticmethod
    def _normalize_property(
        value: Any,
        property_schema: dict[str, Any],
    ) -> tuple[Any, bool]:
        enum = property_schema.get("enum")
        if isinstance(enum, list):
            for choice in enum:
                if str(value).strip().casefold() == str(choice).casefold():
                    return deepcopy(choice), True
            return value, False

        typ = property_schema.get("type")
        if typ == "string":
            return (value.strip(), True) if isinstance(value, str) and value.strip() else (value, False)
        if typ == "integer":
            if isinstance(value, int) and not isinstance(value, bool):
                return value, True
            if isinstance(value, str) and re.fullmatch(r"-?\d+", value.strip()):
                return int(value), True
            return value, False
        if typ == "number":
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return value, True
            return value, False
        if typ == "boolean":
            if isinstance(value, bool):
                return value, True
            if isinstance(value, str):
                low = _ascii(value).lower().strip()
                if low in {"tak", "yes", "true", "1"}:
                    return True, True
                if low in {"nie", "no", "false", "0"}:
                    return False, True
            return value, False
        return deepcopy(value), True

    @staticmethod
    def _identity_property(item_schema: dict[str, Any]) -> str | None:
        properties = item_schema["properties"]
        required = item_schema["required"]
        if "name" in properties:
            return "name"
        for name in required:
            schema = properties.get(name, {})
            if schema.get("type") == "string" and not schema.get("enum"):
                return name
        return required[0] if required else None

    @staticmethod
    def _record_label(
        record: dict[str, Any],
        identity: str | None,
        index: int,
    ) -> str:
        if identity and record.get(identity) not in (None, ""):
            return str(record[identity])
        return str(index + 1)

    @staticmethod
    def _same_identity(left: Any, right: Any) -> bool:
        if isinstance(left, str) and isinstance(right, str):
            return left.casefold() == right.casefold()
        return left == right

    @classmethod
    def _combine_results(
        cls,
        results: list[StructuredParseResult | None],
    ) -> StructuredParseResult | None:
        present = [result for result in results if result is not None]
        if not present:
            return None
        return StructuredParseResult(
            value=[record for result in present for record in result.value],
            missing=cls._dedupe_strings(
                [missing for result in present for missing in result.missing]
            ),
            invalid=cls._dedupe_strings(
                [invalid for result in present for invalid in result.invalid]
            ),
        )

    @staticmethod
    def _dedupe_strings(values: list[str]) -> list[str]:
        return list(dict.fromkeys(values))

    @staticmethod
    def _unambiguous_pattern_value(req: Requirement, value: str) -> bool:
        description = _ascii(str(req.value_schema.get("description", ""))).lower()
        if "cron" not in description:
            return True
        # A permissive five-token schema pattern also matches ordinary sentences.
        # For automatic extraction accept only an unmistakable numeric cron form;
        # Forge still performs the authoritative schema validation afterwards.
        return all(
            re.fullmatch(r"[0-9*/?,\-]+", token) is not None
            for token in value.split()
        )

    @staticmethod
    def _fuzzy_choice(value: str, choices: list[str]) -> str | None:
        if not choices:
            return None
        norm = _ascii(value).lower().strip()
        candidates = [norm] + re.findall(r"[a-z0-9_-]+", norm)
        best: tuple[float, str] | None = None
        for candidate in candidates:
            for choice in choices:
                score = SequenceMatcher(
                    None,
                    candidate,
                    _ascii(choice).lower(),
                ).ratio()
                if candidate == _ascii(choice).lower():
                    score = 1.0
                if best is None or score > best[0]:
                    best = (score, choice)
        return best[1] if best and best[0] >= 0.72 else None
