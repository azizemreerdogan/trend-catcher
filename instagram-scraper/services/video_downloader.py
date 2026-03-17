from __future__ import annotations

import ssl
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen

from models.video_metadata import VideoMetadata


@dataclass
class DownloadResult:
    downloaded: bool
    skipped: bool
    file_path: Path | None = None


class InstagramVideoDownloader:
    def __init__(self, download_dir: str | Path) -> None:
        self._download_dir = Path(download_dir)
        self._ssl_context = self._build_ssl_context()

    def download(self, metadata: VideoMetadata) -> DownloadResult:
        if not metadata.video_download_url:
            return DownloadResult(downloaded=False, skipped=True)

        self._download_dir.mkdir(parents=True, exist_ok=True)
        target_path = self._download_dir / f"{metadata.video_id}.mp4"
        if target_path.exists():
            return DownloadResult(downloaded=False, skipped=True, file_path=target_path)

        request = Request(
            str(metadata.video_download_url),
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/123.0.0.0 Safari/537.36"
                )
            },
        )

        with urlopen(request, timeout=60, context=self._ssl_context) as response:
            target_path.write_bytes(response.read())

        return DownloadResult(downloaded=True, skipped=False, file_path=target_path)

    def _build_ssl_context(self) -> ssl.SSLContext:
        try:
            import certifi

            return ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            return ssl.create_default_context()
