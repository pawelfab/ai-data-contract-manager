from __future__ import annotations

import yaml

from .models import ValidationResult, YamlResult


def render_contract_yaml(
    result: ValidationResult,
) -> YamlResult:
    if not result.valid:
        summary = "; ".join(
            f"{issue.path or '<root>'}: {issue.message}"
            for issue in result.issues[:5]
        )
        raise ValueError(
            "Kontrakt nie przeszedł walidacji i nie może zostać "
            f"wyrenderowany: {summary}"
        )

    rendered = yaml.safe_dump(
        result.normalized_contract,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )
    return YamlResult(
        yaml=rendered,
        contract_fingerprint=result.contract_fingerprint,
        schema_fingerprint=result.schema_fingerprint,
    )
