from dataclasses import dataclass, asdict
from typing import Optional
import logging
import threading
import json
import os

logger = logging.getLogger(__name__)

@dataclass
class ShinyHunterConfig:
    # Screenshot settings
    screenshot_region_x: int = 1180
    screenshot_region_y: int = 132
    emulator_width: int = 1290
    emulator_height: int = 900
    
    # Input delays
    pyautogui_pause: float = 2.0
    input_pause: float = 0.7  # Cross-platform input delay (replaces pydirectinput_pause)
    encounter_delay: float = 5.0
    restart_delay: float = 4.0
    timing_jitter: float = 1.0  # Max random variation (±seconds) added to delays to avoid RNG lock
    
    # New verification settings
    max_encounter_retries: int = 3
    screen_verification_threshold: float = 0.8
    verification_delay: float = 1.0
    
    # Shiny detection
    # correlation_threshold: float = 0.2228965728096372
    correlation_threshold: float = 0.4468404494968037 # we should just set the threshold u
    correlation_tolerance: float = 0.0001
    
    # Calibration mode
    calibration_mode: bool = False  # When True, app is in threshold setup mode
    
    # File paths
    calibration_reference_path: str = './screenshots/calibration_reference.png'
    encounter_template_path: str = './screenshots/encounter_screen_template.png'
    
    # Safety
    failsafe_enabled: bool = False

class ConfigManager:
    _instance: Optional['ConfigManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        # First check (without lock for performance)
        if cls._instance is None:
            # Acquire lock for thread safety
            with cls._lock:
                # Second check (with lock to prevent race condition)
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance.config = ShinyHunterConfig()
                    cls._instance._config_file_path = os.path.join(os.getcwd(), 'shinyhunter_config.json')
                    cls._instance.load_config()
        return cls._instance
    
    def get_config(self) -> ShinyHunterConfig:
        return self.config
    
    def load_config(self):
        """Load configuration from JSON file if it exists."""
        if not os.path.exists(self._config_file_path):
            return

        try:
            with open(self._config_file_path, 'r', encoding='utf-8') as config_file:
                data = json.load(config_file)

            for key, value in data.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
        except Exception as error:
            logger.warning("Failed to load config: %s", error)

    def save_config(self):
        """Save configuration to a JSON file."""
        try:
            with open(self._config_file_path, 'w', encoding='utf-8') as config_file:
                json.dump(asdict(self.config), config_file, indent=2)
            print(f"Config updated: threshold={self.config.correlation_threshold}")
        except Exception as error:
            logger.error("Failed to save config: %s", error)