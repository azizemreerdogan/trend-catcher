from __future__ import annotations

import time
from pathlib import Path

from extractors.instagram_metadata_extractor import InstagramMetadataExtractor
from models.video_metadata import ScrapeResult, VideoMetadata
from navigators.instagram_navigator import InstagramNavigator
from services.browser_session import BrowserSession
from services.catcher_data_exporter import CatcherDataExporter
from services.video_downloader import InstagramVideoDownloader
from services.vision_agent_runner import VisionAgentRunner
from storage.json_storage import JsonVideoStorage


class InstagramScrapeOrchestrator:
    def __init__(
        self,
        navigator: InstagramNavigator,
        extractor: InstagramMetadataExtractor,
        storage: JsonVideoStorage,
        downloader: InstagramVideoDownloader | None = None,
        catcher_exporter: CatcherDataExporter | None = None,
        vision_agent_runner: VisionAgentRunner | None = None,
        browser_session_factory=BrowserSession,
        storage_state_path: str | Path | None = None,
    ) -> None:
        self._navigator = navigator
        self._extractor = extractor
        self._storage = storage
        self._downloader = downloader
        self._catcher_exporter = catcher_exporter
        self._vision_agent_runner = vision_agent_runner
        self._browser_session_factory = browser_session_factory
        self._storage_state_path = Path(storage_state_path) if storage_state_path else None

    def run(
        self,
        max_links: int | None = 20,
        start_url: str | None = None,
        headless: bool = True,
        slow_mo_ms: int = 0,
        keep_open: bool = False,
        pause_before_extract: bool = False,
        step_mode: bool = False,
        download_videos: bool = False,
        run_vision_agent: bool = False,
    ) -> ScrapeResult:
        if self._storage_state_path is None:
            raise ValueError("storage_state_path is required for Instagram scraping.")

        extracted_items = 0
        inserted_items = 0
        skipped_duplicates = 0
        failed_items = 0
        discovered_links = 0
        downloaded_items = 0
        skipped_downloads = 0

        with self._browser_session_factory(
            storage_state_path=self._storage_state_path,
            headless=headless,
            slow_mo_ms=slow_mo_ms,
            keep_open=keep_open,
        ) as browser_session:
            feed_page = browser_session.new_page()
            print("Reels sayfasi aciliyor...")
            if max_links is None:
                print("Sonsuz mod aktif. Durdurmak icin Ctrl+C kullanin.")

            try:
                for link in self._navigator.iter_reel_links(
                    page=feed_page,
                    max_links=max_links,
                    start_url=start_url,
                ):
                    discovered_links += 1
                    if pause_before_extract and discovered_links == 1:
                        print("Ilk link bulundu. Metadata asamasina gecmek icin Enter tusuna basin.")
                        input()

                    if step_mode:
                        print("Siradaki videoya gitmek icin Enter tusuna basin.")
                        input()

                    try:
                        print(f"Metadata cekiliyor: {link}")
                        metadata = self._extract_with_retry(browser_session, link)
                        if metadata is None:
                            failed_items += 1
                            continue

                        extracted_items += 1
                        storage_result = self._storage.append_unique([metadata])
                        inserted_items += storage_result.inserted_count
                        skipped_duplicates += storage_result.skipped_duplicates
                        print(
                            "JSON update:"
                            f" inserted={storage_result.inserted_count}"
                            f" skipped={storage_result.skipped_duplicates}"
                            " path=instagram-scraper/data/videos.json"
                        )

                        bundle = None
                        if self._catcher_exporter is not None:
                            bundle = self._catcher_exporter.prepare_bundle(metadata)
                            print(f"Catcher bundle hazirlandi: {bundle.video_dir}")

                        if download_videos and self._downloader is not None:
                            try:
                                target_path = bundle.video_file_path if bundle is not None else None
                                download_result = self._downloader.download(metadata, target_path=target_path)
                                downloaded_items += int(download_result.downloaded)
                                skipped_downloads += int(download_result.skipped)
                                if download_result.file_path:
                                    action = "Downloaded" if download_result.downloaded else "Skipped download"
                                    print(f"{action}: {download_result.file_path}")
                                if (
                                    run_vision_agent
                                    and self._vision_agent_runner is not None
                                    and (
                                        download_result.downloaded
                                        or (
                                            download_result.file_path is not None
                                            and download_result.file_path.exists()
                                        )
                                    )
                                ):
                                    run_result = self._vision_agent_runner.run(metadata.video_id)
                                    if run_result.return_code == 0:
                                        print(f"Vision agent tamamlandi: {metadata.video_id}")
                                    else:
                                        if self._catcher_exporter is not None:
                                            self._catcher_exporter.write_agent_error(
                                                metadata.video_id,
                                                stage="vision",
                                                message=f"vision-agent exited with code {run_result.return_code}",
                                            )
                                            self._catcher_exporter.write_agent_error(
                                                metadata.video_id,
                                                stage="transcript",
                                                message=f"vision-agent exited with code {run_result.return_code}",
                                            )
                                        print(
                                            f"Vision agent failed for {metadata.video_id} "
                                            f"with exit code {run_result.return_code}"
                                        )
                            except Exception as error:
                                print(f"Video download failed for {link}: {error}")
                    except Exception as error:
                        failed_items += 1
                        print(f"Metadata extraction failed for {link}: {error}")
            except KeyboardInterrupt:
                print("\nScraping kullanici tarafindan durduruldu.")
            except Exception as error:
                print(f"\nNavigator stopped early: {error}")
                print("Collected data has already been written to JSON.")

            feed_page.close()

        return ScrapeResult(
            discovered_links=discovered_links,
            extracted_items=extracted_items,
            inserted_items=inserted_items,
            skipped_duplicates=skipped_duplicates,
            failed_items=failed_items,
            downloaded_items=downloaded_items,
            skipped_downloads=skipped_downloads,
        )

    def _extract_with_retry(self, browser_session, link: str) -> VideoMetadata | None:
        metadata = self._extract_once(browser_session, link)
        if metadata is None:
            return None

        if metadata.view_count is not None:
            return metadata

        print(f"View count eksik, tekrar denenecek: {metadata.video_id}")
        time.sleep(1)
        retried_metadata = self._extract_once(browser_session, link)
        return retried_metadata or metadata

    def _extract_once(self, browser_session, link: str) -> VideoMetadata | None:
        detail_page = browser_session.new_background_page()
        try:
            return self._extractor.extract(detail_page, link)
        finally:
            detail_page.close()


def build_default_orchestrator(project_root: str | Path | None = None) -> InstagramScrapeOrchestrator:
    scraper_root = Path(project_root) if project_root else Path(__file__).resolve().parents[1]
    storage = JsonVideoStorage(scraper_root / "data" / "videos.json")
    storage_state_path = scraper_root / "auth" / "state.json"

    return InstagramScrapeOrchestrator(
        navigator=InstagramNavigator(debug_dir=scraper_root / "debug"),
        extractor=InstagramMetadataExtractor(debug_dir=scraper_root / "debug"),
        storage=storage,
        downloader=InstagramVideoDownloader(scraper_root / "downloads"),
        catcher_exporter=CatcherDataExporter(scraper_root.parent / "catcher-data"),
        vision_agent_runner=VisionAgentRunner(scraper_root.parent),
        storage_state_path=storage_state_path,
    )
