"""`forge` CLI entrypoint.

`forge spec lint` and `forge spec show` land in P1 alongside the spec
engine (ADR-001). Remaining subcommands (`run`, `resume`, `status`, `eval`,
`cost report`, `mcp doctor`) land in P2+.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agentcore.specs.index import build_index
from agentcore.specs.lint import spec_lint
from agentcore.specs.loader import SpecParseError, SpecValidationError, load_spec
from agentcore.specs.resolve import resolve


def _cmd_spec_lint(args: argparse.Namespace) -> int:
    failures = spec_lint(args.specs_dir)
    if not failures:
        print(f"spec_lint: {args.specs_dir} clean")
        return 0
    for failure in failures:
        print(f"spec_lint: {failure}", file=sys.stderr)
    print(f"spec_lint: {len(failures)} failure(s)", file=sys.stderr)
    return 1


def _cmd_spec_show(args: argparse.Namespace) -> int:
    matches = list(Path(args.specs_dir).rglob(f"{args.spec_id}*.md"))
    matches = [m for m in matches if "templates" not in m.parts]
    if not matches:
        print(f"forge spec show: no spec file found for {args.spec_id!r}", file=sys.stderr)
        return 1
    try:
        model = load_spec(matches[0])
    except (SpecParseError, SpecValidationError) as exc:
        print(f"forge spec show: {exc}", file=sys.stderr)
        return 1
    print(model.model_dump_json(indent=2))
    return 0


def _cmd_spec_for(args: argparse.Namespace) -> int:
    index = build_index(args.specs_dir)
    spec_id = resolve(args.target, index)
    if spec_id is None:
        print(f"forge spec for: no spec governs {args.target!r}", file=sys.stderr)
        return 1
    print(spec_id)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forge")
    subparsers = parser.add_subparsers(dest="command")

    spec_parser = subparsers.add_parser("spec", help="spec engine commands")
    spec_subparsers = spec_parser.add_subparsers(dest="spec_command")

    lint_parser = spec_subparsers.add_parser("lint", help="lint all specs under a directory")
    lint_parser.add_argument("specs_dir", nargs="?", default="specs")
    lint_parser.set_defaults(func=_cmd_spec_lint)

    show_parser = spec_subparsers.add_parser("show", help="print a spec's resolved model as JSON")
    show_parser.add_argument("spec_id")
    show_parser.add_argument("--specs-dir", dest="specs_dir", default="specs")
    show_parser.set_defaults(func=_cmd_spec_show)

    for_parser = spec_subparsers.add_parser("for", help="resolve the spec governing a target path")
    for_parser.add_argument("target")
    for_parser.add_argument("--specs-dir", dest="specs_dir", default="specs")
    for_parser.set_defaults(func=_cmd_spec_for)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(0 if args.command is None else 1)
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
