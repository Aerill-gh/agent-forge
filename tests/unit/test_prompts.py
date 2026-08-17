from pathlib import Path

from agentcore.prompts import content_hash, lint_rail, render_prompt

RAIL_PROMPT = """\
## Role

You are a {{ persona }}.

## Action

Answer the user's question directly.

## Information

You have access to: {{ tools }}.

## Limits

Never fabricate data you don't have.
"""

MISSING_LIMITS_PROMPT = """\
## Role

You are an assistant.

## Action

Answer questions.

## Information

None.
"""


def test_render_and_lint_rail(tmp_path: Path) -> None:
    path = tmp_path / "fake_system.md"
    path.write_text(RAIL_PROMPT)

    rendered = render_prompt(path, persona="risk analyst", tools="none")

    assert "You are a risk analyst." in rendered
    assert "You have access to: none." in rendered
    assert lint_rail(path) == []

    bad_path = tmp_path / "bad_system.md"
    bad_path.write_text(MISSING_LIMITS_PROMPT)

    assert lint_rail(bad_path) == ["Limits"]


def test_content_hash_changes_with_content(tmp_path: Path) -> None:
    path = tmp_path / "p.md"
    path.write_text("v1")
    hash1 = content_hash(path)

    path.write_text("v2")
    hash2 = content_hash(path)

    assert hash1 != hash2
    assert len(hash1) == 12
