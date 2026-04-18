"""Contract tests for saved Daikin cloud fixtures.

Every JSON in ``tests/fixtures/`` is treated as a captured cloud response
and must satisfy the minimal response contract declared in
``custom_components.daikin_onecta.schema``. This catches regressions where a
fixture drifts away from the shape the integration relies on, and doubles as
a guard against the Daikin cloud silently changing its response layout
(phase 5.5 will wire the same validator into the coordinator path).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from custom_components.daikin_onecta.schema import validate_cloud_response

FIXTURES_DIR = Path(__file__).parent / "fixtures"
FIXTURES = sorted(FIXTURES_DIR.glob("*.json"))


@pytest.mark.parametrize("fixture_path", FIXTURES, ids=lambda p: p.name)
def test_fixture_matches_cloud_contract(fixture_path: Path) -> None:
    """Every saved cloud fixture must satisfy the minimal response contract."""
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    issues = validate_cloud_response(payload)
    assert issues == [], f"{fixture_path.name} violates contract: {issues}"


def test_fixture_directory_is_not_empty() -> None:
    """Guard against accidentally deleting every fixture at once."""
    assert FIXTURES, "no fixtures discovered under tests/fixtures/"
