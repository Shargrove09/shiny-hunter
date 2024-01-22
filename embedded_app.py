import tkinter as tk
from tkinter import ttk
import win32gui
import win32con
import win32api
import pygetwindow as gw


class EmbeddedAppFrame(tk.Frame):
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.entry_var = tk.StringVar(value="Playback")
        self.grid(column=1)
        self.create_widgets()
        self.dropdown_var = tk.StringVar()
        self.create_dropdown()

        self.app_handle = None

        # Unembed window on close
        master.protocol("WM_DELETE_WINDOW", self.unembed_on_close)

    def create_widgets(self):
        # Button to launch embedded app
        self.launch_button = tk.Button(
            self, text="Launch Epilogue", command=self.launch_app)
        self.launch_button.grid(column=0, pady=10)

        # Frame for embedded app
        self.embed_frame = tk.Frame(self, width=1600, height=500)
        self.embed_frame.configure(bg="red")
        self.embed_frame.grid(column=1)

        # Button to Unembedd App
        self.unembedd_button = tk.Button(
            self, text="Unembed App", command=self.unembed_app)
        self.unembedd_button.grid(column=0)

        # # User Input
        # input_entry = tk.Entry(self, textvariable=self.entry_var)
        # input_entry.grid(pady=10)

        # # Get User Input Button
        # get_input_button = tk.Button(
        #     self, text="Get Input", command=self.get_user_input)
        # get_input_button.grid()

    def launch_app(self):
        # Find app window handle
        print("Looking for: ", self.dropdown_var.get())
        self.app_handle = win32gui.FindWindow(None, self.dropdown_var.get())

        # Setting Parent of App window to be embedded frame
        win32gui.SetParent(self.app_handle, int(self.embed_frame.winfo_id()))

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
        print("Unembdding on Close")
        self.unembed_app()
        self.master.destroy()

    def get_user_input(self):
        user_input = self.entry_var.get()
        print("User Input: ", user_input)

    # Window Dropdown

    def get_window_titles(self):
        window_titles = gw.getAllTitles()
        return window_titles

    def on_dropdown_change(self, event):
        selected_window = self.dropdown_var.get()
        print(f"Selected Window: {selected_window}")

    def create_dropdown(self):
        self.dropdown_label = tk.Label(
            self.master, text="Select the Game Window: ")
        self.dropdown_label.grid()

        # Dropdown Menu
        self.window_dropdown = ttk.Combobox(
            self.master, textvariable=self.dropdown_var, values=self.get_window_titles())
        self.window_dropdown.grid(pady=10)

        self.window_dropdown.set("Select Window")

        # Bind event handler to dropdown change event
        self.window_dropdown.bind(
            "<<ComboboxSelected>>", self.on_dropdown_change)
