"""`forge` CLI entrypoint.

Subcommands (spec {new,lint,index,for,trace}, run, resume, status, eval,
cost report, mcp doctor) land in P1+ alongside the spec engine and runtime
they operate on. P0 ships the entrypoint stub so `uv run forge` resolves.
"""


def main() -> None:
    print("forge: no subcommands yet (P0 scaffold) — see agentic-platform-plan.md")


if __name__ == "__main__":
    main()
