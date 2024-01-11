import tkinter as tk
from tkinter import ttk
from threading import Thread


class ShinyHuntGUI:

    def __init__(self, root, mewtwo_function, count, handle_pause):

        self.root = root
        self.count = count
        self.root.title("Shiny Hunt v0.1")

        def update_label_text():
            # Update the variable value
            count.set(self.count.get() + 1)

        self.mewtwo_function = mewtwo_function

        self.handle_pause = handle_pause

        # GUI Window Size
        self.root.geometry("800x400")

        # Info Label
        self.info_label = ttk.Label(
            root, text="Please make sure that the game is open and targeted before clicking start."
        )
        self.info_label.pack(pady=5)

        # Status Label
        self.status_label = ttk.Label(
            root, text="Press 'Start Hunt' to begin the shiny hunt.")
        self.status_label.pack(pady=10)

        # Start Button
        self.start_button = ttk.Button(
            root, text="Start Hunt", command=self.start_hunt)
        self.start_button.pack(pady=10)

        # Pause Button
        self.pause_button = ttk.Button(
            root, text="Pause Hunt", command=self.handle_pause)
        self.pause_button.pack(pady=10)

        # Reset Counter

        self.reset_count = ttk.Label(root, textvariable=count)
        self.reset_count.pack(pady=10)

        # Test update button
        update_button = tk.Button(
            root, text="Update Label", command=update_label_text)
        update_button.pack(pady=10)

        # Target Image Counter/Search

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
