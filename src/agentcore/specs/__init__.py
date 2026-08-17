"""agentcore.specs — the spec engine (ADR-001).

Pydantic models per spec kind, a frontmatter loader, and `spec_lint` for
CI (`spec-guard.yml`). The `governs:` resolver lands in P2.
"""

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
    "build_index",
    "load_spec",
    "model_for_id",
    "registry",
    "resolve",
    "spec",
    "spec_lint",
]
