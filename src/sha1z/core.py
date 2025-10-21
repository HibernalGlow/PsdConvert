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
    root_path = Path(root_path)
    zip_name = root_path.name + ".zip"
    zip_path = root_path.parent / zip_name
    
    files_to_add = []
    for file_path in root_path.rglob('*'):
        if file_path.is_file():
            sha1 = calculate_sha1(file_path)
            if sha1:
                print(f"{file_path}: {sha1}")
                files_to_add.append(str(file_path))
    
    if files_to_add:
        # Use 7z to create zip with all files
        try:
            cmd = ['7z', 'a', str(zip_path)] + files_to_add
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"Added files to {zip_path}")
                if delete_after_zip:
                    for f in files_to_add:
                        Path(f).unlink()
                        print(f"Deleted {f}")
            else:
                print(f"Error creating zip: {result.stderr}")
        except FileNotFoundError:
            print("7z not found. Please install 7-Zip.")
            sys.exit(1)

def main(root_path, delete_after_zip=False):
    """Main function to process the path."""
    process_files(root_path, delete_after_zip)