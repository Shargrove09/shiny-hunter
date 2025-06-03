#!/usr/bin/env python3
"""
Demo script showing how the settings button and popup window work
"""

import tkinter as tk
from tkinter import ttk
import sv_ttk

# Simple demo class to show the settings functionality
class SettingsDemo:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Settings Button Demo")
        self.root.geometry("300x200")
        
        # Apply dark theme
        sv_ttk.set_theme("dark")
        
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title = ttk.Label(main_frame, text="Settings Button Demo", font=('calibri', 14, 'bold'))
        title.pack(pady=(0, 20))
        
        # Settings button
        settings_btn = ttk.Button(main_frame, text="Open Settings", command=self.open_settings)
        settings_btn.pack(pady=10)
        
        # Info label
        info_label = ttk.Label(main_frame, text="Click the button above to see\nthe settings popup window")
        info_label.pack(pady=10)
    
    def open_settings(self):
        """Open a settings popup window"""
        # Create the settings window
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("400x300")
        settings_window.resizable(False, False)
        
        # Make it modal (blocks interaction with main window)
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # Center the window
        settings_window.update_idletasks()
        x = (settings_window.winfo_screenwidth() // 2) - (400 // 2)
        y = (settings_window.winfo_screenheight() // 2) - (300 // 2)
        settings_window.geometry(f"400x300+{x}+{y}")
        
        # Apply dark theme to settings window
        sv_ttk.set_theme("dark")
        
        # Create main frame with padding
        main_frame = ttk.Frame(settings_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Settings title
        title_label = ttk.Label(main_frame, text="Settings", font=('calibri', 16, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Example settings
        settings_frame = ttk.LabelFrame(main_frame, text="Example Settings", padding="10")
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(settings_frame, text="Setting 1:").pack(anchor="w")
        setting1 = ttk.Entry(settings_frame)
        setting1.pack(fill=tk.X, pady=(5, 10))
        setting1.insert(0, "Default value")
        
        ttk.Label(settings_frame, text="Setting 2:").pack(anchor="w")
        setting2 = ttk.Entry(settings_frame)
        setting2.pack(fill=tk.X, pady=(5, 0))
        setting2.insert(0, "Another value")
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        # Save and Cancel buttons
        def save_settings():
            print(f"Setting 1: {setting1.get()}")
            print(f"Setting 2: {setting2.get()}")
            settings_window.destroy()
        
        def cancel_settings():
            settings_window.destroy()
        
        save_button = ttk.Button(button_frame, text="Save", command=save_settings)
        save_button.pack(side=tk.RIGHT, padx=(10, 0))
        
        cancel_button = ttk.Button(button_frame, text="Cancel", command=cancel_settings)
        cancel_button.pack(side=tk.RIGHT)
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    demo = SettingsDemo()
    demo.run()
