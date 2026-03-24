import json
import os
import sys
from datetime import datetime, timezone


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.video_metadata import VideoMetadata
from services.catcher_data_exporter import CatcherDataExporter


def test_prepare_bundle_creates_catcher_data_structure(tmp_path):
    exporter = CatcherDataExporter(tmp_path / "catcher-data")
    metadata = VideoMetadata(
        video_url="https://www.instagram.com/reel/ABC123/",
        video_id="ABC123",
        video_download_url="https://cdn.example.com/video.mp4",
        author_username="creator_name",
        caption="sample caption",
        collected_at=datetime(2026, 3, 17, tzinfo=timezone.utc),
    )

    bundle = exporter.prepare_bundle(metadata)

    assert bundle.video_dir == tmp_path / "catcher-data" / "ABC123"
    assert bundle.video_file_path == tmp_path / "catcher-data" / "ABC123" / "video.mp4"
    assert (bundle.video_dir / "vision_summary.json").exists()
    assert (bundle.video_dir / "transcript.json").exists()

    video_metadata_payload = json.loads((bundle.video_dir / "video_metadata.json").read_text(encoding="utf-8"))
    assert video_metadata_payload["author"] == "creator_name"
    assert video_metadata_payload["title"] == "sample caption"
    assert video_metadata_payload["platform"] == "Instagram"
