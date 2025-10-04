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
        self.update_target_window_callback = None  # Callback to update input handler
        
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

        # Input simulation buttons
        self._create_input_buttons()
        
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
                text="Position in Boundary",
                command=self._position_window,
                style='standard.TButton'
            )
            self.position_button.grid(row=button_row, column=0, columnspan=2, pady=(0, 5))
            
            self.release_button = ttk.Button(
                self.right_frame,
                text="Release Window",
                command=self._release_window,
                style='standard.TButton',
                state="disabled"
            )
            self.release_button.grid(row=button_row + 1, column=0, columnspan=2, pady=(0, 5))
            
            self.focus_button = ttk.Button(
                self.right_frame,
                text="Focus Window",
                command=self._focus_window,
                style='standard.TButton'
            )
            self.focus_button.grid(row=button_row + 2, column=0, columnspan=2, pady=(0, 10))
            
        else:
            # Manual mode
            info_text = "Manual window management only.\nPlease arrange windows manually."
            ttk.Label(
                self.right_frame, 
                text=info_text, 
                font=('calibri', 10),
                justify="center"
            ).grid(row=button_row, column=0, columnspan=2, pady=10)
    
    def _create_input_buttons(self):
        """Create buttons for simulating user input."""
        input_frame = ttk.LabelFrame(self.right_frame, text="Input Simulation", padding="5")
        input_frame.grid(row=7, column=0, columnspan=2, pady=(10, 0), sticky="ew")

        x_button = ttk.Button(
            input_frame,
            text="Press 'X'",
            command=self._press_x_key,
            style='standard.TButton'
        )
        x_button.pack(fill='x', pady=2)

        z_button = ttk.Button(
            input_frame,
            text="Press 'Z'",
            command=self._press_z_key,
            style='standard.TButton'
        )
        z_button.pack(fill='x', pady=2)

        restart_button = ttk.Button(
            input_frame,
            text="Restart Sequence",
            command=self._execute_restart_sequence,
            style='standard.TButton'
        )
        restart_button.pack(fill='x', pady=2)
    
    def _press_x_key(self):
        """Simulate pressing the X key."""
        self.app.shiny_hunter_controller.input_handler._press_key('x')
    
    def _press_z_key(self):
        """Simulate pressing the Z key."""
        self.app.shiny_hunter_controller.input_handler._press_key('z')
    
    def _execute_restart_sequence(self):
        """Execute the restart sequence."""
        self.app.shiny_hunter_controller.input_handler.restart_sequence()

    def _create_window_area(self):
        """Create the area for embedding or positioning the window."""
        # This frame will act as the container for the embedded window
        # or as a visual boundary for companion mode.
        if self.embedding_mode == EmbeddingMode.FULL_EMBED:
            # Create embedding frame
            self.embed_frame = tk.Frame(self, width=1280, height=960)
            self.embed_frame.configure(bg="#2a2b2a")
            self.embed_frame.grid(column=1, padx=10, pady=10)
            self.embed_frame.grid_propagate(False)  # Maintain size
        elif self.embedding_mode == EmbeddingMode.COMPANION:
            # Create companion frame with defined boundary for window positioning
            self.companion_frame = ttk.LabelFrame(self, text="Companion Window Area", padding="10")
            self.companion_frame.grid(column=1, padx=10, pady=10, sticky="nsew")
            
            # Define the boundary dimensions for the companion window
            self.companion_boundary = {
                'width': 1280,
                'height': 960,
                'padding': 10  # Internal padding within the frame
            }
            
            # Create a visual indicator frame for the boundary
            self.boundary_indicator = tk.Frame(
                self.companion_frame,
                width=self.companion_boundary['width'],
                height=self.companion_boundary['height'],
                bg="#2a2b2a",
                relief='sunken',
                borderwidth=2
            )
            self.boundary_indicator.pack(expand=True)
            self.boundary_indicator.pack_propagate(False)
            
            info_text = ("Selected window will be positioned\n"
                        "within this boundary area\n"
                        f"({self.companion_boundary['width']}x{self.companion_boundary['height']})")
            self.boundary_label = ttk.Label(
                self.boundary_indicator, 
                text=info_text,
                font=('calibri', 10),
                justify="center",
                background="#2a2b2a",
                foreground="#ffffff"
            )
            self.boundary_label.place(relx=0.5, rely=0.5, anchor="center")
    
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
        """Position window within the companion boundary area."""
        window_info = self._get_selected_window()
        if not window_info:
            self._update_status("No window selected")
            return
        
        try:
            # Calculate the boundary position in screen coordinates
            boundary = self._calculate_companion_boundary()
            
            if boundary is None:
                self._update_status("Boundary not available")
                return
            
            # Position and resize the window to fit within the boundary
            success = self.window_manager.position_window_in_boundary(window_info, boundary)
            
            if success:
                self.selected_window = window_info
                self.is_window_managed = True
                
                # Raise the window to be above the main window
                self.window_manager.raise_window(window_info)
                
                # Update screenshot region in config to match boundary
                self._update_screenshot_region(boundary)
                
                # Update visual indicator
                self._update_boundary_indicator(active=True, window_title=window_info.title)
                
                # Update button states
                if hasattr(self, 'position_button'):
                    self.position_button.config(state="disabled")
                if hasattr(self, 'release_button'):
                    self.release_button.config(state="normal")
                
                # Notify app controller if available
                if hasattr(self.app, 'set_target_window'):
                    self.app.set_target_window(window_info)
                
                # Call callback to update input handler
                if self.update_target_window_callback:
                    self.update_target_window_callback()
                
                self._update_status(f"Positioned in boundary: {window_info.title}")
                
                # Setup focus tracking to keep window raised
                if self.master:
                    self._setup_focus_tracking()
            else:
                self._update_status(f"Failed to position: {window_info.title}")
                
        except Exception as e:
            print(f"Positioning error: {e}")
            self._update_status("Positioning failed")
    
    def _calculate_companion_boundary(self) -> tuple:
        """
        Calculate the boundary position in screen coordinates.
        
        Returns:
            Tuple of (x, y, width, height) or None if boundary frame not ready
        """
        try:
            if not hasattr(self, 'boundary_indicator'):
                return None
            
            # Force update to get accurate geometry
            self.boundary_indicator.update_idletasks()
            
            # Get the screen position of the boundary indicator
            x = self.boundary_indicator.winfo_rootx()
            y = self.boundary_indicator.winfo_rooty()
            width = self.companion_boundary['width']
            height = self.companion_boundary['height']
            
            # Verify the boundary fits within the screen
            # Add some validation to ensure we have valid coordinates
            if x <= 0 or y <= 0:
                print(f"Warning: Boundary has invalid position ({x}, {y}), waiting for frame to be ready")
                # Try to update again
                self.master.update()
                x = self.boundary_indicator.winfo_rootx()
                y = self.boundary_indicator.winfo_rooty()
            
            print(f"Calculated companion boundary: ({x}, {y}, {width}, {height})")
            return (x, y, width, height)
            
        except Exception as e:
            print(f"Error calculating boundary: {e}")
            return None
    
    def _setup_focus_tracking(self):
        """Setup focus tracking to raise companion window when main window is focused."""
        if hasattr(self, '_focus_tracking_setup'):
            return  # Already setup
        
        self._focus_tracking_setup = True
        
        # Bind focus events to raise the companion window
        def on_focus_in(event):
            if self.selected_window and self.is_window_managed:
                try:
                    self.window_manager.raise_window(self.selected_window)
                except Exception as e:
                    print(f"Error raising window on focus: {e}")
        
        # Bind configure events to reposition window when main window moves
        def on_configure(event):
            if self.selected_window and self.is_window_managed:
                # Only reposition if this is a move/resize of the root window
                if event.widget == self.master:
                    self._reposition_companion_window()
        
        if self.master:
            self.master.bind("<FocusIn>", on_focus_in)
            self.master.bind("<Configure>", on_configure)
            print("Focus tracking and reposition on move enabled for companion window")
    
    def _reposition_companion_window(self):
        """Reposition the companion window to match the current boundary."""
        if not self.selected_window or not self.is_window_managed:
            return
        
        try:
            # Recalculate boundary
            boundary = self._calculate_companion_boundary()
            
            if boundary:
                # Reposition the window
                self.window_manager.position_window_in_boundary(self.selected_window, boundary)
                
                # Update screenshot region with new position
                self._update_screenshot_region(boundary)
                
                print("Repositioned companion window after main window moved")
        except Exception as e:
            print(f"Error repositioning companion window: {e}")
    
    def _update_screenshot_region(self, boundary: tuple):
        """Update the screenshot region in config to match the companion boundary.
        
        Args:
            boundary: Tuple of (x, y, width, height)
        """
        try:
            x, y, width, height = boundary
            
            # EAFP: Just try to use it - more Pythonic than hasattr checks
            controller = self.app.shiny_hunter_controller
            
            # Update the config values
            controller.config['screenshot_region']['x'] = x
            controller.config['screenshot_region']['y'] = y
            controller.config['screenshot_region']['width'] = width
            controller.config['screenshot_region']['height'] = height
            
            print(f"Updated screenshot region: x={x}, y={y}, width={width}, height={height}")
            
            # Try to update UI fields if they exist
            try:
                config_frame = controller.config_frame
                config_frame.x_entry.delete(0, tk.END)
                config_frame.x_entry.insert(0, str(x))
                config_frame.y_entry.delete(0, tk.END)
                config_frame.y_entry.insert(0, str(y))
                config_frame.width_entry.delete(0, tk.END)
                config_frame.width_entry.insert(0, str(width))
                config_frame.height_entry.delete(0, tk.END)
                config_frame.height_entry.insert(0, str(height))
                
                print("Updated config UI fields with screenshot region")
            except AttributeError:
                # Config UI doesn't exist or doesn't have these fields - that's okay
                print("Config UI not available for update")
                    
        except (AttributeError, KeyError, TypeError) as e:
            print(f"Error updating screenshot region: {e}")
    
    def _update_boundary_indicator(self, active: bool = False, window_title: str = ""):
        """Update the boundary indicator visual state."""
        if not hasattr(self, 'boundary_indicator'):
            return
        
        try:
            if active:
                # Change appearance to indicate active window
                self.boundary_indicator.config(bg="#1a3a1a", relief='solid', borderwidth=3)
                info_text = (f"Companion Window Active:\n{window_title}\n"
                            f"({self.companion_boundary['width']}x{self.companion_boundary['height']})\n\n"
                            "Window positioned in this boundary\n"
                            "and will stay above when focused")
                self.boundary_label.config(
                    text=info_text,
                    foreground="#00ff00"
                )
            else:
                # Restore default appearance
                self.boundary_indicator.config(bg="#2a2b2a", relief='sunken', borderwidth=2)
                info_text = ("Selected window will be positioned\n"
                            "within this boundary area\n"
                            f"({self.companion_boundary['width']}x{self.companion_boundary['height']})")
                self.boundary_label.config(
                    text=info_text,
                    foreground="#ffffff"
                )
        except Exception as e:
            print(f"Error updating boundary indicator: {e}")
    
    def _focus_window(self):
        """Focus and raise the selected window."""
        window_info = self._get_selected_window()
        if not window_info:
            self._update_status("No window selected")
            return
        
        try:
            # First raise the window above others
            raise_success = self.window_manager.raise_window(window_info)
            
            # Then focus it
            focus_success = self.window_manager.focus_window(window_info)
            
            if raise_success and focus_success:
                self._update_status(f"Focused and raised: {window_info.title}")
            elif focus_success:
                self._update_status(f"Focused: {window_info.title}")
            else:
                self._update_status(f"Failed to focus: {window_info.title}")
                
        except Exception as e:
            print(f"Focus error: {e}")
            self._update_status("Focus failed")
    
    def _release_window(self):
        """Release the companion window from boundary management."""
        if not self.selected_window or not self.is_window_managed:
            self._update_status("No window to release")
            return
        
        try:
            # Just mark as no longer managed
            released_title = self.selected_window.title
            self.selected_window = None
            self.is_window_managed = False
            
            # Update visual indicator
            self._update_boundary_indicator(active=False)
            
            # Update button states
            if hasattr(self, 'position_button'):
                self.position_button.config(state="normal")
            if hasattr(self, 'release_button'):
                self.release_button.config(state="disabled")
            
            # Clear the target window in input handler
            if self.update_target_window_callback:
                self.update_target_window_callback()
            
            self._update_status(f"Released: {released_title}")
            
        except Exception as e:
            print(f"Release error: {e}")
            self._update_status("Release failed")
    
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
                elif self.embedding_mode == EmbeddingMode.COMPANION:
                    # For companion mode, just update the indicator
                    self._update_boundary_indicator(active=False)
                    # Optionally restore window to original position/size
                    # (currently we just leave it where it is)
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
    
    def get_selected_window_info(self) -> Optional[WindowInfo]:
        """Get the currently selected/managed window info."""
        return self.selected_window if self.is_window_managed else None
