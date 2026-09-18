"""Debate categories."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel

# Canonical category list from the build prompt (§8).
DEFAULT_CATEGORIES = [
    "Sports", "Technology", "AI", "Programming", "Fashion", "Beauty", "Music",
    "Entertainment", "Business", "Education", "Science", "Gaming", "Lifestyle",
    "Cars", "Travel", "Food", "Movies", "Social", "Politics", "Other",
]


class Category(BaseModel):
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(60), unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(60), unique=True, index=True, nullable=False)
    icon: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
