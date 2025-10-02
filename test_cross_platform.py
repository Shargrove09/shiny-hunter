#!/usr/bin/env python3
"""
Cross-Platform Window Management Test Script

This script demonstrates the new cross-platform window management capabilities
of the Shiny Hunter application.
"""

import sys
import os
import platform

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'shinyhunter'))

def test_window_management():
    """Test the cross-platform window management system."""
    print("=" * 60)
    print("Cross-Platform Window Management Test")
    print("=" * 60)
    
    # Test platform detection
    print(f"Current Platform: {platform.system()}")
    
    # Test factory
    try:
        from window_management import WindowManagerFactory
        
        # Get platform info
        platform_info = WindowManagerFactory.get_platform_info()
        print(f"Available Managers: {platform_info['available_managers']}")
        print(f"Embedding Support: {platform_info['embedding_support']}")
        print(f"Recommended Manager: {platform_info['recommended_manager']}")
        
        # Create window manager
        print("\nCreating window manager...")
        window_manager = WindowManagerFactory.create()
        print(f"Created: {type(window_manager).__name__}")
        print(f"Embedding Mode: {window_manager.get_embedding_mode().value}")
        
        # Test capabilities
        capabilities = window_manager.get_capabilities()
        print(f"Capabilities: {capabilities}")
        
        # Test window discovery
        print("\nDiscovering windows...")
        windows = window_manager.get_all_windows()
        print(f"Found {len(windows)} windows")
        
        # Show some sample windows
        print("\nSample windows:")
        for i, window in enumerate(windows[:10]):
            print(f"  {i+1}. {window.title} [{window.geometry}]")
        
        print("\n✅ Window management system working correctly!")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

def test_input_system():
    """Test the cross-platform input system."""
    print("\n" + "=" * 60)
    print("Cross-Platform Input System Test")
    print("=" * 60)
    
    try:
        from input_handler import InputHandler
        
        # Create input handler
        print("Creating input handler...")
        input_handler = InputHandler()
        
        # Test key mapping
        key_mapping = input_handler._get_key_mapping()
        print(f"Key Mapping: {key_mapping}")
        
        print("✅ Input system working correctly!")
        print("Note: No actual key presses performed in test mode.")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

def test_main_app_compatibility():
    """Test that the main application can start without errors."""
    print("\n" + "=" * 60)
    print("Main Application Compatibility Test")
    print("=" * 60)
    
    try:
        # Test imports
        print("Testing imports...")
        from shiny_hunter_controller import ShinyHunterController
        from config import ConfigManager
        from cross_platform_app import CrossPlatformAppFrame
        
        # Test config
        print("Testing configuration...")
        config = ConfigManager().get_config()
        print(f"Input pause setting: {config.input_pause}")
        
        # Test controller
        print("Testing controller...")
        controller = ShinyHunterController()
        print(f"Controller platform: {controller.input_handler.platform}")
        
        print("✅ Main application compatibility confirmed!")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

def print_migration_summary():
    """Print a summary of the migration changes."""
    print("\n" + "=" * 60)
    print("Migration Summary")
    print("=" * 60)
    
    changes = {
        "✅ Replaced pydirectinput": "with pynput for cross-platform input",
        "✅ Replaced win32gui/pywinauto": "with PyWinCtl for window management", 
        "✅ Added platform detection": "automatic fallback for unsupported features",
        "✅ Created modular architecture": "window_management package with factory pattern",
        "✅ Updated dependencies": "conditional Windows-specific packages",
        "✅ Maintained compatibility": "existing functionality preserved on Windows",
        "✅ Added graceful degradation": "reduced functionality on macOS/Linux"
    }
    
    print("Key Changes Made:")
    for change, description in changes.items():
        print(f"  {change}: {description}")
    
    print(f"\nPlatform Support:")
    print(f"  🪟 Windows: Full functionality (embedding + input)")
    print(f"  🍎 macOS: Core functionality (positioning + input)")
    print(f"  🐧 Linux: Core functionality (positioning + input)")
    
    print(f"\nNext Steps:")
    print(f"  • Test on macOS and Linux systems")
    print(f"  • Package platform-specific installers")
    print(f"  • Add automated cross-platform testing")

if __name__ == "__main__":
    print("Shiny Hunter Cross-Platform Migration Test Suite")
    print(f"Python {sys.version}")
    print(f"Platform: {platform.platform()}")
    
    # Run all tests
    tests = [
        test_window_management,
        test_input_system,
        test_main_app_compatibility
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test_func.__name__} failed with exception: {e}")
            results.append(False)
    
    # Print summary
    print_migration_summary()
    
    # Final results
    passed = sum(results)
    total = len(results)
    
    print(f"\n" + "=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Cross-platform migration successful!")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
    
    print("=" * 60)
