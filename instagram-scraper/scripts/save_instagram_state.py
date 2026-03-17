from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


AUTH_DIR = PROJECT_ROOT / "auth"
STATE_PATH = AUTH_DIR / "state.json"


def main() -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise RuntimeError(
            "Playwright is not installed. Run `python3 -m pip install playwright` and `python3 -m playwright install`."
        ) from error

    AUTH_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://www.instagram.com/accounts/login/", wait_until="domcontentloaded")

        print("Instagram login sayfasi acildi.")
        print("Manuel olarak giris yapin, sonra terminale donup Enter tusuna basin.")
        input()

        context.storage_state(path=str(STATE_PATH))
        print(f"Auth state kaydedildi: {STATE_PATH}")

        context.close()
        browser.close()


if __name__ == "__main__":
    main()
