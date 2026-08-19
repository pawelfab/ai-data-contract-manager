from __future__ import annotations

import json
import re
import unicodedata
from copy import deepcopy
from dataclasses import dataclass
from datetime import date
from difflib import SequenceMatcher
from typing import Any, Protocol

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


class SpecializedResolver(Protocol):
    def resolve(
        self,
        text: str,
        requirement: Requirement,
        *,
        allow_plain_fallback: bool,
    ) -> Any | None: ...


class LabeledContractFieldResolver:
    """Keep UX aliases that JSON Schema cannot express out of the generic core."""

    def resolve(
        self,
        text: str,
        requirement: Requirement,
        *,
        allow_plain_fallback: bool,
    ) -> Any | None:
        del allow_plain_fallback
        stripped = text.strip()
        label_text = re.sub(
            r"\b[A-Za-z][A-Za-z0-9+.-]*://\S+",
            "",
            stripped,
        )

        if requirement.path == "metadata.id":
            match = re.search(
                r"(?<!\w)(?:pipeline|id|nazwa)(?!\w)[ \t]*[:=]?[ \t]*"
                r"([A-Za-z0-9_-]{3,})",
                label_text,
                re.I,
            )
            if match:
                return slugify_identifier(match.group(1))

        if requirement.path == "metadata.owner":
            email = re.search(
                r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
                stripped,
            )
            if email:
                return email.group(0)
            match = re.search(
                r"(?<!\w)(?:owner|właściciel|wlasciciel|zespół|zespol)(?!\w)"
                r"[ \t]*[:=]?[ \t]*"
                r"(?:(?:jednak|actually)\s+)?(.+)$",
                label_text,
                re.I | re.M,
            )
            if match:
                return match.group(1).strip()
        return None


