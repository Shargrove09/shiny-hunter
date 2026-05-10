import os
import sys
import tempfile
from datetime import datetime
from config import ConfigManager

# Try to import screenshot libraries with graceful fallback
SCREENSHOT_METHOD = None

try:
    import pyautogui
    SCREENSHOT_METHOD = "pyautogui"
except Exception as e:
    if sys.platform.startswith('linux'):
        print(f"Warning: pyautogui not available on Linux: {e}")
        print("Attempting to use PIL/Pillow for screenshots...")
    
    try:
        from PIL import ImageGrab
        SCREENSHOT_METHOD = "pil"
        print("Using PIL/Pillow for screenshots")
    except ImportError:
        print("Warning: No screenshot library available")
        print("Please fix X11 authorization or install required dependencies")
        SCREENSHOT_METHOD = None

class ScreenshotManager:
    def __init__(self):
        try:
            self.config = ConfigManager().get_config()
            self.screenshots_dir = 'screenshots'
            self._ensure_directory_exists()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize ScreenshotManager: {e}") from e    
    def _ensure_directory_exists(self):
        """Create screenshots directory if it doesn't exist."""
        if not os.path.exists(self.screenshots_dir):
            os.makedirs(self.screenshots_dir)
    def take_screenshot(self, filename: str) -> str:
        """Take a screenshot and save it with the given filename."""
        if SCREENSHOT_METHOD is None:
            raise RuntimeError(
                "No screenshot library available. "
                "Please fix X11 authorization (run 'xhost +local:') "
                "or install required dependencies."
            )
        
        # Sanitize filename to prevent path traversal
        filename = os.path.basename(filename)
        
        region = (
            self.config.screenshot_region_x,
            self.config.screenshot_region_y,
            self.config.emulator_width,
            self.config.emulator_height
        )
        
        if SCREENSHOT_METHOD == "pyautogui":
            screenshot = pyautogui.screenshot(region=region)
        else:  # PIL
            # PIL ImageGrab uses (left, top, right, bottom) format
            bbox = (
                region[0],
                region[1],
                region[0] + region[2],
                region[1] + region[3]
            )
            screenshot = ImageGrab.grab(bbox=bbox)
        
        filepath = os.path.join(self.screenshots_dir, filename)

        # Write to a temp file in the same directory, then atomically replace the
        # target.  os.replace only needs write permission on the parent directory,
        # so it succeeds even when a previous run left the file owned by root or
        # with read-only permissions.
        fd, tmp_path = tempfile.mkstemp(dir=self.screenshots_dir, suffix='.png')
        try:
            os.close(fd)
            screenshot.save(tmp_path)
            os.replace(tmp_path, filepath)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

        return filepath       
    def take_timestamped_screenshot(self, prefix: str = "screenshot") -> str:
        """Take a screenshot with timestamp in filename."""
        # Sanitize prefix to prevent path traversal
        prefix = os.path.basename(prefix)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}.png"
        return self.take_screenshot(filename)      