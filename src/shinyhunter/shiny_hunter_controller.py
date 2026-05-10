import time
import json
import os
from config import ConfigManager
from image_processor import ImageProcessor
from input_handler import InputHandler
from screenshot_manager import ScreenshotManager
import tkinter as tk

# pyautogui is not needed in this module - removed unused import


class ShinyHunterController:
    """Main driver for shiny hunt application."""
    
    def __init__(self, log_function=None):
        self.running = False
        self.paused = False
        self.thread = None
        self._reset_count = 0  # Use a plain integer for the attempt counter
        self.log_function = log_function
        
        # Initialize components
        self.config = ConfigManager().get_config()
        self.image_processor = ImageProcessor()
        self.input_handler = InputHandler()
        self.screenshot_manager = ScreenshotManager()

    @property
    def count(self):
        return self._reset_count

    @count.setter
    def count(self, value):
        self._reset_count = int(value)

    def increment_count(self):
        self._reset_count += 1
        return self._reset_count
    
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
    
    def _load_custom_sequence_steps(self):
        """Load encounter steps from the sequence config JSON.

        Returns the list of step dicts on success, or raises on failure.
        """
        seq_path = self.config.sequence_config_path
        if not os.path.isabs(seq_path):
            seq_path = os.path.join(os.getcwd(), seq_path.lstrip('./'))
        with open(seq_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get("encounter_sequence", [])

    def attempt_encounter(self):
        """Main hunt loop - encounter, check, and reset."""
        while self.running:
            if self.paused:
                time.sleep(0.1)
                continue

            config = ConfigManager().get_config()
            self.log("Attempting encounter #{}".format(self.count + 1))

            if config.use_custom_sequence:
                # --- Custom sequence mode ---
                try:
                    steps = self._load_custom_sequence_steps()
                except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
                    self.log(f"ERROR: Could not load custom sequence — {e}")
                    self.log("Hunt stopped. Fix your sequence config and try again.")
                    self.running = False
                    break

                self.input_handler.execute_custom_sequence(steps)
                self.increment_count()
                self.log(f"Attempt #{self.count}")
                # TODO: placeholder — shiny detection for custom sequence
                self.log("Shiny check: placeholder (not yet implemented for custom mode)")
                self._handle_no_shiny()

            else:
                # --- Static mode ---
                if hasattr(self.input_handler, 'encounter_sequence_with_verification'):
                    encounter_success = self.input_handler.encounter_sequence_with_verification(
                        self.screenshot_manager, self.image_processor
                    )
                    print(f"Encounter success: {encounter_success}")
                    if not encounter_success:
                        self.log('Failed to reach encounter screen, restarting...')
                        self.input_handler.restart_sequence()
                        continue

                    self.increment_count()
                    self.log(f"Attempt #{self.count}")
                else:
                    self.increment_count()
                    self.log(f"Attempt #{self.count}")
                    self.input_handler.encounter_sequence()

                screenshot_path = self.screenshot_manager.take_screenshot('current_screenshot.png')
                if self.image_processor.is_shiny_found(self.config.calibration_reference_path, screenshot_path):
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
        time.sleep(1)  # Brief pause before reset
        self.input_handler.restart_sequence()
    
    def set_running_status(self, status: bool):
        self.running = status

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
