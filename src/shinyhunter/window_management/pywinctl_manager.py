"""
PyWinCtl-based window manager implementation.
"""

import subprocess
from typing import List, Optional, Any
from .base import WindowManager, WindowInfo, EmbeddingMode

# PyWinCtl imports with fallback
try:
    import pywinctl
    PYWINCTL_AVAILABLE = True
except ImportError:
    PYWINCTL_AVAILABLE = False

# Windows-specific imports for advanced embedding
try:
    import win32gui
    import win32con
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


class LinuxWindowHandle:
    """Wraps an X window ID and exposes a pywinctl-compatible interface.

    Uses xdotool for operations (works on both X11 and XWayland/Wayland).
    Falls back to wmctrl if xdotool is unavailable.
    """

    def __init__(self, xid: int):
        self._xid = xid
        self._hex = hex(xid)

    def _run(self, *args):
        try:
            subprocess.run(list(args), timeout=5)
        except FileNotFoundError:
            pass  # tool not installed — silently skip
        except Exception as e:
            print(f"Window operation error ({args[0]}): {e}")

    def activate(self):
        # xdotool works on XWayland; wmctrl -i -a is X11-only
        try:
            subprocess.run(['xdotool', 'windowactivate', '--sync', str(self._xid)], timeout=5)
        except FileNotFoundError:
            self._run('wmctrl', '-i', '-a', self._hex)

    def moveTo(self, x: int, y: int):
        try:
            subprocess.run(['xdotool', 'windowmove', str(self._xid), str(x), str(y)], timeout=5)
        except FileNotFoundError:
            self._run('wmctrl', '-i', '-r', self._hex, '-e', f'0,{x},{y},-1,-1')

    def resizeTo(self, w: int, h: int):
        try:
            subprocess.run(['xdotool', 'windowsize', str(self._xid), str(w), str(h)], timeout=5)
        except FileNotFoundError:
            self._run('wmctrl', '-i', '-r', self._hex, '-e', f'0,-1,-1,{w},{h}')

    def moveResizeTo(self, x: int, y: int, w: int, h: int):
        try:
            subprocess.run(['xdotool', 'windowmove', str(self._xid), str(x), str(y)], timeout=5)
            subprocess.run(['xdotool', 'windowsize', str(self._xid), str(w), str(h)], timeout=5)
        except FileNotFoundError:
            self._run('wmctrl', '-i', '-r', self._hex, '-e', f'0,{x},{y},{w},{h}')


