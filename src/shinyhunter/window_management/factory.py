"""
Factory for creating the appropriate window manager based on platform and available libraries.
"""

import logging
import platform
from typing import Optional
from .base import WindowManager
from .pywinctl_manager import PyWinCtlManager
from .fallback_manager import FallbackManager

logger = logging.getLogger(__name__)


class WindowManagerFactory:
    """Factory for creating window managers with automatic fallback handling."""
    
    @staticmethod
    def create() -> WindowManager:
        """
        Create the best available window manager for the current platform.
        
        Returns:
            WindowManager: The most capable window manager available
            
        Raises:
            ImportError: If no suitable window manager can be created
        """
        errors = []
        
        # Try PyWinCtl first (best option)
        try:
            return PyWinCtlManager()
        except ImportError as e:
            errors.append(f"PyWinCtlManager: {e}")
        
        # Fallback to pygetwindow
        try:
            return FallbackManager()
        except ImportError as e:
            errors.append(f"FallbackManager: {e}")
        
        # If we get here, nothing worked
        error_msg = "No suitable window manager available. Errors:\n" + "\n".join(errors)
        error_msg += "\n\nPlease install PyWinCtl or pygetwindow."
        raise ImportError(error_msg)
    
    @staticmethod
    def create_specific(manager_type: str) -> Optional[WindowManager]:
        """
        Create a specific type of window manager.
        
        Args:
            manager_type: Either 'pywinctl' or 'fallback'
            
        Returns:
            WindowManager or None if creation fails
        """
        try:
            if manager_type.lower() == 'pywinctl':
                return PyWinCtlManager()
            elif manager_type.lower() == 'fallback':
                return FallbackManager()
            else:
                logger.warning("Unknown manager type: %s", manager_type)
                return None
        except ImportError as e:
            logger.error("Failed to create %s manager: %s", manager_type, e)
            return None
    
    @staticmethod
    def get_available_managers() -> list:
        """
        Get a list of available window manager types.
        
        Returns:
            List of available manager type strings
        """
        available = []
        
        # Check PyWinCtl
        try:
            import pywinctl
            available.append('pywinctl')
        except ImportError:
            pass
        
        # Check pygetwindow
        try:
            import pygetwindow
            available.append('fallback')
        except ImportError:
            pass
        except NotImplementedError:
            # pygetwindow raises NotImplementedError on unsupported platforms like Linux
            pass
        
        return available
    
    @staticmethod
    def get_platform_info() -> dict:
        """
        Get information about the current platform and capabilities.
        
        Returns:
            Dictionary with platform information
        """
        current_platform = platform.system()
        available_managers = WindowManagerFactory.get_available_managers()
        
        # Determine expected capabilities
        embedding_support = False
        if current_platform == "Windows" and 'pywinctl' in available_managers:
            try:
                import win32gui
                embedding_support = True
            except ImportError:
                pass
        
        return {
            'platform': current_platform,
            'available_managers': available_managers,
            'embedding_support': embedding_support,
            'recommended_manager': 'pywinctl' if 'pywinctl' in available_managers else 'fallback'
        }
