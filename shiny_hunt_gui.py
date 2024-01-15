import tkinter as tk
from tkinter import ttk, filedialog
from threading import Thread
from PIL import Image, ImageTk


class ShinyHuntGUI:

    def __init__(self, root, mewtwo_function, count, handle_pause):

        style = ttk.Style()

        style.configure('W.TButton', font=(
            'calibri', 10, 'bold', 'underline'), foreground='red')

        self.root = root
        self.count = count
        self.root.title("Shiny Hunt v0.1")
        self.mewtwo_function = mewtwo_function
        self.handle_pause = handle_pause

        # Root Config
        root.config(bg="#3EB489")

        # GUI Window Size
        self.root.geometry("800x400")

        # Left Frame

        # Right Frame

        # Info Label
        self.info_label = ttk.Label(
            root, text="Please make sure that the game is open and targeted before clicking start."
        )
        self.info_label.grid(row=0, column=1, pady=5)

        # Status Label
        self.status_label = ttk.Label(
            root, text="Press 'Start Hunt' to begin the shiny hunt.")
        self.status_label.grid(row=1, pady=10, column=1,)

        # Start Button
        self.start_button = ttk.Button(
            root, text="Start Hunt", command=self.start_hunt, style='W.TButton')
        self.start_button.grid(row=2, column=0, pady=10)

        # Pause Button
        self.pause_button = ttk.Button(
            root, text="Pause Hunt", command=self.handle_pause)
        self.pause_button.grid(row=3, column=0,)

        # Stop Button
        self.stop_button = ttk.Button(
            root, text="Stop Hunt", command=print("Stop Hunt"))
        self.stop_button.grid(row=4)

        # Reset Counter
        self.reset_count = ttk.Label(root, textvariable=count)
        self.reset_count.grid(pady=10)

        # Select Target Image Button
        self.select_img = ttk.Button(
            root, text="Select Image: ", command=self.open_file_dialog)
        self.select_img.grid()

        # Target Image
        self.label = tk.Label(root)

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
        # Call your mewtwo function here
        self.mewtwo_function()

        # Update GUI after completion
        self.status_label.config(text="Mewtwo Hunt completed!")
        self.start_button.config(state="normal")

    def update_count(self):
        self.count.set(self.count.get())
