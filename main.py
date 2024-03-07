import pyautogui
import pydirectinput
import time
import tkinter as tk
from tkinter import ttk
from shiny_hunt_gui import ShinyHuntGUI
from embedded_app import EmbeddedAppFrame
import pygetwindow as gw
import threading
import sys
import win32gui
import win32con
import win32api
import autoit


print("You are going to get so many shinies king.")

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


def restart():
    print("Restarting!")
    # Restart Sequence
    pydirectinput.keyDown('backspace')
    pydirectinput.keyDown('enter')
    pydirectinput.keyDown('x')
    pydirectinput.keyDown('z')
    pydirectinput.keyUp('backspace')
    pydirectinput.keyUp('enter')
    pydirectinput.keyUp('x')
    pydirectinput.keyUp('z')

    # Input Sequence to get through FRLG start menu
    # TODO: Look into adding options for different games O_o
    input('x')
    input('x')
    input('x')
    input('x')
    input('z')

    return True


def countdown(seconds):
    while seconds > 0:
        print("Starting in:",  seconds)
        time.sleep(1)
        seconds -= 1


def increment_count():
    global count  # Not sure if this or paused needs to be global
    count.set(count.get() + 1)
    app.update_count()  # TODO: What am I doing with this?


# TODO: Make sure all references of "mewtwo" function named is removed
def attempt_encounter():
    global count
    mewtwoPic = True
    print('Initializing Mewtwo Hunt')

    # Should increment count at beginning of this loop
    increment_count()
    print("Attempt #", count.get())

    # Assumes Player is directly in front of encounter and needs to click through one panel of text
    input('x')
    input('x')

    # Delay to give time to check for shiny
    time.sleep(5)

    # TODO: Generalize variable name
    shinyMewtwoPic = pyautogui.locateOnScreen('green.png')
    print("Mewtwo Pic", shinyMewtwoPic)

    screenshot = pyautogui.screenshot(
        region=(emulator_x, emulator_y, emulator_width, emulator_height))
    screenshot.save('emulator_screenshot.png')

    if (shinyMewtwoPic):
        print("SHINY FOUND")
        screenshot = pyautogui.screenshot(
            region=(emulator_x, emulator_y, emulator_width, emulator_height))

        screenshot.save(f'shiny_screenshot_{count}.png')
        exit()

    # Restart game if shiny isn't found
    restart()


def input(input):
    global stopped
    global paused

    while True:
        if stopped:
            sys.exit()

        if not paused:
            title = getTitle()
            print(title)
            # autoit.mouse_click("left", 500, 500)

            autoit.control_click(
                "[CLASS:Qt660QWindowOwnDCIcon; INSTANCE:1]", "", button="primary", x=500, y=500)
            pydirectinput.press(input)
            break
        print("We are paused")
        time.sleep(0.1)


def mewtwo_with_pause():
    global paused
    global stopped
    countdown(5)
    while (not stopped):
        with pause_lock:
            if not paused:
                attempt_encounter()
        time.sleep(0.1)
    sys.exit()


def stop_hunt():
    global stopped
    stopped = not stopped


def getHandle():
    return app_frame.app_handle


def getTitle():
    return app_frame.dropdown_var.get()


if __name__ == '__main__':
    root = tk.Tk()
    root.title("Shiny Hunt v0.1")
    # GUI Window Size
    root.geometry("1680x1260")
    # TODO: Initialize to 0 and on start add one
    count = tk.IntVar(value=count)

    container_frame = ttk.Frame(root, padding="10")
    container_frame.grid(row=0, column=0)

    input_thread = threading.Thread(target=mewtwo_with_pause)

    app = ShinyHuntGUI(root, input_thread, count, handle_pause, stop_hunt)

    right_frame = app.right_frame
    app_frame = EmbeddedAppFrame(
        right_frame, container_frame=root, master=root)
    app_frame.grid(column=1, row=0)

    root.mainloop()
