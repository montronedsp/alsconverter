from __future__ import annotations

from pathlib import Path

import pytest

from tests.fixture_builder import (
    build_minimal_live11_xml,
    build_minimal_live12_xml,
    write_als,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session", autouse=True)
def ensure_fixtures() -> None:
    write_als(FIXTURES / "live12_minimal.als", build_minimal_live12_xml())
    write_als(
        FIXTURES / "live12_with_l12_nodes.als",
        build_minimal_live12_xml(with_live12_nodes=True, with_plugin=True),
    )
    write_als(FIXTURES / "live11_minimal.als", build_minimal_live11_xml())


@pytest.fixture
def live12_minimal() -> Path:
    return FIXTURES / "live12_minimal.als"


@pytest.fixture
def live12_blocked() -> Path:
    return FIXTURES / "live12_with_l12_nodes.als"


@pytest.fixture
def live11_minimal() -> Path:
    return FIXTURES / "live11_minimal.als"
