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
    # eBay SRP templates, tried in order until one yields cards. eBay rotates/A-B-tests
    # these, so keep prior templates as fallbacks rather than deleting them.
    CARD_TEMPLATES = {
        # Verified live 2026-07-19: <li class="s-card s-card--vertical">.
        "s-card": {
            "item": "//li[contains(concat(' ', normalize-space(@class), ' '), ' s-card ')]",
            "link": ".//a[contains(@class,'s-card__link')]",
            "price": ".//span[contains(@class,'s-card__price')]",
        },
        # Previously-seen BEM div-wrapper template.
        "su-item-card": {
            "item": "//div[contains(concat(' ', normalize-space(@class), ' '), ' su-item-card ')]",
            "link": ".//a[contains(@class,'su-media-container__link')]",
            "price": ".//span[contains(@class,'su-item-card__price')]",
        },
        # Older list-based SRP template.
        "s-item": {
            "item": "//li[contains(concat(' ', normalize-space(@class), ' '), ' s-item ')]",
            "link": ".//a[contains(@class,'s-item__link')]",
            "price": ".//span[contains(@class,'s-item__price')]",
        },
    }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._card_template = "s-card"

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
        for name, xpaths in self.CARD_TEMPLATES.items():
            locator = self.page.locator(f"xpath={xpaths['item']}")
            count = await locator.count()
            if count > 0:
                self._card_template = name
                return [locator.nth(i) for i in range(count)]
        return []

    async def extract_price(self, card: Locator) -> float | None:
        xpath = self.CARD_TEMPLATES[self._card_template]["price"]
        price_locator = card.locator(f"xpath={xpath}")
        if await price_locator.count() == 0:
            return None
        text = await price_locator.first.inner_text()
        if not text or not any(ch.isdigit() for ch in text):
            return None
        return parse_price(text)

    async def extract_url(self, card: Locator) -> str | None:
        xpath = self.CARD_TEMPLATES[self._card_template]["link"]
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
