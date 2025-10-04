from dataclasses import dataclass
from typing import Optional
import threading

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
    
    # New verification settings
    max_encounter_retries: int = 3
    screen_verification_threshold: float = 0.8
    verification_delay: float = 1.0
    
    # Shiny detection
    # correlation_threshold: float = 0.2228965728096372
    correlation_threshold: float = 0.4468404494968037
    correlation_tolerance: float = 0.0001
    
    # Calibration mode
    calibration_mode: bool = False  # When True, app is in threshold setup mode
    
    # File paths
    reference_image_path: str = './images/shiny_mewtwo_ref.png'
    encounter_screen_template_path: str = './images/encounter_screen_template.png'
    calibration_reference_path: str = './images/calibration_reference.png'
    
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
        return cls._instance
    
    def get_config(self) -> ShinyHunterConfig:
        return self.config
    
    def save_config(self):
        """
        Save configuration to file (placeholder).
        Currently config is in-memory only.
        TODO: Implement persistence to JSON or YAML file.
        """
        # For now, just log that settings were updated
        # In the future, this could write to a config.json file
        print(f"Config updated: threshold={self.config.correlation_threshold}")