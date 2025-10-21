import os
import sys
from pathlib import Path

def get_input_path():
    """Get input path from command line arguments or user input."""
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = input("Enter the path to process: ").strip()
    
    if not path:
        print("No path provided.")
        sys.exit(1)
    
    path_obj = Path(path)
    if not path_obj.exists():
        print(f"Path does not exist: {path}")
        sys.exit(1)
    
    return path_obj