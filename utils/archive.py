import logging
import tarfile
import zipfile
from pathlib import Path
from typing import Union

logger = logging.getLogger(__name__)

Archive = Union[zipfile.ZipFile, tarfile.TarFile]

def safe_extract(archive: Archive, dest: str) -> None:
    """Safely extract an archive to *dest* ensuring no path traversal.

    Raises RuntimeError if a member tries to escape the destination
    directory. Any extraction errors are logged and re-raised.
    """
    dest_path = Path(dest).resolve()
    try:
        if isinstance(archive, zipfile.ZipFile):
            members = archive.namelist()
            for member in members:
                member_path = dest_path / member
                if not member_path.resolve().is_relative_to(dest_path):
                    logger.warning("Path traversal attempt in zip member: %s", member)
                    raise RuntimeError(f"Unsafe path detected: {member}")
            archive.extractall(dest_path)
        elif isinstance(archive, tarfile.TarFile):
            members = archive.getmembers()
            for member in members:
                member_path = dest_path / member.name
                if not member_path.resolve().is_relative_to(dest_path):
                    logger.warning("Path traversal attempt in tar member: %s", member.name)
                    raise RuntimeError(f"Unsafe path detected: {member.name}")
            archive.extractall(dest_path)
        else:
            raise TypeError("Unsupported archive type")
    except Exception:
        logger.exception("Failed to safely extract archive")
        raise
