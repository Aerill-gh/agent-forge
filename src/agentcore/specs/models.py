"""Pydantic models for spec frontmatter, per ADR-001.

One model per spec kind (`CON-`, `AGT-`, `GRP-`, `TOOL-`, `DS-`, `EVL-`,
`OPS-`, `ADR-`), all sharing the common shape already enforced by
``specs/schema/spec.schema.json``. ``SpecKind`` maps id prefix to model.
"""

from __future__ import annotations

import datetime
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SpecStatus = Literal["draft", "in_review", "approved", "deprecated"]
ModelTier = Literal["light", "versatile", "reasoning", "auto"]

_ID_PATTERN = re.compile(r"^(CON|AGT|GRP|TOOL|DS|EVL|OPS|ADR)-[0-9]{3,}$")
_VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


class AcceptanceCriterion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    given: str | None = None
    then: str
    verified_by: str


class Governs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paths: list[str] = Field(default_factory=list)
    resources: list[str] = Field(default_factory=list)


class SpecBase(BaseModel):
    """Common frontmatter shape for every spec kind."""

    model_config = ConfigDict(extra="allow")

    id: str
    title: str
    status: SpecStatus
    version: str
    owner: str
    extends: str | None = None
    governs: Governs | None = None
    acceptance: list[AcceptanceCriterion] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def _id_matches_pattern(cls, value: str) -> str:
        if not _ID_PATTERN.match(value):
            raise ValueError(
                f"id {value!r} does not match ^(CON|AGT|GRP|TOOL|DS|EVL|OPS|ADR)-[0-9]{{3,}}$"
            )
        return value

    @field_validator("version")
    @classmethod
    def _version_matches_pattern(cls, value: str) -> str:
        if not _VERSION_PATTERN.match(value):
            raise ValueError(f"version {value!r} is not semver (X.Y.Z)")
        return value


class ConstitutionSpec(SpecBase):
    pass


class Budget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_tokens_per_run: int
    max_usd_per_run: float
    max_tool_calls: int


class IO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_schema: str
    output_schema: str


class AgentSpec(SpecBase):
    model_tier: ModelTier
    prompt_path: str
    tools: list[str] = Field(default_factory=list)
    data_sources: list[str] = Field(default_factory=list)
    budget: Budget
    io: IO


class GraphSpec(SpecBase):
    pass


class RateLimits(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_calls_per_run: int
    max_calls_per_minute: int


DataClassification = Literal["public", "internal", "confidential"]
ToolKind = Literal["mcp_server", "local_tool"]


class ToolSpec(SpecBase):
    kind: ToolKind
    scopes: list[str] = Field(default_factory=list)
    rate_limits: RateLimits
    data_classification: DataClassification = "internal"


class DataSourceAccess(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allowed_tables: list[str] = Field(default_factory=list)
    denied_columns: list[str] = Field(default_factory=list)
    max_rows: int = 1000


class DataSourceSpec(SpecBase):
    classification: DataClassification
    access: DataSourceAccess
    semantics: str
    freshness: str


class EvalSpec(SpecBase):
    pass


LangSmithTarget = Literal["cloud", "self_hosted"]
DeployTarget = Literal["self_hosted", "langgraph_platform"]


class OpsSpec(SpecBase):
    deploy_target: DeployTarget
    providers: list[str] = Field(default_factory=list)
    langsmith_target: LangSmithTarget = "cloud"
    langsmith_endpoint: str | None = None  # required when langsmith_target=self_hosted


class AdrSpec(SpecBase):
    date: datetime.date


_KIND_BY_PREFIX: dict[str, type[SpecBase]] = {
    "CON": ConstitutionSpec,
    "AGT": AgentSpec,
    "GRP": GraphSpec,
    "TOOL": ToolSpec,
    "DS": DataSourceSpec,
    "EVL": EvalSpec,
    "OPS": OpsSpec,
    "ADR": AdrSpec,
}


def model_for_id(spec_id: str) -> type[SpecBase]:
    """Return the Pydantic model class governing a spec id's kind."""
    prefix = spec_id.split("-", 1)[0]
    try:
        return _KIND_BY_PREFIX[prefix]
    except KeyError as exc:
        raise ValueError(f"unknown spec kind prefix {prefix!r} in id {spec_id!r}") from exc
