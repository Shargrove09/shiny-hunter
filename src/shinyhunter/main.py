import tkinter as tk
import threading
import os
import sys

# Try to import pyautogui, but handle X11 display errors gracefully on Linux
PYAUTOGUI_AVAILABLE = True
try:
    import pyautogui
except Exception as e:
    PYAUTOGUI_AVAILABLE = False
    if sys.platform.startswith('linux'):
        print(f"Warning: pyautogui not available: {e}")
        print("This is common on Linux systems. The app will use pynput for input handling.")
        print("For screenshots, please fix X11 authorization (run 'xhost +local:') or install required dependencies. See README.md for details.")
    else:
        print(f"Warning: Could not import pyautogui: {e}")

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

# TODO: Move to .env 
# Size that screen cap looks at
emulator_x = 0
emulator_y = 0
emulator_width = 2560  # TODO: Make this a setting
emulator_height = 1440


paused = False
stopped = False
pause_lock = threading.Lock()

# Global reference to the app frame (set in main)
cross_platform_app_frame = None

def handle_pause():
    global paused
    print("Handling Pause")

    paused = not paused

def stop_hunt():
    global stopped
    stopped = not stopped


def getHandle():
    global cross_platform_app_frame
    return cross_platform_app_frame.app_handle if cross_platform_app_frame else None


def getTitle():
    global cross_platform_app_frame
    return cross_platform_app_frame.dropdown_var.get() if cross_platform_app_frame else ""


if __name__ == '__main__':
    print("You are going to get so many shinies king.")
    
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
            print(f"Updated input handler target window: {window_info.title}")
    
    # Store the update function in the cross_platform_app for callback
    cross_platform_app_frame.update_target_window_callback = update_target_window
    
    root.mainloop()