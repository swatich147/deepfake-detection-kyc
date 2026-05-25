"""Local file storage helpers for demo mode."""
import logging
import os
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)


class LocalMediaService:
    """Delete uploaded media from local disk."""

    def delete_path(self, path: str) -> None:
        if not path:
            return

        try:
            file_path = Path(path)
            if file_path.is_file():
                file_path.unlink()
                return

            media_root = Path(settings.MEDIA_ROOT)
            relative = Path(path)
            candidate = media_root / relative if not file_path.is_absolute() else file_path
            if candidate.is_file():
                candidate.unlink()
        except OSError as exc:
            logger.warning("Failed to delete media path %s: %s", path, exc)

    def delete_session_chunks(self, session_id: str) -> None:
        chunk_dir = Path(settings.MEDIA_ROOT) / 'chunks' / str(session_id)
        if not chunk_dir.exists():
            return

        for chunk_file in chunk_dir.iterdir():
            if chunk_file.is_file():
                chunk_file.unlink(missing_ok=True)

        try:
            chunk_dir.rmdir()
        except OSError:
            pass
