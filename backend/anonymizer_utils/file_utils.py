"""File utility functions for the Document Anonymizer."""

import os
import uuid
import time
import shutil
from pathlib import Path
from datetime import datetime, timedelta

try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ANONYMIZER_UPLOAD_DIR as UPLOAD_DIR, ANONYMIZER_SUPPORTED_FORMATS as SUPPORTED_FORMATS
from config import settings
TEMP_RETENTION_HOURS = settings.ANONYMIZER_RETENTION_HOURS


def detect_file_type(file_path: Path) -> str:
    """
    Detect the MIME type of a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        MIME type string
    """
    if HAS_MAGIC:
        mime = magic.Magic(mime=True)
        return mime.from_file(str(file_path))
    else:
        # Fallback to extension-based detection
        ext = file_path.suffix.lower()
        return SUPPORTED_FORMATS.get(ext, "application/octet-stream")


def get_file_extension(filename: str) -> str:
    """
    Get the file extension from filename.
    
    Args:
        filename: Name of the file
        
    Returns:
        File extension including the dot (e.g., '.docx')
    """
    return Path(filename).suffix.lower()


def generate_task_id() -> str:
    """
    Generate a unique task ID for document processing.
    
    Returns:
        UUID string
    """
    return str(uuid.uuid4())


def save_uploaded_file(file_content: bytes, filename: str, task_id: str) -> Path:
    """
    Save an uploaded file to the upload directory.
    
    Args:
        file_content: File content as bytes
        filename: Original filename
        task_id: Task ID for organizing files
        
    Returns:
        Path to the saved file
    """
    # Create task-specific directory
    task_dir = UPLOAD_DIR / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    
    # Sanitize filename
    safe_filename = "".join(c for c in filename if c.isalnum() or c in ".-_")
    if not safe_filename:
        safe_filename = "document"
    
    # Add extension if missing
    ext = get_file_extension(filename)
    if not safe_filename.endswith(ext):
        safe_filename += ext
    
    # Save original file
    original_path = task_dir / f"original_{safe_filename}"
    with open(original_path, "wb") as f:
        f.write(file_content)
    
    return original_path


def get_output_path(task_id: str, original_filename: str) -> Path:
    """
    Get the output path for an anonymized file.
    
    Args:
        task_id: Task ID
        original_filename: Original filename
        
    Returns:
        Path for the output file
    """
    task_dir = UPLOAD_DIR / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate anonymized filename
    ext = get_file_extension(original_filename)
    safe_name = "".join(c for c in original_filename if c.isalnum() or c in ".-_")
    base_name = safe_name.replace(ext, "") if safe_name.endswith(ext) else safe_name
    
    return task_dir / f"anonymized_{base_name}{ext}"


def cleanup_old_files():
    """
    Remove files older than TEMP_RETENTION_HOURS.
    """
    if not UPLOAD_DIR.exists():
        return
    
    cutoff_time = datetime.now() - timedelta(hours=TEMP_RETENTION_HOURS)
    
    for task_dir in UPLOAD_DIR.iterdir():
        if task_dir.is_dir():
            # Check modification time
            mtime = datetime.fromtimestamp(task_dir.stat().st_mtime)
            if mtime < cutoff_time:
                shutil.rmtree(task_dir, ignore_errors=True)


def get_task_files(task_id: str) -> dict:
    """
    Get all files associated with a task.
    
    Args:
        task_id: Task ID
        
    Returns:
        Dictionary with file paths
    """
    task_dir = UPLOAD_DIR / task_id
    
    if not task_dir.exists():
        return {}
    
    files = {}
    for file_path in task_dir.iterdir():
        if file_path.name.startswith("original_"):
            files["original"] = file_path
        elif file_path.name.startswith("anonymized_"):
            files["anonymized"] = file_path
        elif file_path.name == "mapping.json":
            files["mapping"] = file_path
    
    return files


def delete_task_files(task_id: str):
    """
    Delete all files associated with a task.
    
    Args:
        task_id: Task ID
    """
    task_dir = UPLOAD_DIR / task_id
    if task_dir.exists():
        shutil.rmtree(task_dir, ignore_errors=True)


