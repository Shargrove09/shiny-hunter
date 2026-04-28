"""
PyWinCtl-based window manager implementation.
"""

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
        windows = []
        
        try:
            pywinctl_windows = pywinctl.getAllWindows()
            print(f"Found {len(pywinctl_windows)} windows via PyWinCtl")
            print(f"Sample window titles: {[w.title for w in pywinctl_windows[:5]]}")
            for window in pywinctl_windows:
                try:
                    # Filter out windows without titles or that are not visible
                    if not window.title or not window.visible:
                        continue
                    
                    # Get window ID - PyWinCtl uses 'wid' for window ID
                    wid = getattr(window, 'wid', 0)
                        
                    window_info = WindowInfo(
                        title=window.title,
                        handle=window,  # Store the PyWinCtl window object
                        pid=wid,
                        geometry=(window.left, window.top, window.width, window.height),
                        is_visible=window.visible,
                        is_minimized=window.isMinimized
                    )
                    windows.append(window_info)
                    
                except Exception as e:
                    # Skip windows that cause errors (common with system windows)
                    continue
                    
        except Exception as e:
            print(f"Error enumerating windows: {e}")
            
        return windows
    
    def get_window_by_title(self, title: str) -> Optional[WindowInfo]:
        """Find a window by its title."""
        try:
            windows = pywinctl.getWindowsWithTitle(title)
            if windows:
                window = windows[0]  # Get first match
                # Get window ID - PyWinCtl uses 'wid' for window ID
                wid = getattr(window, 'wid', 0)
                    
                return WindowInfo(
                    title=window.title,
                    handle=window,
                    pid=wid,
                    geometry=(window.left, window.top, window.width, window.height),
                    is_visible=window.visible,
                    is_minimized=window.isMinimized
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
        """
        Position and resize window to fit within a defined boundary.
        
        Args:
            window_info: The window to position
            boundary: (x, y, width, height) defining the boundary area
            
        Returns:
            True if successful, False otherwise
        """
        try:
            pywinctl_window = window_info.handle
            x, y, width, height = boundary
            
            # First resize the window to fit the boundary
            pywinctl_window.resizeTo(width, height)
            
            # Then move it to the boundary position
            pywinctl_window.moveTo(x, y)
            
            print(f"Positioned window in boundary: ({x}, {y}, {width}, {height})")
            return True
            
        except Exception as e:
            print(f"Error positioning window in boundary: {e}")
            return False
    
    def raise_window(self, window_info: WindowInfo) -> bool:
        """Raise window above others (stacking order)."""
        try:
            pywinctl_window = window_info.handle
            # PyWinCtl's activate() typically raises the window as well
            pywinctl_window.activate()
            return True
        except Exception as e:
            print(f"Error raising window: {e}")
            return False
    
    def focus_window(self, window_info: WindowInfo) -> bool:
        """Bring window to front and focus it."""
        try:
            pywinctl_window = window_info.handle
            pywinctl_window.activate()
            return True
        except Exception as e:
            print(f"Error focusing window: {e}")
            return False
    
    def resize_window(self, window_info: WindowInfo, width: int, height: int) -> bool:
        """Resize a window to specified dimensions."""
        try:
            # If the window is embedded (child of a tkinter widget), use win32gui.MoveWindow
            # with parent-relative coordinates (0, 0) so it stays inside the embed frame.
            if window_info.title in self._embedded_windows:
                win32_handle = self._embedded_windows[window_info.title]['win32_handle']
                win32gui.MoveWindow(win32_handle, 0, 0, width, height, True)
                return True

            pywinctl_window = window_info.handle
            pywinctl_window.resizeTo(width, height)
            return True
        except Exception as e:
            print(f"Error resizing window: {e}")
            return False
    
    def move_window(self, window_info: WindowInfo, x: int, y: int) -> bool:
        """Move window to specified position."""
        try:
            pywinctl_window = window_info.handle
            pywinctl_window.moveTo(x, y)
            return True
        except Exception as e:
            print(f"Error moving window: {e}")
            return False
