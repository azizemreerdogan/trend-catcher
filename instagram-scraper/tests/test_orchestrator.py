import os
import sys
from datetime import datetime, timezone
from pathlib import Path


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from models.video_metadata import StorageResult, VideoMetadata
from services.orchestrator import InstagramScrapeOrchestrator


class FakePage:
    def close(self):
        return None


class FakeBrowserSession:
    def __init__(
        self,
        storage_state_path: str | Path,
        headless: bool = True,
        slow_mo_ms: int = 0,
        keep_open: bool = False,
    ) -> None:
        self.storage_state_path = Path(storage_state_path)
        self.headless = headless
        self.slow_mo_ms = slow_mo_ms
        self.keep_open = keep_open
        self.created_pages = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return None

    def new_page(self):
        page = FakePage()
        self.created_pages.append(page)
        return page

    def new_background_page(self):
        page = FakePage()
        self.created_pages.append(page)
        return page


class FakeNavigator:
    def iter_reel_links(self, page, max_links: int | None = None, start_url: str | None = None):
        links = [
            "https://www.instagram.com/reel/ABC123/",
            "https://www.instagram.com/reel/XYZ789/",
        ]
        if max_links is None:
            max_links = len(links)
        for link in links[:max_links]:
            yield link


class FakeExtractor:
    def extract(self, page, video_url: str):
        video_id = video_url.rstrip("/").split("/")[-1]
        return VideoMetadata(
            video_url=video_url,
            video_id=video_id,
            author_username="creator",
            collected_at=datetime(2026, 3, 12, tzinfo=timezone.utc),
        )


class FakeStorage:
    def __init__(self):
        self.saved_items = []
        self.call_count = 0

    def append_unique(self, items):
        self.call_count += 1
        self.saved_items.extend(items)
        if self.call_count == 1:
            return StorageResult(received_count=len(items), inserted_count=1, skipped_duplicates=0)
        return StorageResult(received_count=len(items), inserted_count=0, skipped_duplicates=1)


class FakeDownloader:
    def __init__(self):
        self.downloaded_ids = []

    def download(self, metadata):
        self.downloaded_ids.append(metadata.video_id)

        class Result:
            downloaded = True
            skipped = False
            file_path = Path(f"/tmp/{metadata.video_id}.mp4")

        return Result()


def test_orchestrator_runs_end_to_end_with_injected_dependencies():
    storage = FakeStorage()
    orchestrator = InstagramScrapeOrchestrator(
        navigator=FakeNavigator(),
        extractor=FakeExtractor(),
        storage=storage,
        browser_session_factory=FakeBrowserSession,
        storage_state_path="auth/state.json",
    )

    result = orchestrator.run(max_links=2, headless=True)

    assert result.discovered_links == 2
    assert result.extracted_items == 2
    assert result.inserted_items == 1
    assert result.skipped_duplicates == 1
    assert result.failed_items == 0
    assert len(storage.saved_items) == 2


def test_orchestrator_can_download_videos():
    storage = FakeStorage()
    downloader = FakeDownloader()
    orchestrator = InstagramScrapeOrchestrator(
        navigator=FakeNavigator(),
        extractor=FakeExtractor(),
        storage=storage,
        downloader=downloader,
        browser_session_factory=FakeBrowserSession,
        storage_state_path="auth/state.json",
    )

    result = orchestrator.run(max_links=1, headless=True, download_videos=True)

    assert result.downloaded_items == 1
    assert result.skipped_downloads == 0
    assert downloader.downloaded_ids == ["ABC123"]


def test_orchestrator_requires_storage_state_path():
    orchestrator = InstagramScrapeOrchestrator(
        navigator=FakeNavigator(),
        extractor=FakeExtractor(),
        storage=FakeStorage(),
        browser_session_factory=FakeBrowserSession,
    )

    with pytest.raises(ValueError):
        orchestrator.run(max_links=1)
