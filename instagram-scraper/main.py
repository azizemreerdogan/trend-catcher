from __future__ import annotations

import argparse
from pathlib import Path

from navigators.instagram_navigator import build_profile_reels_url
from services.orchestrator import build_default_orchestrator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Instagram metadata scraper")
    parser.add_argument("--username", help="Scrape reels from a specific Instagram username")
    parser.add_argument("--max-links", type=int, default=0, help="Maximum number of reel links to process. Use 0 for unlimited")
    parser.add_argument("--headed", action="store_true", help="Run browser in headed mode")
    parser.add_argument("--slow-mo", type=int, default=0, help="Slow down browser actions in milliseconds")
    parser.add_argument("--keep-open", action="store_true", help="Keep browser open until Enter is pressed")
    parser.add_argument("--pause-before-extract", action="store_true", help="Pause after link discovery before metadata extraction")
    parser.add_argument("--step-mode", action="store_true", help="Wait for Enter before opening each collected reel")
    parser.add_argument("--download-videos", action="store_true", help="Download discovered videos into instagram-scraper/downloads")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    orchestrator = build_default_orchestrator(Path(__file__).resolve().parent)
    max_links = None if args.max_links == 0 else args.max_links
    start_url = build_profile_reels_url(args.username) if args.username else None
    try:
        result = orchestrator.run(
            max_links=max_links,
            start_url=start_url,
            headless=not args.headed,
            slow_mo_ms=args.slow_mo,
            keep_open=args.keep_open,
            pause_before_extract=args.pause_before_extract,
            step_mode=args.step_mode,
            download_videos=args.download_videos,
        )
    except Exception as error:
        print(f"Scraper failed: {error}")
        raise SystemExit(1) from error

    print(result.model_dump())
