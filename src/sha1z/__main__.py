#!/usr/bin/env python3
import argparse
from .input_path import get_input_path
from .core import main

def parse_args():
    parser = argparse.ArgumentParser(description="Process files: calculate SHA1 and add to zip.")
    parser.add_argument('path', nargs='?', help="Path to process")
    parser.add_argument('--delete', action='store_true', help="Delete files after adding to zip")
    return parser.parse_args()

def interactive_mode():
    """Interactive mode when no arguments provided."""
    print("Interactive mode:")
    path = input("Enter the path to process: ").strip()
    if not path:
        print("No path provided.")
        return None, False
    
    from pathlib import Path
    path_obj = Path(path)
    if not path_obj.exists():
        print(f"Path does not exist: {path}")
        return None, False
    
    delete_choice = input("Delete files after adding to zip? (y/n): ").strip().lower()
    delete = delete_choice in ('y', 'yes')
    
    return str(path_obj), delete

if __name__ == "__main__":
    args = parse_args()
    if args.path:
        path = args.path
        delete = args.delete
    else:
        # Interactive mode
        path, delete = interactive_mode()
        if path is None:
            exit(1)
    
    main(path, delete)