import logging
import tkinter as tk
import threading
import os
import sys

from log_config import setup_logging

logger = logging.getLogger(__name__)

# Try to import pyautogui, but handle X11 display errors gracefully on Linux
PYAUTOGUI_AVAILABLE = True
try:
    import pyautogui
except Exception as e:
    PYAUTOGUI_AVAILABLE = False
    if sys.platform.startswith('linux'):
        logger.warning("pyautogui not available: %s", e)
        logger.info("This is common on Linux systems. The app will use pynput for input handling.")
        logger.info("For screenshots, fix X11 authorization (run 'xhost +local:') or see README.md.")
    else:
        logger.warning("Could not import pyautogui: %s", e)

# Conditional import for Windows-specific functionality
try:
    from pywinauto.application import Application
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False
    Application = None

from shiny_hunt_gui import ShinyHuntGUI
from cross_platform_app import CrossPlatformAppFrame
from shiny_hunter_controller import ShinyHunterController
from config import ConfigManager

# Global reference to the app frame (set in main)
cross_platform_app_frame = None


def getHandle():
    global cross_platform_app_frame
    return cross_platform_app_frame.app_handle if cross_platform_app_frame else None


def getTitle():
    global cross_platform_app_frame
    return cross_platform_app_frame.dropdown_var.get() if cross_platform_app_frame else ""


if __name__ == '__main__':
    setup_logging()
    logger.info("Shiny Hunter starting up...")
    
    # Initialize configuration
    config = ConfigManager().get_config()
    
    
    root = tk.Tk()
    root.title("Shiny Hunt v0.2-alpha")
    root.geometry("1920x1080")
    

        
    # Initialize controller
    shiny_hunter = ShinyHunterController()
    
    # Create input thread
    input_thread = threading.Thread(target=shiny_hunter.attempt_encounter)

    
    # Initialize GUI
    app = ShinyHuntGUI(
        root, input_thread, shiny_hunter, 
        shiny_hunter.start_hunt,
        shiny_hunter.pause_hunt, 
        shiny_hunter.stop_hunt, 
    )

    shiny_hunter.log_function = app.log_message
    
    # Store the shiny hunter controller in the app for cross-platform access
    app.shiny_hunter_controller = shiny_hunter
    
    cross_platform_app_frame = CrossPlatformAppFrame(
        app.right_frame, app, container_frame=root, master=root
    )
    cross_platform_app_frame.grid(column=1, row=0)
    
    # Store reference to cross_platform_app_frame in the GUI for window management
    app.cross_platform_app_frame = cross_platform_app_frame
    
    # Connect the window manager to the input handler for Linux/macOS
    # This allows the input handler to focus the target window before sending keystrokes
    def update_target_window():
        """Update the input handler's target window from cross_platform_app."""
        window_info = cross_platform_app_frame.get_selected_window_info()
        if window_info:
            shiny_hunter.input_handler.set_target_window(window_info)
            logger.info("Updated input handler target window: %s", window_info.title)
    
    # Store the update function in the cross_platform_app for callback
    cross_platform_app_frame.update_target_window_callback = update_target_window
    
    root.mainloop()