import os
import hashlib
import re
from pathlib import Path
import tomllib


def load_config():
    """Load configuration from config.toml"""
    config_path = Path(__file__).parent / "config.toml"
    if config_path.exists():
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
        return config
    return {"rename": {"template": "{stem}_{sha1}{suffix}"}}


def natural_sort_key(s):
    """Generate a key for natural sorting."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]


def get_image_files(directory):
    """Get image files in the directory (non-recursive)."""
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.svg'}
    files = []
    for item in os.listdir(directory):
        path = os.path.join(directory, item)
        if os.path.isfile(path):
            ext = Path(item).suffix.lower()
            if ext in image_extensions:
                files.append(item)
    return sorted(files, key=natural_sort_key)


def calculate_sha1(file_path):
    """Calculate SHA1 hash of a file."""
    sha1 = hashlib.sha1()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            sha1.update(chunk)
    return sha1.hexdigest()


def rename_with_sha1(directory, sha1_length=8, template=None):
    """Process directory to rename the first image with SHA1."""
    if template is None:
        config = load_config()
        template = config["rename"]["template"]

    image_files = get_image_files(directory)
    if not image_files:
        print(f"No image files found in {directory}")
        return

    first_image = image_files[0]
    image_path = os.path.join(directory, first_image)

    sha1_hash = calculate_sha1(image_path)
    short_sha1 = sha1_hash[:sha1_length]

    # Split filename and extension
    stem = Path(first_image).stem
    suffix = Path(first_image).suffix

    # Use template
    new_filename = template.format(stem=stem, sha1=short_sha1, suffix=suffix)
    new_path = os.path.join(directory, new_filename)

    # Rename
    os.rename(image_path, new_path)
    print(f"Renamed {first_image} to {new_filename} in {directory}")


def process_directories(root_dir, sha1_length=8):
    """Process all directories that contain images."""
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Check if directory has direct image files
        image_files = get_image_files(dirpath)
        if image_files:
            rename_with_sha1(dirpath, sha1_length)