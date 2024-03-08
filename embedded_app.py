import tkinter as tk
from tkinter import ttk
import win32gui
import win32con
import pygetwindow as gw
from styles import shiny_style
import pywinauto


class EmbeddedAppFrame(tk.Frame):
    def __init__(self, right_frame, app, container_frame, master=None):
        tk.Frame.__init__(self, container_frame)
        self.entry_var = tk.StringVar(value="Playback")
        self.grid(column=1)
        self.right_frame = right_frame
        self.container_frame = container_frame
        self.app = app

        # Import Button Styles
        shiny_style()

        self.create_widgets()
        self.dropdown_var = tk.StringVar()

        self.create_dropdown()

        self.app_handle = None

        # Unembed window on close
        master.protocol("WM_DELETE_WINDOW", self.unembed_on_close)

    def create_widgets(self):
        # Button to launch embedded app
        self.launch_button = ttk.Button(
            self.right_frame, text="Launch Epilogue", command=self.launch_app, style='standard.TButton')
        self.launch_button.grid(row=0, column=2, sticky="")

        # Frame for embedded app
        self.embed_frame = tk.Frame(self, width=1280, height=960)
        self.embed_frame.configure(bg="#2a2b2a")
        self.embed_frame.grid(column=1)

        # Button to Unembedd App
        self.unembedd_button = ttk.Button(
            self.right_frame, text="Unembed App", command=self.unembed_app, style='standard.TButton')
        self.unembedd_button.grid(row=1, column=2)

    def launch_app(self):
        # Find app window handle
        print("Looking for: ", self.dropdown_var.get())
        self.app_handle = win32gui.FindWindow(None, self.dropdown_var.get())
        # Setting Parent of App window to be embedded frame
        win32gui.SetParent(self.app_handle, int(self.embed_frame.winfo_id()))
        self.app.connect(handle=self.app_handle)

        # Adjust the size and position of the embedded window
        win32gui.MoveWindow(self.app_handle, 0, 0, self.embed_frame.winfo_width(
        ), self.embed_frame.winfo_height(), True)

        # Show the embedded App Window
        win32gui.ShowWindow(self.app_handle, win32con.SW_SHOW)

    def unembed_app(self):
        if self.app_handle:
            win32gui.SetParent(self.app_handle, 0)
            self.app_handle = None
            print("Window Successfully Unembedded.")
        else:
            print("No Embedded winto to unembed")

    def unembed_on_close(self):
        print("Closing App! Unembedding Window if necessary!")
        self.unembed_app()
        self.master.destroy()

    # Window Dropdown
    def get_window_titles(self):
        window_titles = gw.getAllTitles()
        return window_titles

    def on_dropdown_change(self, event):
        selected_window = self.dropdown_var.get()
        print(f"Selected Window: {selected_window}")

    def create_dropdown(self):
        self.dropdown_label = ttk.Label(
            self.right_frame, text="Select the Game Window: ", style='select.TLabel')
        self.dropdown_label.grid(column=2, row=3)

        # Dropdown Menu
        self.window_dropdown = ttk.Combobox(
            self.right_frame, textvariable=self.dropdown_var, values=self.get_window_titles(), font="calibri 16", style='dropdown.TCombobox')
        self.window_dropdown.grid(column=2, row=4, pady=10)

        self.window_dropdown.set("Select Window")

        # Bind event handler to dropdown change event
        self.window_dropdown.bind(
            "<<ComboboxSelected>>", self.on_dropdown_change)
