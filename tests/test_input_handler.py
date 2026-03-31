"""Tests for the InputHandler module."""

import os
import pytest

# These modules import GUI/display libraries at module level, so they
# cannot even be imported when no display is available (headless CI).
if not os.environ.get("DISPLAY"):
    pytest.skip("No DISPLAY available", allow_module_level=True)

from config import ConfigManager
from input_handler import InputHandler


class TestInputHandlerInit:
    """Verify InputHandler initialises correctly without executing keystrokes."""

    def test_import(self):
        """InputHandler can be imported and instantiated."""
        handler = InputHandler()
        assert handler is not None

    def test_platform_detection(self):
        """Platform string is populated."""
        handler = InputHandler()
        assert handler.platform in ("Windows", "Linux", "Darwin")

    def test_input_method_selected(self):
        """An input method (pynput or pyautogui) is selected."""
        handler = InputHandler()
        assert handler.input_method in ("pynput", "pyautogui")

    def test_key_mapping(self):
        """Key mappings contain the expected game controls."""
        handler = InputHandler()
        key_map = handler._get_key_mapping()
        for expected_key in ("x", "z", "enter", "backspace"):
            assert expected_key in key_map
