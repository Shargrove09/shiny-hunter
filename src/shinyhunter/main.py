import pyautogui
import pydirectinput
import tkinter as tk
from tkinter import ttk
from shiny_hunt_gui import ShinyHuntGUI
from embedded_app import EmbeddedAppFrame
import pygetwindow as gw
import threading
from pywinauto.application import Application
from shiny_hunter_controller import ShinyHunterController

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


window_titles = gw.getAllTitles()
print("Window Titles: ", window_titles)


def handle_pause():
    global paused
    print("Handling Pause")

    paused = not paused


# TODO: Optimize time and look into utlizing built in input delays from pyauto


def stop_hunt():
    global stopped
    stopped = not stopped


def getHandle():
    return embedded_app_frame.app_handle


def getTitle():
    return embedded_app_frame.dropdown_var.get()


if __name__ == '__main__':
    print("You are going to get so many shinies king.")

    root = tk.Tk()
    root.title("Shiny Hunt v0.2-alpha")

    # GUI Window Size TODO: Breakpoints?
    root.geometry("1920x1080")

    count = tk.IntVar(value=0)


    shiny_hunter = ShinyHunterController()

    input_thread = threading.Thread(target=shiny_hunter.mewtwo_with_pause)
    app = ShinyHuntGUI(root, input_thread, count, shiny_hunter.start_hunt,
                       shiny_hunter.pause_hunt, shiny_hunter.stop_hunt)
    
    shiny_hunter.set_log_function(app.log_message)


    pyApp = Application() # TODO: Do we need this if we are using pygetwindow?
    right_frame = app.right_frame


    embedded_app_frame = EmbeddedAppFrame(
        right_frame, pyApp, container_frame=root, master=root)
    embedded_app_frame.grid(column=1, row=0)

    root.mainloop()