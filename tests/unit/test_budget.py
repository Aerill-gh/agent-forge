import pytest

from agentcore.budget import BudgetExceeded, BudgetTracker, estimate_tokens
from agentcore.specs.models import Budget


def test_budget_tracker_warns_then_raises() -> None:
    budget = Budget(max_tokens_per_run=100, max_usd_per_run=1.0, max_tool_calls=10)
    tracker = BudgetTracker(budget)

    warnings = tracker.record_tokens(85)
    assert len(warnings) == 1
    assert warnings[0].dimension == "tokens"

    with pytest.raises(BudgetExceeded) as exc_info:
        tracker.record_tokens(20)

    assert exc_info.value.dimension == "tokens"


def test_budget_tracker_tracks_tool_calls_independently() -> None:
    budget = Budget(max_tokens_per_run=1_000_000, max_usd_per_run=100.0, max_tool_calls=2)
    tracker = BudgetTracker(budget)

    tracker.record_tool_call()
    with pytest.raises(BudgetExceeded) as exc_info:
        tracker.record_tool_call()
        tracker.record_tool_call()

    assert exc_info.value.dimension == "tool_calls"


def test_estimate_tokens_is_positive_and_roughly_proportional() -> None:
    assert estimate_tokens("") == 1
    assert estimate_tokens("a" * 400) > estimate_tokens("a" * 40)
