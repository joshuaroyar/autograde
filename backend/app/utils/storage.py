import os
from typing import Tuple
from fastapi import UploadFile


STORAGE_DIR = os.getenv("STORAGE_DIR", "/app/storage")

# Ensure base storage directories exist at import time
os.makedirs(STORAGE_DIR, exist_ok=True)
os.makedirs(os.path.join(STORAGE_DIR, "submissions"), exist_ok=True)
os.makedirs(os.path.join(STORAGE_DIR, "question_papers"), exist_ok=True)


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def submission_dir(submission_id: str) -> str:
    path = os.path.join(STORAGE_DIR, "submissions", submission_id)
    ensure_dir(path)
    return path


def question_paper_dir(subject_name: str, paper_id: int) -> str:
    # Sanitize subject name for filesystem use
    safe_subject = "".join(c for c in subject_name if c.isalnum() or c in ("_", "-")).strip() or "subject"
    path = os.path.join(STORAGE_DIR, "question_papers", safe_subject, str(paper_id))
    ensure_dir(path)
    return path


essential_chunk = 1024 * 1024  # 1MB

def save_upload_file(file: UploadFile, dest_path: str) -> Tuple[str, int]:
    """
    Save an UploadFile stream to the given destination path.
    Returns the final file path and number of bytes written.
    """
    ensure_dir(os.path.dirname(dest_path))
    written = 0
    with open(dest_path, "wb") as out:
        while True:
            chunk = file.file.read(essential_chunk)
            if not chunk:
                break
            out.write(chunk)
            written += len(chunk)
    return dest_path, written