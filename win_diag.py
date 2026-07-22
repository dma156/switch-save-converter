# Run this diagnostic BEFORE building:
from pathlib import Path
import sys

print(f"Platform: {sys.platform}")
print(f"Frozen: {getattr(sys, 'frozen', False)}")
print(f"__file__: {__file__ if '__file__' in globals() else 'N/A'}")
print(f"sys.executable: {sys.executable}")
print(f"sys._MEIPASS: {getattr(sys, '_MEIPASS', 'NOT SET')}")

# Test resource path resolution
if hasattr(sys, '_MEIPASS'):
    print(f"Resource would be at: {Path(sys._MEIPASS) / 'icons'}")
else:
    print(f"Resource would be at: {Path(__file__).parent / 'icons'}")