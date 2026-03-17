from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class VideoMetadata(BaseModel):
    model_config = ConfigDict(extra="ignore")

    platform: Literal["instagram"] = "instagram"
    video_url: HttpUrl
    video_id: str = Field(min_length=1)
    video_download_url: HttpUrl | None = None
    author_username: str | None = None
    caption: str | None = None
    view_count: int | None = Field(default=None, ge=0)
    like_count: int | None = Field(default=None, ge=0)
    comment_count: int | None = Field(default=None, ge=0)
    posted_at: datetime | None = None
    thumbnail_url: HttpUrl | None = None
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StorageResult(BaseModel):
    received_count: int
    inserted_count: int
    skipped_duplicates: int


class ScrapeResult(BaseModel):
    discovered_links: int
    extracted_items: int
    inserted_items: int
    skipped_duplicates: int
    failed_items: int
    downloaded_items: int = 0
    skipped_downloads: int = 0
