"""Shared base class for all Page Objects."""
from __future__ import annotations

import logging
from pathlib import Path

from playwright.async_api import Locator, Page

from utils.helpers import timestamped_filename


class BasePage:
    def __init__(self, page: Page, screenshots_dir: Path, logger: logging.Logger) -> None:
        self.page = page
        self.screenshots_dir = screenshots_dir
        self.logger = logger

    async def goto(self, url: str) -> None:
        self.log_step(f"Navigating to {url}")
        await self.page.goto(url)
        await self.wait_for_load()

    async def wait_for_load(self, state: str = "load") -> None:
        await self.page.wait_for_load_state(state)

    async def screenshot(self, name: str) -> Path:
        path = self.screenshots_dir / timestamped_filename(name)
        await self.page.screenshot(path=str(path), full_page=True)
        self.log_step(f"Saved screenshot: {path}")
        return path

    async def scroll_into_view(self, locator: Locator) -> None:
        await locator.scroll_into_view_if_needed()

    async def dismiss_cookie_banner(self) -> None:
        """Best-effort dismissal of eBay's cookie/consent banner; not all sessions show it."""
        try:
            button = self.page.get_by_role("button", name="Accept All Cookies")
            await button.click(timeout=3000)
            self.log_step("Dismissed cookie banner")
        except Exception:
            self.log_step("No cookie banner to dismiss")

    def log_step(self, message: str) -> None:
        self.logger.info(message)
