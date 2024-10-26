import pyautogui
import pydirectinput
import time
import sys


class ShinyHuntApp:
    '''
    Main driver for shiny hunt application. Includes all core logic and functions.
    '''

    def __init__(self):
        self.running = False
        self.paused = False
        self.thread = None
        self.count = 0

        self.emulator_x = 0
        self.emulator_y = 0
        self.emulator_width = 2560  # TODO: Make this a setting
        self.emulator_height = 1440

    def set_running_status(self, status: bool):
        self.running = status

    def countdown(self, seconds):
        while seconds > 0:
            print("Starting in:",  seconds)
            time.sleep(1)
            seconds -= 1

    def mewtwo_with_pause(self):

        self.countdown(3)
        self.attempt_encounter()
        time.sleep(0.1)
        sys.exit()

    def restart(self):
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
        pydirectinput.press('enter')
        time.sleep(3)
        pydirectinput.press('enter')
        pydirectinput.press('enter')
        pydirectinput.press('x')
        pydirectinput.press('z')
        return True

    # TODO: Make sure all references of "mewtwo" function named is removed

    def attempt_encounter(self):
        '''
        Method to handle sequence of encounter procedure (button presses, shiny checking, and resetting)
        '''
        while self.running:
            print('Initializing Mewtwo Hunt')

            # Should increment count at beginning of this loop
            self.increment_count()

            print("Attempt #", self.count)

            # Assumes Player is directly in front of encounter and needs to click through one panel of text

            pydirectinput.press('x')
            pydirectinput.press('x')

            # Delay to give time to check for shiny
            time.sleep(5)

            # Needed to catch image not found exception
            pyautogui.useImageNotFoundException()

            try:

                green_color_locatation_attempt = pyautogui.locateOnScreen(
                    'green.png')

                print("Shiny Mewtwo Pic Attempt",
                      green_color_locatation_attempt)
                print("Shiny Found!")
                self.screenshot_app_and_save('shiny_screenshot.png')
                exit()
            except pyautogui.ImageNotFoundException:
                print('No Shiny Found!')
                self.screenshot_app_and_save('emulator_screenshot.png')

                self.restart()

    def screenshot_app_and_save(self, name: str):
        screenshot = pyautogui.screenshot(
            region=(self.emulator_x, self.emulator_y, self.emulator_width, self.emulator_height))
        screenshot.save(name)

    def increment_count(self):
        self.count += 1

    def start_hunt(self):
        '''
        Called when hunt application begins
        '''
        self.set_running_status(True)
        print("Running Status set to: ", self.running)

    def pause_hunt(self):
        if self.running:
            self.paused = True

    def resume_hunt(self):
        if self.running and self.paused:
            self.paused = False

    def stop_hunt(self):
        self.running = False
        if self.thread:
            self.thread.join()

    def input(self, input):
        '''
        !!DEPRECATED!! Input method not currently used. !!DEPRECATED!!
        '''
        global stopped
        global paused
        global form
        global pyApp

        if stopped:
            sys.exit()

        if not paused:
            title = getTitle()
            # pydirectinput.press(input)
            print("\nWaiting 1 second")
            time.sleep(1)

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
