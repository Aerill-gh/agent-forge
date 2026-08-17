import pytest

from agentcore.mcp import (
    DeniedColumn,
    DeniedTable,
    GovernedClient,
    MCPManager,
    OverLimitQuery,
    UnapprovedTool,
    UnknownTool,
    redact_for_trace,
)
from agentcore.specs.models import (
    DataSourceAccess,
    DataSourceSpec,
    Governs,
    OpsSpec,
    RateLimits,
    ToolSpec,
)


def _ds(**overrides: object) -> DataSourceSpec:
    defaults: dict[str, object] = {
        "id": "DS-900",
        "title": "Fake warehouse",
        "status": "approved",
        "version": "1.0.0",
        "owner": "@tester",
        "classification": "internal",
        "access": DataSourceAccess(
            allowed_tables=["contracts"], denied_columns=["ssn"], max_rows=100
        ),
        "semantics": "docs/data-dictionary/contracts.md",
        "freshness": "updated nightly at 02:00 UTC",
    }
    defaults.update(overrides)
    return DataSourceSpec(**defaults)  # type: ignore[arg-type]


def _rows() -> list[dict[str, object]]:
    return [
        {"id": 1, "name": "Acme", "ssn": "123-45-6789"},
        {"id": 2, "name": "Globex", "ssn": "987-65-4321"},
    ]


def test_query_rejects_unallowlisted_table() -> None:
    client = GovernedClient(_ds(), executor=lambda table, op, limit: _rows())

    with pytest.raises(DeniedTable):
        client.query("employees")


def test_query_rejects_explicit_denied_column() -> None:
    client = GovernedClient(_ds(), executor=lambda table, op, limit: _rows())

    with pytest.raises(DeniedColumn):
        client.query("contracts", columns=["id", "ssn"])


def test_query_strips_denied_column_when_not_explicitly_requested() -> None:
    client = GovernedClient(_ds(), executor=lambda table, op, limit: _rows())

    result = client.query("contracts")

    assert result.redacted_columns == ["ssn"]
    assert all("ssn" not in row for row in result.rows)
    assert result.rows[0] == {"id": 1, "name": "Acme"}


def test_query_blocks_over_limit_and_defaults_limit() -> None:
    captured_limits: list[int] = []

    def executor(table: str, op: str, limit: int) -> list[dict[str, object]]:
        captured_limits.append(limit)
        return _rows()

    client = GovernedClient(_ds(), executor=executor)

    with pytest.raises(OverLimitQuery):
        client.query("contracts", limit=10_000)

    client.query("contracts")
    assert captured_limits == [100]  # auto-set to access.max_rows


def test_query_result_tags_trace_metadata() -> None:
    client = GovernedClient(_ds(), executor=lambda table, op, limit: _rows())

    result = client.query("contracts")

    assert result.ds_spec_id == "DS-900"
    assert result.classification == "internal"
    assert result.freshness_caveat == "updated nightly at 02:00 UTC"


def test_redact_for_trace_keyed_off_target_and_classification() -> None:
    confidential_ds = _ds(classification="confidential")
    cloud_ops = OpsSpec(
        id="OPS-900",
        title="Fake ops",
        status="draft",
        version="0.1.0",
        owner="@tester",
        deploy_target="self_hosted",
        langsmith_target="cloud",
    )
    self_hosted_ops = OpsSpec(
        id="OPS-901",
        title="Fake ops",
        status="draft",
        version="0.1.0",
        owner="@tester",
        deploy_target="self_hosted",
        langsmith_target="self_hosted",
        langsmith_endpoint="https://langsmith.internal",
    )
    payload = {"rows": _rows()}

    redacted = redact_for_trace(payload, confidential_ds, cloud_ops)
    assert redacted["redacted"] is True
    assert redacted["row_count"] == 2
    assert "rows" not in redacted

    unredacted_self_hosted = redact_for_trace(payload, confidential_ds, self_hosted_ops)
    assert unredacted_self_hosted == payload

    internal_ds = _ds(classification="internal")
    unredacted_internal = redact_for_trace(payload, internal_ds, cloud_ops)
    assert unredacted_internal == payload


def test_manager_rejects_unapproved_and_unknown_tools() -> None:
    approved_tool = ToolSpec(
        id="TOOL-900",
        title="Filesystem read",
        status="approved",
        version="1.0.0",
        owner="@tester",
        kind="mcp_server",
        rate_limits=RateLimits(max_calls_per_run=10, max_calls_per_minute=30),
        governs=Governs(resources=["mcp:filesystem"]),
    )
    draft_tool = ToolSpec(
        id="TOOL-901",
        title="Postgres query",
        status="draft",
        version="0.1.0",
        owner="@tester",
        kind="mcp_server",
        rate_limits=RateLimits(max_calls_per_run=10, max_calls_per_minute=30),
        governs=Governs(resources=["mcp:postgres"]),
    )
    tool_specs = {"TOOL-900": approved_tool, "TOOL-901": draft_tool}
    manager = MCPManager()

    resolved = manager.resolve_allowlist(["mcp:filesystem.read"], tool_specs)
    assert resolved[0].spec_id == "TOOL-900"

    with pytest.raises(UnapprovedTool):
        manager.resolve_allowlist(["mcp:postgres.query"], tool_specs)

    with pytest.raises(UnknownTool):
        manager.resolve_allowlist(["mcp:github.issues"], tool_specs)
