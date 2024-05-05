from ctypes.wintypes import WCHAR
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
from pywinauto.application import Application


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
    time.sleep(1)
    # Restart Sequence - (A + B Start + Select)
    pydirectinput.keyDown('backspace')
    pydirectinput.keyDown('enter')
    pydirectinput.keyDown('x')
    pydirectinput.keyDown('z')
    pydirectinput.keyUp('backspace')
    pydirectinput.keyUp('enter')
    pydirectinput.keyUp('x')
    pydirectinput.keyUp('z')

    # pyApp.window(title=getTitle(),
    #              top_level_only=False, active_only=True).send_keystrokes('{x down}' '{z down}' '{ENTER down}' '{BACKSPACE down}''{x up}' '{z up}' '{ENTER up}' '{BACKSPACE up}')

    time.sleep(7)

    # Input Sequence to get through FRLG start menu
    # TODO: Look into adding options for different games O_o

    # input('{ENTER}')
    # time.sleep(5)
    # input('{ENTER}')
    # input('{ENTER}')

    pydirectinput.press('enter')
    time.sleep(3)
    pydirectinput.press('enter')
    pydirectinput.press('enter')

    # input('x')
    pydirectinput.press('x')

    # print('Waiting 2 secs!')
    # time.sleep(2)

    pydirectinput.press('z')
    # input('z')
    # input('x')
    # print('Waiting 3 secs!')
    # time.sleep(3)
    # input('x')
    # time.sleep(3)
    # # # Spare - Catch case not sure if needed
    # input('x')
    # input('z')
    # time.sleep(1)

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
    # input('x')
    # input('x')
    pydirectinput.press('x')
    pydirectinput.press('x')

    # Delay to give time to check for shiny
    time.sleep(5)

    # Needed to catch image not found exception
    pyautogui.useImageNotFoundException()

    try:
        # TODO: Generalize variable name
        # shinyMewtwoPic = pyautogui.locateOnScreen('green2.png')
        # print("Mewtwo Pic", shinyMewtwoPic) x*********
        expected_picture = pyautogui.locateOnScreen('expected_mewtwo.png')
        print("Mewtwo Pic", expected_picture) 

        print("Not Shiny")


    except pyautogui.ImageNotFoundException:
        print('Shiny Found!')
        screenshot = pyautogui.screenshot(
        region=(emulator_x, emulator_y, emulator_width, emulator_height))

        screenshot.save(f'shiny_screenshot_{count}.png')
        exit()

    screenshot = pyautogui.screenshot(
        region=(emulator_x, emulator_y, emulator_width, emulator_height))
    screenshot.save('emulator_screenshot.png')

    # if (shinyMewtwoPic):
    #     print("SHINY FOUND")
    #     screenshot = pyautogui.screenshot(
    #         region=(emulator_x, emulator_y, emulator_width, emulator_height))

    #     screenshot.save(f'shiny_screenshot_{count}.png')
    #     exit()

    # Restart game if shiny isn't found
    restart()

# TODO: Optimize time and look into utlizing built in input delays from pyauto


def input(input):
    global stopped
    global paused
    global form
    global pyApp

    if stopped:
        sys.exit()

    if not paused:
        title = getTitle()
        # pydirectinput.press(input)
        print("\nWaiting 2 second")
        time.sleep(2)
        print("Inputing: ", input)

        # if input == 'x':
        #     input = '0x58'
        # elif input == 'z':
        #     input = '0x5A'
        # elif input == '{ENTER}':
        #     input = '0x0D'

        # hwndChild = win32gui.GetWindow(getHandle(), win32con.GW_CHILD)
        # temp = win32api.PostMessage(getHandle(), win32con.WM_CHAR, input, 0)
        # print(temp)

        # pyApp.window(title=title,
        #              top_level_only=False, active_only=False).send_keystrokes(input + ' up')
        # time.sleep(0.5)
        pyApp.window(title=title,
                     top_level_only=False, active_only=True).send_keystrokes(input)
        time.sleep(0.25)
        # pyApp.window(title=title,
        #              top_level_only=False, active_only=False).send_keystrokes(input + " up")

    time.sleep(0.1)


def mewtwo_with_pause():
    global paused
    global stopped
    countdown(3)
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
    root.geometry("1920x1080")
    # TODO: Initialize to 0 and on start add one
    count = tk.IntVar(value=count)

    container_frame = ttk.Frame(root, padding="10")
    container_frame.grid(row=0, column=0)

    input_thread = threading.Thread(target=mewtwo_with_pause)

    app = ShinyHuntGUI(root, input_thread, count, handle_pause, stop_hunt)

    pyApp = Application()
    right_frame = app.right_frame
    app_frame = EmbeddedAppFrame(
        right_frame, pyApp, container_frame=root, master=root)
    app_frame.grid(column=1, row=0)

    root.mainloop()
