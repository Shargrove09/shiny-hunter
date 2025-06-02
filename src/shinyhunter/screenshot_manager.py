import pyautogui
import os
from datetime import datetime
from config import ConfigManager

class ScreenshotManager:
    def __init__(self):
        self.config = ConfigManager().get_config()
        self.screenshots_dir = 'screenshots'
        self._ensure_directory_exists()
    
    def _ensure_directory_exists(self):
        """Create screenshots directory if it doesn't exist."""
        if not os.path.exists(self.screenshots_dir):
            os.makedirs(self.screenshots_dir)
    
    def take_screenshot(self, filename: str) -> str:
        """Take a screenshot and save it with the given filename."""
        region = (
            self.config.screenshot_region_x,
            self.config.screenshot_region_y,
            self.config.emulator_width,
            self.config.emulator_height
        )
        
        screenshot = pyautogui.screenshot(region=region)
        filepath = os.path.join(self.screenshots_dir, filename)
        screenshot.save(filepath)
        return filepath
    
    def take_timestamped_screenshot(self, prefix: str = "screenshot") -> str:
        """Take a screenshot with timestamp in filename."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}.png"
        return self.take_screenshot(filename)