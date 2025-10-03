"""
Base classes and interfaces for cross-platform window management.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Tuple, Any
from dataclasses import dataclass
import platform


class EmbeddingMode(Enum):
    """Different modes of window management available."""
    FULL_EMBED = "full_embed"        # Full window embedding (Windows)
    COMPANION = "companion"          # Side-by-side positioning (macOS/Linux)
    MANUAL = "manual"               # Manual window management only


@dataclass
class WindowInfo:
    """Information about a discovered window."""
    title: str
    handle: Any  # Platform-specific handle type
    pid: int
    geometry: Tuple[int, int, int, int]  # x, y, width, height
    is_visible: bool
    is_minimized: bool


class WindowManager(ABC):
    """Abstract base class for cross-platform window management."""
    
    def __init__(self):
        self.platform = platform.system()
        self.embedding_mode = self._determine_embedding_mode()
    
    @abstractmethod
    def get_all_windows(self) -> List[WindowInfo]:
        """Get information about all available windows."""
        pass
    
    @abstractmethod
    def get_window_by_title(self, title: str) -> Optional[WindowInfo]:
        """Find a window by its title."""
        pass
    
    @abstractmethod
    def get_window_by_handle(self, handle: Any) -> Optional[WindowInfo]:
        """Get window information by handle."""
        pass
    
    @abstractmethod
    def embed_window(self, window_info: WindowInfo, parent_widget: Any) -> bool:
        """Embed a window into a parent widget. Returns success status."""
        pass
    
    @abstractmethod
    def unembed_window(self, window_info: WindowInfo) -> bool:
        """Remove window embedding. Returns success status."""
        pass
    
    @abstractmethod
    def position_window_beside(self, window_info: WindowInfo, reference_window: Any) -> bool:
        """Position window beside a reference window (companion mode)."""
        pass
    
    @abstractmethod
    def position_window_in_boundary(self, window_info: WindowInfo, boundary: Tuple[int, int, int, int]) -> bool:
        """
        Position and resize window to fit within a defined boundary.
        
        Args:
            window_info: The window to position
            boundary: (x, y, width, height) defining the boundary area
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def raise_window(self, window_info: WindowInfo) -> bool:
        """Raise window above others (stacking order)."""
        pass
    
    @abstractmethod
    def focus_window(self, window_info: WindowInfo) -> bool:
        """Bring window to front and focus it."""
        pass
    
    @abstractmethod
    def resize_window(self, window_info: WindowInfo, width: int, height: int) -> bool:
        """Resize a window to specified dimensions."""
        pass
    
    @abstractmethod
    def move_window(self, window_info: WindowInfo, x: int, y: int) -> bool:
        """Move window to specified position."""
        pass
    
    def get_embedding_mode(self) -> EmbeddingMode:
        """Get the embedding mode supported by this manager."""
        return self.embedding_mode
    
    def _determine_embedding_mode(self) -> EmbeddingMode:
        """Determine the best embedding mode for the current platform."""
        if self.platform == "Windows":
            return EmbeddingMode.FULL_EMBED
        elif self.platform in ["Darwin", "Linux"]:
            return EmbeddingMode.COMPANION
        else:
            return EmbeddingMode.MANUAL
    
    def get_capabilities(self) -> dict:
        """Get a dictionary of supported capabilities."""
        return {
            'window_discovery': True,
            'window_embedding': self.embedding_mode == EmbeddingMode.FULL_EMBED,
            'window_positioning': self.embedding_mode != EmbeddingMode.MANUAL,
            'window_focusing': True,
            'window_resizing': True
        }
