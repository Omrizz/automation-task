"""eBay search results page: price filter, item extraction (XPath), pagination."""
from __future__ import annotations

import re

from playwright.async_api import Locator

from pages.base_page import BasePage
from utils.helpers import parse_price

NEXT_PAGE_NAME = re.compile("next", re.I)
MIN_PRICE_NAME = re.compile("Minimum Value", re.I)
MAX_PRICE_NAME = re.compile("Maximum Value", re.I)


class SearchResultsPage(BasePage):
    # Current eBay SRP template (verified live): semantic BEM classes on div wrappers.
    RESULT_ITEM_XPATH = "//div[contains(concat(' ', normalize-space(@class), ' '), ' su-item-card ')]"
    ITEM_LINK_XPATH = ".//a[contains(@class,'su-media-container__link')]"
    ITEM_PRICE_XPATH = ".//span[contains(@class,'su-item-card__price')]"

    # eBay occasionally A/B-tests an older list-based SRP template.
    LEGACY_ITEM_XPATH = "//li[contains(concat(' ', normalize-space(@class), ' '), ' s-item ')]"
    LEGACY_ITEM_LINK_XPATH = ".//a[contains(@class,'s-item__link')]"
    LEGACY_ITEM_PRICE_XPATH = ".//span[contains(@class,'s-item__price')]"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._card_template = "current"

    async def apply_price_filter(self, max_price: float, min_price: float | None = None) -> bool:
        try:
            max_input = self.page.get_by_role("textbox", name=MAX_PRICE_NAME).first
            await max_input.fill(str(max_price))
            if min_price is not None:
                min_input = self.page.get_by_role("textbox", name=MIN_PRICE_NAME).first
                await min_input.fill(str(min_price))
            await max_input.press("Enter")
            await self.wait_for_load()
            self.log_step(f"Applied price filter: max={max_price} min={min_price}")
            return True
        except Exception as exc:
            self.log_step(f"Price filter UI unavailable ({exc}); relying on client-side filtering")
            return False

    async def get_item_cards(self) -> list[Locator]:
        primary = self.page.locator(f"xpath={self.RESULT_ITEM_XPATH}")
        count = await primary.count()
        if count > 0:
            self._card_template = "current"
            return [primary.nth(i) for i in range(count)]

        legacy = self.page.locator(f"xpath={self.LEGACY_ITEM_XPATH}")
        count = await legacy.count()
        self._card_template = "legacy"
        return [legacy.nth(i) for i in range(count)]

    async def extract_price(self, card: Locator) -> float | None:
        xpath = self.ITEM_PRICE_XPATH if self._card_template == "current" else self.LEGACY_ITEM_PRICE_XPATH
        price_locator = card.locator(f"xpath={xpath}")
        if await price_locator.count() == 0:
            return None
        text = await price_locator.first.inner_text()
        if not text or not any(ch.isdigit() for ch in text):
            return None
        return parse_price(text)

    async def extract_url(self, card: Locator) -> str | None:
        xpath = self.ITEM_LINK_XPATH if self._card_template == "current" else self.LEGACY_ITEM_LINK_XPATH
        link_locator = card.locator(f"xpath={xpath}")
        if await link_locator.count() == 0:
            return None
        href = await link_locator.first.get_attribute("href")
        if href and "/itm/" in href:
            return href
        return None

    async def has_next_page(self) -> bool:
        next_link = self.page.get_by_role("link", name=NEXT_PAGE_NAME)
        return await next_link.count() > 0

    async def go_to_next_page(self) -> None:
        next_link = self.page.get_by_role("link", name=NEXT_PAGE_NAME).first
        await next_link.click()
        await self.wait_for_load()
        self.log_step("Navigated to next results page")
