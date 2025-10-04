import tkinter as tk
from tkinter import ttk, filedialog
from threading import Thread
from PIL import Image, ImageTk
import sv_ttk
import os
from styles import shiny_style
from screenshot_manager import ScreenshotManager
from input_handler import InputHandler
from config import ConfigManager


class ShinyHuntGUI:
    def __init__(self, root, input_thread, controller, handle_start, handle_pause, handle_stop):
        self.input_handler = InputHandler()
        
        # Store controller reference
        self.controller = controller
        
        # Create a tkinter variable for displaying the count
        self.count_var = tk.IntVar(value=0)
        
        ### Styling ###
        sv_ttk.set_theme("dark")
        style = ttk.Style()
        style.configure('start.TButton', font=(
            'calibri', 12, 'bold', 'underline'), foreground='green')
        style.configure('standard.TButton', font=(
            'calibri', 12, 'bold'))
        style.configure('side.TFrame', background="#2a2b2a")
        style.configure('reset.TLabel', font=(
            'calibri', 12, 'bold'))
        style.configure('status.TLabel', font=(
            'calibri', 12, 'bold', 'underline'))

        shiny_style()

        ### Scaling ###
        root.grid_columnconfigure(0, weight=1)
        root.grid_columnconfigure(1, weight=3)
        root.grid_columnconfigure(2, weight=0)
        # root.grid_rowconfigure(0, weight=1)
        # root.grid_rowconfigure(1, weight=1)

        self.paused = False
        self.stopped = False

        self.input_thread = input_thread
        self.handle_start = handle_start
        self.handle_pause = handle_pause
        self.handle_stop = handle_stop



        # Root Config
        self.root = root

        # Initialize Screenshot Manager
        self.screenshot_manager = ScreenshotManager()

        # Left Frame Initialization
        self.left_frame = ttk.Frame(
            root, width=200, height=400, style='side.TFrame', padding=10)
        self.left_frame.grid(row=0, column=0, padx=20, pady=40, sticky="nws")

        # Right Frame
        self.right_frame = ttk.Frame(
            root, width=200, height=400, style='side.TFrame',)
        self.right_frame.grid(row=0, column=2,ipadx=10, padx=40, pady=40, sticky="nsew")
        self.right_frame.grid_columnconfigure(0, weight=1)



        # Status Label
        self.status_label = ttk.Label(
            root, text="Press 'Start Hunt' to begin the shiny hunt.", style='status.TLabel')
        self.status_label.grid(row=3, column=1,)

         # Log Text Widget
        self.log_text = tk.Text(root, height=10, width=50, state='disabled')
        self.log_text.grid(row=4, column=1, padx=20, pady=20, sticky="nsew")

        ##################
        ### LEFT Frame ###
        ##################
        # Start Button
        self.start_button = ttk.Button(
            self.left_frame, text="Start Hunt", command=self.on_start_hunt, style='start.TButton')
        self.start_button.grid(row=2, column=0, pady=10, )

        # Pause Button
        self.pause_button = ttk.Button(
            self.left_frame, text="Pause Hunt", command=self.toggle_pause, style="standard.TButton")
        self.pause_button.grid(row=3, column=0, padx=25)

        # Stop Button
        self.stop_button = ttk.Button(
            self.left_frame, text="Stop Hunt", command=self.stop_hunt, style="standard.TButton")
        self.stop_button.grid(row=4, padx=2)

        # Reset Counter
        self.reset_count = ttk.Label(
            self.left_frame, textvariable=self.count_var, style='reset.TLabel')
        self.reset_count.grid(row=5, pady=(10, 0), )

        # Settings Button
        self.settings_button = ttk.Button(
            self.left_frame, text="Settings", command=self.open_settings, style="standard.TButton")
        self.settings_button.grid(row=6, column=0, pady=10)

        # Calibration Section
        self._create_calibration_section()

        screenshot_button = ttk.Button(
            self.right_frame, 
            text="Take Screenshot", 
            command=lambda: self.screenshot_manager.take_screenshot("encounter_screen_template.png"),
            style='standard.TButton'
        )
        screenshot_button.grid(row=7, column=0)

        restart_button = ttk.Button(
            self.right_frame,
            text="Manual Reset",
            command=lambda: self.input_handler.restart_sequence(),
            style='standard.TButton'
        )
        restart_button.grid(row=6, padx=2)

        ###################
        ### Right Frame ###
        ###################
    
    def _create_calibration_section(self):
        """Create the threshold calibration section in the left frame."""
        # Calibration Frame
        calibration_frame = ttk.LabelFrame(self.left_frame, text="Threshold Calibration", padding="10")
        calibration_frame.grid(row=7, column=0, pady=(20, 0), sticky="ew")
        
        # Calibration mode toggle
        self.calibration_mode_var = tk.BooleanVar(value=False)
        calibration_toggle = ttk.Checkbutton(
            calibration_frame,
            text="Calibration Mode",
            variable=self.calibration_mode_var,
            command=self._toggle_calibration_mode
        )
        calibration_toggle.pack(anchor="w", pady=(0, 10))
        
        # Info label
        self.calibration_info = ttk.Label(
            calibration_frame,
            text="Toggle on to setup threshold.\nNavigate to encounter screen,\nthen capture reference.",
            font=('calibri', 9),
            justify="left"
        )
        self.calibration_info.pack(anchor="w", pady=(0, 10))
        
        # Capture reference button
        self.capture_reference_button = ttk.Button(
            calibration_frame,
            text="Capture Reference",
            command=self._capture_calibration_reference,
            style='standard.TButton',
            state='disabled'
        )
        self.capture_reference_button.pack(fill='x', pady=(0, 5))
        
        # Calculate threshold button
        self.calculate_threshold_button = ttk.Button(
            calibration_frame,
            text="Calculate Threshold",
            command=self._calculate_threshold,
            style='standard.TButton',
            state='disabled'
        )
        self.calculate_threshold_button.pack(fill='x', pady=(0, 5))
        
        # Current threshold display
        self.threshold_display = ttk.Label(
            calibration_frame,
            text=f"Current: {self.controller.config.correlation_threshold:.4f}",
            font=('calibri', 9, 'bold')
        )
        self.threshold_display.pack(anchor="w", pady=(5, 0))
    
    def _toggle_calibration_mode(self):
        """Toggle calibration mode on/off."""
        config = ConfigManager().get_config()
        config.calibration_mode = self.calibration_mode_var.get()
        
        if config.calibration_mode:
            # Enable calibration buttons and disable hunt
            self.capture_reference_button.config(state='normal')
            self.start_button.config(state='disabled')
            self.calibration_info.config(
                text="Calibration Mode Active!\nNavigate to encounter screen,\nthen capture reference.",
                foreground='orange'
            )
            self.log_message("Calibration mode enabled. Hunt disabled.")
        else:
            # Disable calibration buttons and enable hunt
            self.capture_reference_button.config(state='disabled')
            self.calculate_threshold_button.config(state='disabled')
            self.start_button.config(state='normal')
            self.calibration_info.config(
                text="Toggle on to setup threshold.\nNavigate to encounter screen,\nthen capture reference.",
                foreground=''
            )
            self.log_message("Calibration mode disabled. Hunt enabled.")
    
    def _capture_calibration_reference(self):
        """Capture a reference screenshot for calibration."""
        import time
        config = ConfigManager().get_config()
        
        # Try to focus the game window first if cross_platform_app_frame is available
        if hasattr(self, 'cross_platform_app_frame'):
            window_info = self.cross_platform_app_frame.get_selected_window_info()
            
            if window_info:
                try:
                    # Raise and focus the window
                    window_manager = self.cross_platform_app_frame.window_manager
                    if window_manager:
                        self.log_message("Focusing game window...")
                        window_manager.raise_window(window_info)
                        window_manager.focus_window(window_info)
                        # Give the window time to come to front and render
                        time.sleep(0.5)
                except Exception as e:
                    self.log_message(f"Warning: Could not focus window: {e}")
            else:
                self.log_message("Warning: No window selected. Screenshot may not capture game window.")
        
        # Take screenshot and save as calibration reference
        screenshot_path = self.screenshot_manager.take_screenshot('calibration_reference.png')
        
        self.log_message(f"Calibration reference captured: {screenshot_path}")
        self.log_message("Now capture a second screenshot to calculate threshold.")
        
        # Enable the calculate button
        self.calculate_threshold_button.config(state='normal')
    
    def _calculate_threshold(self):
        """Calculate the correlation threshold between reference and current screen."""
        import time
        config = ConfigManager().get_config()
        
        # Try to focus the game window first if cross_platform_app_frame is available
        if hasattr(self, 'cross_platform_app_frame'):
            window_info = self.cross_platform_app_frame.get_selected_window_info()
            
            if window_info:
                try:
                    # Raise and focus the window
                    window_manager = self.cross_platform_app_frame.window_manager
                    if window_manager:
                        self.log_message("Focusing game window...")
                        window_manager.raise_window(window_info)
                        window_manager.focus_window(window_info)
                        # Give the window time to come to front and render
                        time.sleep(0.5)
                except Exception as e:
                    self.log_message(f"Warning: Could not focus window: {e}")
        
        # Take a current screenshot
        current_screenshot = self.screenshot_manager.take_screenshot('calibration_current.png')
        
        # Calculate correlation between calibration reference and current
        reference_path = config.calibration_reference_path
        
        if not os.path.exists(reference_path):
            self.log_message("Error: Calibration reference not found. Capture reference first.")
            return
        
        # Use the image processor to calculate correlation
        correlation = self.controller.image_processor.get_correlation(
            reference_path, 
            current_screenshot
        )
        
        self.log_message(f"Calculated correlation: {correlation:.6f}")
        self.log_message(f"Recommended threshold: {correlation:.6f}")
        
        # Update the config with the new threshold
        config.correlation_threshold = correlation
        self.threshold_display.config(text=f"Current: {correlation:.4f}")
        
        self.log_message("Threshold updated! You can disable calibration mode now.")

    ### Methods for GUI Interaction ###
    def log_message(self, message):
        # Update GUI components (the controller will handle its own logging via log_function)
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + '\n')
        self.log_text.config(state='disabled')
        self.log_text.see(tk.END)



    def on_start_hunt(self):
        self.status_label.config(text="Mewtwo Hunt in progress...")
        self.start_button.config(state="disabled")

        # Calls start_hunt from shiny_hunt_app
        self.handle_start()
        self.input_thread.start()

    def update_count(self):
        if self.controller:
            self.count_var.set(self.controller.count)

    def toggle_pause(self):
        # TODO: Decide where to store paused state - main or here

        self.paused = not self.paused
        if self.paused:
            self.status_label.config(text="Hunt Paused")
        else:
            self.status_label.config(text="Mewtwo Hunt in progress...")
        self.handle_pause()


    def stop_hunt(self):
        print('Stopping Hunt')
        self.handle_stop()
        self.start_button.config(state="enabled")
        self.status_label.config(text="Mewtwo Hunt stopped.")

    def open_settings(self):
        """Open a settings popup window"""
        # Get the config manager
        config_manager = ConfigManager()
        config = config_manager.get_config()
        
        # Create the settings window
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("450x400")
        settings_window.resizable(False, False)
        
        # Make it modal (blocks interaction with main window)
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # Center the window
        settings_window.update_idletasks()
        x = (settings_window.winfo_screenwidth() // 2) - (450 // 2)
        y = (settings_window.winfo_screenheight() // 2) - (400 // 2)
        settings_window.geometry(f"450x400+{x}+{y}")
        
        # Apply dark theme to settings window
        sv_ttk.set_theme("dark")
        
        # Create main frame with padding
        main_frame = ttk.Frame(settings_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Settings title
        title_label = ttk.Label(main_frame, text="Settings", font=('calibri', 16, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Input delay settings
        delay_frame = ttk.LabelFrame(main_frame, text="Input Delays", padding="10")
        delay_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(delay_frame, text="PyAutoGUI pause (s):").pack(anchor="w")
        pyautogui_delay = ttk.Entry(delay_frame)
        pyautogui_delay.pack(fill=tk.X, pady=(5, 10))
        pyautogui_delay.insert(0, str(config.pyautogui_pause))
        
        ttk.Label(delay_frame, text="Encounter delay (s):").pack(anchor="w")
        encounter_delay = ttk.Entry(delay_frame)
        encounter_delay.pack(fill=tk.X, pady=(5, 10))
        encounter_delay.insert(0, str(config.encounter_delay))
        
        ttk.Label(delay_frame, text="Restart delay (s):").pack(anchor="w")
        restart_delay = ttk.Entry(delay_frame)
        restart_delay.pack(fill=tk.X, pady=(5, 0))
        restart_delay.insert(0, str(config.restart_delay))
        
        # Detection settings
        detection_frame = ttk.LabelFrame(main_frame, text="Shiny Detection", padding="10")
        detection_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(detection_frame, text="Correlation threshold:").pack(anchor="w")
        correlation_threshold = ttk.Entry(detection_frame)
        correlation_threshold.pack(fill=tk.X, pady=(5, 10))
        correlation_threshold.insert(0, str(config.correlation_threshold))
        
        ttk.Label(detection_frame, text="Max encounter retries:").pack(anchor="w")
        max_retries = ttk.Entry(detection_frame)
        max_retries.pack(fill=tk.X, pady=(5, 0))
        max_retries.insert(0, str(config.max_encounter_retries))
        
        # Safety settings
        safety_frame = ttk.LabelFrame(main_frame, text="Safety", padding="10")
        safety_frame.pack(fill=tk.X, pady=(0, 10))
        
        failsafe_var = tk.BooleanVar(value=config.failsafe_enabled)
        failsafe_check = ttk.Checkbutton(safety_frame, text="Enable PyAutoGUI failsafe", variable=failsafe_var)
        failsafe_check.pack(anchor="w")
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        def save_settings():
            try:
                # Update config values
                config.pyautogui_pause = float(pyautogui_delay.get())
                config.encounter_delay = float(encounter_delay.get())
                config.restart_delay = float(restart_delay.get())
                config.correlation_threshold = float(correlation_threshold.get())
                config.max_encounter_retries = int(max_retries.get())
                config.failsafe_enabled = failsafe_var.get()
                
                # Persist the changes
                config_manager.save_config()
                
                # Log the changes
                if hasattr(self, 'log_message'):
                    self.log_message("Settings updated successfully!")
                
                settings_window.destroy()
            except ValueError as e:
                error_label = ttk.Label(button_frame, text="Invalid values entered!", foreground="red")
                error_label.pack(pady=(10, 0))
                # Remove error after 3 seconds, but only if window still exists
                def safe_destroy():
                    if settings_window.winfo_exists():
                        error_label.destroy()
                settings_window.after(3000, safe_destroy)# Remove error after 3 seconds
        
        def cancel_settings():
            settings_window.destroy()
        
        save_button = ttk.Button(button_frame, text="Save", command=save_settings, style='start.TButton')
        save_button.pack(side=tk.RIGHT, padx=(10, 0))
        
        cancel_button = ttk.Button(button_frame, text="Cancel", command=cancel_settings, style='standard.TButton')
        cancel_button.pack(side=tk.RIGHT)
