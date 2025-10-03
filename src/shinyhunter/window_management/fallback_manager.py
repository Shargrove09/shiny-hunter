"""
Fallback window manager using pygetwindow for basic functionality.
"""

from typing import List, Optional, Any
from .base import WindowManager, WindowInfo, EmbeddingMode

try:
    import pygetwindow as gw
    PYGETWINDOW_AVAILABLE = True
except ImportError:
    PYGETWINDOW_AVAILABLE = False
except NotImplementedError:
    # pygetwindow raises NotImplementedError on unsupported platforms like Linux
    PYGETWINDOW_AVAILABLE = False


class FallbackManager(WindowManager):
    """Fallback window manager using pygetwindow for basic window operations."""
    
    def __init__(self):
        super().__init__()
        
        if not PYGETWINDOW_AVAILABLE:
            if self.platform.lower() == 'linux':
                raise ImportError("pygetwindow does not support Linux platform")
            else:
                raise ImportError("pygetwindow is required but not available")
        
        # Fallback manager only supports manual mode
        self.embedding_mode = EmbeddingMode.MANUAL
        
        print(f"FallbackManager initialized for {self.platform} (manual mode only)")
    
    def get_all_windows(self) -> List[WindowInfo]:
        """Get information about all available windows using pygetwindow."""
        windows = []
        
        try:
            window_titles = gw.getAllTitles()
            
            for title in window_titles:
                if not title.strip():  # Skip empty titles
                    continue
                    
                try:
                    gw_windows = gw.getWindowsWithTitle(title)
                    if gw_windows:
                        window = gw_windows[0]  # Get first match
                        
                        window_info = WindowInfo(
                            title=title,
                            handle=window,
                            pid=0,  # pygetwindow doesn't provide PID
                            geometry=(window.left, window.top, window.width, window.height),
                            is_visible=window.visible,
                            is_minimized=window.isMinimized
                        )
                        windows.append(window_info)
                        
                except Exception as e:
                    print(f"Skipping window '{title}' due to error: {e}")
                    continue                    
        except Exception as e:
            print(f"Error enumerating windows with pygetwindow: {e}")
            
        return windows
    
    def get_window_by_title(self, title: str) -> Optional[WindowInfo]:
        """Find a window by its title."""
        try:
            windows = gw.getWindowsWithTitle(title)
            if windows:
                window = windows[0]
                return WindowInfo(
                    title=title,
                    handle=window,
                    pid=0,
                    geometry=(window.left, window.top, window.width, window.height),
                    is_visible=window.visible,
                    is_minimized=window.isMinimized
                )
        except Exception as e:
            print(f"Error finding window by title '{title}': {e}")
            
        return None
    
    def get_window_by_handle(self, handle: Any) -> Optional[WindowInfo]:
        """Get window information by handle (pygetwindow window object)."""
        try:
            if hasattr(handle, 'title'):
                return WindowInfo(
                    title=handle.title,
                    handle=handle,
                    pid=0,
                    geometry=(handle.left, handle.top, handle.width, handle.height),
                    is_visible=handle.visible,
                    is_minimized=handle.isMinimized
                )
        except Exception as e:
            print(f"Error getting window info by handle: {e}")
            
        return None
    
    def embed_window(self, window_info: WindowInfo, parent_widget: Any) -> bool:
        """Embedding not supported in fallback manager."""
        print("Window embedding not supported in fallback mode")
        return False
    
    def unembed_window(self, window_info: WindowInfo) -> bool:
        """Unembedding not supported in fallback manager."""
        print("Window unembedding not supported in fallback mode")
        return False
    
    def position_window_beside(self, window_info: WindowInfo, reference_window: Any) -> bool:
        """Basic window positioning (legacy method)."""
        try:
            gw_window = window_info.handle
            
            # Get reference window position
            ref_x = reference_window.winfo_rootx()
            ref_y = reference_window.winfo_rooty()
            ref_width = reference_window.winfo_width()
            
            # Position to the right
            new_x = ref_x + ref_width + 20
            new_y = ref_y
            
            gw_window.moveTo(new_x, new_y)
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
            gw_window = window_info.handle
            x, y, width, height = boundary
            
            # First resize the window to fit the boundary
            gw_window.resizeTo(width, height)
            
            # Then move it to the boundary position
            gw_window.moveTo(x, y)
            
            print(f"Positioned window in boundary: ({x}, {y}, {width}, {height})")
            return True
            
        except Exception as e:
            print(f"Error positioning window in boundary: {e}")
            return False
    
    def raise_window(self, window_info: WindowInfo) -> bool:
        """Raise window above others (stacking order)."""
        try:
            gw_window = window_info.handle
            # activate() typically raises the window
            gw_window.activate()
            return True
        except Exception as e:
            print(f"Error raising window: {e}")
            return False
    
    def focus_window(self, window_info: WindowInfo) -> bool:
        """Bring window to front."""
        try:
            gw_window = window_info.handle
            gw_window.activate()
            return True
        except Exception as e:
            print(f"Error focusing window: {e}")
            return False
    
    def resize_window(self, window_info: WindowInfo, width: int, height: int) -> bool:
        """Resize window."""
        try:
            gw_window = window_info.handle
            gw_window.resizeTo(width, height)
            return True
        except Exception as e:
            print(f"Error resizing window: {e}")
            return False
    
    def move_window(self, window_info: WindowInfo, x: int, y: int) -> bool:
        """Move window."""
        try:
            gw_window = window_info.handle
            gw_window.moveTo(x, y)
            return True
        except Exception as e:
            print(f"Error moving window: {e}")
            return False
    
    def get_capabilities(self) -> dict:
        """Get fallback manager capabilities."""
        return {
            'window_discovery': True,
            'window_embedding': False,
            'window_positioning': True,
            'window_focusing': True,
            'window_resizing': True
        }
