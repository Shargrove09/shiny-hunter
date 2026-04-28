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

# Fallback imports
    # pygetwindow raises NotImplementedError on unsupported platforms like Linux
    PYGETWINDOW_AVAILABLE = False


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

                window_info = WindowInfo(
                    title=window.title,
                    handle=window,
                    pid=wid,
                    geometry=(window.left, window.top, window.width, window.height),
                    is_visible=window.visible,
                    is_minimized=window.isMinimized,
                )
                windows.append(window_info)

            except Exception:
                continue

        return windows

    def _get_all_windows_linux(self) -> List[WindowInfo]:
        """Enumerate windows on Linux using wmctrl (avoids pywinctl KeyError issues)."""
        windows = []
        try:
            result = subprocess.run(
                ['wmctrl', '-l'], capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.strip().splitlines():
                parts = line.split(None, 3)
                if len(parts) < 4:
                    continue
                title = parts[3].strip()
                if not title or title == 'N/A':
                    continue
                try:
                    xid = int(parts[0], 16)
                except ValueError:
                    continue
                windows.append(WindowInfo(
                    title=title,
                    handle=xid,
                    pid=0,
                    geometry=(0, 0, 0, 0),
                    is_visible=True,
                    is_minimized=False,
                ))
        except FileNotFoundError:
            print("wmctrl not found — install with: sudo apt-get install wmctrl")
        except Exception as e:
            print(f"Error enumerating windows via wmctrl: {e}")
        return windows
    
    def _wmctrl(self, xid: int, *args) -> bool:
        """Run a wmctrl command targeting a window by X ID."""
        try:
            subprocess.run(
                ['wmctrl', '-i', '-r', hex(xid)] + list(args),
                check=True, timeout=5
            )
            return True
        except Exception as e:
            print(f"wmctrl error: {e}")
            return False

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
            if hasattr(handle, 'title'):  # It's a PyWinCtl window object
                # Get window ID - PyWinCtl uses 'wid' for window ID
                wid = getattr(handle, 'wid', 0)
                    
                return WindowInfo(
                    title=handle.title,
                    handle=handle,
                    pid=wid,
                    geometry=(handle.left, handle.top, handle.width, handle.height),
                    is_visible=handle.visible,
                    is_minimized=handle.isMinimized
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
            # Get the native handle from PyWinCtl window
            pywinctl_window = window_info.handle
            
            # Try to get Win32 handle - this might need adjustment based on PyWinCtl version
            if hasattr(pywinctl_window, '_hWnd'):
                win32_handle = pywinctl_window._hWnd
            elif hasattr(pywinctl_window, 'getHandle'):
                win32_handle = pywinctl_window.getHandle()
            else:
                # Fallback: find window by title
                win32_handle = win32gui.FindWindow(None, window_info.title)
                
            if not win32_handle:
                print(f"Could not get Win32 handle for window: {window_info.title}")
                return False
            
            # Capture the original parent before reparenting
            original_parent = win32gui.GetParent(win32_handle)
            
            # Get parent widget's window ID
            parent_id = int(parent_widget.winfo_id())
            
            # Embed the window
            win32gui.SetParent(win32_handle, parent_id)
            
            # Resize and position the embedded window
            parent_width = parent_widget.winfo_width()
            parent_height = parent_widget.winfo_height()
            
            win32gui.MoveWindow(win32_handle, 0, 0, parent_width, parent_height, True)
            win32gui.ShowWindow(win32_handle, win32con.SW_SHOW)
            
            # Track the embedded window
            self._embedded_windows[window_info.title] = {
                'win32_handle': win32_handle,
                'parent_widget': parent_widget,
                'original_parent': original_parent
            }
            
            print(f"Successfully embedded window: {window_info.title}")
            return True
            
        except Exception as e:
            print(f"Win32 embedding failed: {e}")
            return False
    
    def _embed_window_fallback(self, window_info: WindowInfo, parent_widget: Any) -> bool:
        """Fallback embedding using positioning (for non-Windows platforms)."""
        try:
            # Position window next to parent
            parent_x = parent_widget.winfo_rootx()
            parent_y = parent_widget.winfo_rooty()
            parent_width = parent_widget.winfo_width()
            
            # Position the window to the right of the parent
            new_x = parent_x + parent_width + 10
            new_y = parent_y
            
            pywinctl_window = window_info.handle
            pywinctl_window.moveTo(new_x, new_y)
            pywinctl_window.activate()
            
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
            
            # Restore original parent, fall back to desktop (0) if original_parent is missing or None
            if original_parent is not None and isinstance(original_parent, int):
                win32gui.SetParent(win32_handle, original_parent)
            else:
                win32gui.SetParent(win32_handle, 0)
            
            # Remove from tracking
            del self._embedded_windows[window_info.title]
            
            print(f"Successfully unembedded window: {window_info.title}")
            return True
            
        except Exception as e:
            print(f"Win32 unembedding failed: {e}")
            return False
    
    def _unembed_window_fallback(self, window_info: WindowInfo) -> bool:
        """Fallback unembedding (just activate the window)."""
        try:
            pywinctl_window = window_info.handle
            pywinctl_window.activate()
            return True
        except Exception as e:
            print(f"Fallback unembedding failed: {e}")
            return False
    
    def position_window_beside(self, window_info: WindowInfo, reference_window: Any) -> bool:
        """Position window beside a reference window (legacy method)."""
        try:
            pywinctl_window = window_info.handle
            
            # Get reference window position
            ref_x = reference_window.winfo_rootx()
            ref_y = reference_window.winfo_rooty()
            ref_width = reference_window.winfo_width()
            
            # Position to the right with some padding
            new_x = ref_x + ref_width + 20
            new_y = ref_y
            
            pywinctl_window.moveTo(new_x, new_y)
            return True
            
        except Exception as e:
            print(f"Error positioning window: {e}")
            return False
    
    def position_window_in_boundary(self, window_info: WindowInfo, boundary: tuple) -> bool:
        try:
            x, y, width, height = boundary
            if isinstance(window_info.handle, int):
                # Linux: use wmctrl -e gravity,x,y,w,h
                return self._wmctrl(window_info.handle, '-e', f'0,{x},{y},{width},{height}')
            pywinctl_window = window_info.handle
            pywinctl_window.resizeTo(width, height)
            pywinctl_window.moveTo(x, y)
            print(f"Positioned window in boundary: ({x}, {y}, {width}, {height})")
            return True
        except Exception as e:
            print(f"Error positioning window in boundary: {e}")
            return False

    def raise_window(self, window_info: WindowInfo) -> bool:
        try:
            if isinstance(window_info.handle, int):
                return self._wmctrl(window_info.handle, '-b', 'remove,hidden')
            window_info.handle.activate()
            return True
        except Exception as e:
            print(f"Error raising window: {e}")
            return False

    def focus_window(self, window_info: WindowInfo) -> bool:
        try:
            if isinstance(window_info.handle, int):
                return self._wmctrl(window_info.handle, '-b', 'remove,hidden')
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
            if isinstance(window_info.handle, int):
                return self._wmctrl(window_info.handle, '-e', f'0,-1,-1,{width},{height}')
            window_info.handle.resizeTo(width, height)
            return True
        except Exception as e:
            print(f"Error resizing window: {e}")
            return False

    def move_window(self, window_info: WindowInfo, x: int, y: int) -> bool:
        try:
            if isinstance(window_info.handle, int):
                return self._wmctrl(window_info.handle, '-e', f'0,{x},{y},-1,-1')
            window_info.handle.moveTo(x, y)
            return True
        except Exception as e:
            print(f"Error moving window: {e}")
            return False
