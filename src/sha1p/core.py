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
        # Ensure types
        if "rename" in config and "sha1_length" in config["rename"]:
            config["rename"]["sha1_length"] = int(config["rename"]["sha1_length"])
        if "rename" in config and "max_images" in config["rename"]:
            config["rename"]["max_images"] = int(config["rename"]["max_images"])
        return config
    return {"rename": {"template": "{stem}[SHA1:{sha1}]{suffix}", "sha1_length": -1, "max_images": 3, "blacklist_keywords": ["画集"]}}


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


def rename_with_sha1(directory, sha1_length=None, template=None, max_images=None):
    if hasattr(sha1_length, 'default'):
        sha1_length = sha1_length.default
    sha1_length = int(sha1_length) if sha1_length is not None else None
    
    if template is None or sha1_length is None or max_images is None:
        config = load_config()
        if template is None:
            template = config["rename"]["template"]
        if sha1_length is None:
            sha1_length = config["rename"]["sha1_length"]
        if max_images is None:
            max_images = config["rename"]["max_images"]

    image_files = get_image_files(directory)
    if not image_files:
        print(f"No image files found in {directory}")
        return

    # Filter out already renamed files (containing [SHA1:...])
    sha1_pattern = re.compile(r'\[SHA1:[a-f0-9]+\]')
    image_files = [f for f in image_files if not sha1_pattern.search(f)]
    if not image_files:
        print(f"All image files already renamed in {directory}")
        return

    # Process up to max_images
    for i, first_image in enumerate(image_files[:max_images]):
        image_path = os.path.join(directory, first_image)

        sha1_hash = calculate_sha1(image_path)
        if sha1_length == -1:
            short_sha1 = sha1_hash
        else:
            short_sha1 = sha1_hash[:sha1_length]

        # Split filename and extension
        stem = Path(first_image).stem
        suffix = Path(first_image).suffix

        # Use template
        new_filename = template.format(stem=stem, sha1=short_sha1, suffix=suffix, sha1_length=sha1_length)
        
        # Sanitize filename for Windows (remove invalid characters)
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            new_filename = new_filename.replace(char, '_')
        
        new_path = os.path.join(directory, new_filename)

        # Rename
        os.rename(image_path, new_path)
        print(f"Renamed {first_image} to {new_filename} in {directory}")


def process_directories(root_dir, sha1_length=None, max_images=None):
    """Process all directories that contain images."""
    config = load_config()
    blacklist_keywords = config["rename"].get("blacklist_keywords", [])
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Check blacklist
        if any(keyword in dirpath for keyword in blacklist_keywords):
            print(f"Skipping blacklisted directory: {dirpath}")
            continue
        
        # Check if directory has direct image files
        image_files = get_image_files(dirpath)
        if image_files:
            rename_with_sha1(dirpath, sha1_length, max_images=max_images)