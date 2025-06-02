import pyautogui
import pydirectinput
import time
import sys
import os
from config import ConfigManager
from image_processor import ImageProcessor
from input_handler import InputHandler
from screenshot_manager import ScreenshotManager


class ShinyHunterController:
    """Main driver for shiny hunt application."""
    
    def __init__(self, log_function=None):
        self.running = False
        self.paused = False
        self.thread = None
        self.count = 0
        self.log_function = log_function
        
        # Initialize components
        self.config = ConfigManager().get_config()
        self.image_processor = ImageProcessor()
        self.input_handler = InputHandler()
        self.screenshot_manager = ScreenshotManager()
    
    def log(self, message: str):
        """Log message if log function is available."""
        if self.log_function:
            self.log_function(message)
        print(message)
    
    def countdown(self, seconds: int):
        """Countdown before starting hunt."""
        while seconds > 0:
            self.log(f"Starting in: {seconds}")
            time.sleep(1)
            seconds -= 1
    
    def attempt_encounter(self):
        """Main hunt loop - encounter, check, and reset."""
        while self.running:
            if self.paused:
                time.sleep(0.1)
                continue
                
            self.log('Initializing Shiny Hunt')
            self.increment_count()
            self.log(f"Attempt #{self.count}")
            
            # Execute encounter with verification
            if hasattr(self.input_handler, 'encounter_sequence_with_verification'):
                encounter_success = self.input_handler.encounter_sequence_with_verification(
                    self.screenshot_manager, self.image_processor
                )
                print(f"Encounter success: {encounter_success}")
                if not encounter_success:
                    self.log('Failed to reach encounter screen, restarting...')
                    self.input_handler.restart_sequence()
                    continue
            else:
                # Fallback to original method
                self.input_handler.encounter_sequence()
            
            # Take screenshot and check for shiny
            screenshot_path = self.screenshot_manager.take_screenshot('current_screenshot.png')
            
            if self.image_processor.is_shiny_found(self.config.reference_image_path, screenshot_path):
                self._handle_shiny_found()
                break
            else:
                self._handle_no_shiny()
    
    def _handle_shiny_found(self):
        """Handle when a shiny is found."""
        self.log('Shiny Found!')
        self.screenshot_manager.take_timestamped_screenshot('shiny_found')
        self.running = False
    
    def _handle_no_shiny(self):
        """Handle when no shiny is found."""
        self.log('No Shiny Found!')
        self.screenshot_manager.take_screenshot('emulator_screenshot.png')
        self.input_handler.restart_sequence()
    
    def set_running_status(self, status: bool):
        self.running = status

    def increment_count(self):
        self.count += 1
    
    def start_hunt(self):
        """Start the shiny hunt."""
        # TODO: Make this a setting
        self.countdown(3)
        self.running = True
        self.log(f"Running Status set to: {self.running}")
    
    def pause_hunt(self):
        if self.running:
            self.paused = not self.paused
            self.log(f"Hunt {'paused' if self.paused else 'resumed'}")
    
    def stop_hunt(self):
        self.running = False
        if self.thread:
            self.thread.join()
        self.log("Hunt stopped")
