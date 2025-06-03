import pydirectinput
import pyautogui
import time
from config import ConfigManager

class InputHandler:
    def __init__(self):
        self.config = ConfigManager().get_config()
        pydirectinput.PAUSE = self.config.pydirectinput_pause
        pyautogui.PAUSE = self.config.pyautogui_pause
        pydirectinput.FAILSAFE = self.config.failsafe_enabled

        print("InputHandler initialized with the following configuration:")
    
    def encounter_sequence(self):
        """Execute the encounter button sequence."""
        pydirectinput.press('x')
        pydirectinput.press('x')
        time.sleep(self.config.encounter_delay)

    def encounter_sequence_with_verification(self, screenshot_manager, image_processor):
        """Execute encounter sequence with verification steps."""
        max_retries = 3
        
        for attempt in range(max_retries):
            # Execute encounter
            time.sleep(0.25)
            print("PRESSING X")
            pydirectinput.press('x')
            time.sleep(2)  # Wait for first press to registerx
            print("PRESSING X AGAIN")
            pydirectinput.press('x')
            time.sleep(self.config.encounter_delay)

            
            # Verify we reached encounter screen
            screenshot_path = screenshot_manager.take_screenshot('verification_screenshot.png')
            if image_processor.is_on_encounter_screen(screenshot_path):
                return True
                
            print(f"Encounter sequence verification failed, attempt {attempt + 1}/{max_retries}")
            time.sleep(1)  # Wait before retry
            
        return False
    


    
    def restart_sequence(self):
        """Execute the restart sequence."""
        # Restart Sequence - (A + B Start + Select)
        keys = ['backspace', 'enter', 'x', 'z']
        
        # Press all keys down
        for key in keys:
            pydirectinput.keyDown(key)
        
        # Release all keys
        for key in keys:
            pydirectinput.keyUp(key)
        
        
        # Navigate through start menu
        self._navigate_start_menu()
    
    def _navigate_start_menu(self):
        """Navigate through the FRLG start menu."""
        pydirectinput.press('enter')
        time.sleep(3)
        pydirectinput.press('enter')
        pydirectinput.press('enter')
        pydirectinput.press('x')
        pydirectinput.press('z')