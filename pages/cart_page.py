"""eBay cart page: read subtotal for budget assertion.

NOTE: navigating straight to cart.ebay.com can trigger eBay's bot-detection
verification challenge ("Please verify yourself to continue") instead of
showing the real cart. See README > Limitations. `add_items_to_cart` avoids
this by clicking "See in cart" from the last product's confirmation panel
rather than a cold goto; `open()` below is a fallback for when that isn't
possible.
"""
from __future__ import annotations

from pages.base_page import BasePage
from utils.helpers import parse_price

SUBTOTAL_LABEL_XPATH = "//*[contains(text(),'Subtotal')]"
PRICE_IN_ROW_XPATH = ".//span[contains(text(),'$')]"
VERIFICATION_CHALLENGE_TEXT = "Please verify yourself"


class CartPage(BasePage):
    URL = "https://cart.ebay.com/"

    async def open(self) -> None:
        if self.page.url.startswith(self.URL):
            self.log_step(f"Already on {self.URL}; skipping redundant navigation")
            return
        await self.goto(self.URL)

    async def is_verification_challenge(self) -> bool:
        return await self.page.get_by_text(VERIFICATION_CHALLENGE_TEXT, exact=False).count() > 0

    async def get_subtotal_text(self) -> str:
        if await self.is_verification_challenge():
            raise AssertionError(
                "eBay served a bot-detection verification challenge instead of the cart "
                "page; cannot read a real subtotal (see README > Limitations)."
            )
        subtotal_label = self.page.locator(f"xpath={SUBTOTAL_LABEL_XPATH}")
        if await subtotal_label.count() == 0:
            self.log_step("No subtotal element found (cart may be empty)")
            return "0.00"
        row = subtotal_label.first.locator("xpath=ancestor::div[1]")
        price_span = row.locator(f"xpath={PRICE_IN_ROW_XPATH}")
        if await price_span.count() == 0:
            return "0.00"
        return await price_span.first.inner_text()

    async def get_subtotal(self) -> float:
        return parse_price(await self.get_subtotal_text())
