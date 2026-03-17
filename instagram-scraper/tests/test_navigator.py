import os
import sys


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from navigators.instagram_navigator import (
    InstagramNavigator,
    build_profile_reels_url,
    normalize_instagram_video_url,
)


def test_build_profile_reels_url_normalizes_username():
    assert build_profile_reels_url("@creator.name") == "https://www.instagram.com/creator.name/"


def test_build_profile_reels_url_rejects_invalid_username():
    with pytest.raises(ValueError):
        build_profile_reels_url("bad/user")


def test_normalize_instagram_video_url_forces_reel_canonical_path():
    assert normalize_instagram_video_url("https://www.instagram.com/p/ABC123/", force_reel=True) == "https://www.instagram.com/reel/ABC123/"
    assert normalize_instagram_video_url("https://www.instagram.com/reels/ABC123/", force_reel=True) == "https://www.instagram.com/reel/ABC123/"
    assert normalize_instagram_video_url("/reel/ABC123/", force_reel=True) == "https://www.instagram.com/reel/ABC123/"


def test_normalize_instagram_video_url_preserves_post_links_in_profile_mode():
    assert normalize_instagram_video_url("https://www.instagram.com/p/ABC123/") == "https://www.instagram.com/p/ABC123/"
    assert normalize_instagram_video_url("https://www.instagram.com/reels/ABC123/") == "https://www.instagram.com/reels/ABC123/"


def test_extract_profile_video_hrefs_filters_audio_and_deduplicates():
    class FakePage:
        def eval_on_selector_all(self, selector, script):
            return [
                "/p/ABC123/",
                "/reels/XYZ789/",
                "/reels/audio/123/",
                "/p/ABC123/",
                "/accounts/login/",
            ]

    navigator = InstagramNavigator()
    result = navigator._extract_profile_video_hrefs(FakePage())

    assert result == [
        "https://www.instagram.com/p/ABC123/",
        "https://www.instagram.com/reels/XYZ789/",
    ]
