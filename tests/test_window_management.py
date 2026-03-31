"""Tests for the window management factory and base classes."""

import os
import platform

import pytest

# These modules import display libraries at module level, so they
# cannot even be imported when no display is available (headless CI).
if not os.environ.get("DISPLAY"):
    pytest.skip("No DISPLAY available", allow_module_level=True)

from window_management import WindowManagerFactory, EmbeddingMode


class TestWindowManagerFactory:
    """Verify factory creation and platform detection."""

    def test_get_platform_info(self):
        info = WindowManagerFactory.get_platform_info()
        assert "platform" in info
        assert info["platform"] == platform.system()

    def test_get_available_managers_returns_list(self):
        managers = WindowManagerFactory.get_available_managers()
        assert isinstance(managers, list)

    def test_create_returns_manager(self):
        """Factory returns a working manager (or raises ImportError)."""
        try:
            manager = WindowManagerFactory.create()
            assert manager is not None
            assert manager.get_embedding_mode() in EmbeddingMode
        except ImportError:
            pytest.skip("No window manager library available in this environment")

    def test_create_specific_unknown_returns_none(self):
        assert WindowManagerFactory.create_specific("nonexistent") is None
