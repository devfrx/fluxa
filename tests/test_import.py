"""Test fluxa."""

import fluxa


def test_import() -> None:
    """Test that the package can be imported."""
    assert isinstance(fluxa.__name__, str)
