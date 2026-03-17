import os
import sys


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from extractors.instagram_metadata_extractor import (
    extract_metadata_from_html,
    _extract_view_count_from_api_payload,
)


def test_extract_metadata_from_shortcode_media_html():
    html = """
    <html>
      <head>
        <meta property="og:url" content="https://www.instagram.com/reel/ABC123/" />
      </head>
      <body>
        <script>
          window.__additionalDataLoaded('/reel/ABC123/', {
            "graphql": {
              "shortcode_media": {
                "shortcode": "ABC123",
                "owner": {"username": "creator_name"},
                "edge_media_to_caption": {"edges": [{"node": {"text": "caption text"}}]},
                "edge_media_preview_like": {"count": 456},
                "edge_media_to_comment": {"count": 12},
                "video_view_count": 12345,
                "taken_at_timestamp": 1773310500,
                "display_url": "https://cdn.example.com/thumb.jpg"
              },
              "dimensions": {"height": 1080}
            }
          });
        </script>
      </body>
    </html>
    """

    payload = extract_metadata_from_html(html, "https://www.instagram.com/reel/ABC123/")

    assert payload is not None
    assert payload["video_id"] == "ABC123"
    assert payload["video_download_url"] is None
    assert payload["author_username"] == "creator_name"
    assert payload["caption"] == "caption text"
    assert payload["view_count"] == 12345
    assert payload["like_count"] == 456
    assert payload["comment_count"] == 12
    assert payload["thumbnail_url"] == "https://cdn.example.com/thumb.jpg"


def test_extract_metadata_from_meta_tags_when_json_missing():
    html = """
    <html>
      <head>
        <meta property="og:url" content="https://www.instagram.com/reel/XYZ789/" />
        <meta property="og:title" content="@creator_name on Instagram" />
        <meta property="description" content="1,234 views, 55 likes, 4 comments - creator_name on Instagram: &quot;fallback caption&quot;" />
        <meta property="article:published_time" content="2026-03-12T10:15:00+00:00" />
        <meta property="og:image" content="https://cdn.example.com/fallback.jpg" />
      </head>
    </html>
    """

    payload = extract_metadata_from_html(html, "https://www.instagram.com/reel/XYZ789/")

    assert payload is not None
    assert payload["video_id"] == "XYZ789"
    assert payload["video_download_url"] is None
    assert payload["author_username"] == "creator_name"
    assert payload["view_count"] == 1234
    assert payload["like_count"] == 55
    assert payload["comment_count"] == 4
    assert payload["thumbnail_url"] == "https://cdn.example.com/fallback.jpg"


def test_extract_metadata_from_modern_xdt_media_payload():
    html = """
    <html>
      <body>
        <script>
          {"require":[["X", "Y", {"__bbox":{"result":{"data":{"xdt_api__v1__clips__home__connection_v2":{"edges":[{"node":{"media":{"__typename":"XDTMediaDict","code":"ABC123","user":{"username":"creator_name"},"like_count":456,"comment_count":12,"taken_at":1773310500,"caption":{"text":"caption text"},"image_versions2":{"candidates":[{"url":"https://cdn.example.com/thumb.jpg"}]}}}}]}}}}}]]}
        </script>
      </body>
    </html>
    """

    payload = extract_metadata_from_html(html, "https://www.instagram.com/reels/ABC123/")

    assert payload is not None
    assert payload["video_id"] == "ABC123"
    assert payload["video_download_url"] is None
    assert payload["author_username"] == "creator_name"
    assert payload["caption"] == "caption text"
    assert payload["like_count"] == 456
    assert payload["comment_count"] == 12
    assert payload["thumbnail_url"] == "https://cdn.example.com/thumb.jpg"


def test_extract_metadata_prefers_network_view_count_when_html_lacks_it():
    html = """
    <html>
      <body>
        <script>
          {"require":[["X", "Y", {"__bbox":{"result":{"data":{"xdt_api__v1__clips__home__connection_v2":{"edges":[{"node":{"media":{"__typename":"XDTMediaDict","code":"ABC123","user":{"username":"creator_name"},"like_count":456,"comment_count":12,"taken_at":1773310500,"caption":{"text":"caption text"}}}}]}}}}}]]}
        </script>
      </body>
    </html>
    """
    network_payloads = [
        {
            "data": {
                "media": {
                    "code": "ABC123",
                    "view_count": 987654,
                }
            }
        }
    ]

    payload = extract_metadata_from_html(
        html,
        "https://www.instagram.com/reels/ABC123/",
        network_payloads=network_payloads,
    )

    assert payload is not None
    assert payload["video_id"] == "ABC123"
    assert payload["view_count"] == 987654


def test_extract_metadata_includes_video_download_url():
    html = """
    <html>
      <body>
        <script>
          {"require":[["X", "Y", {"__bbox":{"result":{"data":{"xdt_api__v1__clips__home__connection_v2":{"edges":[{"node":{"media":{"__typename":"XDTMediaDict","code":"ABC123","user":{"username":"creator_name"},"video_versions":[{"url":"https://cdn.example.com/video.mp4"}]}}}]}}}}}]]}
        </script>
      </body>
    </html>
    """

    payload = extract_metadata_from_html(html, "https://www.instagram.com/reels/ABC123/")

    assert payload is not None
    assert payload["video_download_url"] == "https://cdn.example.com/video.mp4"


def test_extract_metadata_prefers_smallest_video_variant_for_download():
    html = """
    <html>
      <body>
        <script>
          {"require":[["X", "Y", {"__bbox":{"result":{"data":{"xdt_api__v1__clips__home__connection_v2":{"edges":[{"node":{"media":{"__typename":"XDTMediaDict","code":"ABC123","user":{"username":"creator_name"},"video_versions":[{"url":"https://cdn.example.com/video-large.mp4","width":1080,"height":1920,"bandwidth":900000},{"url":"https://cdn.example.com/video-small.mp4","width":540,"height":960,"bandwidth":300000}]}}}]}}}}}]]}
        </script>
      </body>
    </html>
    """

    payload = extract_metadata_from_html(html, "https://www.instagram.com/reels/ABC123/")

    assert payload is not None
    assert payload["video_download_url"] == "https://cdn.example.com/video-small.mp4"


def test_extract_view_count_from_internal_api_payload():
    payload = {
        "items": [
            {
                "code": "ABC123",
                "view_count": 555000,
            }
        ]
    }

    assert _extract_view_count_from_api_payload(payload, "ABC123") == 555000