class HeuristicResolver:
    """Cheap deterministic normalization before any LLM call."""

    def __init__(
        self,
        specialized_resolvers: tuple[SpecializedResolver, ...] | None = None,
    ) -> None:
        self.specialized_resolvers = (
            (LabeledContractFieldResolver(),)
            if specialized_resolvers is None
            else specialized_resolvers
        )

    def extract(
        self,
        text: str,
        requirements: list[Requirement],
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
        if requirement.unsupported_schema_keywords:
            return None
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
        *,
        allow_plain_fallback: bool,
    ) -> Any | None:
        stripped = text.strip()
        if not stripped:
            return None
        if req.unsupported_schema_keywords:
            return self._explicit_json_value(stripped) if allow_plain_fallback else None

        choices = self._schema_choices(req)
        if choices:
            return self._fuzzy_choice(stripped, choices)

        schema = req.value_schema
        for resolver in self.specialized_resolvers:
            value = resolver.resolve(
                text,
                req,
                allow_plain_fallback=allow_plain_fallback,
            )
            if value is not None:
                if schema.get("type") == "string" and isinstance(value, str):
                    return value if self._valid_string(value, schema) else None
                return value

        typ = schema.get("type")
        if typ == "boolean":
            return self._boolean_value(stripped) if allow_plain_fallback else None
        if typ == "integer":
            return self._integer_value(stripped, schema) if allow_plain_fallback else None
        if typ == "number":
            return self._number_value(stripped, schema) if allow_plain_fallback else None
        if typ == "string":
            return self._string_value(
                stripped,
                req,
                allow_plain_fallback=allow_plain_fallback,
            )
        return None

    @staticmethod
    def supports(requirement: Requirement) -> bool:
        return not requirement.unsupported_schema_keywords

    @staticmethod
    def _schema_choices(requirement: Requirement) -> list[Any]:
        schema = requirement.value_schema
        if "const" in schema:
            return [schema["const"]]
        if isinstance(schema.get("enum"), list):
            return list(schema["enum"])
        return list(requirement.allowed_values or [])

    @staticmethod
    def _explicit_json_value(value: str) -> Any | None:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _boolean_value(value: str) -> bool | None:
        low = _ascii(value).lower()
        if low in {"tak", "yes", "true", "1"}:
            return True
        if low in {"nie", "no", "false", "0"}:
            return False
        return None

    @classmethod
    def _integer_value(cls, value: str, schema: dict[str, Any]) -> int | None:
        if re.fullmatch(r"-?\d+", value) is None:
            return None
        candidate = int(value)
        return candidate if cls._within_numeric_bounds(candidate, schema) else None

    @classmethod
    def _number_value(cls, value: str, schema: dict[str, Any]) -> int | float | None:
        if (
            re.fullmatch(
                r"-?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?",
                value,
            )
            is None
        ):
            return None
        candidate: int | float = (
            float(value)
            if any(char in value.lower() for char in ".e")
            else int(value)
        )
        return candidate if cls._within_numeric_bounds(candidate, schema) else None

    @staticmethod
    def _within_numeric_bounds(value: int | float, schema: dict[str, Any]) -> bool:
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if isinstance(minimum, (int, float)) and value < minimum:
            return False
        if isinstance(maximum, (int, float)) and value > maximum:
            return False
        return True

    def _string_value(
        self,
        value: str,
        requirement: Requirement,
        *,
        allow_plain_fallback: bool,
    ) -> str | None:
        schema = requirement.value_schema
        format_name = schema.get("format")
        if format_name == "uri":
            match = re.search(r"\b[A-Za-z][A-Za-z0-9+.-]*://[^\s,;]+", value)
            candidate = match.group(0).rstrip(".)]") if match else None
            return candidate if candidate and self._valid_string(candidate, schema) else None
        if format_name == "date":
            match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", value)
            if match:
                try:
                    date.fromisoformat(match.group(0))
                except ValueError:
                    return None
                return match.group(0) if self._valid_string(match.group(0), schema) else None
            return None
        if format_name == "email":
            match = re.search(
                r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
                value,
            )
            candidate = match.group(0) if match else None
            return candidate if candidate and self._valid_string(candidate, schema) else None
        if format_name is not None:
            return None

        pattern = schema.get("pattern")
        if isinstance(pattern, str):
            candidates = [value]
            if allow_plain_fallback:
                normalized = slugify_identifier(value)
                if normalized and normalized != value:
                    candidates.append(normalized)
            else:
                historical_candidate = self._unambiguous_pattern_candidate(
                    requirement,
                    value,
                )
                if historical_candidate is None:
                    return None
                candidates = [historical_candidate]
            for candidate in candidates:
                if self._valid_string(candidate, schema):
                    return candidate
            return None

        if allow_plain_fallback and self._valid_string(value, schema):
            return value
        return None

    @staticmethod
    def _valid_string(value: str, schema: dict[str, Any]) -> bool:
        minimum = schema.get("minLength")
        maximum = schema.get("maxLength")
        if isinstance(minimum, int) and len(value) < minimum:
            return False
        if isinstance(maximum, int) and len(value) > maximum:
            return False
        pattern = schema.get("pattern")
        if isinstance(pattern, str):
            try:
                return re.fullmatch(pattern, value) is not None
            except re.error:
                return False
        return True

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
        if ":" in line and not evaluated.complete:
            # Labelled scalar facts in a mixed message are not partial array rows.
            # Complete ``name: TYPE`` records still pass through this shape parser.
            return None
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
    def _unambiguous_pattern_candidate(
        req: Requirement,
        value: str,
    ) -> str | None:
        description = _ascii(str(req.value_schema.get("description", ""))).lower()
        if "cron" in description:
            # A permissive five-token schema pattern also matches ordinary sentences,
            # so history extraction accepts exactly one cron-shaped fragment.
            matches = list(
                dict.fromkeys(
                    match.group(1)
                    for match in re.finditer(
                        r"(?<!\S)([0-9*/?,\-]+(?:[ \t]+[0-9*/?,\-]+){4})(?!\S)",
                        value,
                    )
                )
            )
            return matches[0] if len(matches) == 1 else None
        return None

    @staticmethod
    def _fuzzy_choice(value: str, choices: list[Any]) -> Any | None:
        if not choices:
            return None
        norm = _ascii(value).lower().strip()
        candidates = list(dict.fromkeys([norm, *re.findall(r"[a-z0-9_-]+", norm)]))
        for choice in choices:
            if norm == _ascii(str(choice)).lower():
                return deepcopy(choice)
        ranked: list[tuple[float, Any]] = []
        for choice in choices:
            normalized_choice = _ascii(str(choice)).lower()
            score = max(
                SequenceMatcher(None, candidate, normalized_choice).ratio()
                for candidate in candidates
            )
            ranked.append((score, choice))
        ranked.sort(key=lambda item: item[0], reverse=True)
        best_score, best_choice = ranked[0]
        second_score = ranked[1][0] if len(ranked) > 1 else 0.0
        if best_score < 0.84 or best_score - second_score < 0.08:
            return None
        return deepcopy(best_choice)
