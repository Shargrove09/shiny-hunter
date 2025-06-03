import tkinter as tk
from tkinter import ttk, filedialog
from threading import Thread
from PIL import Image, ImageTk
import sv_ttk
from styles import shiny_style
from screenshot_manager import ScreenshotManager
from input_handler import InputHandler
from config import ConfigManager


class ShinyHuntGUI:
    def __init__(self, root, input_thread, count, handle_start, handle_pause, handle_stop, controller=None):
        self.input_handler = InputHandler()

        if controller: 
            self.log_message = controller

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

        self.count = count
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
            self.left_frame, textvariable=count, style='reset.TLabel')
        self.reset_count.grid(row=5, pady=(10, 0), )

        # Settings Button
        self.settings_button = ttk.Button(
            self.left_frame, text="Settings", command=self.open_settings, style="standard.TButton")
        self.settings_button.grid(row=6, column=0, pady=10)

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
    

    ### Methods for GUI Interaction ###
    def log_message(self, message):
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
        self.count.set(self.count.get())

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
        
        # Save and Cancel buttons
        def save_settings():
            try:
                # Update config values
                config.pyautogui_pause = float(pyautogui_delay.get())
                config.encounter_delay = float(encounter_delay.get())
                config.restart_delay = float(restart_delay.get())
                config.correlation_threshold = float(correlation_threshold.get())
                config.max_encounter_retries = int(max_retries.get())
                config.failsafe_enabled = failsafe_var.get()
                
                # Log the changes
                if hasattr(self, 'log_message'):
                    self.log_message("Settings updated successfully!")
                
                settings_window.destroy()
            except ValueError as e:
                # Show error if invalid values entered
                error_label = ttk.Label(button_frame, text="Invalid values entered!", foreground="red")
                error_label.pack(pady=(10, 0))
                settings_window.after(3000, error_label.destroy)  # Remove error after 3 seconds
        
        def cancel_settings():
            settings_window.destroy()
        
        save_button = ttk.Button(button_frame, text="Save", command=save_settings, style='start.TButton')
        save_button.pack(side=tk.RIGHT, padx=(10, 0))
        
        cancel_button = ttk.Button(button_frame, text="Cancel", command=cancel_settings, style='standard.TButton')
        cancel_button.pack(side=tk.RIGHT)
