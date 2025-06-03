import pyautogui
import pydirectinput
import tkinter as tk
import threading
from pywinauto.application import Application

from shiny_hunt_gui import ShinyHuntGUI
from embedded_app import EmbeddedAppFrame
from shiny_hunter_controller import ShinyHunterController
from config import ConfigManager

# TODO: Move to .env 
# Size that screen cap looks at
emulator_x = 0
emulator_y = 0
emulator_width = 2560  # TODO: Make this a setting
emulator_height = 1440
pyautogui.PAUSE = 2
pydirectinput.PAUSE = 0.8

# Reset Count
count = 0
paused = False
stopped = False
pause_lock = threading.Lock()

def handle_pause():
    global paused
    print("Handling Pause")

    paused = not paused

def stop_hunt():
    global stopped
    stopped = not stopped


def getHandle():
    return embedded_app_frame.app_handle


def getTitle():
    return embedded_app_frame.dropdown_var.get()


if __name__ == '__main__':
    print("You are going to get so many shinies king.")
    
    # Initialize configuration
    config = ConfigManager().get_config()
    
    
    root = tk.Tk()
    root.title("Shiny Hunt v0.2-alpha")
    root.geometry("1920x1080")
    
    count = tk.IntVar(value=0)

        
    # Initialize controller
    shiny_hunter = ShinyHunterController()
    
    # Create input thread
    input_thread = threading.Thread(target=shiny_hunter.attempt_encounter)

    
    # Initialize GUI
    app = ShinyHuntGUI(
        root, input_thread, count, 
        shiny_hunter.start_hunt,
        shiny_hunter.pause_hunt, 
        shiny_hunter.stop_hunt, 
    )

    shiny_hunter.log_function = app.log_message
    
    # TODO: CHECK if we are Set the log function for the controller
    # shiny_hunter.set_log_function(app.log_message)
    
    # Initialize embedded app frame
    pyApp = Application()
    embedded_app_frame = EmbeddedAppFrame(
        app.right_frame, pyApp, container_frame=root, master=root
    )
    embedded_app_frame.grid(column=1, row=0)
    
    root.mainloop()