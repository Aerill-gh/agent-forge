.PHONY: sync lint format typecheck test check

sync:
	uv sync --frozen

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run mypy src/agentcore

test:
	uv run pytest

check: lint typecheck test
