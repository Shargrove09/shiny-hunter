from dataclasses import dataclass
from typing import Optional

@dataclass
class ShinyHunterConfig:
    # Screenshot settings
    screenshot_region_x: int = 1180
    screenshot_region_y: int = 132
    emulator_width: int = 1290
    emulator_height: int = 900
    
    # Input delays
    pyautogui_pause: float = 0.8
    pydirectinput_pause: float = 1
    encounter_delay: float = 5.0
    restart_delay: float = 7.0
    
    # New verification settings
    max_encounter_retries: int = 3
    screen_verification_threshold: float = 0.8
    verification_delay: float = 1.0
    
    # Shiny detection
    # correlation_threshold: float = 0.11743583737659061
    correlation_threshold: float = 0.17200420695376417
    correlation_tolerance: float = 0.0001
    
    # File paths
    reference_image_path: str = './images/shiny_mewtwo_ref.png'
    encounter_screen_template_path: str = './images/encounter_screen_template.png'
    
    # Safety
    failsafe_enabled: bool = False

class ConfigManager:
    _instance: Optional['ConfigManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.config = ShinyHunterConfig()
        return cls._instance
    
    def get_config(self) -> ShinyHunterConfig:
        return self.config