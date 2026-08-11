from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml


MISSING = object()


@dataclass(frozen=True)
class ContractDocument:
    path: Path
    data: dict[str, Any]


def get_path(data: Any, dotted_path: str) -> Any:
    current = data
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return MISSING
        current = current[part]
    return current


def flatten_dict(
    value: Any,
    prefix: str = "",
    *,
    include_lists: bool = False,
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            result.update(flatten_dict(child, path, include_lists=include_lists))
        return result

    if isinstance(value, list):
        if include_lists:
            result[prefix] = value
        return result

    if prefix:
        result[prefix] = value
    return result


def load_yaml_contracts(directory: Path) -> list[ContractDocument]:
    documents: list[ContractDocument] = []
    patterns = ("*.yaml", "*.yml")

    paths: list[Path] = []
    for pattern in patterns:
        paths.extend(directory.rglob(pattern))

    for path in sorted(set(paths)):
        try:
            with path.open("r", encoding="utf-8") as handle:
                raw = yaml.safe_load(handle)
        except (OSError, yaml.YAMLError) as exc:
            print(f"[WARN] Pomijam {path}: {exc}")
            continue

        if isinstance(raw, dict):
            documents.append(ContractDocument(path=path, data=raw))
        else:
            print(f"[WARN] Pomijam {path}: root YAML nie jest obiektem/mapą.")

    return documents


def filter_by_source_system(
    docs: Iterable[ContractDocument],
    source_system: str,
    source_system_path: str,
) -> list[ContractDocument]:
    expected = source_system.casefold()
    selected = []

    for doc in docs:
        value = get_path(doc.data, source_system_path)
        if value is MISSING or value is None:
            continue
        if str(value).casefold() == expected:
            selected.append(doc)

    return selected


def make_hashable(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def confidence(matches: int, total: int) -> str:
    if total >= 3 and matches / total >= 0.95:
        return "high"
    if total >= 3 and matches / total >= 0.80:
        return "medium"
    return "low"


def analyze_constants(
    flattened: list[dict[str, Any]],
    docs: list[ContractDocument],
    min_presence: float,
) -> list[dict[str, Any]]:
    total = len(flattened)
    values_by_path: dict[str, list[tuple[int, Any]]] = defaultdict(list)

    for index, flat in enumerate(flattened):
        for path, value in flat.items():
            values_by_path[path].append((index, value))

    findings: list[dict[str, Any]] = []

    for path, indexed_values in sorted(values_by_path.items()):
        presence = len(indexed_values)
        if total == 0 or presence / total < min_presence:
            continue

        encoded = Counter(make_hashable(v) for _, v in indexed_values)
        encoded_value, matches = encoded.most_common(1)[0]
        value = json.loads(encoded_value)

        example_files = [
            str(docs[index].path)
            for index, candidate in indexed_values
            if make_hashable(candidate) == encoded_value
        ][:5]

        findings.append(
            {
                "kind": "constant_candidate",
                "path": path,
                "value": value,
                "matches": matches,
                "present": presence,
                "total": total,
                "match_ratio": round(matches / total, 4),
                "confidence": confidence(matches, total),
                "example_files": example_files,
                "suggested_action": "set_default",
            }
        )

    return findings


def analyze_equal_path_relations(
    flattened: list[dict[str, Any]],
    docs: list[ContractDocument],
    *,
    min_matches: int = 2,
    min_ratio: float = 0.80,
) -> list[dict[str, Any]]:
    total = len(flattened)
    all_paths = sorted({path for flat in flattened for path in flat})
    findings: list[dict[str, Any]] = []

    for target in all_paths:
        for source in all_paths:
            if target == source:
                continue

            comparable = 0
            matches = 0
            matched_files: list[str] = []

            for index, flat in enumerate(flattened):
                if target not in flat or source not in flat:
                    continue
                comparable += 1
                if flat[target] == flat[source]:
                    matches += 1
                    if len(matched_files) < 5:
                        matched_files.append(str(docs[index].path))

            if comparable < min_matches:
                continue
            ratio = matches / comparable
            if ratio < min_ratio:
                continue

            findings.append(
                {
                    "kind": "equal_path_candidate",
                    "path": target,
                    "source_path": source,
                    "matches": matches,
                    "comparable": comparable,
                    "total": total,
                    "match_ratio": round(ratio, 4),
                    "confidence": confidence(matches, comparable),
                    "example_files": matched_files,
                    "suggested_action": "copy_value",
                }
            )

    # Usuń symetryczne i oczywiście słabsze duplikaty.
    unique: dict[tuple[str, str], dict[str, Any]] = {}
    for item in findings:
        key = (item["path"], item["source_path"])
        unique[key] = item
    return list(unique.values())


def analyze_simple_string_templates(
    flattened: list[dict[str, Any]],
    docs: list[ContractDocument],
    *,
    min_matches: int = 3,
    min_ratio: float = 0.80,
) -> list[dict[str, Any]]:
    """
    Wykrywa prostą relację:
      target = PREFIX + source + SUFFIX

    Nie próbuje inferować Jinja ani złożonych transformacji.
    Takie przypadki powinien zinterpretować agent na podstawie raportu.
    """
    all_paths = sorted({path for flat in flattened for path in flat})
    findings: list[dict[str, Any]] = []

    for target in all_paths:
        for source in all_paths:
            if target == source:
                continue

            samples: list[tuple[int, str, str]] = []
            for index, flat in enumerate(flattened):
                tv = flat.get(target, MISSING)
                sv = flat.get(source, MISSING)
                if isinstance(tv, str) and isinstance(sv, str) and sv and sv in tv:
                    samples.append((index, tv, sv))

            if len(samples) < min_matches:
                continue

            templates: Counter[tuple[str, str]] = Counter()
            indices_by_template: dict[tuple[str, str], list[int]] = defaultdict(list)

            for index, target_value, source_value in samples:
                before, after = target_value.split(source_value, 1)
                key = (before, after)
                templates[key] += 1
                indices_by_template[key].append(index)

            (prefix, suffix), matches = templates.most_common(1)[0]
            ratio = matches / len(samples)
            if ratio < min_ratio:
                continue

            example_files = [
                str(docs[i].path)
                for i in indices_by_template[(prefix, suffix)][:5]
            ]

            findings.append(
                {
                    "kind": "simple_template_candidate",
                    "path": target,
                    "source_path": source,
                    "template": f"{prefix}{{source}}{suffix}",
                    "matches": matches,
                    "comparable": len(samples),
                    "match_ratio": round(ratio, 4),
                    "confidence": confidence(matches, len(samples)),
                    "example_files": example_files,
                    "suggested_action": "format_value",
                    "note": "Wykryto wyłącznie prosty prefix + source + suffix.",
                }
            )

    return findings


def build_report(
    docs: list[ContractDocument],
    *,
    source_system: str,
    source_system_path: str,
    min_presence: float,
) -> dict[str, Any]:
    flattened = [flatten_dict(doc.data) for doc in docs]

    return {
        "source_system": source_system,
        "source_system_path": source_system_path,
        "contract_count": len(docs),
        "files": [str(doc.path) for doc in docs],
        "candidates": {
            "constants": analyze_constants(
                flattened, docs, min_presence=min_presence
            ),
            "equal_paths": analyze_equal_path_relations(flattened, docs),
            "simple_templates": analyze_simple_string_templates(flattened, docs),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analiza kontraktów YAML pod kątem kandydatów do UX rules."
    )
    parser.add_argument(
        "--contracts-dir",
        type=Path,
        required=True,
        help="Katalog zawierający kontrakty YAML/YML.",
    )
    parser.add_argument(
        "--source-system",
        required=True,
        help="Wartość systemu źródłowego do analizy.",
    )
    parser.add_argument(
        "--source-system-path",
        default="metadata.sourceSystemGcpId",
        help="Dotted path wskazujący system źródłowy.",
    )
    parser.add_argument(
        "--min-presence",
        type=float,
        default=0.80,
        help="Minimalny udział kontraktów, w których ścieżka musi istnieć.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Opcjonalny plik JSON z raportem.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    all_docs = load_yaml_contracts(args.contracts_dir)
    selected = filter_by_source_system(
        all_docs,
        source_system=args.source_system,
        source_system_path=args.source_system_path,
    )

    if not selected:
        print(
            f"Nie znaleziono kontraktów dla systemu "
            f"{args.source_system!r} pod ścieżką "
            f"{args.source_system_path!r}."
        )
        return 2

    report = build_report(
        selected,
        source_system=args.source_system,
        source_system_path=args.source_system_path,
        min_presence=args.min_presence,
    )

    rendered = json.dumps(report, indent=2, ensure_ascii=False)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(f"Zapisano raport: {args.output}")
    else:
        print(rendered)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
