import tkinter as tk
from tkinter import ttk, filedialog
from threading import Thread
from PIL import Image, ImageTk
import sv_ttk
from styles import shiny_style
from screenshot_manager import ScreenshotManager
from input_handler import InputHandler


class ShinyHuntGUI:
    def __init__(self, root, input_thread, count, handle_start, handle_pause, handle_stop):
        self.input_handler = InputHandler()

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
        root.grid_columnconfigure(2, weight=1)
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
            root, width=200, height=400, style='side.TFrame')
        self.right_frame.grid(row=0, column=2, padx=20, pady=40, sticky="ns")

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
            self.left_frame, text="Start Hunt", command=self.start_hunt, style='start.TButton')
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

        # Console Window 
        self.console = tk.Text(self.left_frame, height=10, width=30)


        screenshot_button = ttk.Button(
            self.right_frame, 
            text="Take Screenshot", 
            command=lambda: self.screenshot_manager.take_screenshot("encounter_screen_template.png.png"),
            style='standard.TButton'
        )
        screenshot_button.grid(row=4, padx=2)

        restart_button = ttk.Button(
            self.right_frame,
            text="Manual Reset",
            command=lambda: self.input_handler.restart_sequence(),
            style='standard.TButton'
        )
        restart_button.grid(row=5, padx=2)

        ###################
        ### Right Frame ###
        ###################

        # Select Target Image Button
        # self.select_img = ttk.Button(
        #     self.right_frame, text="Select Image: ", command=self.open_file_dialog, style='standard.TButton')
        # TODO: Feature: Allow user to select own target image
        # self.select_img.config(state='disabled')
        # self.select_img.grid(row=2, column=2)

        # Target Image - TODO: Add Target Image + Logic
        # self.target_image = tk.Label(self.right_frame)


    def display_selected_image(self, file_path):
        image = Image.open(file_path)
        image = image.resize((300, 300))
        photo = ImageTk.PhotoImage(image)

        self.target_image.config(image=photo)
        self.target_image.image = photo
        self.target_image.grid(row=6, column=2)

    
    def log_message(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + '\n')
        self.log_text.config(state='disabled')
        self.log_text.see(tk.END)

    def open_file_dialog(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.gif")])
        if file_path:
            self.display_selected_image(file_path)

    def start_hunt(self):
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
