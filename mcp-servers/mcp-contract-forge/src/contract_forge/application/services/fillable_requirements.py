from contract_forge.domain.evaluation.models import Requirement


def fillable_requirements(requirements: list[Requirement]) -> list[Requirement]:
    """Remove structural parents whose existence follows from filling a required child."""
    paths = [r.path.rstrip("/") for r in requirements]
    out: list[Requirement] = []
    for requirement in requirements:
        prefix = requirement.path.rstrip("/") + "/"
        if any(other != requirement.path.rstrip("/") and other.startswith(prefix) for other in paths):
            continue
        out.append(requirement)
    return out
