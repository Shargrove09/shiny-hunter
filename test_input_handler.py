#!/usr/bin/env python3
"""
Test script for the new cross-platform InputHandler
"""
import sys
import os

# Add the src directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'shinyhunter'))

try:
    from input_handler import InputHandler
    from config import ConfigManager
    
    print("Testing cross-platform InputHandler...")
    
    # Initialize the input handler
    input_handler = InputHandler()
    
    print(f"Input method: {input_handler.input_method}")
    print(f"Platform: {input_handler.platform}")
    
    # Test key mapping
    key_map = input_handler._get_key_mapping()
    print(f"Key mappings: {key_map}")
    
    print("\nInputHandler test completed successfully!")
    print("Note: Actual key presses were not executed to avoid interference.")
    
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure all dependencies are installed.")
except Exception as e:
    print(f"Error: {e}")
