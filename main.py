#!/usr/bin/env python3
"""
Main entry point for the Switch Save Converter application.
Handles initialization, logging setup, and error recovery.
"""
import sys
import logging
from pathlib import Path

# Configure logging
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

log_file = LOG_DIR / \
    f"converter_{sys.platform}_{sys.version.replace('.', '_')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("SwitchSaveConverter")


def check_dependencies():
    """Verify all required packages are installed."""
    logger.info("Checking dependencies...")

    required = ["Pillow", "tk"]
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

    if missing:
        logger.fatal(f"Missing dependencies: {', '.join(missing)}")
        print(f"\nError: Missing packages: {', '.join(missing)}")
        print("Install them with: pip install -r requirements.txt")
        return False

    return True


def check_resources():
    """Verify resource files exist (icons, mappings)."""
    logger.info("Checking resource files...")

    resources = {
        "icons/": Path(__file__).parent / "icons",
    }

    missing = []
    for name, path in resources.items():
        if path.exists():
            logger.info(f"✓ {name} found")
        else:
            missing.append(name)
            logger.warning(f"⚠ {name} not found (will use fallback)")

    if missing:
        logger.warning(f"Some resources missing: {', '.join(missing)}")

    return True


def launch_gui():
    """Start the GUI application."""
    logger.info("Launching GUI...")

    try:
        import tkinter as tk

        # Import the main app
        from gui import FolderProcessorApp

        root = tk.Tk()

        # Set window icon if available
        icon_path = Path(__file__).parent / "icons" / "checkpoint.jpg"
        if icon_path.exists():
            try:
                from PIL import Image, ImageTk
                img = Image.open(icon_path).resize((64, 64))
                photo = ImageTk.PhotoImage(img)
                root.iconphoto(True, photo)
            except Exception as e:
                logger.warning(f"Could not set window icon: {e}")

        root.title("Switch Save Converter")
        root.geometry("850x550")

        # Prevent multiple instances (basic)
        try:
            root.resizable(True, True)
        except:
            pass

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
    logger.info(f"Python: {sys.version}")
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
