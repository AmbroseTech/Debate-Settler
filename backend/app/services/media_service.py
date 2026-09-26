"""Media storage service.

Handles secure persistence of user-uploaded images, videos and profile pictures.
Files are never accepted blindly (§13): the declared content type is checked
against an allowlist, image bytes are verified with Pillow, size limits are
enforced while streaming, and stored files always get a generated safe filename
(the client-supplied name is kept only as sanitized display metadata).

Stored paths are relative to ``settings.MEDIA_ROOT`` and are resolved through the
database — a client can never request an arbitrary filesystem path.
"""
from __future__ import annotations

import io
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple

from fastapi import UploadFile
from PIL import Image

from app.core.config import settings
from app.core.exceptions import ValidationError

# Generous cap on how much we will buffer for an image to verify/measure it.
_MAX_IMAGE_BYTES = settings.MAX_IMAGE_UPLOAD_MB * 1024 * 1024
_MAX_VIDEO_BYTES = settings.MAX_MEDIA_UPLOAD_MB * 1024 * 1024

_UNSAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")

# Leading magic bytes for the video containers we allow.
_VIDEO_SIGNATURES: Tuple[Tuple[bytes, int], ...] = (
    (b"ftyp", 4),   # mp4 / mov: bytes 4..8 are 'ftyp'
    (b"\x1a\x45\xdf\xa3", 0),  # webm / matroska EBML header
)


def media_root() -> str:
    root = os.path.abspath(settings.MEDIA_ROOT)
    os.makedirs(root, exist_ok=True)
    return root


def safe_display_name(original: Optional[str]) -> str:
    """Sanitize a client filename for display only (never used as the stored path)."""
    name = os.path.basename(original or "upload")
    name = _UNSAFE_NAME.sub("_", name).strip("._")
    return name[:180] or "upload"


def _extension_for(content_type: str) -> str:
    mapping = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "video/mp4": ".mp4",
        "video/quicktime": ".mov",
        "video/webm": ".webm",
    }
    return mapping.get(content_type, ".bin")


def _looks_like_video(head: bytes) -> bool:
    for signature, offset in _VIDEO_SIGNATURES:
        if head[offset:offset + len(signature)] == signature:
            return True
    return False


async def _measure_image(data: bytes) -> Tuple[int, int]:
    with Image.open(io.BytesIO(data)) as img:
        return img.width, img.height


async def save_upload(
    file: UploadFile,
    *,
    kind: str,
    owner_id: uuid.UUID,
    debate_id: Optional[uuid.UUID] = None,
    public: bool = True,
    duration_seconds: Optional[float] = None,
) -> dict:
    """Validate and persist an upload. Returns metadata for the Media row.

    ``kind`` is one of image | video | avatar. Raises ValidationError on any
    disallowed type or oversized payload.
    """
    content_type = (file.content_type or "").lower()

    if kind in ("image", "avatar"):
        if content_type not in settings.ALLOWED_IMAGE_TYPES:
            raise ValidationError("That image format isn't supported. Use JPEG, PNG, WEBP or GIF.")
        max_bytes = _MAX_IMAGE_BYTES
    elif kind == "video":
        if content_type not in settings.ALLOWED_VIDEO_TYPES:
            raise ValidationError("That video format isn't supported. Use MP4, WEBM or MOV.")
        max_bytes = _MAX_VIDEO_BYTES
    else:
        raise ValidationError("Unknown upload kind.")

    # Stream to a temporary buffer, enforcing the size cap as we go.
    buffer = io.BytesIO()
    total = 0
    chunk_size = 1024 * 256
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            limit_mb = max_bytes // (1024 * 1024)
            raise ValidationError(f"That file is too large. The limit is {limit_mb} MB.")
        buffer.write(chunk)

    if total == 0:
        raise ValidationError("The uploaded file is empty.")

    data = buffer.getvalue()
    head = data[:16]

    width = height = None
    if kind in ("image", "avatar"):
        # Verify the bytes really are the declared image type.
        try:
            width, height = await _measure_image(data)
        except Exception:
            raise ValidationError("That image file appears to be corrupted or mislabelled.")
    else:
        if not _looks_like_video(head):
            raise ValidationError("That video file appears to be corrupted or mislabelled.")

    now = datetime.now(timezone.utc)
    subdir = os.path.join(kind, now.strftime("%Y"), now.strftime("%m"))
    abs_dir = os.path.join(media_root(), subdir)
    os.makedirs(abs_dir, exist_ok=True)

    stored_name = f"{uuid.uuid4().hex}{_extension_for(content_type)}"
    abs_path = os.path.join(abs_dir, stored_name)
    with open(abs_path, "wb") as out:
        out.write(data)

    rel_path = os.path.join(subdir, stored_name).replace(os.sep, "/")

    return {
        "owner_id": owner_id,
        "debate_id": debate_id,
        "kind": kind,
        "file_path": rel_path,
        "original_filename": safe_display_name(file.filename),
        "content_type": content_type,
        "size_bytes": total,
        "width": width,
        "height": height,
        "duration_seconds": duration_seconds,
        "status": "ready",
        "public": public,
    }


def absolute_path(rel_path: str) -> str:
    """Resolve a stored relative path to an absolute path inside the media root.

    Guards against traversal: the resolved path must remain under media_root().
    """
    root = media_root()
    candidate = os.path.abspath(os.path.join(root, rel_path))
    if not candidate.startswith(root + os.sep) and candidate != root:
        raise ValidationError("Invalid media path.")
    return candidate
