from __future__ import annotations

from pathlib import Path


class BrowserSession:
    def __init__(
        self,
        storage_state_path: str | Path,
        headless: bool = True,
        slow_mo_ms: int = 0,
        keep_open: bool = False,
    ) -> None:
        self._storage_state_path = Path(storage_state_path)
        self._headless = headless
        self._slow_mo_ms = slow_mo_ms
        self._keep_open = keep_open
        self._playwright = None
        self._browser = None
        self._context = None
        self._background_browser = None
        self._background_context = None

    def __enter__(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as error:
            raise RuntimeError(
                "Playwright is not installed. Run `python3 -m pip install playwright` and `python3 -m playwright install`."
            ) from error

        if not self._storage_state_path.exists():
            raise FileNotFoundError(
                f"Instagram auth state file not found: {self._storage_state_path}. "
                "Run `python3 scripts/save_instagram_state.py` first."
            )

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=self._headless,
            slow_mo=self._slow_mo_ms,
        )
        self._context = self._browser.new_context(storage_state=str(self._storage_state_path))

        self._background_browser = self._playwright.chromium.launch(headless=True)
        self._background_context = self._background_browser.new_context(
            storage_state=str(self._storage_state_path)
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._keep_open:
            print("Browser acik birakildi. Kapatmak icin terminalde Enter tusuna basin.")
            input()

        if self._background_context is not None:
            self._background_context.close()
            self._background_context = None
        if self._background_browser is not None:
            self._background_browser.close()
            self._background_browser = None
        if self._context is not None:
            self._context.close()
            self._context = None
        if self._browser is not None:
            self._browser.close()
            self._browser = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None

    def new_page(self):
        if self._context is None:
            raise RuntimeError("Browser session is not started.")
        return self._context.new_page()

    def new_background_page(self):
        if self._background_context is None:
            raise RuntimeError("Background browser session is not started.")
        return self._background_context.new_page()
