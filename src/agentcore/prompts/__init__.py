"""RAIL prompt loader, per ADR-004.

Prompt files live under the top-level `prompts/` directory (governed
content, same shape as `specs/`) and are plain Markdown with `## Role`,
`## Action`, `## Information`, `## Limits` sections, Jinja2-rendered.
`lint_rail` enforces the plan's §0 RAIL principle: `## Limits` is
required.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from jinja2 import Template

_REQUIRED_SECTIONS = ("Role", "Action", "Information", "Limits")


def render_prompt(path: str | Path, **context: object) -> str:
    """Jinja2-render a RAIL prompt file with the given context."""
    text = Path(path).read_text(encoding="utf-8")
    rendered: str = Template(text).render(**context)
    return rendered


def lint_rail(path: str | Path) -> list[str]:
    """Return a list of missing required RAIL sections (empty if clean)."""
    text = Path(path).read_text(encoding="utf-8")
    missing = []
    for section in _REQUIRED_SECTIONS:
        if not re.search(rf"^##\s+{section}\b", text, re.MULTILINE | re.IGNORECASE):
            missing.append(section)
    return missing


def content_hash(path: str | Path) -> str:
    """Short content hash for trace metadata (pins which prompt version ran)."""
    data = Path(path).read_bytes()
    return hashlib.sha256(data).hexdigest()[:12]
