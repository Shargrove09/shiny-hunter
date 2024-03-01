import tkinter as tk
from tkinter import ttk, filedialog
from threading import Thread
from PIL import Image, ImageTk
import sv_ttk


class ShinyHuntGUI:
    def __init__(self, root, mewtwo_function, count, handle_pause):
        style = ttk.Style()

        sv_ttk.set_theme("dark")
        style.configure('start.TButton', font=(
            'calibri', 10, 'bold', 'underline'), foreground='green')

        style.configure('side.TFrame', background="#2a2b2a")

        self.root = root
        self.count = count

        self.mewtwo_function = mewtwo_function
        self.handle_pause = handle_pause

        # Root Config
        # root.config(bg="#3EB489")

        # Left Frame
        self.left_frame = ttk.Frame(
            root, width=200, height=400, style='side.TFrame', padding=10)
        self.left_frame.grid(row=0, column=0, padx=20, pady=0, sticky="nws")

        # Right Frame
        self.right_frame = ttk.Frame(
            root, width=200, height=400, style='side.TFrame')
        self.right_frame.grid(row=0, column=2, padx=20, pady=0, sticky="nes")

        # Status Label
        self.status_label = ttk.Label(
            root, text="Press 'Start Hunt' to begin the shiny hunt.")
        self.status_label.grid(row=3, column=1,)

        # Reset Counter
        self.reset_count = ttk.Label(self.left_frame, textvariable=count)
        self.reset_count.grid(pady=0)

        # Select Target Image Button
        self.select_img = ttk.Button(
            self.root, text="Select Image: ", command=self.open_file_dialog)
        self.select_img.grid(row=2, column='2')

        # Target Image
        self.label = tk.Label(root)

        ##################
        ### LEFT Frame ###
        ##################
        # Start Button
        self.start_button = ttk.Button(
            self.left_frame, text="Start Hunt", command=self.start_hunt, style='start.TButton')
        self.start_button.grid(row=2, column=0, pady=10, )

        # Pause Button
        self.pause_button = ttk.Button(
            self.left_frame, text="Pause Hunt", command=self.handle_pause)
        self.pause_button.grid(row=3, column=0, padx=25)

        # Stop Button
        self.stop_button = ttk.Button(
            self.left_frame, text="Stop Hunt", command=print("Stop Hunt"))
        self.stop_button.grid(row=4, padx=2)

        ###################
        ### Right Frame ###
        ###################

    def display_selected_image(self, file_path):
        image = Image.open(file_path)
        image = image.resize((300, 300))
        photo = ImageTk.PhotoImage(image)

        self.label.config(image=photo)
        self.label.image = photo
        self.label.grid()

    def open_file_dialog(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.gif")])
        if file_path:
            self.display_selected_image(file_path)

    def start_hunt(self):
        self.status_label.config(text="Mewtwo Hunt in progress...")
        self.start_button.config(state="disabled")
        self.hunt_thread = Thread(target=self.shiny_hunt_thread)
        self.hunt_thread.start()

    def shiny_hunt_thread(self):
        # Call mewtwo function here
        self.mewtwo_function()

        # Update GUI after completion
        self.status_label.config(text="Mewtwo Hunt completed!")
        self.start_button.config(state="normal")

    def update_count(self):
        self.count.set(self.count.get())
