"""Tests for the ConfigManager singleton and ShinyHunterConfig dataclass."""

import json
import os
import tempfile

import pytest
from config import ConfigManager, ShinyHunterConfig


class TestShinyHunterConfig:
    """Verify the configuration dataclass defaults."""

    def test_default_encounter_delay(self):
        config = ShinyHunterConfig()
        assert config.encounter_delay == 5.0

    def test_default_timing_jitter(self):
        config = ShinyHunterConfig()
        assert config.timing_jitter == 1.0

    def test_default_correlation_tolerance(self):
        config = ShinyHunterConfig()
        assert config.correlation_tolerance == 0.0001

    def test_default_max_retries(self):
        config = ShinyHunterConfig()
        assert config.max_encounter_retries == 3


class TestConfigManager:
    """Verify ConfigManager singleton behaviour."""

    def test_singleton_returns_same_instance(self):
        a = ConfigManager()
        b = ConfigManager()
        assert a is b

    def test_get_config_returns_dataclass(self):
        config = ConfigManager().get_config()
        assert isinstance(config, ShinyHunterConfig)

    def test_save_and_load_round_trip(self, tmp_path):
        """Config can be saved to JSON and reloaded."""
        manager = ConfigManager()
        original_path = manager._config_file_path

        try:
            test_file = tmp_path / "test_config.json"
            manager._config_file_path = str(test_file)

            manager.config.encounter_delay = 99.0
            manager.save_config()

            assert test_file.exists()
            data = json.loads(test_file.read_text())
            assert data["encounter_delay"] == 99.0

        finally:
            # Restore original path and default value
            manager._config_file_path = original_path
            manager.config.encounter_delay = 5.0
