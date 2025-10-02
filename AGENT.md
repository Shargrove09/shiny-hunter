# AGENT.md - Codebase Guide for AI Agents

## Project Overview

**Shiny Hunter** is an automated Pokemon shiny hunting application that uses computer vision and input automation to repeatedly encounter Pokemon in an emulator until a shiny variant is found. The application is cross-platform compatible (Windows/Linux) and features a GUI built with Tkinter.

## Core Architecture

### Design Patterns

- **MVC-like Pattern**: Separation between GUI (`shiny_hunt_gui.py`), Controller (`shiny_hunter_controller.py`), and business logic components
- **Singleton Pattern**: Used in `ConfigManager` with thread-safe double-checked locking
- **Factory Pattern**: Used in `window_management/factory.py` for creating appropriate window managers
- **Strategy Pattern**: Cross-platform input handling with pynput/pyautogui fallback

### Key Principles

1. **Cross-Platform Compatibility**: Windows and Linux support via abstraction layers
2. **Decoupled Architecture**: GUI components are separate from core logic
3. **Thread Safety**: Singleton patterns use proper locking mechanisms
4. **Fail-Safe Design**: Multiple fallback mechanisms for library availability

## Directory Structure

```
src/shinyhunter/
├── main.py                      # Application entry point
├── shiny_hunter_controller.py   # Main application controller/driver
├── shiny_hunt_gui.py           # Tkinter GUI interface
├── config.py                    # Configuration management (singleton)
├── image_processor.py          # Computer vision and shiny detection
├── input_handler.py            # Cross-platform input automation
├── screenshot_manager.py       # Screenshot capture management
├── embedded_app.py             # Window embedding utilities
├── cross_platform_app.py       # Cross-platform window management
├── styles.py                   # GUI styling utilities
└── window_management/          # Modular window management system
    ├── base.py                 # Abstract base classes and interfaces
    ├── factory.py              # Window manager factory
    ├── pywinctl_manager.py     # PyWinCtl implementation (preferred)
    └── fallback_manager.py     # pygetwindow fallback (Windows-only)
```

## Core Components

### 1. ShinyHunterController (`shiny_hunter_controller.py`)

**Purpose**: Main application driver that orchestrates the shiny hunting loop

**Key Responsibilities**:

- Manages the hunt loop (encounter → screenshot → check → reset)
- Tracks attempt count using a plain integer with property accessors
- Coordinates between input handling, image processing, and screenshot management
- Provides logging interface for GUI

**Important Details**:

- Uses `_reset_count` (private int) with a `count` property (getter/setter)
- Increments counter ONLY after successful encounter verification (not before)
- Decoupled from Tkinter (no tk.IntVar usage)
- Thread-safe for concurrent access

**Key Methods**:

- `attempt_encounter()`: Main hunt loop
- `increment_count()`: Increments and returns new count
- `log(message)`: Logs to GUI if log_function is set

### 2. ShinyHuntGUI (`shiny_hunt_gui.py`)

**Purpose**: Tkinter-based graphical user interface

**Key Responsibilities**:

- Displays hunt status, attempt counter, and logs
- Provides controls (start, pause, stop, settings)
- Manages settings dialog for configuration changes
- Displays screenshots and reference images

**Important Details**:

- Accepts `controller` reference (not individual count variable)
- Uses `count_var` (tk.IntVar) for display purposes, syncs with `controller.count`
- Settings are persisted via `ConfigManager`
- Dark theme via `sv_ttk`

**Key Methods**:

- `log_message(message)`: Updates log display
- `update_count()`: Syncs display with controller count
- `open_settings()`: Opens settings modal dialog

### 3. ConfigManager (`config.py`)

**Purpose**: Thread-safe singleton for application configuration

**Key Responsibilities**:

- Manages all application settings (delays, thresholds, paths)
- Provides singleton access pattern with thread safety
- Stores configuration as a dataclass

**Important Details**:

- **Thread-safe singleton**: Uses double-checked locking with `threading.Lock()`
- First check without lock (performance), second check with lock (safety)
- Configuration stored in `ShinyHunterConfig` dataclass
- Settings include: screenshot regions, input delays, correlation thresholds, file paths

**Configuration Categories**:

- Screenshot settings (region coordinates, dimensions)
- Input delays (pyautogui_pause, encounter_delay, restart_delay)
- Verification settings (max_retries, thresholds)
- Shiny detection (correlation_threshold, correlation_tolerance)
- File paths (reference images, templates)
- Safety (failsafe_enabled)

### 4. ImageProcessor (`image_processor.py`)

**Purpose**: Computer vision for shiny detection and screen verification

