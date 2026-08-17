"""Data & MCP governance, per ADR-005.

`GovernedClient` enforces a `DS-` spec in-process around a caller-injected
executor (a fake in tests, a real DB driver in a generated project) —
never a live database connection built here. `MCPManager` resolves an
agent's requested tool strings against a registry of `TOOL-` specs
(lazy — structural allowlist resolution, no live MCP session).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from agentcore.specs.models import DataSourceSpec, OpsSpec, ToolSpec

Executor = Callable[[str, str, int], list[dict[str, object]]]  # (table, operation, limit) -> rows


class DeniedTable(Exception):
    pass


class DeniedColumn(Exception):
    pass


class OverLimitQuery(Exception):
    pass


class UnknownTool(Exception):
    pass


class UnapprovedTool(Exception):
    pass


@dataclass
class QueryResult:
    rows: list[dict[str, object]]
    ds_spec_id: str
    classification: str
    freshness_caveat: str
    redacted_columns: list[str] = field(default_factory=list)


class GovernedClient:
    def __init__(self, ds: DataSourceSpec, executor: Executor):
        self._ds = ds
        self._executor = executor

    def query(
        self,
        table: str,
        columns: list[str] | None = None,
        operation: str = "read",
        limit: int | None = None,
    ) -> QueryResult:
        access = self._ds.access

        if table not in access.allowed_tables:
            raise DeniedTable(f"{table!r} is not in DS spec {self._ds.id}'s allowed_tables")

        if columns is not None:
            denied_requested = [c for c in columns if c in access.denied_columns]
            if denied_requested:
                raise DeniedColumn(
                    f"columns {denied_requested} are denied by DS spec {self._ds.id}"
                )

        if limit is not None and limit > access.max_rows:
            raise OverLimitQuery(
                f"requested limit {limit} exceeds DS spec {self._ds.id}'s "
                f"max_rows={access.max_rows}"
            )
        effective_limit = limit if limit is not None else access.max_rows

        rows = self._executor(table, operation, effective_limit)

        redacted_columns: list[str] = []
        clean_rows: list[dict[str, object]] = []
        for row in rows:
            clean_row = {}
            for key, value in row.items():
                if key in access.denied_columns:
                    if key not in redacted_columns:
                        redacted_columns.append(key)
                    continue
                clean_row[key] = value
            clean_rows.append(clean_row)

        return QueryResult(
            rows=clean_rows,
            ds_spec_id=self._ds.id,
            classification=self._ds.classification,
            freshness_caveat=self._ds.freshness,
            redacted_columns=redacted_columns,
        )


def redact_for_trace(
    payload: dict[str, object], ds: DataSourceSpec, ops: OpsSpec
) -> dict[str, object]:
    """Cloud-redaction rule from specs/templates/ops.md: self_hosted traces
    never leave the VPC (full payload acceptable); cloud traces redact
    confidential-classified data to a summary before leaving.
    """
    if ops.langsmith_target == "cloud" and ds.classification == "confidential":
        rows = payload.get("rows")
        row_count = len(rows) if isinstance(rows, list) else None
        return {
            "redacted": True,
            "ds_spec_id": ds.id,
            "classification": ds.classification,
            "row_count": row_count,
        }
    return payload


@dataclass(frozen=True)
class ResolvedTool:
    tool_ref: str
    spec_id: str


class MCPManager:
    def resolve_allowlist(
        self, agent_tools: list[str], tool_specs: dict[str, ToolSpec]
    ) -> list[ResolvedTool]:
        resolved: list[ResolvedTool] = []
        for tool_ref in agent_tools:
            spec = self._match(tool_ref, tool_specs)
            if spec is None:
                raise UnknownTool(f"no TOOL- spec governs {tool_ref!r}")
            if spec.status != "approved":
                raise UnapprovedTool(
                    f"TOOL- spec {spec.id} governing {tool_ref!r} is not approved "
                    f"(status={spec.status})"
                )
            resolved.append(ResolvedTool(tool_ref=tool_ref, spec_id=spec.id))
        return resolved

    @staticmethod
    def _match(tool_ref: str, tool_specs: dict[str, ToolSpec]) -> ToolSpec | None:
        for spec in tool_specs.values():
            if spec.governs is None:
                continue
            for resource in spec.governs.resources:
                if tool_ref == resource or tool_ref.startswith(f"{resource}."):
                    return spec
        return None
