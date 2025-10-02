import pyautogui
import tkinter as tk
import threading

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
    
    # Initialize cross-platform app frame
    if PYWINAUTO_AVAILABLE:
        pyApp = Application()
    else:
        pyApp = None
        print("PyWinAuto not available - some features may be limited")
    
    cross_platform_app_frame = CrossPlatformAppFrame(
        app.right_frame, pyApp, container_frame=root, master=root
    )
    cross_platform_app_frame.grid(column=1, row=0)
    
    root.mainloop()