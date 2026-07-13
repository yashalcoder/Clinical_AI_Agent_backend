import os
import sys

# Ensure parent directory is in sys.path so 'app' module can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
