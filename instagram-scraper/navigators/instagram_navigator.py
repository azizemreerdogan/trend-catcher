from __future__ import annotations

import re
import time
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


INSTAGRAM_REELS_URL = "https://www.instagram.com/reels/"
INSTAGRAM_VIDEO_PATH_RE = re.compile(r"^/(reel|reels|p)/([A-Za-z0-9_-]+)/?$")
INSTAGRAM_USERNAME_RE = re.compile(r"^[A-Za-z0-9._]+$")
INSTAGRAM_PROFILE_VIDEO_LINK_RE = re.compile(
    r"^/(?:[A-Za-z0-9._]+/)?(p|reel|reels)/([A-Za-z0-9_-]+)/?$"
)


class InstagramNavigator:
    def __init__(
        self,
        scroll_pause_seconds: float = 1.0,
        max_scrolls: int = 5,
        debug_dir: str | Path | None = None,
    ) -> None:
        self._scroll_pause_seconds = scroll_pause_seconds
        self._max_scrolls = max_scrolls
        self._debug_dir = Path(debug_dir) if debug_dir else None

    def discover_reel_links(
        self,
        page,
        max_links: int | None = 20,
        start_url: str | None = None,
    ) -> list[str]:
        return list(self.iter_reel_links(page=page, max_links=max_links, start_url=start_url))

    def iter_reel_links(
        self,
        page,
        max_links: int | None = None,
        start_url: str | None = None,
    ):
        target_url = start_url or INSTAGRAM_REELS_URL
        profile_mode = bool(start_url and start_url != INSTAGRAM_REELS_URL)
        page.goto(target_url, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        self._ensure_logged_in(page)

        if profile_mode:
            yield from self._iter_profile_modal_links(page=page, max_links=max_links)
            return

        seen_links: set[str] = set()
        yielded_count = 0

        scroll_limit = None if max_links is None else self._max_scrolls + 1
        scroll_count = 0

        while scroll_limit is None or scroll_count < scroll_limit:
            page.wait_for_load_state("domcontentloaded")
            self._ensure_logged_in(page)
            current_link = self._normalize_new_link(page.url, seen_links, force_reel=not profile_mode)
            if current_link:
                yielded_count += 1
                print(f"Collected reel link: {current_link}")
                yield current_link
                if max_links is not None and yielded_count >= max_links:
                    return

            hrefs = page.eval_on_selector_all(
                "a[href]",
                "elements => elements.map(element => element.getAttribute('href'))",
            )
            print(f"Current page: {page.url}")
            print(f"Visible href count: {len(hrefs)}")
            for href in hrefs:
                normalized = self._normalize_new_link(href, seen_links, force_reel=not profile_mode)
                if not normalized:
                    continue
                yielded_count += 1
                print(f"Collected reel link: {normalized}")
                yield normalized
                if max_links is not None and yielded_count >= max_links:
                    return

            page.mouse.wheel(0, 1200)
            page.keyboard.press("PageDown")
            page.wait_for_timeout(int(self._scroll_pause_seconds * 1000))
            time.sleep(self._scroll_pause_seconds)
            scroll_count += 1

        if yielded_count == 0:
            self._write_debug_artifacts(page)
            raise RuntimeError(
                f"No reel links were found on {page.url}. "
                "The auth state may be expired, Instagram may have redirected the session, "
                "or the page markup may have changed."
            )

    def _iter_profile_modal_links(self, page, max_links: int | None = None):
        seen_links: set[str] = set()
        yielded_count = 0

        profile_links = self._collect_profile_video_links(page, max_links=max_links)
        if not profile_links:
            self._write_debug_artifacts(page)
            raise RuntimeError(
                f"No profile video links were found on {page.url}. "
                "The profile may not contain video posts/reels or the page markup may have changed."
            )

        for profile_link in profile_links:
            page.goto(profile_link, wait_until="domcontentloaded")
            page.wait_for_timeout(1500)
            self._ensure_logged_in(page)
            current_link = self._normalize_new_link(page.url, seen_links, force_reel=False)
            if current_link:
                yielded_count += 1
                print(f"Collected reel link: {current_link}")
                yield current_link
                if max_links is not None and yielded_count >= max_links:
                    return

    def _collect_profile_video_links(self, page, max_links: int | None = None) -> list[str]:
        collected_links: list[str] = []
        seen: set[str] = set()
        previous_count = -1
        stagnant_rounds = 0

        for _ in range(self._max_scrolls + 10):
            hrefs = self._extract_profile_video_hrefs(page)
            for href in hrefs:
                if href in seen:
                    continue
                seen.add(href)
                collected_links.append(href)
                print(f"Collected profile link: {href}")
                if max_links is not None and len(collected_links) >= max_links:
                    return collected_links

            if len(collected_links) == previous_count:
                stagnant_rounds += 1
            else:
                stagnant_rounds = 0
                previous_count = len(collected_links)

            if stagnant_rounds >= 2:
                break

            page.mouse.wheel(0, 2500)
            page.wait_for_timeout(int(self._scroll_pause_seconds * 1000))
            time.sleep(self._scroll_pause_seconds)

        return collected_links

    def _extract_profile_video_hrefs(self, page) -> list[str]:
        hrefs = page.eval_on_selector_all(
            "a[href]",
            "elements => elements.map(element => element.getAttribute('href'))",
        )
        normalized_links: list[str] = []
        seen: set[str] = set()

        for href in hrefs:
            if not href or not INSTAGRAM_PROFILE_VIDEO_LINK_RE.match(href):
                continue
            if href.startswith("/reels/audio/"):
                continue

            normalized = normalize_instagram_video_url(href, force_reel=False)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            normalized_links.append(normalized)

        return normalized_links

    def _ensure_logged_in(self, page) -> None:
        current_url = page.url
        if any(fragment in current_url for fragment in ("/accounts/login", "/challenge/", "/checkpoint/")):
            self._write_debug_artifacts(page)
            raise RuntimeError(
                f"Instagram session is not authenticated. Current page: {current_url}. "
                "Recreate auth/state.json with `python3 scripts/save_instagram_state.py`."
            )

    def _write_debug_artifacts(self, page) -> None:
        if self._debug_dir is None:
            return

        self._debug_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = self._debug_dir / "navigator_failure.png"
        html_path = self._debug_dir / "navigator_failure.html"

        page.screenshot(path=str(screenshot_path), full_page=True)
        html_path.write_text(page.content(), encoding="utf-8")
        print(f"Debug screenshot saved to: {screenshot_path}")
        print(f"Debug HTML saved to: {html_path}")

    def _normalize_new_link(
        self,
        raw_url: str | None,
        seen_links: set[str],
        force_reel: bool,
    ) -> str | None:
        normalized = normalize_instagram_video_url(raw_url, force_reel=force_reel)
        if not normalized or normalized in seen_links:
            return None

        seen_links.add(normalized)
        return normalized


def normalize_instagram_video_url(url: str | None, force_reel: bool = False) -> str | None:
    if not url:
        return None

    if url.startswith("/"):
        url = f"https://www.instagram.com{url}"

    parsed = urlsplit(url)
    if parsed.netloc not in {"instagram.com", "www.instagram.com"}:
        return None

    match = INSTAGRAM_VIDEO_PATH_RE.match(parsed.path)
    if not match:
        match = INSTAGRAM_PROFILE_VIDEO_LINK_RE.match(parsed.path)
    if not match:
        return None

    segment = "reel" if force_reel else match.group(1)
    normalized_path = f"/{segment}/{match.group(2)}/"
    return urlunsplit(("https", "www.instagram.com", normalized_path, "", ""))


def build_profile_reels_url(username: str) -> str:
    normalized_username = username.strip().lstrip("@")
    if not INSTAGRAM_USERNAME_RE.fullmatch(normalized_username):
        raise ValueError(f"Invalid Instagram username: {username}")

    return f"https://www.instagram.com/{normalized_username}/"
