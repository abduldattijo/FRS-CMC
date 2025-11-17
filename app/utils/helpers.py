"""
Helper utility functions
"""

import os
from pathlib import Path
from typing import List


def ensure_dir(directory: str or Path) -> None:
    """
    Ensure a directory exists, create if it doesn't

    Args:
        directory: Directory path
    """
    Path(directory).mkdir(parents=True, exist_ok=True)


def get_file_size_mb(file_path: str) -> float:
    """
    Get file size in megabytes

    Args:
        file_path: Path to file

    Returns:
        File size in MB
    """
    return os.path.getsize(file_path) / (1024 * 1024)


def is_valid_video_format(filename: str, allowed_formats: List[str]) -> bool:
    """
    Check if a file has a valid video format

    Args:
        filename: Filename to check
        allowed_formats: List of allowed extensions (e.g., ['.mp4', '.avi'])

    Returns:
        True if valid format
    """
    ext = os.path.splitext(filename)[1].lower()
    return ext in allowed_formats


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path traversal

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove any directory paths
    filename = os.path.basename(filename)

    # Replace unsafe characters
    unsafe_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*']
    for char in unsafe_chars:
        filename = filename.replace(char, '_')

    return filename
