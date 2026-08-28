import os
import sys
import tempfile
from datetime import datetime
from config import ConfigManager, project_path
import window_capture

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
            self.screenshots_dir = project_path('screenshots')
            self._ensure_directory_exists()
            self._window_capturer = None
        except Exception as e:
            raise RuntimeError(f"Failed to initialize ScreenshotManager: {e}") from e
    def _ensure_directory_exists(self):
        """Create screenshots directory if it doesn't exist."""
        if not os.path.exists(self.screenshots_dir):
            os.makedirs(self.screenshots_dir)

    def _get_window_capturer(self):
        """Lazily build the window capturer, rebuilding if the target changed."""
        owner = getattr(self.config, 'capture_window_owner', '')
        title = getattr(self.config, 'capture_window_title', '')

        if not owner and not title:
            raise RuntimeError(
                "capture_mode is 'window' but no capture_window_owner is set. "
                "Run: python tools/setup_capture.py"
            )

        if (self._window_capturer is None
                or self._window_capturer.owner != owner
                or self._window_capturer.title != title):
            self._window_capturer = window_capture.WindowCapturer(owner, title)

        return self._window_capturer

    def _uses_window_capture(self) -> bool:
        return getattr(self.config, 'capture_mode', 'region') == 'window'

    def grab(self):
        """Capture the configured source and return a PIL Image, without saving.

        Window capture is preferred where configured: it is immune to the window
        moving, to occlusion, and to Retina point-vs-pixel confusion, all of which
        silently corrupt a screen-rectangle capture.
        """
        if self._uses_window_capture():
            return self._get_window_capturer().grab()

        if SCREENSHOT_METHOD is None:
            raise RuntimeError(
                "No screenshot library available. "
                "Please fix X11 authorization (run 'xhost +local:') "
                "or install required dependencies."
            )

        capture_width = self.config.screenshot_capture_width or self.config.emulator_width
        capture_height = self.config.screenshot_capture_height or self.config.emulator_height
        region = (
            self.config.screenshot_region_x,
            self.config.screenshot_region_y,
            capture_width,
            capture_height
        )

        if SCREENSHOT_METHOD == "pyautogui":
            return pyautogui.screenshot(region=region)

        # PIL ImageGrab uses (left, top, right, bottom) format
        bbox = (
            region[0],
            region[1],
            region[0] + region[2],
            region[1] + region[3]
        )
        return ImageGrab.grab(bbox=bbox)

    def grab_array(self):
        """Capture straight to a BGR numpy array, never touching disk.

        The walk loop polls a detector several times per second. Routing those
        through take_screenshot would write roughly 48,000 PNGs (~6 GB) over an
        overnight hunt for frames that are looked at once and discarded.
        """
        import numpy as np
        import cv2
        return cv2.cvtColor(np.asarray(self.grab().convert('RGB')), cv2.COLOR_RGB2BGR)

    def grab_native(self):
        """Capture and normalise to exactly 240x160, the GBA's own resolution.

        This is the frame every detector and the sprite matcher should work on.
        Once a frame is in native space, window size, Retina scale and letterbox
        no longer affect any measurement, and regions can be plain native pixel
        coordinates that mean the same thing forever.
        """
        import image_processor
        return image_processor.to_native(self.grab_array(), self.config.game_viewport)

    def detect_viewport(self, frame=None, store: bool = False):
        """Locate the game viewport in a capture and validate it.

        Returns (rect_or_None, reason). Detection is only trustworthy on a battle
        frame: Gen 3 fills beyond the map boundary with black, which reads as
        letterbox, so an overworld frame yields a truncated viewport. The caller
        gets a validated answer or nothing, never a plausible-looking guess.
        """
        import image_processor

        if frame is None:
            frame = self.grab_array()

        candidates = image_processor.detect_game_viewport(frame)
        if not candidates:
            return None, "no viewport found in the capture"

        best = candidates[0]
        ok, reason = image_processor.validate_viewport(best['pixels'])
        if not ok:
            return None, reason

        if store:
            self.config.game_viewport = best['fraction']
        return best, reason

    def take_screenshot(self, filename: str) -> str:
        """Take a screenshot and save it with the given filename."""
        # Sanitize filename to prevent path traversal
        filename = os.path.basename(filename)

        screenshot = self.grab()

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