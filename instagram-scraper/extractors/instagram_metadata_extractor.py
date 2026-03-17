from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from models.video_metadata import VideoMetadata
from navigators.instagram_navigator import normalize_instagram_video_url


class InstagramMetadataExtractor:
    def __init__(self, debug_dir: str | Path | None = None) -> None:
        self._debug_dir = Path(debug_dir) if debug_dir else None

    def extract(self, page, video_url: str) -> VideoMetadata | None:
        normalized_url = normalize_instagram_video_url(video_url)
        if not normalized_url:
            return None

        html, visible_text, network_payloads = self._collect_page_data(page, normalized_url)
        payload = extract_metadata_from_html(
            html,
            normalized_url,
            visible_text=visible_text,
            network_payloads=network_payloads,
        )
        if payload is None:
            return None

        if payload.get("view_count") is None and payload.get("author_username"):
            fallback_url = f"https://www.instagram.com/{payload['author_username']}/reels/"
            fallback_html, fallback_visible_text, fallback_network_payloads = self._collect_page_data(
                page,
                fallback_url,
            )
            fallback_payload = extract_metadata_from_html(
                fallback_html,
                normalized_url,
                visible_text=fallback_visible_text,
                network_payloads=fallback_network_payloads,
            )
            if fallback_payload and fallback_payload.get("view_count") is not None:
                payload["view_count"] = fallback_payload["view_count"]
                print(
                    f"View count profil fallback ile bulundu: "
                    f"{payload.get('video_id')} -> {payload['view_count']}"
                )

        if payload.get("view_count") is None and payload.get("video_id"):
            api_view_count = self._fetch_view_count_via_internal_api(page, payload["video_id"])
            if api_view_count is not None:
                payload["view_count"] = api_view_count
                print(
                    f"View count internal API ile bulundu: "
                    f"{payload.get('video_id')} -> {payload['view_count']}"
                )

        view_count = payload.get("view_count")
        if view_count is not None:
            print(f"View count bulundu: {payload.get('video_id')} -> {view_count}")
        else:
            print(f"View count bulunamadi: {payload.get('video_id')}")
            self._write_view_debug_dump(
                video_id=payload.get("video_id"),
                visible_text=visible_text,
                network_payloads=network_payloads,
            )

        payload["collected_at"] = datetime.now(timezone.utc)
        return VideoMetadata.model_validate(payload)

    def _collect_page_data(self, page, url: str) -> tuple[str, str, list[dict]]:
        network_payloads: list[dict] = []

        def _capture_response(response) -> None:
            try:
                if response.request.resource_type not in {"fetch", "xhr"}:
                    return
                if "instagram.com" not in response.url:
                    return

                content_type = response.header_value("content-type") or ""
                if "json" not in content_type.lower():
                    return

                payload = response.json()
                if isinstance(payload, dict):
                    network_payloads.append(payload)
            except Exception:
                return

        page.on("response", _capture_response)
        try:
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(1500)
        finally:
            page.remove_listener("response", _capture_response)

        html = page.content()
        visible_text = page.locator("body").inner_text()
        return html, visible_text, network_payloads

    def _fetch_view_count_via_internal_api(self, page, shortcode: str) -> int | None:
        endpoints = [
            f"/api/v1/media/shortcode/{shortcode}/info/",
            f"/api/v1/media/shortcode/{shortcode}/info/?__a=1&__d=dis",
        ]

        for endpoint in endpoints:
            try:
                payload = page.evaluate(
                    """
                    async ({ endpoint }) => {
                      const response = await fetch(endpoint, {
                        credentials: "include",
                        headers: {
                          "x-ig-app-id": "936619743392459"
                        }
                      });

                      if (!response.ok) {
                        return null;
                      }

                      return await response.json();
                    }
                    """,
                    {"endpoint": endpoint},
                )
            except Exception:
                continue

            if not isinstance(payload, dict):
                continue

            view_count = _extract_view_count_from_api_payload(payload, shortcode)
            if view_count is not None:
                return view_count

        return None

    def _write_view_debug_dump(
        self,
        video_id: str | None,
        visible_text: str,
        network_payloads: list[dict],
    ) -> None:
        if not self._debug_dir or not video_id:
            return

        self._debug_dir.mkdir(parents=True, exist_ok=True)
        payload_path = self._debug_dir / f"{video_id}_view_debug.json"
        text_path = self._debug_dir / f"{video_id}_visible_text.txt"

        matched_payload = _extract_media_dict_from_network_payloads(network_payloads, video_id)
        if matched_payload is None:
            matched_payload = {
                "message": "No shortcode-matched media dict found in captured network payloads.",
                "captured_payload_count": len(network_payloads),
            }

        payload_path.write_text(
            json.dumps(matched_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        text_path.write_text(visible_text, encoding="utf-8")
        print(f"View debug JSON saved to: {payload_path}")
        print(f"Visible text dump saved to: {text_path}")


def extract_metadata_from_html(
    html: str,
    video_url: str,
    visible_text: str | None = None,
    network_payloads: list[dict] | None = None,
) -> dict | None:
    shortcode = _extract_shortcode_from_url(video_url)
    network_media = _extract_media_dict_from_network_payloads(network_payloads or [], shortcode)

    modern_media = _extract_media_dict_for_shortcode(html, shortcode)
    if modern_media:
        modern_media = _merge_media_dicts(modern_media, network_media)
        return _build_metadata_payload(video_url, modern_media, visible_text=visible_text)

    shortcode_data = _extract_shortcode_media(html)
    if shortcode_data:
        shortcode_data = _merge_media_dicts(shortcode_data, network_media)
        return _build_metadata_payload(video_url, shortcode_data, visible_text=visible_text)

    page_data = _extract_fallback_page_data(html)
    if page_data:
        page_data = _merge_media_dicts(page_data, network_media)
        return _build_metadata_payload(video_url, page_data, visible_text=visible_text)

    if network_media:
        return _build_metadata_payload(video_url, network_media, visible_text=visible_text)

    return None


def _extract_shortcode_from_url(video_url: str) -> str | None:
    path_parts = [part for part in urlsplit(video_url).path.split("/") if part]
    if not path_parts:
        return None
    return path_parts[-1]


def _extract_media_dict_for_shortcode(html: str, shortcode: str | None) -> dict | None:
    if not shortcode:
        return None

    code_pattern = f'"code":"{shortcode}"'
    code_index = html.find(code_pattern)
    if code_index == -1:
        return None

    media_marker = '"media":{"__typename":"XDTMediaDict"'
    media_index = html.rfind(media_marker, 0, code_index)
    if media_index != -1:
        object_start = media_index + len('"media":')
        return _extract_balanced_json_object(html, object_start)

    direct_marker = '{"__typename":"XDTMediaDict"'
    direct_index = html.rfind(direct_marker, 0, code_index)
    if direct_index != -1:
        return _extract_balanced_json_object(html, direct_index)

    return None


def _extract_media_dict_from_network_payloads(
    payloads: list[dict],
    shortcode: str | None,
) -> dict | None:
    if not shortcode:
        return None

    for payload in payloads:
        candidate = _find_media_dict_by_shortcode(payload, shortcode)
        if candidate is not None:
            return candidate
    return None


def _extract_shortcode_media(html: str) -> dict | None:
    patterns = [
        re.compile(r'"shortcode_media"\s*:\s*(\{.*?\})\s*,\s*"dimensions"', re.DOTALL),
        re.compile(r'"xdt_shortcode_media"\s*:\s*(\{.*?\})\s*,\s*"viewer"', re.DOTALL),
    ]

    for pattern in patterns:
        match = pattern.search(html)
        if not match:
            continue
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            continue

    json_blob = _extract_json_script(html)
    if not json_blob:
        return None

    nested_candidate = (
        _find_nested_key(json_blob, "shortcode_media")
        or _find_nested_key(json_blob, "xdt_shortcode_media")
        or _find_nested_key(json_blob, "items")
    )
    if isinstance(nested_candidate, list) and nested_candidate:
        first_item = nested_candidate[0]
        if isinstance(first_item, dict):
            return first_item

    return nested_candidate if isinstance(nested_candidate, dict) else None


def _extract_fallback_page_data(html: str) -> dict | None:
    description = _extract_meta_content(html, "description")
    caption = _extract_caption(description)

    data = {
        "shortcode": _extract_meta_value(html, "og:url", r"/(?:reel|reels|p)/([A-Za-z0-9_-]+)/"),
        "owner": {"username": _extract_meta_value(html, "og:title", r"@([A-Za-z0-9._]+)")},
        "edge_media_preview_like": {"count": _extract_number_from_text(description, " likes")},
        "edge_media_to_comment": {"count": _extract_number_from_text(description, " comments")},
        "video_view_count": _extract_number_from_text(description, " views"),
        "taken_at_timestamp": _extract_timestamp(html),
        "display_url": _extract_meta_content(html, "og:image"),
        "edge_media_to_caption": {"edges": [{"node": {"text": caption}}] if caption else []},
    }
    return data if data["shortcode"] else None


def _build_metadata_payload(video_url: str, raw_data: dict, visible_text: str | None = None) -> dict:
    caption = _extract_caption_text(raw_data)

    posted_at = None
    timestamp = raw_data.get("taken_at_timestamp") or raw_data.get("taken_at")
    if timestamp:
        posted_at = datetime.fromtimestamp(timestamp, tz=timezone.utc)

    view_count, _ = _resolve_view_count(raw_data, visible_text=visible_text)

    return {
        "platform": "instagram",
        "video_url": normalize_instagram_video_url(video_url),
        "video_id": raw_data.get("shortcode") or raw_data.get("code"),
        "video_download_url": _extract_video_download_url(raw_data),
        "author_username": _extract_username(raw_data),
        "caption": caption,
        "view_count": view_count,
        "like_count": _extract_like_count(raw_data),
        "comment_count": _extract_comment_count(raw_data),
        "posted_at": posted_at,
        "thumbnail_url": _extract_thumbnail_url(raw_data),
    }


def _extract_json_script(html: str) -> dict | None:
    matches = re.findall(
        r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    for match in matches:
        try:
            parsed = json.loads(match)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _find_nested_key(data, target_key: str):
    if isinstance(data, dict):
        if target_key in data:
            return data[target_key]
        for value in data.values():
            found = _find_nested_key(value, target_key)
            if found is not None:
                return found
    elif isinstance(data, list):
        for item in data:
            found = _find_nested_key(item, target_key)
            if found is not None:
                return found
    return None


def _find_media_dict_by_shortcode(data, shortcode: str):
    if isinstance(data, dict):
        current_shortcode = data.get("code") or data.get("shortcode")
        if current_shortcode == shortcode:
            return data
        for value in data.values():
            found = _find_media_dict_by_shortcode(value, shortcode)
            if found is not None:
                return found
    elif isinstance(data, list):
        for item in data:
            found = _find_media_dict_by_shortcode(item, shortcode)
            if found is not None:
                return found
    return None


def _extract_view_count_from_api_payload(payload: dict, shortcode: str) -> int | None:
    media_dict = _find_media_dict_by_shortcode(payload, shortcode)
    if media_dict is not None:
        view_count, _ = _resolve_view_count(media_dict)
        if view_count is not None:
            return view_count

    items = payload.get("items")
    if isinstance(items, list) and items:
        for item in items:
            if isinstance(item, dict):
                view_count, _ = _resolve_view_count(item)
                if view_count is not None:
                    return view_count

    return None


def _merge_media_dicts(primary: dict, secondary: dict | None) -> dict:
    if not secondary:
        return primary

    merged = dict(primary)
    for key, value in secondary.items():
        if key not in merged or merged[key] in (None, "", [], {}):
            merged[key] = value
            continue

        if isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _merge_media_dicts(merged[key], value)

    return merged


def _extract_balanced_json_object(text: str, start_index: int) -> dict | None:
    if start_index < 0 or start_index >= len(text) or text[start_index] != "{":
        return None

    depth = 0
    in_string = False
    escape = False

    for index in range(start_index, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            continue
        if char == "{":
            depth += 1
            continue
        if char == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start_index : index + 1])
                except json.JSONDecodeError:
                    return None

    return None


def _extract_meta_content(html: str, property_name: str) -> str | None:
    match = re.search(
        rf'<meta[^>]+(?:property|name)="{re.escape(property_name)}"[^>]+content="([^"]*)"',
        html,
        flags=re.IGNORECASE,
    )
    return match.group(1) if match else None


def _extract_meta_value(html: str, property_name: str, pattern: str) -> str | None:
    content = _extract_meta_content(html, property_name)
    if not content:
        return None

    match = re.search(pattern, content)
    return match.group(1) if match else None


def _extract_number_from_text(text: str | None, suffix: str) -> int | None:
    if not text:
        return None

    match = re.search(rf'([\d.,]+)\s*{re.escape(suffix)}', text, flags=re.IGNORECASE)
    if not match:
        return None

    return _coerce_int(match.group(1))


def _extract_timestamp(html: str) -> int | None:
    candidates = [
        _extract_meta_content(html, "video:release_date"),
        _extract_meta_content(html, "article:published_time"),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            return int(datetime.fromisoformat(candidate.replace("Z", "+00:00")).timestamp())
        except ValueError:
            continue
    return None


def _extract_caption(description: str | None) -> str | None:
    if not description:
        return None

    parts = description.split(" on Instagram: ")
    if len(parts) != 2:
        return None

    return parts[1].strip(' "')


def _extract_caption_text(raw_data: dict) -> str | None:
    caption = raw_data.get("caption")
    if isinstance(caption, dict):
        return caption.get("text")
    if isinstance(caption, str):
        return caption

    caption_edges = raw_data.get("edge_media_to_caption", {}).get("edges", [])
    if caption_edges:
        return caption_edges[0].get("node", {}).get("text")
    return None


def _extract_username(raw_data: dict) -> str | None:
    user = raw_data.get("user")
    if isinstance(user, dict) and user.get("username"):
        return user.get("username")

    owner = raw_data.get("owner")
    if isinstance(owner, dict):
        return owner.get("username")

    return None


def _extract_like_count(raw_data: dict) -> int | None:
    return _coerce_int(
        raw_data.get("like_count")
        or raw_data.get("edge_media_preview_like", {}).get("count")
        or raw_data.get("fb_like_count")
    )


def _extract_comment_count(raw_data: dict) -> int | None:
    return _coerce_int(
        raw_data.get("comment_count")
        or raw_data.get("edge_media_to_comment", {}).get("count")
        or raw_data.get("fb_comment_count")
    )


def _resolve_view_count(raw_data: dict, visible_text: str | None = None) -> tuple[int | None, str | None]:
    direct_value = _coerce_int(
        raw_data.get("video_view_count")
        or raw_data.get("view_count")
        or raw_data.get("play_count")
    )
    if direct_value is not None:
        return direct_value, "payload"

    if visible_text:
        patterns = [
            r"([\d.,]+)\s+views",
            r"([\d.,]+)\s+plays",
            r"([\d.,]+)\s+g[oö]r[uü]nt[uü]lenme",
            r"([\d.,]+)\s+izlenme",
            r"([\d.,]+)\s+oynatma",
        ]
        for pattern in patterns:
            view_match = re.search(pattern, visible_text, flags=re.IGNORECASE)
            if view_match:
                return _coerce_int(view_match.group(1)), "visible_text"

    return None, None


def _extract_thumbnail_url(raw_data: dict) -> str | None:
    image_versions = raw_data.get("image_versions2", {}).get("candidates", [])
    if image_versions:
        return image_versions[0].get("url")

    return raw_data.get("display_url") or raw_data.get("thumbnail_src")


def _extract_video_download_url(raw_data: dict) -> str | None:
    direct_url = raw_data.get("video_url")
    if isinstance(direct_url, str) and direct_url:
        return direct_url

    video_versions = raw_data.get("video_versions")
    if isinstance(video_versions, list):
        best_candidate = _select_preferred_video_version(video_versions)
        if best_candidate is not None:
            return best_candidate.get("url")

    clips_metadata = raw_data.get("clips_metadata")
    if isinstance(clips_metadata, dict):
        original_media = clips_metadata.get("original_media")
        if isinstance(original_media, dict):
            nested_url = _extract_video_download_url(original_media)
            if nested_url:
                return nested_url

    return None


def _select_preferred_video_version(video_versions: list[dict]) -> dict | None:
    valid_candidates = [
        candidate
        for candidate in video_versions
        if isinstance(candidate, dict) and isinstance(candidate.get("url"), str) and candidate.get("url")
    ]
    if not valid_candidates:
        return None

    def _score(candidate: dict) -> tuple[int, int, int]:
        width = _coerce_int(candidate.get("width")) or 0
        height = _coerce_int(candidate.get("height")) or 0
        area = width * height
        bitrate = _coerce_int(candidate.get("bit_rate")) or _coerce_int(candidate.get("bandwidth")) or 0
        candidate_type = _coerce_int(candidate.get("type")) or 0
        return (area, bitrate, candidate_type)

    return min(valid_candidates, key=_score)


def _coerce_int(value) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        cleaned = value.replace(",", "").replace(".", "")
        if cleaned.isdigit():
            return int(cleaned)
    return None
