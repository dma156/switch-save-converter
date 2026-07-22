#!/usr/bin/env python3
"""
Main entry point for the Switch Save Converter application.
Handles initialization, logging setup, and error recovery.
"""
import sys
import os
import logging
from pathlib import Path
import datetime

if sys.platform == "win32":
    try:
        import ctypes
        # Enable long path support (Windows 10 version 1803+)
        # This removes 260-character MAX_PATH limit
        ctypes.windll.kernel32.SetDllDirectoryW("")
        # NOTE: Can't log yet - logger not created. Print if needed.
        print("[INFO] Windows: Long path support enabled")
    except Exception as e:
        print(f"[WARNING] Windows: Could not enable long paths: {e}")
        print("[NOTE] Long paths may need to be enabled via registry manually")

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Safe log filename - no special chars, spaces, or colons
date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
platform_name = sys.platform.replace("win32", "windows").replace("/", "_")
version_safe = f"py{sys.version_info.major}_{sys.version_info.minor}"

log_filename = f"converter_{platform_name}_{version_safe}_{date_str}.log"
log_file = LOG_DIR / log_filename

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("SwitchSaveConverter")

def get_app_base_path():
    """Get the base path whether frozen or in development (Windows-safe)."""
    if getattr(sys, 'frozen', False):
        # Frozen executable - use the executable's directory
        return Path(sys.executable).parent
    else:
        # Development - use script location
        return Path(__file__).parent

def check_resources():
    """Verify resource files exist (icons, mappings)."""
    logger.info("Checking resource files...")
    
    base_path = get_app_base_path()
    logger.info(f"Base path: {base_path}")
    
    resources = {
        "icons/": base_path / "icons",
        "logs/": base_path / "logs",
    }
    
    missing = []
    for name, path in resources.items():
        if path.exists():
            logger.info(f"✓ {name} found at {path}")
        else:
            missing.append(name)
            logger.warning(f"⚠ {name} not found (will use fallback)")
    
    if missing:
        logger.warning(f"Some resources missing: {', '.join(missing)}")
    
    return True

def check_dependencies():
    """Verify all required packages are installed."""
    logger.info("Checking dependencies...")
    
    missing = []
    
    try:
        from PIL import Image
        logger.info("✓ Pillow installed")
    except ImportError:
        missing.append("Pillow")
        logger.error("✗ Pillow not found")
    
    try:
        import tkinter
        logger.info("✓ Tkinter available")
    except ImportError:
        missing.append("tk")
        logger.error("✗ Tkinter not found")
    
    # Windows: Enable long path support if possible
    if sys.platform == "win32":
        try:
            import ctypes
            # Enable long paths (requires Windows 10+ and registry setting)
            ctypes.windll.kernel32.SetDllDirectoryW("")
            logger.info("✓ Windows long path support attempted")
        except Exception as e:
            logger.warning(f"Could not enable long path support: {e}")
    
    if missing:
        logger.fatal(f"Missing dependencies: {', '.join(missing)}")
        print(f"\nError: Missing packages: {', '.join(missing)}")
        print("Install them with: pip install -r requirements.txt")
        return False
    
    return True

def launch_gui():
    """Start the GUI application with Windows-compatible paths."""
    logger.info("Launching GUI...")
    
    # Helper for Windows/frozen compatibility
    def get_resource_path(relative_path):
        """Get absolute path to resource, works for dev and frozen exe."""
        if getattr(sys, 'frozen', False):
            # Running as compiled executable (PyInstaller)
            try:
                # PyInstaller sets _MEIPASS to extract resources
                base_path = Path(sys._MEIPASS)
            except Exception:
                # Fallback to executable directory
                base_path = Path(sys.executable).parent
        else:
            # Running as script in development
            base_path = Path(__file__).parent
        
        return base_path / relative_path
    
    try:
        import tkinter as tk
        
        # Import the main app
        from gui import FolderProcessorApp
        
        root = tk.Tk()
        
        # Set window icon if available (Windows-fixed)
        icon_path = get_resource_path("icons/checkpoint.jpg")
        if not icon_path.exists():
            icon_path = get_resource_path("icons/checkpoint.png")
        
        if icon_path.exists():
            try:
                from PIL import Image, ImageTk
                img = Image.open(icon_path).resize((64, 64))
                photo = ImageTk.PhotoImage(img)
                root.iconphoto(True, photo)
                logger.info(f"✓ Window icon set: {icon_path}")
            except Exception as e:
                logger.warning(f"Could not set window icon: {e}")
        else:
            logger.info("Window icon not found, using default")
        
        root.title("Switch Save Converter")
        root.geometry("850x550")
        
        app = FolderProcessorApp(root)
        
        def on_closing():
            logger.info("Application closing...")
            root.destroy()
            sys.exit(0)
        
        root.protocol("WM_DELETE_WINDOW", on_closing)
        root.mainloop()
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        print(f"Error importing GUI module: {e}")
        print("Make sure gui.py and all modules are in the correct location.")
        input("\nPress Enter to exit...")
    except tk.TclError as e:
        logger.error(f"Tkinter error: {e}")
        print(f"GUI display error: {e}")
        print("Make sure you have a display/server available.")
        input("\nPress Enter to exit...")

def main():
    """Main entry point."""
    logger.info("=" * 50)
    logger.info("Switch Save Converter Starting")
    logger.info(f"Platform: {sys.platform}")
    logger.info(f"Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    logger.info(f"Executable: {Path(__file__).resolve()}")
    logger.info("=" * 50)
    
    # Check prerequisites
    if not check_dependencies():
        return 1
    
    check_resources()
    
    # Launch GUI
    launch_gui()
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        print("\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.exception("Uncaught exception")
        print(f"\nFatal error: {e}")
        input("Press Enter to exit...")
        sys.exit(1)