**Key Responsibilities**:

- Verifies player is on encounter screen before checking for shiny
- Compares screenshots against reference images using correlation
- Determines if a shiny Pokemon is present

**Important Details**:

- Uses OpenCV for image processing (`cv2`)
- Two-step verification: encounter screen check, then shiny check
- Correlation-based detection: compares difference from threshold
- Template matching for encounter screen validation

**Key Methods**:

- `is_on_encounter_screen(screenshot_path)`: Validates correct screen
- `is_shiny_found(ref_img_path, screenshot_path)`: Detects shiny
- `get_correlation(ref_img_path, screenshot_path)`: Calculates correlation coefficient

### 5. InputHandler (`input_handler.py`)

**Purpose**: Cross-platform keyboard input automation

**Key Responsibilities**:

- Abstracts input handling across Windows/Linux
- Provides encounter and restart sequences
- Handles verification during encounter sequences

**Important Details**:

- **Primary**: Uses `pynput` for cross-platform input
- **Fallback**: Uses `pyautogui` if pynput unavailable
- Platform detection via `platform.system()`
- Key mapping abstraction for cross-platform compatibility

**Key Methods**:

- `encounter_sequence()`: Basic encounter sequence
- `encounter_sequence_with_verification()`: Encounter with screen verification
- `restart_sequence()`: Reset/restart sequence
- `_press_key(key)`, `_key_down(key)`, `_key_up(key)`: Cross-platform input primitives

### 6. ScreenshotManager (`screenshot_manager.py`)

**Purpose**: Screenshot capture and management

**Key Responsibilities**:

- Takes screenshots of configured emulator region
- Saves screenshots with proper naming (regular and timestamped)
- Manages screenshots directory

**Important Details**:

- Uses `pyautogui.screenshot()` with region parameter
- Region defined by config: (x, y, width, height)
- Sanitizes filenames to prevent path traversal
- Creates `screenshots/` directory if missing

**Key Methods**:

- `take_screenshot(filename)`: Save screenshot with given name
- `take_timestamped_screenshot(prefix)`: Save with timestamp in filename

### 7. Window Management System (`window_management/`)

**Purpose**: Cross-platform window discovery and embedding

**Architecture**:

- **base.py**: Abstract interfaces (`WindowManager`, `WindowInfo`, `EmbeddingMode`)
- **factory.py**: Creates appropriate manager for platform
- **pywinctl_manager.py**: Preferred implementation using PyWinCtl
- **fallback_manager.py**: Windows-only fallback using pygetwindow

**Important Details**:

- **PyWinCtlManager** (preferred):
  - Uses PyWinCtl for cross-platform window operations
  - On Windows: Full embedding via win32gui API
  - On Linux: Companion mode (side-by-side positioning)
  - Stores `original_parent` BEFORE calling `SetParent()` for proper restoration
  - Validates `original_parent` before restoration (falls back to desktop if invalid)
- **FallbackManager**:
  - Uses pygetwindow (Windows-only, raises NotImplementedError on Linux)
  - Manual mode only (no embedding support)
  - Catches NotImplementedError during import for graceful degradation

**Key Classes**:

- `WindowInfo`: Dataclass containing window metadata
- `EmbeddingMode`: Enum for embedding capabilities (FULL_EMBED, COMPANION, MANUAL)
- `WindowManagerFactory`: Creates appropriate manager based on platform and library availability

**Critical Bug Fixes Applied**:

1. Capture `original_parent` BEFORE `SetParent()` in embedding
2. Validate `original_parent` type/value before restoration
3. Catch `NotImplementedError` from pygetwindow on Linux platforms

## Common Patterns and Conventions

### Error Handling

- Libraries checked for availability with try/except during import
- Graceful degradation when optional libraries unavailable
- Fallback mechanisms for critical functionality

### Threading

- Main hunt loop runs in separate thread
- GUI updates use Tkinter's thread-safe methods
- Singleton patterns use proper locking

### Logging

- Controller provides `log()` method that outputs to console and GUI
- GUI's `log_message()` method updates text widget in thread-safe manner

### State Management

- Controller manages hunt state (`running`, `paused`)
- Attempt counter is a plain integer with property accessors (NOT tk.IntVar)
- GUI syncs display state from controller

## Critical Implementation Notes

### 1. Attempt Counter Architecture

**IMPORTANT**: Recent refactoring changed counter implementation:

- **Controller**: Uses `_reset_count` (private int) with `count` property
- **GUI**: Uses `count_var` (tk.IntVar) for display, syncs from `controller.count`
- **Never** access `reset_count` directly - use `controller.count` property
- Counter incremented ONLY after successful encounter verification

