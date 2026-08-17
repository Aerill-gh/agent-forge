"""Parse a spec file's YAML frontmatter and validate it, per ADR-001."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from agentcore.specs.models import SpecBase, model_for_id

_FRONTMATTER_DELIM = "---"


class SpecParseError(Exception):
    """Raised when a spec file has no well-formed frontmatter block."""


class SpecValidationError(Exception):
    """Raised when a spec's frontmatter fails its kind's schema."""

    def __init__(self, path: Path, errors: ValidationError):
        self.path = path
        self.errors = errors
        super().__init__(f"{path}: {errors}")


def split_frontmatter(text: str) -> tuple[str, str]:
    """Split a spec file's raw text into (frontmatter_yaml, body_markdown)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != _FRONTMATTER_DELIM:
        raise SpecParseError("spec file must start with '---' frontmatter delimiter")
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == _FRONTMATTER_DELIM:
            frontmatter = "\n".join(lines[1:i])
            body = "\n".join(lines[i + 1 :])
            return frontmatter, body
    raise SpecParseError("unterminated frontmatter block (no closing '---')")


def load_spec(path: str | Path) -> SpecBase:
    """Load and validate a spec file, returning its kind-specific model."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    frontmatter_yaml, _body = split_frontmatter(text)
    raw = yaml.safe_load(frontmatter_yaml) or {}

    spec_id = raw.get("id")
    if not isinstance(spec_id, str):
        raise SpecParseError(f"{path}: frontmatter missing string 'id' field")

    try:
        model_cls = model_for_id(spec_id)
    except ValueError as exc:
        raise SpecParseError(f"{path}: {exc}") from exc

    try:
        return model_cls.model_validate(raw)
    except ValidationError as exc:
        raise SpecValidationError(path, exc) from exc
