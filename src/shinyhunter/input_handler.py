import time
from config import ConfigManager
import platform

# Cross-platform input handling
try:
    from pynput.keyboard import Key, Controller as KeyboardController
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    KeyboardController = None

# Fallback imports for compatibility
try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

class InputHandler:
    def __init__(self):
        self.config = ConfigManager().get_config()
        self.platform = platform.system()
        self.target_window = None  # Reference to target window for focusing
        
        # Initialize the appropriate input method
        if PYNPUT_AVAILABLE:
            self.keyboard = KeyboardController()
            self.input_method = "pynput"
            print("Using pynput for cross-platform input handling")
        elif PYAUTOGUI_AVAILABLE:
            self.input_method = "pyautogui"
            pyautogui.PAUSE = self.config.pyautogui_pause
            pyautogui.FAILSAFE = self.config.failsafe_enabled
            print("Using pyautogui as fallback input method")
        else:
            raise ImportError("No suitable input library available. Please install pynput or pyautogui")

        print(f"InputHandler initialized for {self.platform} using {self.input_method}:")
    
    def set_target_window(self, window_info):
        """
        Set the target window that should receive keystrokes.
        
        Args:
            window_info: WindowInfo object from window_management
        """
        self.target_window = window_info
        print(f"Target window set to: {window_info.title if window_info else 'None'}")
    
    def _ensure_window_focused(self):
        """Ensure the target window has focus before sending keystrokes."""
        if not self.target_window:
            print("Warning: No target window set")
            return False
            
        if hasattr(self.target_window, 'handle') and hasattr(self.target_window.handle, 'activate'):
            try:
                # Focus/activate the target window
                self.target_window.handle.activate()
                time.sleep(0.2)  # Increased delay to ensure focus is set
                return True
            except Exception as e:
                print(f"Warning: Could not focus target window: {e}")
                return False
        elif hasattr(self.target_window, 'focus'):
            try:
                # Alternative method for focusing
                self.target_window.focus()
                time.sleep(0.2)
                return True
            except Exception as e:
                print(f"Warning: Could not focus target window (alternative method): {e}")
                return False
        else:
            print("Warning: Target window does not support focusing")
            return False
    
    def _get_key_mapping(self):
        """Get platform-specific key mappings."""
        if self.input_method == "pynput":
            return {
                'x': 'x',
                'z': 'z', 
                'enter': Key.enter,
                'backspace': Key.backspace
            }
        else:  # pyautogui
            return {
                'x': 'x',
                'z': 'z',
                'enter': 'enter',
                'backspace': 'backspace'
            }
    
    def _press_key(self, key):
        """Cross-platform key press."""
        key_map = self._get_key_mapping()
        mapped_key = key_map.get(key, key)
        
        if self.input_method == "pynput":
            self.keyboard.press(mapped_key)
            time.sleep(0.05)  # Small delay between press and release
            self.keyboard.release(mapped_key)
            time.sleep(0.1)  # Small delay after key press
        else:  # pyautogui fallback
            pyautogui.press(mapped_key)
    
    def _key_down(self, key):
        """Cross-platform key down."""
        key_map = self._get_key_mapping()
        mapped_key = key_map.get(key, key)
        
        if self.input_method == "pynput":
            print(f"Key down: {mapped_key}")
            self.keyboard.press(mapped_key)
        else:  # pyautogui fallback
            pyautogui.keyDown(mapped_key)
    
    def _key_up(self, key):
        """Cross-platform key up."""
        key_map = self._get_key_mapping()
        mapped_key = key_map.get(key, key)
        
        if self.input_method == "pynput":
            print(f"Key up: {mapped_key}")
            self.keyboard.release(mapped_key)
        else:  # pyautogui fallback
            pyautogui.keyUp(mapped_key)
    
    def encounter_sequence(self):
        """Execute the encounter button sequence."""
        # Ensure target window is focused (Linux/macOS)
        if self.platform in ["Linux", "Darwin"]:
            self._ensure_window_focused()
        
        self._press_key('x')
        self._press_key('x')
        time.sleep(self.config.encounter_delay)

    def encounter_sequence_with_verification(self, screenshot_manager, image_processor):
        """Execute encounter sequence with verification steps."""
        max_retries = 3
        
        for attempt in range(max_retries):
            # Ensure target window is focused (Linux/macOS)
            if self.platform in ["Linux", "Darwin"]:
                focused = self._ensure_window_focused()
                if not focused:
                    print(f"Warning: Target window may not be focused")
            
            # Execute encounter
            time.sleep(0.25)
            print("PRESSING X")
            self._press_key('x')
            time.sleep(2)  # Wait for first press to register
            print("PRESSING X AGAIN")
            self._press_key('x')
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
        print("Starting restart sequence...")
        
        # Ensure target window is focused (Linux/macOS)
        if self.platform in ["Linux", "Darwin"]:
            focused = self._ensure_window_focused()
            if not focused:
                print("Warning: Could not focus target window for restart")
            time.sleep(0.3)  # Give window time to focus
        
        # Restart Sequence - (A + B + Start + Select) - All pressed simultaneously
        keys = ['backspace', 'enter', 'x', 'z']
        
        print("Pressing reset combination (A+B+Start+Select)...")
        # Press all keys down
        for key in keys:
            self._key_down(key)
            time.sleep(0.02)  # Small delay between each key down
        
        # Hold for a moment
        time.sleep(0.2)
        
        # Release all keys
        for key in keys:
            self._key_up(key)
            time.sleep(0.02)  # Small delay between each key release
        
        # Wait for reset to complete
        print("Waiting for game reset...")
        time.sleep(self.config.restart_delay)
        
        # Navigate through start menu
        self._navigate_start_menu()
    
    def _navigate_start_menu(self):
        """Navigate through the FRLG start menu."""
        print("Navigating start menu...")
        
        # Continue through opening screens
        self._press_key('enter')
        time.sleep(3)
        
        # Continue
        self._press_key('enter')
        time.sleep(0.05)
        
        # Continue
        self._press_key('enter')
        time.sleep(0.05)
        
        # Final menu navigation
        self._press_key('x')
        time.sleep(0.05)

        self._press_key('z')
        
        print("Start menu navigation complete")