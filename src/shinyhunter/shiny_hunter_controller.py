import pyautogui
import pydirectinput
import time
import sys
import os 
import cv2


class ShinyHunterController:
    '''
    Main driver for shiny hunt application. Includes all core logic and functions.
    '''

    def __init__(self, log_function=None):
        self.running = False
        self.paused = False
        self.thread = None
        self.count = 0
        self.log_function = log_function

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

    def set_log_function(self, log_function):
        self.log_function = log_function

    def log(self, message):
        if self.log_function:
            self.log_function(message)

    def attempt_encounter(self):
        '''
        Method to handle sequence of encounter procedure (button presses, shiny checking, and resetting)
        '''
        while self.running:
            print('Initializing Shiny Hunt')
            self.log('Initializing Shiny Hunt')

            # Should increment count at beginning of this loop
            self.increment_count()

            print("Attempt #", self.count)
            self.log(f"Attempt #{self.count}")

            # Assumes Player is directly in front of encounter and needs to click through one panel of text

            pydirectinput.press('x')
            pydirectinput.press('x')

            # Delay to give time to check for shiny
            time.sleep(5)

            # Needed to catch image not found exception
            pyautogui.useImageNotFoundException()

            reference_image = os.path.abspath('./shiny_mewtwo_reference_img.png')
            base_image = os.path.abspath('./mewtwo.png')

            if self.is_shiny_found(reference_image, base_image):
                print('Shiny Found!')
                self.log('Shiny Found!')
                self.screenshot_app_and_save('shiny_screenshot.png')
                exit()
            else: 
                print('No Shiny Found!')
                self.log('No Shiny Found!')
                self.screenshot_app_and_save('emulator_screenshot.png')
                self.restart()

    def is_shiny_found(self,reference_image_path, screenshot_path): 
        reference_image = cv2.imread(reference_image_path)
        screenshot = cv2.imread(screenshot_path)

        # Convert images to HSV color space 
        reference_hsv = cv2.cvtColor(reference_image, cv2.COLOR_BGR2HSV)
        screenshot_hsv = cv2.cvtColor(screenshot, cv2.COLOR_BGR2HSV)

        # Calc color histograms 
        reference_hist = cv2.calcHist([reference_hsv], [0, 1], None, [180, 256], [0, 180, 0, 256])
        screenshot_hist = cv2.calcHist([screenshot_hsv], [0, 1], None, [180, 256], [0, 180, 0, 256])

        # Normalize histograms
        cv2.normalize(reference_hist, reference_hist, 0, 1, cv2.NORM_MINMAX)
        cv2.normalize(screenshot_hist, screenshot_hist, 0, 1, cv2.NORM_MINMAX)

        # Compare histograms 
        correlation = cv2.compareHist(reference_hist, screenshot_hist, cv2.HISTCMP_CORREL)
        print(f"Correlation: {correlation}")

        threshold = 0.56
        return correlation > threshold


    def get_correlation(self, reference_image_path, screenshot_path):
        ref_image = cv2.imread(reference_image_path)
        screenshot = cv2.imread(screenshot_path)

        # Convert images to HSV color space
        reference_hsv = cv2.cvtColor(ref_image, cv2.COLOR_BGR2HSV)
        screenshot_hsv = cv2.cvtColor(screenshot, cv2.COLOR_BGR2HSV)

        # Calc color histograms
        reference_hist = cv2.calcHist(
            [reference_hsv], [0, 1], None, [180, 256], [0, 180, 0, 256])
        screenshot_hist = cv2.calcHist(
            [screenshot_hsv], [0, 1], None, [180, 256], [0, 180, 0, 256])

        # Normalize histograms
        cv2.normalize(reference_hist, reference_hist, 0, 1, cv2.NORM_MINMAX)
        cv2.normalize(screenshot_hist, screenshot_hist, 0, 1, cv2.NORM_MINMAX)

        # Compare histograms
        correlation = cv2.compareHist(
            reference_hist, screenshot_hist, cv2.HISTCMP_CORREL)
        
        print(f"Correlation: {correlation}")
        self.log(f"Correlation: {correlation}")

        return correlation


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