### 2. Window Embedding Parent Restoration

**CRITICAL BUG FIX**: Original parent must be captured BEFORE reparenting:

```python
# CORRECT:
original_parent = win32gui.GetParent(win32_handle)  # Before SetParent
win32gui.SetParent(win32_handle, parent_id)
store_in_dict(original_parent=original_parent)

# INCORRECT:
win32gui.SetParent(win32_handle, parent_id)
original_parent = win32gui.GetParent(win32_handle)  # Gets NEW parent!
```

### 3. Thread-Safe Singleton

**ConfigManager** uses double-checked locking:

```python
if cls._instance is None:          # First check (no lock)
    with cls._lock:                 # Acquire lock
        if cls._instance is None:   # Second check (with lock)
            cls._instance = create_instance()
```

### 4. Cross-Platform Library Handling

All platform-specific imports wrapped with exception handling:

```python
try:
    import platform_specific_lib
    LIB_AVAILABLE = True
except (ImportError, NotImplementedError):  # Catch both!
    LIB_AVAILABLE = False
```

### 5. GUI Controller Integration

GUI receives controller reference and delegates state access:

```python
# In GUI __init__:
def __init__(self, root, input_thread, controller, ...):
    self.controller = controller
    self.count_var = tk.IntVar(value=0)  # Display variable

# Update display from controller:
def update_count(self):
    if self.controller:
        self.count_var.set(self.controller.count)
```

## Dependencies

### Core Dependencies

- **tkinter**: GUI framework (Python standard library)
- **opencv-python (cv2)**: Computer vision and image processing
- **pyautogui**: Screenshot capture and fallback input
- **Pillow (PIL)**: Image handling

### Cross-Platform Dependencies

- **pynput**: Preferred cross-platform input handling
- **PyWinCtl**: Preferred cross-platform window management

### Windows-Specific (Optional)

- **win32gui/win32con**: Windows API for full window embedding
- **pygetwindow**: Fallback window management (Windows-only)
- **pywinauto**: Window discovery utilities

### GUI Dependencies

- **sv_ttk**: Dark theme for Tkinter

## Testing Considerations

When testing or modifying code:

1. **Always test on both Windows and Linux** if changing cross-platform code
2. **Check library availability** - code should gracefully handle missing libraries
3. **Test threading** - verify thread-safe access to shared resources
4. **Verify counter logic** - ensure counter increments only after successful verification
5. **Test window management** - verify embedding/unembedding restores original parent

## Common Modification Scenarios

### Adding New Configuration Options

1. Add field to `ShinyHunterConfig` dataclass in `config.py`
2. Add UI controls in `ShinyHuntGUI.open_settings()`
3. Update save/load logic in settings dialog
4. Use via `ConfigManager().get_config().your_setting`

### Modifying Hunt Logic

1. Main loop in `ShinyHunterController.attempt_encounter()`
2. Input sequences in `InputHandler`
3. Detection logic in `ImageProcessor.is_shiny_found()`
4. Remember: increment counter AFTER verification, not before

### Adding Cross-Platform Features

1. Check library availability with try/except (catch both ImportError and NotImplementedError)
2. Implement primary method using preferred library
3. Implement fallback method with alternative library
4. Use factory pattern for platform selection if needed

### GUI Modifications

1. GUI state syncs FROM controller (controller is source of truth)
2. Use `self.controller` reference for state access
3. Update display variables (like `count_var`) from controller values
4. Never store state in GUI that should be in controller

## Known Issues and Future Improvements

### Current Limitations

- Correlation threshold tuning may be needed for different Pokemon
- Screenshot region must be manually configured for different emulator sizes
- Encounter sequences are game-specific (currently configured for specific Pokemon game)

### Areas for Enhancement

- Configuration file persistence (currently in-memory only)
- Multi-Pokemon support with different reference images
- Automatic emulator window detection and region configuration
- More robust screen state detection
- Logging to file with rotation

## References

- **Main Entry Point**: `src/shinyhunter/main.py`
- **Controller**: `src/shinyhunter/shiny_hunter_controller.py`
- **Config**: `src/shinyhunter/config.py`
- **Window Management**: `src/shinyhunter/window_management/`

## Version History

- **Recent**: Refactored for cross-platform compatibility (removed Windows-only dependencies)
- **Recent**: Fixed window embedding parent restoration bug
- **Recent**: Implemented thread-safe singleton for ConfigManager
- **Recent**: Decoupled controller from Tkinter (removed tk.IntVar dependency)
- **Recent**: Fixed attempt counter logic (increment after verification only)
