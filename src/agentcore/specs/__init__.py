"""agentcore.specs — the spec engine and binding layer (ADR-001/002/003).

Pydantic models per spec kind, a frontmatter loader, a `governs:` index +
resolver, a nested-AGENTS.md generator, and `spec_lint` for CI
(`spec-guard.yml`).
"""

from agentcore.specs.agents_md import StaleAgentsMd, check_agents_md, sync_agents_md
from agentcore.specs.decorators import registry, spec
from agentcore.specs.index import Diagnostic, SpecIndex, build_index
from agentcore.specs.lint import LintFailure, spec_lint
from agentcore.specs.loader import SpecParseError, SpecValidationError, load_spec
from agentcore.specs.models import SpecBase, model_for_id
from agentcore.specs.resolve import resolve

__all__ = [
    "Diagnostic",
    "LintFailure",
    "SpecBase",
    "SpecIndex",
    "SpecParseError",
    "SpecValidationError",
    "StaleAgentsMd",
    "build_index",
    "check_agents_md",
    "load_spec",
    "model_for_id",
    "registry",
    "resolve",
    "spec",
    "spec_lint",
    "sync_agents_md",
]
