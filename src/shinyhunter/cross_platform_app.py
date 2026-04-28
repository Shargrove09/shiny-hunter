"""
Cross-platform application frame for embedding or managing external windows.

This module replaces the Windows-specific embedded_app.py with a cross-platform solution
that adapts its functionality based on the available window management capabilities.
"""

import tkinter as tk
import customtkinter as ctk
from typing import Optional, List
from styles import BTN_STANDARD, FONT_BOLD, FONT_SMALL, DROPDOWN
from config import ConfigManager
from window_management import WindowManagerFactory, WindowManager, WindowInfo, EmbeddingMode


class CrossPlatformAppFrame(ctk.CTkFrame):
    """Cross-platform application frame with adaptive window management."""

    def __init__(self, right_frame, app, container_frame, master=None):
        ctk.CTkFrame.__init__(self, container_frame)

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
        self.update_target_window_callback = None

        # UI variables
        self.dropdown_var = tk.StringVar()
        self.status_var = tk.StringVar()

        # Initialize UI
        self._create_ui()
        self._update_status_display()

        # Setup cleanup
        if master:
            master.protocol("WM_DELETE_WINDOW", self._cleanup_on_close)

        print(f"CrossPlatformAppFrame initialized with {self.embedding_mode.value} mode")

    def _create_ui(self):
        """Create the user interface adapted to current capabilities."""
        self.grid(row=0, column=1, sticky="nsew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._create_status_display()
        self._create_window_selection()
        self._create_action_buttons()
        self._create_input_buttons()

        if self.embedding_mode != EmbeddingMode.MANUAL:
            self._create_window_area()

    def _create_status_display(self):
        """Create status display showing current platform and capabilities."""
        status_frame = ctk.CTkFrame(self.right_frame)
        status_frame.grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky="ew")

        ctk.CTkLabel(status_frame, text="Window Management Status", font=FONT_BOLD).pack(
            anchor="w", padx=10, pady=(8, 0)
        )

        platform_text = f"Platform: {self.window_manager.platform if self.window_manager else 'Unknown'}"
        ctk.CTkLabel(status_frame, text=platform_text, font=FONT_SMALL).pack(anchor="w", padx=10)

        mode_text = f"Mode: {self.embedding_mode.value.replace('_', ' ').title()}"
        ctk.CTkLabel(status_frame, text=mode_text, font=FONT_SMALL).pack(anchor="w", padx=10)

        self.status_label = ctk.CTkLabel(status_frame, textvariable=self.status_var, font=FONT_SMALL)
        self.status_label.pack(anchor="w", padx=10, pady=(0, 8))

    def _create_window_selection(self):
        """Create window selection dropdown."""
        ctk.CTkLabel(self.right_frame, text="Select Game Window", font=FONT_SMALL).grid(
            row=1, column=0, columnspan=2, pady=(0, 5)
        )

        self.dropdown = ctk.CTkComboBox(
            self.right_frame,
            variable=self.dropdown_var,
            state="readonly",
            **DROPDOWN,
        )
        self.dropdown.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        self.refresh_button = ctk.CTkButton(
            self.right_frame,
            text="Refresh Windows",
            command=self._refresh_windows,
            **BTN_STANDARD,
        )
        self.refresh_button.grid(row=3, column=0, columnspan=2, pady=(0, 10))

        self._refresh_windows()

    def _create_action_buttons(self):
        """Create action buttons based on available capabilities."""
        button_row = 4

        if self.capabilities.get('window_embedding', False):
            self.launch_button = ctk.CTkButton(
                self.right_frame,
                text="Embed Window",
                command=self._embed_window,
                **BTN_STANDARD,
            )
            self.launch_button.grid(row=button_row, column=0, columnspan=2, pady=(0, 5))

            self.unembed_button = ctk.CTkButton(
                self.right_frame,
                text="Unembed Window",
                command=self._unembed_window,
                state="disabled",
                **BTN_STANDARD,
            )
            self.unembed_button.grid(row=button_row + 1, column=0, columnspan=2, pady=(0, 10))

        elif self.capabilities.get('window_positioning', False):
            self.position_button = ctk.CTkButton(
                self.right_frame,
                text="Position in Boundary",
                command=self._position_window,
                **BTN_STANDARD,
            )
            self.position_button.grid(row=button_row, column=0, columnspan=2, pady=(0, 5))

            self.release_button = ctk.CTkButton(
                self.right_frame,
                text="Release Window",
                command=self._release_window,
                state="disabled",
                **BTN_STANDARD,
            )
            self.release_button.grid(row=button_row + 1, column=0, columnspan=2, pady=(0, 5))

            self.focus_button = ctk.CTkButton(
                self.right_frame,
                text="Focus Window",
                command=self._focus_window,
                **BTN_STANDARD,
            )
            self.focus_button.grid(row=button_row + 2, column=0, columnspan=2, pady=(0, 10))

        else:
            ctk.CTkLabel(
                self.right_frame,
                text="Manual window management only.\nPlease arrange windows manually.",
                font=FONT_SMALL,
                justify="center",
            ).grid(row=button_row, column=0, columnspan=2, pady=10)

    def _create_input_buttons(self):
        """Create buttons for simulating user input."""
        input_frame = ctk.CTkFrame(self.right_frame)
        input_frame.grid(row=7, column=0, columnspan=2, pady=(10, 0), sticky="ew")

        ctk.CTkLabel(input_frame, text="Input Simulation", font=FONT_BOLD).pack(
            anchor="w", padx=10, pady=(8, 0)
        )

        ctk.CTkButton(
            input_frame, text="Press 'X'", command=self._press_x_key, **BTN_STANDARD
        ).pack(fill='x', padx=10, pady=2)

        ctk.CTkButton(
            input_frame, text="Press 'Z'", command=self._press_z_key, **BTN_STANDARD
        ).pack(fill='x', padx=10, pady=2)

        ctk.CTkButton(
            input_frame, text="Restart Sequence", command=self._execute_restart_sequence, **BTN_STANDARD
        ).pack(fill='x', padx=10, pady=(2, 8))

    def _press_x_key(self):
        self.app.shiny_hunter_controller.input_handler._press_key('x')

    def _press_z_key(self):
        self.app.shiny_hunter_controller.input_handler._press_key('z')

    def _execute_restart_sequence(self):
        self.app.shiny_hunter_controller.input_handler.restart_sequence()

    def _create_window_area(self):
        """Create the area for embedding or positioning the window."""
        if self.embedding_mode == EmbeddingMode.FULL_EMBED:
            self.embed_frame = ctk.CTkFrame(self)
            self.embed_frame.grid(column=1, padx=10, pady=10, sticky="nsew")
            self.embed_frame.bind("<Configure>", self._on_embed_resize)

        elif self.embedding_mode == EmbeddingMode.COMPANION:
            self.companion_frame = ctk.CTkFrame(self)
            self.companion_frame.grid(column=1, padx=10, pady=10, sticky="nsew")
            self.companion_frame.grid_rowconfigure(0, weight=1)
            self.companion_frame.grid_columnconfigure(0, weight=1)

            self.companion_boundary = {'width': 1280, 'height': 960, 'padding': 10}

            self.boundary_indicator = ctk.CTkFrame(
                self.companion_frame,
                fg_color="#2a2b2a",
                border_width=2,
            )
            self.boundary_indicator.pack(fill='both', expand=True)
            self.boundary_indicator.bind("<Configure>", self._on_boundary_resize)

            info_text = (
                "Selected window will be positioned\n"
                "within this boundary area\n"
                f"({self.companion_boundary['width']}x{self.companion_boundary['height']})"
            )
            self.boundary_label = ctk.CTkLabel(
                self.boundary_indicator,
                text=info_text,
                font=FONT_SMALL,
                justify="center",
                fg_color="transparent",
            )
            self.boundary_label.place(relx=0.5, rely=0.5, anchor="center")

    def _on_boundary_resize(self, event):
        """Update companion_boundary when the indicator frame is resized by Tkinter layout."""
        self.companion_boundary['width'] = event.width
        self.companion_boundary['height'] = event.height

        if hasattr(self, 'boundary_label'):
            if self.is_window_managed and self.selected_window:
                info_text = (
                    f"Companion Window Active:\n{self.selected_window.title}\n"
                    f"({event.width}x{event.height})\n\n"
                    "Window positioned in this boundary\n"
                    "and will stay above when focused"
                )
            else:
                info_text = (
                    "Selected window will be positioned\n"
                    "within this boundary area\n"
                    f"({event.width}x{event.height})"
                )
            self.boundary_label.configure(text=info_text)

        # Debounce: only reposition external window after resize settles (150ms)
        if self.is_window_managed and self.selected_window:
            if hasattr(self, '_boundary_resize_after_id'):
                self.master.after_cancel(self._boundary_resize_after_id)
            self._boundary_resize_after_id = self.master.after(
                150, self._reposition_companion_window
            )

    def _on_embed_resize(self, event):
        """Resize the embedded window when the embed frame is resized by Tkinter layout."""
        if self.selected_window and self.is_window_managed:
            if hasattr(self, '_embed_resize_after_id'):
                self.master.after_cancel(self._embed_resize_after_id)
            self._embed_resize_after_id = self.master.after(
                150,
                lambda: self._resize_embedded_window(event.width, event.height)
            )

    def _resize_embedded_window(self, width: int, height: int):
        """Call window manager to resize the embedded window to match the frame."""
        try:
            self.window_manager.resize_window(self.selected_window, width, height)
        except Exception as e:
            print(f"Error resizing embedded window: {e}")

    def _refresh_windows(self):
        """Refresh the list of available windows."""
        if not self.window_manager:
            self.dropdown.configure(values=["No window manager available"])
            return

        try:
            windows = self.window_manager.get_all_windows()

            window_options = []
            for window in windows:
                if window.title and len(window.title.strip()) > 0:
                    if window.pid > 0:
                        option = f"{window.title} [PID: {window.pid}]"
                    else:
                        option = window.title
                    window_options.append(option)

            self.dropdown.configure(values=window_options if window_options else ["No windows found"])
            self._update_status("Window list refreshed")

        except Exception as e:
            print(f"Error refreshing windows: {e}")
            self.dropdown.configure(values=["Error loading windows"])
            self._update_status("Error refreshing windows")

    def _get_selected_window(self) -> Optional[WindowInfo]:
        """Get the currently selected window info."""
        selection = self.dropdown_var.get()
        if not selection or not self.window_manager:
            return None

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

                self.launch_button.configure(state="disabled")
                self.unembed_button.configure(state="normal")

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

                self.launch_button.configure(state="normal")
                self.unembed_button.configure(state="disabled")
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
            boundary = self._calculate_companion_boundary()

            if boundary is None:
                self._update_status("Boundary not available")
                return

            success = self.window_manager.position_window_in_boundary(window_info, boundary)

            if success:
                self.selected_window = window_info
                self.is_window_managed = True

                self.window_manager.raise_window(window_info)
                self._update_screenshot_region(boundary)
                self._update_boundary_indicator(active=True, window_title=window_info.title)

                if hasattr(self, 'position_button'):
                    self.position_button.configure(state="disabled")
                if hasattr(self, 'release_button'):
                    self.release_button.configure(state="normal")

                if hasattr(self.app, 'set_target_window'):
                    self.app.set_target_window(window_info)

                if self.update_target_window_callback:
                    self.update_target_window_callback()

                self._update_status(f"Positioned in boundary: {window_info.title}")

                if self.master:
                    self._setup_focus_tracking()
            else:
                self._update_status(f"Failed to position: {window_info.title}")

        except Exception as e:
            print(f"Positioning error: {e}")
            self._update_status("Positioning failed")

    def _calculate_companion_boundary(self) -> tuple:
        try:
            if not hasattr(self, 'boundary_indicator'):
                return None

            self.boundary_indicator.update_idletasks()

            x = self.boundary_indicator.winfo_rootx()
            y = self.boundary_indicator.winfo_rooty()
            width = self.companion_boundary['width']
            height = self.companion_boundary['height']

            if x <= 0 or y <= 0:
                print(f"Warning: Boundary has invalid position ({x}, {y}), waiting for frame to be ready")
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
            return

        self._focus_tracking_setup = True

        def on_focus_in(event):
            if self.selected_window and self.is_window_managed:
                try:
                    self.window_manager.raise_window(self.selected_window)
                except Exception as e:
                    print(f"Error raising window on focus: {e}")

        def on_configure(event):
            if self.selected_window and self.is_window_managed:
                if event.widget == self.master:
                    self._reposition_companion_window()

        if self.master:
            self.master.bind("<FocusIn>", on_focus_in)
            self.master.bind("<Configure>", on_configure)
            print("Focus tracking and reposition on move enabled for companion window")

    def _reposition_companion_window(self):
        if not self.selected_window or not self.is_window_managed:
            return

        try:
            boundary = self._calculate_companion_boundary()
            if boundary:
                self.window_manager.position_window_in_boundary(self.selected_window, boundary)
                self._update_screenshot_region(boundary)
                print("Repositioned companion window after main window moved")
        except Exception as e:
            print(f"Error repositioning companion window: {e}")

    def _update_screenshot_region(self, boundary: tuple):
        try:
            x, y, width, height = boundary

            controller = self.app.shiny_hunter_controller

            controller.config.screenshot_region_x = x
            controller.config.screenshot_region_y = y
            controller.config.emulator_width = width
            controller.config.emulator_height = height
            ConfigManager().save_config()

            print(f"Updated screenshot region: x={x}, y={y}, width={width}, height={height}")

            try:
                config_frame = controller.config_frame
                config_frame.x_entry.delete(0, 'end')
                config_frame.x_entry.insert(0, str(x))
                config_frame.y_entry.delete(0, 'end')
                config_frame.y_entry.insert(0, str(y))
                config_frame.width_entry.delete(0, 'end')
                config_frame.width_entry.insert(0, str(width))
                config_frame.height_entry.delete(0, 'end')
                config_frame.height_entry.insert(0, str(height))
                print("Updated config UI fields with screenshot region")
            except AttributeError:
                print("Config UI not available for update")

        except (AttributeError, KeyError, TypeError) as e:
            print(f"Error updating screenshot region: {e}")

    def _update_boundary_indicator(self, active: bool = False, window_title: str = ""):
        if not hasattr(self, 'boundary_indicator'):
            return

        try:
            if active:
                self.boundary_indicator.configure(fg_color="#1a3a1a", border_width=3)
                info_text = (
                    f"Companion Window Active:\n{window_title}\n"
                    f"({self.companion_boundary['width']}x{self.companion_boundary['height']})\n\n"
                    "Window positioned in this boundary\n"
                    "and will stay above when focused"
                )
                self.boundary_label.configure(text=info_text, text_color="#00ff00")
            else:
                self.boundary_indicator.configure(fg_color="#2a2b2a", border_width=2)
                info_text = (
                    "Selected window will be positioned\n"
                    "within this boundary area\n"
                    f"({self.companion_boundary['width']}x{self.companion_boundary['height']})"
                )
                self.boundary_label.configure(text=info_text, text_color="#ffffff")
        except Exception as e:
            print(f"Error updating boundary indicator: {e}")

    def _focus_window(self):
        window_info = self._get_selected_window()
        if not window_info:
            self._update_status("No window selected")
            return

        try:
            raise_success = self.window_manager.raise_window(window_info)
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
        if not self.selected_window or not self.is_window_managed:
            self._update_status("No window to release")
            return

        try:
            released_title = self.selected_window.title
            self.selected_window = None
            self.is_window_managed = False

            self._update_boundary_indicator(active=False)

            if hasattr(self, 'position_button'):
                self.position_button.configure(state="normal")
            if hasattr(self, 'release_button'):
                self.release_button.configure(state="disabled")

            if self.update_target_window_callback:
                self.update_target_window_callback()

            self._update_status(f"Released: {released_title}")

        except Exception as e:
            print(f"Release error: {e}")
            self._update_status("Release failed")

    def _update_status(self, message: str):
        self.status_var.set(f"Status: {message}")
        print(f"Window Manager: {message}")

    def _update_status_display(self):
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
        print("Cleaning up window management...")

        if self.is_window_managed and self.selected_window:
            try:
                if self.embedding_mode == EmbeddingMode.FULL_EMBED:
                    self.window_manager.unembed_window(self.selected_window)
                elif self.embedding_mode == EmbeddingMode.COMPANION:
                    self._update_boundary_indicator(active=False)
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
