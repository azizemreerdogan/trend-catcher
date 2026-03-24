from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from models.video_metadata import VideoMetadata


@dataclass
class CatcherVideoBundle:
    video_dir: Path
    video_file_path: Path


class CatcherDataExporter:
    def __init__(self, catcher_data_root: str | Path) -> None:
        self._catcher_data_root = Path(catcher_data_root)

    def prepare_bundle(self, metadata: VideoMetadata) -> CatcherVideoBundle:
        video_dir = self._catcher_data_root / metadata.video_id
        video_dir.mkdir(parents=True, exist_ok=True)

        self._write_metadata(video_dir, metadata)
        self._ensure_placeholder(video_dir / "vision_summary.json")
        self._ensure_placeholder(video_dir / "transcript.json")

        return CatcherVideoBundle(
            video_dir=video_dir,
            video_file_path=video_dir / "video.mp4",
        )

    def write_agent_error(self, video_id: str, stage: str, message: str) -> None:
        video_dir = self._catcher_data_root / video_id
        video_dir.mkdir(parents=True, exist_ok=True)

        target_name = "vision_summary.json" if stage == "vision" else "transcript.json"
        target_path = video_dir / target_name
        target_path.write_text(
            json.dumps(
                {
                    "status": "error",
                    "stage": stage,
                    "message": message,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def _write_metadata(self, video_dir: Path, metadata: VideoMetadata) -> None:
        metadata_path = video_dir / "video_metadata.json"
        payload = {
            "title": metadata.caption or "",
            "author": metadata.author_username or "",
            "platform": metadata.platform.capitalize(),
            "duration": 0,
            "video_id": metadata.video_id,
            "video_url": str(metadata.video_url),
            "video_download_url": str(metadata.video_download_url) if metadata.video_download_url else None,
            "thumbnail_url": str(metadata.thumbnail_url) if metadata.thumbnail_url else None,
            "view_count": metadata.view_count,
            "like_count": metadata.like_count,
            "comment_count": metadata.comment_count,
            "posted_at": metadata.posted_at.isoformat() if metadata.posted_at else None,
            "collected_at": metadata.collected_at.isoformat(),
        }
        metadata_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _ensure_placeholder(self, path: Path) -> None:
        if path.exists():
            return
        path.write_text(
            json.dumps({"status": "pending"}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
