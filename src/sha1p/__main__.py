#!/usr/bin/env python3
"""SHA1 Processor CLI"""

import sys
import argparse
from pathlib import Path
from .core import process_directories


def main():
    parser = argparse.ArgumentParser(description="Process images in directories to rename first image with SHA1.")
    parser.add_argument("root_dir", help="Root directory to process")
    parser.add_argument("--sha1-length", type=int, default=8, help="Length of SHA1 to append (default: 8)")

    args = parser.parse_args()

    root_path = Path(args.root_dir)
    if not root_path.exists() or not root_path.is_dir():
        print(f"Error: {args.root_dir} is not a valid directory")
        sys.exit(1)

    # Note: sha1_length is not used in current implementation, can be extended
    process_directories(str(root_path))
    print("Processing complete.")


if __name__ == "__main__":
    main()