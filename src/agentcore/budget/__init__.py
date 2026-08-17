"""BudgetTracker: pre-flight estimate + running counter, per ADR-004.

Soft-warns at 80% of any dimension (tokens, USD, tool calls), raises
`BudgetExceeded` at 100%. Token/USD figures are estimates
(`len(text) // 4` as a rough tokens-per-char heuristic — not a real
tokenizer; swap in a provider-specific one later without changing this
interface), not billing-accurate counts.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agentcore.specs.models import Budget

_WARN_THRESHOLD = 0.8


class BudgetExceeded(Exception):
    def __init__(self, dimension: str, used: float, limit: float) -> None:
        self.dimension = dimension
        self.used = used
        self.limit = limit
        super().__init__(f"budget exceeded on {dimension}: {used} > {limit}")


@dataclass
class BudgetWarning:
    dimension: str
    used: float
    limit: float


def estimate_tokens(text: str) -> int:
    """Rough pre-flight estimate — not a real tokenizer, see module docstring."""
    return max(1, len(text) // 4)


@dataclass
class BudgetTracker:
    budget: Budget
    tokens_used: int = field(default=0, init=False)
    usd_used: float = field(default=0.0, init=False)
    tool_calls_used: int = field(default=0, init=False)

    def record_tokens(self, count: int, usd_cost: float = 0.0) -> list[BudgetWarning]:
        self.tokens_used += count
        self.usd_used += usd_cost
        warnings = []
        warnings.extend(self._check("tokens", self.tokens_used, self.budget.max_tokens_per_run))
        warnings.extend(self._check("usd", self.usd_used, self.budget.max_usd_per_run))
        return warnings

    def record_tool_call(self) -> list[BudgetWarning]:
        self.tool_calls_used += 1
        return self._check("tool_calls", self.tool_calls_used, self.budget.max_tool_calls)

    def _check(self, dimension: str, used: float, limit: float) -> list[BudgetWarning]:
        if used > limit:
            raise BudgetExceeded(dimension, used, limit)
        if used >= limit * _WARN_THRESHOLD:
            return [BudgetWarning(dimension, used, limit)]
        return []
