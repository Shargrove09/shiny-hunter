"""
Cross-platform application frame for embedding or managing external windows.

This module replaces the Windows-specific embedded_app.py with a cross-platform solution
that adapts its functionality based on the available window management capabilities.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, List
from styles import shiny_style
from window_management import WindowManagerFactory, WindowManager, WindowInfo, EmbeddingMode


class CrossPlatformAppFrame(tk.Frame):
    """Cross-platform application frame with adaptive window management."""
    
    def __init__(self, right_frame, app, container_frame, master=None):
        tk.Frame.__init__(self, container_frame, relief='sunken', borderwidth=2)
        
        # Store references
        self.right_frame = right_frame
        self.container_frame = container_frame
        self.app = app
        self.master = master
        
        # Initialize window manager
        try:
            self.window_manager = WindowManagerFactory.create()
            self.embedding_mode = self.window_manager.get_embedding_mode()
            self.capabilities = self.window_manager.get_capabilities()
        except ImportError as e:
            print(f"Window manager initialization failed: {e}")
            self.window_manager = None
            self.embedding_mode = EmbeddingMode.MANUAL
            self.capabilities = {}
        
        # State tracking
        self.selected_window: Optional[WindowInfo] = None
        self.is_window_managed = False
        
        # UI components
        self.dropdown_var = tk.StringVar()
        self.status_var = tk.StringVar()
        
        # Initialize UI
        shiny_style()
        self._create_ui()
        self._update_status_display()
        
        # Setup cleanup
        if master:
            master.protocol("WM_DELETE_WINDOW", self._cleanup_on_close)
        
        print(f"CrossPlatformAppFrame initialized with {self.embedding_mode.value} mode")
    
    def _create_ui(self):
        """Create the user interface adapted to current capabilities."""
        self.grid(column=1)
        
        # Platform status display
        self._create_status_display()
        
        # Window selection
        self._create_window_selection()
        
        # Action buttons (adapted to capabilities)
        self._create_action_buttons()
        
        # Embedded/companion area (if supported)
        if self.embedding_mode != EmbeddingMode.MANUAL:
            self._create_window_area()
    
    def _create_status_display(self):
        """Create status display showing current platform and capabilities."""
        status_frame = ttk.LabelFrame(self.right_frame, text="Window Management Status", padding="5")
        status_frame.grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky="ew")
        
        # Platform info
        platform_text = f"Platform: {self.window_manager.platform if self.window_manager else 'Unknown'}"
        ttk.Label(status_frame, text=platform_text, font=('calibri', 10)).pack(anchor="w")
        
        # Mode info
        mode_text = f"Mode: {self.embedding_mode.value.replace('_', ' ').title()}"
        ttk.Label(status_frame, text=mode_text, font=('calibri', 10)).pack(anchor="w")
        
        # Dynamic status
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, font=('calibri', 10))
        self.status_label.pack(anchor="w")
    
    def _create_window_selection(self):
        """Create window selection dropdown."""
        # Label
        ttk.Label(self.right_frame, text="Select Game Window", style='select.TLabel').grid(
            row=1, column=0, columnspan=2, pady=(0, 5)
        )
        
        # Dropdown
        self.dropdown = ttk.Combobox(
            self.right_frame, 
            textvariable=self.dropdown_var,
            state="readonly",
            style='dropdown.TCombobox'
        )
        self.dropdown.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        # Refresh button
        self.refresh_button = ttk.Button(
            self.right_frame, 
            text="Refresh Windows", 
            command=self._refresh_windows,
            style='standard.TButton'
        )
        self.refresh_button.grid(row=3, column=0, columnspan=2, pady=(0, 10))
        
        # Populate initially
        self._refresh_windows()
    
    def _create_action_buttons(self):
        """Create action buttons based on available capabilities."""
        button_row = 4
        
        if self.capabilities.get('window_embedding', False):
            # Full embedding mode (Windows)
            self.launch_button = ttk.Button(
                self.right_frame,
                text="Embed Window",
                command=self._embed_window,
                style='standard.TButton'
            )
            self.launch_button.grid(row=button_row, column=0, columnspan=2, pady=(0, 5))
            
            self.unembed_button = ttk.Button(
                self.right_frame,
                text="Unembed Window",
                command=self._unembed_window,
                style='standard.TButton',
                state="disabled"
            )
            self.unembed_button.grid(row=button_row + 1, column=0, columnspan=2, pady=(0, 10))
            
        elif self.capabilities.get('window_positioning', False):
            # Companion mode (macOS/Linux)
            self.position_button = ttk.Button(
                self.right_frame,
                text="Position Beside",
                command=self._position_window,
                style='standard.TButton'
            )
            self.position_button.grid(row=button_row, column=0, columnspan=2, pady=(0, 5))
            
            self.focus_button = ttk.Button(
                self.right_frame,
                text="Focus Window",
                command=self._focus_window,
                style='standard.TButton'
            )
            self.focus_button.grid(row=button_row + 1, column=0, columnspan=2, pady=(0, 10))
            
        else:
            # Manual mode
            info_text = "Manual window management only.\nPlease arrange windows manually."
            ttk.Label(
                self.right_frame, 
                text=info_text, 
                font=('calibri', 10),
                justify="center"
            ).grid(row=button_row, column=0, columnspan=2, pady=10)
    
    def _create_window_area(self):
        """Create the area for embedded or companion windows."""
        if self.embedding_mode == EmbeddingMode.FULL_EMBED:
            # Create embedding frame
            self.embed_frame = tk.Frame(self, width=1280, height=960)
            self.embed_frame.configure(bg="#2a2b2a")
            self.embed_frame.grid(column=1, padx=10, pady=10)
            self.embed_frame.grid_propagate(False)  # Maintain size
        elif self.embedding_mode == EmbeddingMode.COMPANION:
            # Create placeholder for companion mode info
            self.companion_frame = ttk.LabelFrame(self, text="Companion Window Area", padding="10")
            self.companion_frame.grid(column=1, padx=10, pady=10, sticky="nsew")
            
            info_text = ("Selected window will be positioned\n"
                        "beside this application window")
            ttk.Label(
                self.companion_frame, 
                text=info_text,
                font=('calibri', 10),
                justify="center"
            ).pack(expand=True)
    
    def _refresh_windows(self):
        """Refresh the list of available windows."""
        if not self.window_manager:
            self.dropdown['values'] = ["No window manager available"]
            return
        
        try:
            windows = self.window_manager.get_all_windows()
            
            # Filter and format window titles
            window_options = []
            for window in windows:
                # Skip empty titles and system windows
                if window.title and len(window.title.strip()) > 0:
                    # Format: "Title [PID: 1234]" or just "Title" if no PID
                    if window.pid > 0:
                        option = f"{window.title} [PID: {window.pid}]"
                    else:
                        option = window.title
                    window_options.append(option)
            
            self.dropdown['values'] = window_options if window_options else ["No windows found"]
            self._update_status("Window list refreshed")
            
        except Exception as e:
            print(f"Error refreshing windows: {e}")
            self.dropdown['values'] = ["Error loading windows"]
            self._update_status("Error refreshing windows")
    
    def _get_selected_window(self) -> Optional[WindowInfo]:
        """Get the currently selected window info."""
        selection = self.dropdown_var.get()
        if not selection or not self.window_manager:
            return None
        
        # Extract title from selection (remove PID part if present)
        title = selection.split(" [PID:")[0]
        
        return self.window_manager.get_window_by_title(title)
    
    def _embed_window(self):
        """Embed the selected window (Windows only)."""
        window_info = self._get_selected_window()
        if not window_info:
            self._update_status("No window selected")
            return
        
        if not hasattr(self, 'embed_frame'):
            self._update_status("Embed frame not available")
            return
        
        try:
            success = self.window_manager.embed_window(window_info, self.embed_frame)
            if success:
                self.selected_window = window_info
                self.is_window_managed = True
                self._update_status(f"Embedded: {window_info.title}")
                
                # Update button states
                self.launch_button.config(state="disabled")
                self.unembed_button.config(state="normal")
                
                # Connect to app if it has a connect method
                if hasattr(self.app, 'connect') and hasattr(window_info.handle, '_hWnd'):
                    try:
                        self.app.connect(handle=window_info.handle._hWnd)
                    except Exception as e:
                        print(f"App connection failed: {e}")
            else:
                self._update_status(f"Failed to embed: {window_info.title}")
                
        except Exception as e:
            print(f"Embedding error: {e}")
            self._update_status("Embedding failed")
    
    def _unembed_window(self):
        """Unembed the current window."""
        if not self.selected_window:
            self._update_status("No window to unembed")
            return
        
        try:
            success = self.window_manager.unembed_window(self.selected_window)
            if success:
                self._update_status(f"Unembedded: {self.selected_window.title}")
                self.selected_window = None
                self.is_window_managed = False
                
                # Update button states
                self.launch_button.config(state="normal")
                self.unembed_button.config(state="disabled")
            else:
                self._update_status("Failed to unembed window")
                
        except Exception as e:
            print(f"Unembedding error: {e}")
            self._update_status("Unembedding failed")
    
    def _position_window(self):
        """Position window beside the main application (companion mode)."""
        window_info = self._get_selected_window()
        if not window_info:
            self._update_status("No window selected")
            return
        
        try:
            success = self.window_manager.position_window_beside(window_info, self.master)
            if success:
                self.selected_window = window_info
                self.is_window_managed = True
                self._update_status(f"Positioned: {window_info.title}")
            else:
                self._update_status(f"Failed to position: {window_info.title}")
                
        except Exception as e:
            print(f"Positioning error: {e}")
            self._update_status("Positioning failed")
    
    def _focus_window(self):
        """Focus the selected window."""
        window_info = self._get_selected_window()
        if not window_info:
            self._update_status("No window selected")
            return
        
        try:
            success = self.window_manager.focus_window(window_info)
            if success:
                self._update_status(f"Focused: {window_info.title}")
            else:
                self._update_status(f"Failed to focus: {window_info.title}")
                
        except Exception as e:
            print(f"Focus error: {e}")
            self._update_status("Focus failed")
    
    def _update_status(self, message: str):
        """Update the status display."""
        self.status_var.set(f"Status: {message}")
        print(f"Window Manager: {message}")
    
    def _update_status_display(self):
        """Update the status display with current state."""
        if not self.window_manager:
            self._update_status("No window manager available")
        else:
            capabilities_text = ", ".join([
                key.replace('_', ' ').title() 
                for key, value in self.capabilities.items() 
                if value
            ])
            self._update_status(f"Ready - {capabilities_text}")
    
    def _cleanup_on_close(self):
        """Clean up when the application is closing."""
        print("Cleaning up window management...")
        
        if self.is_window_managed and self.selected_window:
            try:
                if self.embedding_mode == EmbeddingMode.FULL_EMBED:
                    self.window_manager.unembed_window(self.selected_window)
                print("Window management cleanup completed")
            except Exception as e:
                print(f"Cleanup error: {e}")
        
        if self.master:
            self.master.destroy()
    
    @property
    def app_handle(self):
        """Compatibility property for existing code."""
        if self.selected_window and hasattr(self.selected_window.handle, '_hWnd'):
            return self.selected_window.handle._hWnd
        return None
