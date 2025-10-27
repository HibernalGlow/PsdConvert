import hashlib
import os
import subprocess
import sys
from pathlib import Path

def calculate_sha1(file_path):
    """Calculate SHA1 hash of a file."""
    sha1 = hashlib.sha1()
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                sha1.update(chunk)
        return sha1.hexdigest()
    except Exception as e:
        print(f"Error calculating SHA1 for {file_path}: {e}")
        return None

def process_files(root_path, delete_after_zip=False):
    """Process files in the given path."""
    for file_path in Path(root_path).rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() != '.zip':
            sha1 = calculate_sha1(file_path)
            if sha1:
                print(f"{file_path}: {sha1}")
                zip_name = file_path.stem + ".zip"
                zip_path = file_path.parent / zip_name
                
                # Use 7z to add to existing zip (or create new if not exists)
                try:
                    cmd = ['7z', 'a', str(zip_path), str(file_path)]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        print(f"Added {file_path} to {zip_path}")
                        if delete_after_zip:
                            file_path.unlink()
                            print(f"Deleted {file_path}")
                    else:
                        print(f"Error adding to zip for {file_path}: {result.stderr}")
                except FileNotFoundError:
                    print("7z not found. Please install 7-Zip.")
                    sys.exit(1)

def main(root_path, delete_after_zip=False):
    """Main function to process the path."""
    process_files(root_path, delete_after_zip)