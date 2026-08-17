"""`@spec("AGT-014")` binds a function/class to its governing spec id.

P1 only needs the binding recorded and inspectable via `registry`; the P2
binding layer (`governs:` resolver, orphan/ambiguity checks) consumes it.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TypeVar

T = TypeVar("T")

registry: dict[str, list[object]] = defaultdict(list)


def spec(spec_id: str) -> _SpecDecorator:
    """Decorator factory: `@spec("AGT-014")` on a function or class."""
    return _SpecDecorator(spec_id)


class _SpecDecorator:
    def __init__(self, spec_id: str) -> None:
        self.spec_id = spec_id

    def __call__(self, obj: T) -> T:
        registry[self.spec_id].append(obj)
        return obj
