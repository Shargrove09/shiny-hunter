import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog
from threading import Thread
from PIL import Image, ImageTk
import os
from styles import BTN_START, BTN_STANDARD, BTN_SET, DROPDOWN, FONT_BOLD, FONT_SMALL
from screenshot_manager import ScreenshotManager
from config import ConfigManager


class ShinyHuntGUI:
    def __init__(self, root, input_thread, controller, handle_start, handle_pause, handle_stop):
        self.input_handler = controller.input_handler

        # Store controller reference
        self.controller = controller

        # Create a tkinter variable for displaying the count
        self.count_var = tk.IntVar(value=0)
        self.calibration_normal_samples = []
        self.current_input_var = tk.StringVar(value="Now Pressing: —")
        self._input_clear_after_id = None
        self._count_update_after_id = None

        ### Scaling ###
        root.grid_columnconfigure(0, weight=0)
        root.grid_columnconfigure(1, weight=6)
        root.grid_columnconfigure(2, weight=1)

        root.grid_rowconfigure(0, weight=3)  # main content row (frames + game view)
        root.grid_rowconfigure(4, weight=1)  # log textbox row

        self.paused = False
        self.stopped = False

        self.input_thread = input_thread
        self.handle_start = handle_start
        self.handle_pause = handle_pause
        self.handle_stop = handle_stop

        # Root Config
        self.root = root

        # Initialize Screenshot Manager
        self.screenshot_manager = ScreenshotManager()

        # Left Frame
        self.left_frame = ctk.CTkScrollableFrame(root, width=200)
        self.left_frame.grid(row=0, column=0, padx=20, pady=40, sticky="nsew")
        self.left_frame.grid_columnconfigure(0, weight=1)

        # Calibration Frame

        # Right Frame
        self.right_frame = ctk.CTkScrollableFrame(root, width=200)
        self.right_frame.grid(row=0, column=2, ipadx=10, padx=20, pady=40, sticky="nsew")
        self.right_frame.grid_columnconfigure(0, weight=1)

        # Input indicator label
        self.input_indicator_label = ctk.CTkLabel(
            root,
            textvariable=self.current_input_var,
            font=FONT_BOLD,
        )
        self.input_indicator_label.grid(row=2, column=1)

        # Status Label
        self.status_label = ctk.CTkLabel(
            root,
            text="Press 'Start Hunt' to begin the shiny hunt.",
            font=FONT_BOLD,
        )
        self.status_label.grid(row=3, column=1)

        # Log Text Widget
        self.log_text = ctk.CTkTextbox(root, state='disabled')
        self.log_text.grid(row=4, column=1, padx=20, pady=20, sticky="nsew")

        ##################
        ### LEFT Frame ###
        ##################
        # Start Button
        self.start_button = ctk.CTkButton(
            self.left_frame, text="Start Hunt", command=self.on_start_hunt, **BTN_START)
        self.start_button.grid(row=2, column=0, pady=10, padx=10, sticky="ew")

        # Pause Button
        self.pause_button = ctk.CTkButton(
            self.left_frame, text="Pause Hunt", command=self.toggle_pause, **BTN_STANDARD)
        self.pause_button.grid(row=3, column=0, padx=10, sticky="ew")

        # Stop Button
        self.stop_button = ctk.CTkButton(
            self.left_frame, text="Stop Hunt", command=self.stop_hunt, **BTN_STANDARD)
        self.stop_button.grid(row=4, column=0, padx=10, sticky="ew")

        # Reset Counter
        self.reset_count = ctk.CTkLabel(
            self.left_frame, textvariable=self.count_var, font=FONT_BOLD)
        self.reset_count.grid(row=5, column=0, pady=(10, 0))

        # Settings Button
        self.settings_button = ctk.CTkButton(
            self.left_frame, text="Settings", command=self.open_settings, **BTN_STANDARD)
        self.settings_button.grid(row=6, column=0, pady=10, padx=10, sticky="ew")

        # Save Encounter Template Button
        ctk.CTkButton(
            self.left_frame,
            text="Save Encounter Template",
            command=self._save_encounter_template,
            **BTN_STANDARD
        ).grid(row=7, column=0, pady=10, padx=10, sticky="ew")

        # Calibration Section
        self._create_calibration_section(root)

        restart_button = ctk.CTkButton(
            self.right_frame,
            text="Manual Reset",
            command=lambda: self.input_handler.restart_sequence(),
            **BTN_STANDARD
        )
        restart_button.grid(row=6, column=0, padx=10, sticky="ew")

        # Hook telemetry from input handler to live UI indicator
        self.input_handler.set_input_event_callback(self._on_input_event)

        # Keep counter label synchronized with controller state
        self._start_count_sync()

    def _create_calibration_section(self, root):
        """Create the threshold calibration section in the left frame."""
        calibration_frame = ctk.CTkFrame(self.left_frame)
        calibration_frame.grid(row=4, column=0, pady=(20, 0), sticky="nsew")

        ctk.CTkLabel(calibration_frame, text="Threshold Calibration", font=FONT_BOLD).pack(
            anchor="w", padx=10, pady=(8, 0)
        )

        # Calibration mode toggle
        self.calibration_mode_var = tk.BooleanVar(value=False)
        calibration_toggle = ctk.CTkCheckBox(
            calibration_frame,
            text="Calibration Mode",
            variable=self.calibration_mode_var,
            command=self._toggle_calibration_mode,
        )
        calibration_toggle.pack(anchor="w", padx=10, pady=(6, 10))

        # Info label
        self.calibration_info = ctk.CTkLabel(
            calibration_frame,
            text="1. Capture reference (normal)\n2. View correlation\n3. Set threshold so normal stays above it",
            font=FONT_SMALL,
            justify="left",
        )
        self.calibration_info.pack(anchor="w", padx=10, pady=(0, 10))

        # Capture reference button
        self.capture_reference_button = ctk.CTkButton(
            calibration_frame,
            text="Capture Reference",
            command=self._capture_calibration_reference,
            state='disabled',
            **BTN_STANDARD,
        )
        self.capture_reference_button.pack(fill='x', padx=10, pady=(0, 5))

        self.view_correlation_button = ctk.CTkButton(
            calibration_frame,
            text="View Correlation",
            command=self._view_correlation,
            state='disabled',
            **BTN_STANDARD,
        )
        self.view_correlation_button.pack(fill='x', padx=10, pady=(0, 5))

        self.record_sample_button = ctk.CTkButton(
            calibration_frame,
            text="Record Normal Sample",
            command=self._record_normal_sample,
            state='disabled',
            **BTN_STANDARD,
        )
        self.record_sample_button.pack(fill='x', padx=10, pady=(0, 5))

        self.suggest_threshold_button = ctk.CTkButton(
            calibration_frame,
            text="Suggest Threshold",
            command=self._suggest_threshold_from_samples,
            state='disabled',
            **BTN_STANDARD,
        )
        self.suggest_threshold_button.pack(fill='x', padx=10, pady=(0, 5))

        self.sample_count_label = ctk.CTkLabel(
            calibration_frame,
            text="Normal samples: 0",
            font=FONT_SMALL,
        )
        self.sample_count_label.pack(anchor="w", padx=10, pady=(0, 5))

        # Separator
        ctk.CTkFrame(calibration_frame, height=2, fg_color="gray40").pack(
            fill='x', padx=10, pady=(10, 10)
        )

        # Threshold input section
        ctk.CTkLabel(calibration_frame, text="Correlation Threshold:", font=FONT_SMALL).pack(
            anchor="w", padx=10, pady=(0, 5)
        )

        threshold_frame = ctk.CTkFrame(calibration_frame, fg_color="transparent")
        threshold_frame.pack(fill='x', padx=10, pady=(0, 5))

        self.threshold_entry = ctk.CTkEntry(threshold_frame, width=120)
        self.threshold_entry.pack(side='left', expand=True, fill='x')
        self.threshold_entry.insert(0, str(self.controller.config.correlation_threshold))

        ctk.CTkButton(
            threshold_frame,
            text="Set",
            command=self._update_threshold,
            **BTN_SET,
        ).pack(side='left', padx=(5, 0))

        # Tolerance input section
        ctk.CTkLabel(calibration_frame, text="Correlation Tolerance:", font=FONT_SMALL).pack(
            anchor="w", padx=10, pady=(5, 5)
        )

        tolerance_frame = ctk.CTkFrame(calibration_frame, fg_color="transparent")
        tolerance_frame.pack(fill='x', padx=10, pady=(0, 5))

        self.tolerance_entry = ctk.CTkEntry(tolerance_frame, width=120)
        self.tolerance_entry.pack(side='left', expand=True, fill='x')
        self.tolerance_entry.insert(0, str(self.controller.config.correlation_tolerance))

        ctk.CTkButton(
            tolerance_frame,
            text="Set",
            command=self._update_tolerance,
            **BTN_SET,
        ).pack(side='left', padx=(5, 0))

        # Current threshold display
        self.threshold_display = ctk.CTkLabel(
            calibration_frame,
            text=f"Active: {self.controller.config.correlation_threshold:.4f}",
            font=(*FONT_SMALL[:1], FONT_SMALL[1], "bold"),
        )
        self.threshold_display.pack(anchor="w", padx=10, pady=(10, 8))

    def _toggle_calibration_mode(self):
        """Toggle calibration mode on/off."""
        config = ConfigManager().get_config()
        config.calibration_mode = self.calibration_mode_var.get()

        if config.calibration_mode:
            self.capture_reference_button.configure(state='normal')
            self.start_button.configure(state='disabled')
            self.calibration_info.configure(
                text="Calibration Mode Active!\nNavigate to encounter screen,\nthen capture reference.",
                text_color="orange",
            )
            self.log_message("Calibration mode enabled. Hunt disabled.")
        else:
            self.capture_reference_button.configure(state='disabled')
            self.view_correlation_button.configure(state='disabled')
            self.record_sample_button.configure(state='disabled')
            self.suggest_threshold_button.configure(state='disabled')
            self.start_button.configure(state='normal')
            self.calibration_info.configure(
                text="1. Capture reference (normal)\n2. View correlation\n3. Set threshold so normal stays above it",
                text_color=ctk.ThemeManager.theme["CTkLabel"]["text_color"],
            )
            self.log_message("Calibration mode disabled. Hunt enabled.")

    def _capture_calibration_reference(self):
        """Capture a reference screenshot for calibration."""
        import time
        config = ConfigManager().get_config()

        if hasattr(self, 'cross_platform_app_frame'):
            window_info = self.cross_platform_app_frame.get_selected_window_info()
            if window_info:
                try:
                    window_manager = self.cross_platform_app_frame.window_manager
                    if window_manager:
                        self.log_message("Focusing game window...")
                        window_manager.raise_window(window_info)
                        window_manager.focus_window(window_info)
                        time.sleep(0.5)
                except Exception as e:
                    self.log_message(f"Warning: Could not focus window: {e}")
            else:
                self.log_message("Warning: No window selected. Screenshot may not capture game window.")

        screenshot_path = self.screenshot_manager.take_screenshot('calibration_reference.png')
        self.calibration_normal_samples.clear()
        self.sample_count_label.configure(text="Normal samples: 0")

        self.log_message(f"Calibration reference captured: {screenshot_path}")
        self.log_message("Now record normal samples, then use Suggest Threshold.")

        self.view_correlation_button.configure(state='normal')
        self.record_sample_button.configure(state='normal')
        self.suggest_threshold_button.configure(state='disabled')

    def _view_correlation(self):
        """View the correlation between reference and current screen for calibration purposes."""
        import time
        config = ConfigManager().get_config()

        if hasattr(self, 'cross_platform_app_frame'):
            window_info = self.cross_platform_app_frame.get_selected_window_info()
            if window_info:
                try:
                    window_manager = self.cross_platform_app_frame.window_manager
                    if window_manager:
                        self.log_message("Focusing game window...")
                        window_manager.raise_window(window_info)
                        window_manager.focus_window(window_info)
                        time.sleep(0.5)
                except Exception as e:
                    self.log_message(f"Warning: Could not focus window: {e}")

        current_screenshot = self.screenshot_manager.take_screenshot('calibration_current.png')
        reference_path = config.calibration_reference_path

        if not os.path.exists(reference_path):
            self.log_message("Error: Calibration reference not found. Capture reference first.")
            return

        correlation = self.controller.image_processor.get_correlation(
            reference_path,
            current_screenshot
        )

        self.log_message("=" * 50)
        self.log_message(f"📊 Correlation with reference: {correlation:.6f}")
        self.log_message("=" * 50)

        if correlation > 0.85:
            self.log_message("✅ This appears to be a NORMAL encounter (high correlation)")
            self.log_message(f"💡 Keep threshold BELOW this value (example: ~{correlation * 0.75:.4f})")
        elif correlation < 0.60:
            self.log_message("🌟 This appears to be DIFFERENT from reference (possible shiny!)")
            self.log_message(f"💡 Keep threshold ABOVE this value to catch low-correlation encounters")
        else:
            self.log_message("⚠️  Mid-range correlation - hard to determine")
            self.log_message("💡 Try with more encounters to find a clear pattern")

        self.log_message("\n👉 Record normal samples and click Suggest Threshold, or set it manually in Settings")

    def _record_normal_sample(self):
        """Capture and store one normal encounter correlation sample."""
        config = ConfigManager().get_config()
        reference_path = config.calibration_reference_path

        if not os.path.exists(reference_path):
            self.log_message("Error: Calibration reference not found. Capture reference first.")
            return

        sample_index = len(self.calibration_normal_samples) + 1
        screenshot_name = f'calibration_sample_{sample_index}.png'
        current_screenshot = self.screenshot_manager.take_screenshot(screenshot_name)

        correlation = self.controller.image_processor.get_correlation(
            reference_path,
            current_screenshot
        )

        self.calibration_normal_samples.append(correlation)
        self.sample_count_label.configure(text=f"Normal samples: {len(self.calibration_normal_samples)}")
        self.suggest_threshold_button.configure(state='normal')

        self.log_message(f"✅ Recorded normal sample #{sample_index}: {correlation:.6f}")

    def _suggest_threshold_from_samples(self):
        """Suggest and apply threshold from recorded normal samples."""
        if not self.calibration_normal_samples:
            self.log_message("❌ No normal samples recorded yet.")
            return

        config_manager = ConfigManager()
        config = config_manager.get_config()

        suggested_threshold = self.controller.image_processor.suggest_threshold_from_normals(
            self.calibration_normal_samples,
            config.correlation_tolerance
        )

        config.correlation_threshold = suggested_threshold
        config_manager.save_config()

        self.threshold_entry.delete(0, 'end')
        self.threshold_entry.insert(0, f"{suggested_threshold:.6f}")
        self.threshold_display.configure(text=f"Active: {suggested_threshold:.4f}")

        sample_min = min(self.calibration_normal_samples)
        sample_max = max(self.calibration_normal_samples)
        self.log_message(
            f"✅ Suggested threshold applied: {suggested_threshold:.6f} "
            f"(from {len(self.calibration_normal_samples)} normal samples; range {sample_min:.6f}-{sample_max:.6f})"
        )

    def _update_threshold(self):
        """Update the correlation threshold from the calibration section."""
        try:
            new_threshold = float(self.threshold_entry.get())

            if new_threshold < 0 or new_threshold > 1:
                self.log_message("❌ Error: Threshold must be between 0 and 1")
                return

            config = ConfigManager().get_config()
            config.correlation_threshold = new_threshold
            ConfigManager().save_config()

            self.threshold_display.configure(text=f"Active: {new_threshold:.4f}")

            self.log_message(f"✅ Threshold updated to: {new_threshold:.4f}")
            self.log_message(f"   Values < {new_threshold:.4f} will be flagged as shiny")

        except ValueError:
            self.log_message("❌ Error: Invalid threshold value. Please enter a number.")

    def _update_tolerance(self):
        """Update the correlation tolerance from the calibration section."""
        try:
            new_tolerance = float(self.tolerance_entry.get())

            if new_tolerance < 0 or new_tolerance > 1:
                self.log_message("❌ Error: Tolerance must be between 0 and 1")
                return

            config = ConfigManager().get_config()
            config.correlation_tolerance = new_tolerance
            ConfigManager().save_config()

            self.log_message(f"✅ Tolerance updated to: {new_tolerance:.6f}")
            self.log_message("   Effective shiny cutoff = threshold - tolerance")

        except ValueError:
            self.log_message("❌ Error: Invalid tolerance value. Please enter a number.")

    def _on_input_event(self, event: dict):
        """Handle input telemetry events from InputHandler in a thread-safe way."""
        key_labels = {
            'x': 'A (X key)',
            'z': 'B (Z key)',
            'enter': 'Start (Enter)',
            'backspace': 'Select (Backspace)'
        }

        label = key_labels.get(event.get('key'), str(event.get('key')).upper())
        action = event.get('action', 'press').upper()
        self.root.after(0, self._update_input_indicator, f"Now Pressing: {label} [{action}]")

    def _update_input_indicator(self, text: str):
        """Update live input indicator and auto-clear shortly after."""
        self.current_input_var.set(text)
        if self._input_clear_after_id is not None:
            self.root.after_cancel(self._input_clear_after_id)
        self._input_clear_after_id = self.root.after(450, self._clear_input_indicator)

    def _clear_input_indicator(self):
        self.current_input_var.set("Now Pressing: —")
        self._input_clear_after_id = None

    ### Methods for GUI Interaction ###
    def log_message(self, message):
        self.log_text.configure(state='normal')
        self.log_text.insert('end', message + '\n')
        self.log_text.configure(state='disabled')
        self.log_text.see('end')

    def _save_encounter_template(self):
        path = self.screenshot_manager.take_screenshot("encounter_screen_template.png")
        self.log_message(f"Encounter template saved to: {path}")

    def on_start_hunt(self):
        config = ConfigManager().get_config()
        if not os.path.exists(config.encounter_template_path):
            self.log_message(
                "Warning: No encounter template set — pre-encounter screen guard is inactive. "
                "Navigate to the pre-encounter screen and press 'Save Encounter Template'."
            )

        self.status_label.configure(text="Mewtwo Hunt in progress...")
        self.start_button.configure(state="disabled")

        if hasattr(self, 'cross_platform_app_frame'):
            self.cross_platform_app_frame.set_window_position_locked(True)

        self.handle_start()
        self.input_thread.start()

    def update_count(self):
        if self.controller:
            self.count_var.set(self.controller.count)

    def _start_count_sync(self):
        """Start periodic synchronization of the GUI counter with the controller."""
        self._schedule_count_sync()

    def _schedule_count_sync(self):
        """Poll controller count and update Tk variable on the UI thread."""
        if not self.root.winfo_exists():
            return

        self.update_count()
        self._count_update_after_id = self.root.after(150, self._schedule_count_sync)

    def _stop_count_sync(self):
        """Stop periodic counter synchronization."""
        if self._count_update_after_id is not None and self.root.winfo_exists():
            self.root.after_cancel(self._count_update_after_id)
        self._count_update_after_id = None

    def toggle_pause(self):
        self.paused = not self.paused
        if self.paused:
            self.status_label.configure(text="Hunt Paused")
        else:
            self.status_label.configure(text="Mewtwo Hunt in progress...")
        self.handle_pause()

    def stop_hunt(self):
        print('Stopping Hunt')
        self.handle_stop()
        self.start_button.configure(state="normal")
        self.status_label.configure(text="Mewtwo Hunt stopped.")
        self.update_count()

        if hasattr(self, 'cross_platform_app_frame'):
            self.cross_platform_app_frame.set_window_position_locked(False)

    def open_settings(self):
        """Open a settings popup window."""
        config_manager = ConfigManager()
        config = config_manager.get_config()

        settings_window = ctk.CTkToplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("450x480")
        settings_window.resizable(False, False)

        # Modal behaviour
        settings_window.transient(self.root)
        settings_window.grab_set()

        # Center the window
        settings_window.update_idletasks()
        x = (settings_window.winfo_screenwidth() // 2) - (450 // 2)
        y = (settings_window.winfo_screenheight() // 2) - (480 // 2)
        settings_window.geometry(f"450x480+{x}+{y}")

        # Main frame
        main_frame = ctk.CTkScrollableFrame(settings_window)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)

        ctk.CTkLabel(main_frame, text="Settings", font=("Calibri", 16, "bold")).pack(pady=(0, 20))

        # Input delay settings
        delay_frame = ctk.CTkFrame(main_frame)
        delay_frame.pack(fill='x', pady=(0, 10))
        ctk.CTkLabel(delay_frame, text="Input Delays", font=FONT_BOLD).pack(anchor="w", padx=10, pady=(8, 0))

        ctk.CTkLabel(delay_frame, text="PyAutoGUI pause (s):").pack(anchor="w", padx=10)
        pyautogui_delay = ctk.CTkEntry(delay_frame)
        pyautogui_delay.pack(fill='x', padx=10, pady=(2, 8))
        pyautogui_delay.insert(0, str(config.pyautogui_pause))

        ctk.CTkLabel(delay_frame, text="Encounter delay (s):").pack(anchor="w", padx=10)
        encounter_delay = ctk.CTkEntry(delay_frame)
        encounter_delay.pack(fill='x', padx=10, pady=(2, 8))
        encounter_delay.insert(0, str(config.encounter_delay))

        ctk.CTkLabel(delay_frame, text="Restart delay (s):").pack(anchor="w", padx=10)
        restart_delay = ctk.CTkEntry(delay_frame)
        restart_delay.pack(fill='x', padx=10, pady=(2, 8))
        restart_delay.insert(0, str(config.restart_delay))

        # Detection settings
        detection_frame = ctk.CTkFrame(main_frame)
        detection_frame.pack(fill='x', pady=(0, 10))
        ctk.CTkLabel(detection_frame, text="Shiny Detection", font=FONT_BOLD).pack(anchor="w", padx=10, pady=(8, 0))

        ctk.CTkLabel(detection_frame, text="Correlation threshold:").pack(anchor="w", padx=10)
        correlation_threshold = ctk.CTkEntry(detection_frame)
        correlation_threshold.pack(fill='x', padx=10, pady=(2, 8))
        correlation_threshold.insert(0, str(config.correlation_threshold))

        ctk.CTkLabel(detection_frame, text="Max encounter retries:").pack(anchor="w", padx=10)
        max_retries = ctk.CTkEntry(detection_frame)
        max_retries.pack(fill='x', padx=10, pady=(2, 8))
        max_retries.insert(0, str(config.max_encounter_retries))

        # Safety settings
        safety_frame = ctk.CTkFrame(main_frame)
        safety_frame.pack(fill='x', pady=(0, 10))
        ctk.CTkLabel(safety_frame, text="Safety", font=FONT_BOLD).pack(anchor="w", padx=10, pady=(8, 0))

        failsafe_var = tk.BooleanVar(value=config.failsafe_enabled)
        ctk.CTkCheckBox(
            safety_frame, text="Enable PyAutoGUI failsafe", variable=failsafe_var
        ).pack(anchor="w", padx=10, pady=(4, 8))

        # Error label placeholder
        self._settings_error_label = None

        def save_settings():
            try:
                config.pyautogui_pause = float(pyautogui_delay.get())
                config.encounter_delay = float(encounter_delay.get())
                config.restart_delay = float(restart_delay.get())
                config.correlation_threshold = float(correlation_threshold.get())
                config.max_encounter_retries = int(max_retries.get())
                config.failsafe_enabled = failsafe_var.get()

                config_manager.save_config()
                self.log_message("Settings updated successfully!")
                settings_window.destroy()
            except ValueError:
                if self._settings_error_label is None or not self._settings_error_label.winfo_exists():
                    self._settings_error_label = ctk.CTkLabel(
                        button_frame, text="Invalid values entered!", text_color="red"
                    )
                    self._settings_error_label.pack(pady=(10, 0))

                    def safe_destroy():
                        if settings_window.winfo_exists() and self._settings_error_label.winfo_exists():
                            self._settings_error_label.destroy()
                            self._settings_error_label = None
                    settings_window.after(3000, safe_destroy)

        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill='x', pady=(10, 0))

        ctk.CTkButton(button_frame, text="Save", command=save_settings, **BTN_START).pack(
            side='right', padx=(10, 0)
        )
        ctk.CTkButton(button_frame, text="Cancel", command=settings_window.destroy, **BTN_STANDARD).pack(
            side='right'
        )

    def __del__(self):
        self._stop_count_sync()
