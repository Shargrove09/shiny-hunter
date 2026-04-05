# AGENT.md

## Project Purpose

Shiny Hunter is a desktop automation app for Pokemon shiny hunting.

It automates a repeatable hunt loop by:

- Sending encounter/reset inputs to a target game window
- Capturing screenshots from a configured region
- Running image-based detection to decide whether a shiny encounter occurred

The project targets cross-platform operation with adaptive behavior on Windows, macOS, and Linux.

## High-Level Architecture

The codebase is organized as a controller-driven desktop app with separate modules for UI, automation, detection, and platform integrations.

### Entry and Composition

- `src/shinyhunter/main.py`
  - Initializes logging, configuration, controller, GUI, and cross-platform window frame
  - Wires window selection/focus info into input handling

### Core Runtime Modules

- `src/shinyhunter/shiny_hunter_controller.py`
  - Orchestrates the hunt loop and state (`running`, `paused`, attempt counter)
- `src/shinyhunter/input_handler.py`
  - Cross-platform key input abstraction (pynput primary, pyautogui fallback)
  - Implements encounter/restart/menu sequences
- `src/shinyhunter/image_processor.py`
  - Encounter-screen validation and shiny detection via OpenCV
- `src/shinyhunter/screenshot_manager.py`
  - Region-based screenshot capture and screenshot file management
- `src/shinyhunter/config.py`
  - Thread-safe singleton config manager with JSON persistence

### UI and Window Management

- `src/shinyhunter/shiny_hunt_gui.py`
  - Tkinter UI for controls, logs, settings, and calibration workflow
- `src/shinyhunter/cross_platform_app.py`
  - Adaptive window management UI and actions based on capabilities
- `src/shinyhunter/window_management/`
  - `base.py`: abstractions (`WindowManager`, `WindowInfo`, `EmbeddingMode`)
  - `factory.py`: manager selection with fallback chain
  - `pywinctl_manager.py`: primary manager implementation
  - `fallback_manager.py`: pygetwindow-based fallback implementation

## Runtime Workflow

1. User selects and manages a target game window.
2. Hunt starts and controller enters a loop.
3. Input handler runs encounter sequence.
4. Screenshot manager captures the configured region.
5. Image processor verifies encounter screen and computes correlation against reference.
6. If shiny is detected, loop stops and a timestamped screenshot is saved.
7. If not shiny, input handler executes reset flow and the loop repeats.

## Major Functionalities

### 1) Automated Hunt Loop

- Continuous encounter -> check -> reset cycle
- Attempt counter increments after verified encounter
- Pause/resume/stop controls available from the GUI

### 2) Cross-Platform Input Automation

- Preferred input backend: pynput
- Fallback backend: pyautogui
- Focus assistance for Linux/macOS before critical key events
- Configurable timing and jitter to avoid rigid timing patterns

### 3) Image-Based Shiny Detection

- Template matching confirms the expected encounter screen
- HSV histogram correlation compares current screenshot to calibration reference
- Effective shiny cutoff uses threshold - tolerance

### 4) Calibration and Tuning

- Capture reference image for normal encounter baseline
- Record normal samples and suggest threshold from observed distribution
- Manual threshold/tolerance adjustment through GUI

### 5) Adaptive Window Management

- Windows: supports full embed mode where available
- macOS/Linux: companion mode (position/resize/focus in boundary)
- Fallback/manual behavior when advanced APIs are unavailable

### 6) Persistent Configuration

- Settings loaded from and saved to `shinyhunter_config.json`
- Includes screenshot region, delays, retries, thresholds, and safety options

## Platform Behavior Summary

- Windows
  - Best capability set (window embedding + full management when APIs available)
- macOS
  - Window positioning/focus flows (no true embedding)
- Linux
  - Window positioning/focus flows, environment-dependent screenshot/input constraints

## Testing and Validation

Pytest suite exists in `tests/` for key modules:

- `tests/test_config.py`
- `tests/test_image_processor.py`
- `tests/test_input_handler.py`
- `tests/test_window_management.py`

There are also top-level diagnostic scripts:

- `test_cross_platform.py`
- `test_input_handler.py`

Notes:

- Some tests are display-dependent and skip in headless environments.

## Key Files for Fast Orientation

- Application start: `src/shinyhunter/main.py`
- Hunt loop: `src/shinyhunter/shiny_hunter_controller.py`
- GUI: `src/shinyhunter/shiny_hunt_gui.py`
- Input automation: `src/shinyhunter/input_handler.py`
- Detection logic: `src/shinyhunter/image_processor.py`
- Window management UI: `src/shinyhunter/cross_platform_app.py`
- Window abstraction layer: `src/shinyhunter/window_management/`
- Configuration: `src/shinyhunter/config.py`

## Agent Guidance

When modifying this project:

- Preserve the separation between controller, GUI, and platform adapters.
- Keep cross-platform behavior explicit and add graceful fallbacks for missing libraries.
- Avoid moving runtime state into the GUI; treat the controller as source of truth.
- Keep threshold/detection changes measurable and configurable.
- Prefer structured logging over print output.
- Update or add tests in `tests/` for logic changes.
