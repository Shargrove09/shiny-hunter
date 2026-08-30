from dataclasses import dataclass, field
from dataclasses import asdict
from typing import List, Optional
import threading
import json
import os
import re
import socket

# Anchor project files to the repo, not the working directory. Resolving against
# os.getcwd() meant running from src/shinyhunter/ read and wrote a *different*
# shinyhunter_config.json than running from the repo root, so settings appeared
# to silently not take effect depending on where the app was launched from.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CONFIG_NAME = 'shinyhunter_config.json'


def project_path(relative: str) -> str:
    """Resolve a project-relative path against the repo root."""
    if os.path.isabs(relative):
        return relative
    return os.path.join(PROJECT_ROOT, relative.lstrip('./'))


def host_slug() -> str:
    """This machine's short name, safe to put in a filename."""
    name = socket.gethostname().split('.')[0]
    return re.sub(r'[^A-Za-z0-9_-]', '-', name) or 'unknown'


def config_path() -> str:
    """Which config file this machine uses.

    Almost everything in the config is *geometry* -- window owner, viewport,
    ROIs -- and geometry is a property of the machine, not of the project. One
    shared file means syncing a branch between a Mac and a VM silently overwrites
    whichever one was calibrated last, which is indistinguishable from the
    hunt breaking on its own.

    Order: $SHINYHUNTER_CONFIG, then a per-host file, then the shared default.
    """
    override = os.environ.get('SHINYHUNTER_CONFIG')
    if override:
        return project_path(override)

    per_host = project_path(f'shinyhunter_config.{host_slug()}.json')
    if os.path.exists(per_host):
        return per_host

    return project_path(CONFIG_NAME)

@dataclass
class ShinyHunterConfig:
    # Capture source.
    # 'window' captures the game window by id (macOS): immune to the window
    # moving, to occlusion, and to Retina point-vs-pixel mismatch.
    # 'region' captures a screen rectangle and is subject to all three.
    capture_mode: str = 'region'
    capture_window_owner: str = ''   # e.g. 'Playback' — matched case-insensitively
    capture_window_title: str = ''

    # Game viewport as fractions [x, y, w, h] of the captured image. Fractions
    # rather than pixels so nothing breaks if the capture resolution changes.
    game_viewport: List[float] = field(default_factory=lambda: [0.0, 0.0, 1.0, 1.0])
    # The capture size game_viewport was measured against, purely so a mismatch
    # can name what changed. A fractional viewport is correct at exactly one
    # capture *aspect* -- it survives the window being scaled, not reshaped.
    game_viewport_capture: Optional[List[int]] = None

    # Regions of interest.
    # battle_detector: a patch identical in every wild battle and absent from the
    # overworld, polled to answer "is a battle up yet".
    # enemy_sprite: the 64x64 box the wild sprite is drawn in.
    # In NATIVE 240x160 pixels: [x, y, w, h]. Native rather than fractions so the
    # numbers mean the same thing at any window size, and are readable.
    battle_detector_roi: List[int] = field(default_factory=lambda: [80, 136, 40, 20])
    battle_detector_template: str = './screenshots/templates/battle_ready.png'
    battle_detector_threshold: float = 0.75
    enemy_sprite_roi: List[int] = field(default_factory=lambda: [143, 8, 64, 64])
    # battle_menu: the FIGHT/BAG/POKeMON/RUN box. Distinct from battle_detector,
    # which is up during the intro text too — this one says the game is ready to
    # accept menu input, so the flee sequence can wait for it instead of guessing
    # a delay and pressing into nothing.
    battle_menu_roi: List[int] = field(default_factory=lambda: [136, 124, 40, 24])
    battle_menu_template: str = './screenshots/templates/battle_menu.png'
    battle_menu_threshold: float = 0.70

    # Sprite matching. Thresholds sit inside measured gaps, and are deliberately
    # asymmetric: a borderline sprite must fall to 'unknown' (one prompt), never
    # to 'normal' (a shiny fled past in silence).
    sprite_shape_threshold: float = 0.85
    sprite_colour_threshold: float = 0.45
    sprite_silhouette_threshold: float = 0.92
    sprite_ambiguity_margin: float = 0.05
    sprite_library_root: str = './sprite_library'

    # Walking and unattended-run limits
    walk_step_duration: float = 0.35
    walk_jitter: float = 0.0
    detector_poll_interval: float = 0.35
    max_flee_attempts: int = 3
    max_consecutive_resets: int = 3
    max_consecutive_errors: int = 5
    error_backoff_seconds: float = 5.0

    # Screenshot settings (region mode)
    screenshot_region_x: int = 1180
    screenshot_region_y: int = 132
    emulator_width: int = 1290
    emulator_height: int = 900
    # Optional capture crop — if set, the screenshot is limited to this size
    # instead of the full emulator boundary. Set to 0 to use the boundary size.
    screenshot_capture_width: int = 0
    screenshot_capture_height: int = 0
    
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
    pre_encounter_template_path: str = './screenshots/encounter_screen_template.png'
    encounter_template_path: str = './screenshots/battle_screen_template.png'
    
    # Safety
    failsafe_enabled: bool = False

    # Custom encounter sequence
    use_custom_sequence: bool = False
    sequence_config_path: str = './encounter_sequence.json'

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
                    cls._instance._config_file_path = config_path()
                    cls._instance.load_config()
        return cls._instance

    def get_config(self) -> ShinyHunterConfig:
        return self.config

    @property
    def path(self) -> str:
        """The config file actually in use — print it, don't assume it."""
        return self._config_file_path


    def load_config(self):
        """Load configuration from JSON file if it exists."""
        # Say which file won. Two separate bugs in this project came down to
        # reading one config while writing another, and both were invisible.
        print(f"config: {os.path.relpath(self._config_file_path, PROJECT_ROOT)}"
              f"{'' if os.path.exists(self._config_file_path) else '  (absent — using defaults)'}")

        if not os.path.exists(self._config_file_path):
            return

        try:
            with open(self._config_file_path, 'r', encoding='utf-8') as config_file:
                data = json.load(config_file)

            # Migrate: old configs stored the overworld template under encounter_template_path.
            # It is now pre_encounter_template_path; encounter_template_path is the battle screen.
            if 'encounter_template_path' in data and 'pre_encounter_template_path' not in data:
                self.config.pre_encounter_template_path = data.pop('encounter_template_path')

            # ROIs used to be fractions of the viewport; they are now native
            # 240x160 pixels. Convert on load so an older config keeps working.
            for key, (width, height) in (('battle_detector_roi', (240, 160)),
                                         ('battle_menu_roi', (240, 160)),
                                         ('enemy_sprite_roi', (240, 160))):
                rect = data.get(key)
                if rect and max(rect) <= 1.0:
                    data[key] = [int(round(rect[0] * width)), int(round(rect[1] * height)),
                                 int(round(rect[2] * width)), int(round(rect[3] * height))]
                    print(f"config: migrated {key} from fractions to native pixels {data[key]}")

            for key, value in data.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
        except Exception as error:
            print(f"Failed to load config: {error}")

    def save_config(self):
        """Save configuration to a JSON file."""
        try:
            with open(self._config_file_path, 'w', encoding='utf-8') as config_file:
                json.dump(asdict(self.config), config_file, indent=2)
            print(f"Config updated: threshold={self.config.correlation_threshold}")
        except Exception as error:
            print(f"Failed to save config: {error}")