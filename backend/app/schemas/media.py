"""Media upload schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class MediaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str
    url: str
    original_filename: str
    content_type: str
    size_bytes: int
    width: Optional[int] = None
    height: Optional[int] = None
    duration_seconds: Optional[float] = None
    debate_id: Optional[uuid.UUID] = None
    public: bool = True
    created_at: datetime
