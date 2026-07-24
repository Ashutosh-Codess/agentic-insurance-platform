"""Small helper for saving an uploaded file to disk with a collision-safe
name. Kept as a plain function -- no storage abstraction/interface, since
there is exactly one storage backend (local disk) in this project."""
import os
import uuid

from fastapi import UploadFile


def save_upload(file: UploadFile, directory: str, prefix: str) -> str:
    os.makedirs(directory, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1]
    filename = f"{prefix}_{uuid.uuid4().hex}{ext}"
    dest_path = os.path.join(directory, filename)
    with open(dest_path, "wb") as f:
        f.write(file.file.read())
    return dest_path
