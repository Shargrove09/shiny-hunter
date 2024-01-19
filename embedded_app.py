import tkinter as tk
import win32gui
import win32con
import win32api


class EmbeddedAppFrame(tk.Frame):
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.grid()
        self.create_widgets()

    def create_widgets(self):
        # Button to launch embedded app
        self.launch_button = tk.Button(
            self, text="Launch Epilogue", command=self.launch_app)
        self.launch_button.grid(pady=10)

        # Frame for embedded app
        self.embed_frame = tk.Frame(self, width=1600, height=600)
        self.embed_frame.configure(bg="red")
        self.embed_frame.grid()

    def launch_app(self):
        # Find app window handle
        app_handle = win32gui.FindWindow(None, 'Playback')
        print("App Handle: ", app_handle)

        # Setting Parent of App window to be embedded frame
        win32gui.SetParent(app_handle, int(self.embed_frame.winfo_id()))

        # Adjust the size and position of the embedded window
        win32gui.MoveWindow(app_handle, 0, 0, self.embed_frame.winfo_width(
        ), self.embed_frame.winfo_height(), True)

        # Show the embedded App Window
        win32gui.ShowWindow(app_handle, win32con.SW_SHOW)
