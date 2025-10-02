"""
Cross-platform window management module for Shiny Hunter.

This module provides a unified interface for window management across different platforms,
with platform-specific implementations for optimal functionality.
"""

from .factory import WindowManagerFactory
from .base import WindowManager, WindowInfo, EmbeddingMode

__all__ = ['WindowManagerFactory', 'WindowManager', 'WindowInfo', 'EmbeddingMode']
