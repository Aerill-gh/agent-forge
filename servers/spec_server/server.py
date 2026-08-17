"""spec-server: resolver + spec CRUD + scaffolding, per ADR-005 / plan §7.

Built on `mcp.server.mcpserver.MCPServer` (package `mcp>=2.0` — note this
version's API lives at `mcp.server.mcpserver.MCPServer`, not the
`mcp.server.fastmcp.FastMCP` path older docs reference). Capped at the
plan's 8-tool budget; every tool is a thin wrapper over `agentcore.specs`
functions already built in P1/P2. Tested in-process via
`MCPServer.call_tool()` — no transport is spun up here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from mcp.server.mcpserver import MCPServer

from agentcore.specs.index import build_index, load_specs, spec_file_path
from agentcore.specs.lint import spec_lint, verified_by_resolves
from agentcore.specs.loader import (
    SpecParseError,
    SpecValidationError,
    load_spec,
    split_frontmatter,
)
from agentcore.specs.models import AgentSpec
from agentcore.specs.resolve import resolve

_KIND_LAYOUT: dict[str, tuple[str, str]] = {
    "AGT": ("agents", "agent.md"),
    "GRP": ("graphs", "graph.md"),
    "TOOL": ("tools", "tool.md"),
    "DS": ("data_sources", "data_source.md"),
    "EVL": ("evals", "eval.md"),
    "OPS": ("ops", "ops.md"),
    "ADR": ("adr", "adr.md"),
}

server = MCPServer(
    "spec-server",
    instructions=(
        "Resolves which spec governs a path/resource, reads/creates specs, "
        "and scaffolds agent code — refusing anything not backed by an "
        "approved spec, per agent-forge's CON-001."
    ),
)


@server.tool()
def spec_for_target(target: str, specs_dir: str = "specs", repo_root: str = ".") -> dict[str, Any]:
    """Resolve the spec id governing a file path (or None if unowned)."""
    index = build_index(Path(repo_root) / specs_dir, repo_root)
    return {"spec_id": resolve(target, index)}


@server.tool()
def spec_get(spec_id: str, specs_dir: str = "specs") -> dict[str, Any]:
    """Return a spec's full resolved model as JSON."""
    path = spec_file_path(specs_dir, spec_id)
    if path is None:
        return {"error": f"no spec file found for {spec_id!r}"}
    try:
        model = load_spec(path)
    except (SpecParseError, SpecValidationError) as exc:
        return {"error": str(exc)}
    return model.model_dump(mode="json")


@server.tool()
def spec_search(query: str, specs_dir: str = "specs") -> list[dict[str, Any]]:
    """Search spec id/title for a case-insensitive substring match."""
    needle = query.lower()
    matches = []
    for spec_id, spec in load_specs(specs_dir).items():
        if needle in spec_id.lower() or needle in spec.title.lower():
            matches.append({"id": spec_id, "title": spec.title, "status": spec.status})
    return matches


@server.tool()
def spec_create(kind: str, spec_id: str, title: str, specs_dir: str = "specs") -> dict[str, Any]:
    """Scaffold a new spec file from its kind's template."""
    layout = _KIND_LAYOUT.get(kind)
    if layout is None:
        return {"error": f"unknown spec kind {kind!r}, expected one of {sorted(_KIND_LAYOUT)}"}
    subdir, template_name = layout

    specs_path = Path(specs_dir)
    target_dir = specs_path / subdir
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{spec_id}.md"
    if target_path.exists():
        return {"error": f"{target_path} already exists"}

    template_path = specs_path / "templates" / template_name
    text = template_path.read_text(encoding="utf-8")
    text = text.replace(f"{kind}-NNN", spec_id).replace("<Agent name>", title)
    target_path.write_text(text, encoding="utf-8")
    return {"path": str(target_path), "created": True}


@server.tool()
def next_task(spec_id: str, specs_dir: str = "specs", repo_root: str = ".") -> dict[str, Any]:
    """Return the first acceptance criterion whose verified_by doesn't resolve yet."""
    path = spec_file_path(specs_dir, spec_id)
    if path is None:
        return {"error": f"no spec file found for {spec_id!r}"}
    spec = load_spec(path)
    for criterion in spec.acceptance:
        if not verified_by_resolves(criterion.verified_by, Path(repo_root)):
            return {
                "ac_id": criterion.id,
                "then": criterion.then,
                "verified_by": criterion.verified_by,
            }
    return {"done": True}


@server.tool()
def bind_test(
    spec_id: str, ac_id: str, verified_by: str, specs_dir: str = "specs"
) -> dict[str, Any]:
    """Set an acceptance criterion's verified_by field on an existing spec."""
    path = spec_file_path(specs_dir, spec_id)
    if path is None:
        return {"error": f"no spec file found for {spec_id!r}"}

    text = path.read_text(encoding="utf-8")
    frontmatter_yaml, body = split_frontmatter(text)
    raw = yaml.safe_load(frontmatter_yaml) or {}

    found = False
    for criterion in raw.get("acceptance", []):
        if criterion.get("id") == ac_id:
            criterion["verified_by"] = verified_by
            found = True
            break
    if not found:
        return {"error": f"{spec_id} has no acceptance criterion {ac_id!r}"}

    new_frontmatter = yaml.safe_dump(raw, sort_keys=False)
    path.write_text(f"---\n{new_frontmatter}---\n{body}", encoding="utf-8")
    return {"updated": True}


@server.tool()
def scaffold_agent(spec_id: str, specs_dir: str = "specs", repo_root: str = ".") -> dict[str, Any]:
    """Create placeholder source files for an AGT- spec's governed paths.

    Refuses unless the spec is approved — an unapproved spec has no
    reviewed contract for the scaffold to satisfy.
    """
    path = spec_file_path(specs_dir, spec_id)
    if path is None:
        return {"error": f"no spec file found for {spec_id!r}"}
    spec = load_spec(path)
    if not isinstance(spec, AgentSpec):
        return {"error": f"{spec_id} is not an AGT- spec"}
    if spec.status != "approved":
        return {"error": f"{spec_id} is not approved (status={spec.status}); refusing to scaffold"}

    created = []
    if spec.governs is not None:
        for pattern in spec.governs.paths:
            if "*" in pattern:
                directory = Path(repo_root) / pattern.split("*")[0].rstrip("/")
                directory.mkdir(parents=True, exist_ok=True)
                init_file = directory / "__init__.py"
                if not init_file.exists():
                    init_file.write_text('"""Scaffolded by spec-server.scaffold_agent."""\n')
                    created.append(str(init_file))
    return {"created": created}


@server.tool(name="spec_lint")
def spec_lint_tool(specs_dir: str = "specs", repo_root: str = ".") -> dict[str, Any]:
    """Run spec_lint and return the failures found (empty if clean)."""
    failures = spec_lint(specs_dir, repo_root)
    return {"failures": [str(f) for f in failures]}


if __name__ == "__main__":
    server.run()
