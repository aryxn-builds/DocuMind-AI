"""
Root conftest.py for the API test suite.

Ensures that global state in FastAPI's dependency_overrides and in the
security module's PyJWKClient singleton cannot leak between test modules.
"""

import pytest

from app.main import app


@pytest.fixture(autouse=True, scope="function")
def _global_dependency_cleanup():
    """
    Guarantee that FastAPI dependency_overrides are empty before and after
    every single test function, regardless of which module owns the fixture.
    This prevents any test that sets dependency_overrides from contaminating
    subsequent tests in other modules.
    """
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()
