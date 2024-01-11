import pyautogui
import pydirectinput
import time
import tkinter as tk
from shiny_hunt_gui import ShinyHuntGUI


print("You are going to get so many shinies king.")

# Size that screen cap looks at
emulator_x = 0
emulator_y = 0
emulator_width = 2560  # TODO: Make this a setting
emulator_height = 1440

# Global GUI Time Intervals
pyautogui.PAUSE = 2
pydirectinput.PAUSE = 1

# Reset Count
count = 1

paused = False


def handle_pause():
    print("Handling Pause")
    paused = not paused


def restart():
    pydirectinput.keyDown('backspace')
    pydirectinput.keyDown('enter')
    pydirectinput.keyDown('x')
    pydirectinput.keyDown('z')
    pydirectinput.keyUp('backspace')
    pydirectinput.keyUp('enter')
    pydirectinput.keyUp('x')
    pydirectinput.keyUp('z')

    return True


def countdown(seconds):
    while seconds > 0:
        print("Starting in:",  seconds)
        time.sleep(1)
        seconds -= 1


def increment_count():
    count.set(count.get() + 1)
    app.update_count()  # What am I doing with this?


def mewtwo():
    global count
    mewtwoPic = True
    print('Initializing Mewto Hunt')

    # Player must start from in game right in front of mewtwo
    countdown(5)

    while (mewtwoPic and not paused):
        print("Attempt #", count.get())
        pydirectinput.press('x')
        pydirectinput.press('x')
        # Check if shiny
        time.sleep(5)

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

        # if not shiny restart game
        restart()
        increment_count()
        pydirectinput.press('x')
        pydirectinput.press('x')
        pydirectinput.press('x')
        pydirectinput.press('x')
        pydirectinput.press('z')


if __name__ == '__main__':
    root = tk.Tk()
    count = tk.IntVar(value=1)
    app = ShinyHuntGUI(root, mewtwo, count, handle_pause)
    root.mainloop()
