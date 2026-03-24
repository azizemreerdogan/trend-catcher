import json
import os
import sys
from datetime import datetime, timezone


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.video_metadata import VideoMetadata
from storage.json_storage import JsonVideoStorage


def build_video(video_id: str) -> VideoMetadata:
    return VideoMetadata(
        video_url=f"https://www.instagram.com/reel/{video_id}/",
        video_id=video_id,
        author_username="creator",
        collected_at=datetime(2026, 3, 12, tzinfo=timezone.utc),
    )


def test_append_unique_creates_file_and_writes_items(tmp_path):
    storage_path = tmp_path / "data" / "videos.json"
    storage = JsonVideoStorage(storage_path)

    result = storage.append_unique([build_video("ABC123")])

    assert result.received_count == 1
    assert result.inserted_count == 1
    assert result.skipped_duplicates == 0

    payload = json.loads(storage_path.read_text(encoding="utf-8"))
    assert len(payload) == 1
    assert payload[0]["video_id"] == "ABC123"


def test_append_unique_skips_duplicate_video_ids(tmp_path):
    storage_path = tmp_path / "data" / "videos.json"
    storage = JsonVideoStorage(storage_path)

    storage.append_unique([build_video("ABC123")])
    result = storage.append_unique([build_video("ABC123"), build_video("XYZ789")])

    assert result.received_count == 2
    assert result.inserted_count == 1
    assert result.skipped_duplicates == 1

    items = storage.load_all()
    assert [item.video_id for item in items] == ["ABC123", "XYZ789"]
