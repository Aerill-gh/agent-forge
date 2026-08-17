from pathlib import Path

import pytest

from agentcore.specs.loader import SpecParseError, SpecValidationError, load_spec
from agentcore.specs.models import AdrSpec

VALID_ADR = """\
---
id: ADR-999
title: Test decision
status: draft
version: 0.1.0
owner: "@tester"
date: 2026-08-17
governs:
  paths: []
---

# ADR-999 — Test decision
"""

INVALID_ADR_BAD_ID = """\
---
id: NOT-A-REAL-ID
title: Test decision
status: draft
version: 0.1.0
owner: "@tester"
date: 2026-08-17
---
"""

INVALID_ADR_MISSING_DATE = """\
---
id: ADR-998
title: Test decision
status: draft
version: 0.1.0
owner: "@tester"
---
"""


def test_load_spec_valid(tmp_path: Path) -> None:
    spec_file = tmp_path / "ADR-999-test.md"
    spec_file.write_text(VALID_ADR)

    result = load_spec(spec_file)

    assert isinstance(result, AdrSpec)
    assert result.id == "ADR-999"
    assert result.status == "draft"


def test_load_spec_invalid(tmp_path: Path) -> None:
    spec_file = tmp_path / "bad-id.md"
    spec_file.write_text(INVALID_ADR_BAD_ID)

    with pytest.raises(SpecParseError, match="unknown spec kind prefix"):
        load_spec(spec_file)

    spec_file2 = tmp_path / "missing-date.md"
    spec_file2.write_text(INVALID_ADR_MISSING_DATE)

    with pytest.raises(SpecValidationError):
        load_spec(spec_file2)


def test_load_spec_missing_frontmatter(tmp_path: Path) -> None:
    spec_file = tmp_path / "no-frontmatter.md"
    spec_file.write_text("# Just a heading, no frontmatter\n")

    with pytest.raises(SpecParseError, match="must start with"):
        load_spec(spec_file)