class PyWinCtlManager(WindowManager):
    """Window manager using PyWinCtl for cross-platform functionality."""

    def __init__(self):
        super().__init__()

        if not PYWINCTL_AVAILABLE:
            raise ImportError("PyWinCtl is required but not available")

        self.use_win32_embedding = (self.platform == "Windows" and WIN32_AVAILABLE)
        self._embedded_windows = {}  # Track embedded windows

        print(f"PyWinCtlManager initialized for {self.platform}")
        if self.use_win32_embedding:
            print("Using Win32 API for advanced embedding features")

    def get_all_windows(self) -> List[WindowInfo]:
        """Get information about all available windows using PyWinCtl."""
        if self.platform == "Linux":
            return self._get_all_windows_linux()

        windows = []

        try:
            pywinctl_windows = pywinctl.getAllWindows()
        except Exception as e:
            print(f"Error enumerating windows: {e}")
            return windows

        print(f"Found {len(pywinctl_windows)} windows via PyWinCtl")

        for window in pywinctl_windows:
            try:
                if not window.title or not window.visible:
                    continue

                wid = getattr(window, 'wid', 0)

                windows.append(WindowInfo(
                    title=window.title,
                    handle=window,
                    pid=wid,
                    geometry=(window.left, window.top, window.width, window.height),
                    is_visible=window.visible,
                    is_minimized=window.isMinimized,
                ))

            except Exception:
                continue

        return windows

    def _get_all_windows_linux(self) -> List[WindowInfo]:
        """Enumerate windows on Linux using python-xlib (works on X11 and XWayland)."""
        windows = []
        try:
            from Xlib import X, display as xdisplay
            d = xdisplay.Display()
            root = d.screen().root

            # Walk root + one level of children.  Real application windows always
            # have WM_CLASS set; compositor internals (mutter guard, etc.) do not.
            seen_titles = set()

            def _check(win):
                try:
                    attrs = win.get_attributes()
                    if attrs.map_state != X.IsViewable:
                        return
                    wm_class = win.get_wm_class()
                    if not wm_class:
                        return
                    name = win.get_wm_name()
                    if not name or not isinstance(name, str):
                        return
                    title = name.strip()
                    if not title or title in seen_titles:
                        return
                    seen_titles.add(title)
                    windows.append(WindowInfo(
                        title=title,
                        handle=LinuxWindowHandle(win.id),
                        pid=0,
                        geometry=(0, 0, 0, 0),
                        is_visible=True,
                        is_minimized=False,
                    ))
                except Exception:
                    pass

            for child in root.query_tree().children:
                _check(child)
                try:
                    for grandchild in child.query_tree().children:
                        _check(grandchild)
                except Exception:
                    pass

            d.close()

        except ImportError:
            print("python-xlib not available — install with: pip install python-xlib")
        except Exception as e:
            print(f"Error enumerating windows via python-xlib: {e}")
        return windows

    def get_window_by_title(self, title: str) -> Optional[WindowInfo]:
        """Find a window by its title."""
        if self.platform == "Linux":
            for w in self._get_all_windows_linux():
                if w.title == title:
                    return w
            return None

        try:
            windows = pywinctl.getWindowsWithTitle(title)
            if windows:
                window = windows[0]
                wid = getattr(window, 'wid', 0)
                return WindowInfo(
                    title=window.title,
                    handle=window,
                    pid=wid,
                    geometry=(window.left, window.top, window.width, window.height),
                    is_visible=window.visible,
                    is_minimized=window.isMinimized,
                )
        except Exception as e:
            print(f"Error finding window by title '{title}': {e}")

        return None

    def get_window_by_handle(self, handle: Any) -> Optional[WindowInfo]:
        """Get window information by handle (PyWinCtl window object)."""
        try:
            if hasattr(handle, 'title'):
                wid = getattr(handle, 'wid', 0)
                return WindowInfo(
                    title=handle.title,
                    handle=handle,
                    pid=wid,
                    geometry=(handle.left, handle.top, handle.width, handle.height),
                    is_visible=handle.visible,
                    is_minimized=handle.isMinimized,
                )
        except Exception as e:
            print(f"Error getting window info by handle: {e}")

        return None

    def embed_window(self, window_info: WindowInfo, parent_widget: Any) -> bool:
        """Embed a window into a parent widget."""
        try:
            if self.use_win32_embedding:
                return self._embed_window_win32(window_info, parent_widget)
            else:
                return self._embed_window_fallback(window_info, parent_widget)
        except Exception as e:
            print(f"Error embedding window: {e}")
            return False

    def _embed_window_win32(self, window_info: WindowInfo, parent_widget: Any) -> bool:
        """Embed window using Win32 API for full functionality."""
        try:
            pywinctl_window = window_info.handle

            if hasattr(pywinctl_window, '_hWnd'):
                win32_handle = pywinctl_window._hWnd
            elif hasattr(pywinctl_window, 'getHandle'):
                win32_handle = pywinctl_window.getHandle()
            else:
                win32_handle = win32gui.FindWindow(None, window_info.title)

            if not win32_handle:
                print(f"Could not get Win32 handle for window: {window_info.title}")
                return False

            original_parent = win32gui.GetParent(win32_handle)
            parent_id = int(parent_widget.winfo_id())

            win32gui.SetParent(win32_handle, parent_id)

            parent_width = parent_widget.winfo_width()
            parent_height = parent_widget.winfo_height()

            win32gui.MoveWindow(win32_handle, 0, 0, parent_width, parent_height, True)
            win32gui.ShowWindow(win32_handle, win32con.SW_SHOW)

            self._embedded_windows[window_info.title] = {
                'win32_handle': win32_handle,
                'parent_widget': parent_widget,
                'original_parent': original_parent,
            }

            print(f"Successfully embedded window: {window_info.title}")
            return True

        except Exception as e:
            print(f"Win32 embedding failed: {e}")
            return False

    def _embed_window_fallback(self, window_info: WindowInfo, parent_widget: Any) -> bool:
        """Fallback embedding using positioning (for non-Windows platforms)."""
        try:
            parent_x = parent_widget.winfo_rootx()
            parent_y = parent_widget.winfo_rooty()
            parent_width = parent_widget.winfo_width()

            new_x = parent_x + parent_width + 10
            new_y = parent_y

            window_info.handle.moveTo(new_x, new_y)
            window_info.handle.activate()

            print(f"Positioned window beside parent: {window_info.title}")
            return True

        except Exception as e:
            print(f"Fallback positioning failed: {e}")
            return False

    def unembed_window(self, window_info: WindowInfo) -> bool:
        """Remove window embedding."""
        try:
            if self.use_win32_embedding and window_info.title in self._embedded_windows:
                return self._unembed_window_win32(window_info)
            else:
                return self._unembed_window_fallback(window_info)
        except Exception as e:
            print(f"Error unembedding window: {e}")
            return False

    def _unembed_window_win32(self, window_info: WindowInfo) -> bool:
        """Unembed window using Win32 API."""
        try:
            embedded_info = self._embedded_windows.get(window_info.title)
            if not embedded_info:
                return False

            win32_handle = embedded_info['win32_handle']
            original_parent = embedded_info.get('original_parent')

            if original_parent is not None and isinstance(original_parent, int):
                win32gui.SetParent(win32_handle, original_parent)
            else:
                win32gui.SetParent(win32_handle, 0)

            del self._embedded_windows[window_info.title]

            print(f"Successfully unembedded window: {window_info.title}")
            return True

        except Exception as e:
            print(f"Win32 unembedding failed: {e}")
            return False

    def _unembed_window_fallback(self, window_info: WindowInfo) -> bool:
        """Fallback unembedding (just activate the window)."""
        try:
            window_info.handle.activate()
            return True
        except Exception as e:
            print(f"Fallback unembedding failed: {e}")
            return False

    def position_window_beside(self, window_info: WindowInfo, reference_window: Any) -> bool:
        """Position window beside a reference window (legacy method)."""
        try:
            ref_x = reference_window.winfo_rootx()
            ref_y = reference_window.winfo_rooty()
            ref_width = reference_window.winfo_width()

            new_x = ref_x + ref_width + 20
            new_y = ref_y

            window_info.handle.moveTo(new_x, new_y)
            return True

        except Exception as e:
            print(f"Error positioning window: {e}")
            return False

    def position_window_in_boundary(self, window_info: WindowInfo, boundary: tuple) -> bool:
        try:
            x, y, width, height = boundary
            handle = window_info.handle
            if hasattr(handle, 'moveResizeTo'):
                handle.moveResizeTo(x, y, width, height)
            else:
                handle.resizeTo(width, height)
                handle.moveTo(x, y)
            print(f"Positioned window in boundary: ({x}, {y}, {width}, {height})")
            return True
        except Exception as e:
            print(f"Error positioning window in boundary: {e}")
            return False

    def raise_window(self, window_info: WindowInfo) -> bool:
        try:
            window_info.handle.activate()
            return True
        except Exception as e:
            print(f"Error raising window: {e}")
            return False

    def focus_window(self, window_info: WindowInfo) -> bool:
        try:
            window_info.handle.activate()
            return True
        except Exception as e:
            print(f"Error focusing window: {e}")
            return False

    def resize_window(self, window_info: WindowInfo, width: int, height: int) -> bool:
        try:
            if window_info.title in self._embedded_windows:
                win32_handle = self._embedded_windows[window_info.title]['win32_handle']
                win32gui.MoveWindow(win32_handle, 0, 0, width, height, True)
                return True
            window_info.handle.resizeTo(width, height)
            return True
        except Exception as e:
            print(f"Error resizing window: {e}")
            return False

    def move_window(self, window_info: WindowInfo, x: int, y: int) -> bool:
        try:
            window_info.handle.moveTo(x, y)
            return True
        except Exception as e:
            print(f"Error moving window: {e}")
            return False
