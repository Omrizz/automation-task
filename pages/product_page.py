"""eBay product listing page: variant selection, add to cart."""
from __future__ import annotations

import random
import re

from playwright.async_api import Locator

from pages.base_page import BasePage

# Verified live: variant dropdowns expose an accessible name like "Size Select dropdown".
VARIANT_DROPDOWN_NAME = re.compile(r"Select dropdown", re.I)
# Verified live: role=button or role=link, accessible name "Add to cart".
ADD_TO_CART_NAME = re.compile(r"Add to cart", re.I)
# Verified live: the post-add-to-cart confirmation panel exposes a "See in cart" link/button
# and a small "X" close button (accessible name "Close").
SEE_IN_CART_NAME = re.compile(r"See in cart", re.I)
CLOSE_PANEL_NAME = re.compile(r"close", re.I)


class ProductPage(BasePage):
    async def _get_variant_dropdowns(self) -> list[Locator]:
        dropdowns = self.page.get_by_role("combobox", name=VARIANT_DROPDOWN_NAME)
        count = await dropdowns.count()
        return [dropdowns.nth(i) for i in range(count)]

    async def has_variants(self) -> bool:
        return len(await self._get_variant_dropdowns()) > 0

    async def select_random_variants(self) -> None:
        for dropdown in await self._get_variant_dropdowns():
            await dropdown.click()
            options = self.page.get_by_role("option")
            count = await options.count()
            enabled_indices = []
            for i in range(count):
                aria_disabled = await options.nth(i).get_attribute("aria-disabled")
                if aria_disabled != "true":
                    enabled_indices.append(i)
            if not enabled_indices:
                self.log_step("No enabled variant options found; skipping this dropdown")
                continue
            choice = random.choice(enabled_indices)
            await options.nth(choice).click()
            self.log_step(f"Selected variant option at index {choice}")

    async def has_add_to_cart(self) -> bool:
        button = self.page.get_by_role("button", name=ADD_TO_CART_NAME)
        link = self.page.get_by_role("link", name=ADD_TO_CART_NAME)
        return (await button.count() > 0) or (await link.count() > 0)

    async def add_to_cart(self) -> None:
        button = self.page.get_by_role("button", name=ADD_TO_CART_NAME)
        if await button.count() > 0:
            await button.first.click()
        else:
            await self.page.get_by_role("link", name=ADD_TO_CART_NAME).first.click()
        await self.wait_for_load()
        self.log_step("Clicked Add to Cart")

    async def go_to_cart_from_panel(self) -> bool:
        """Click 'See in cart' in the post-add confirmation panel, if present.

        Navigating this way (an in-page click from a page we're already legitimately on)
        is far less likely to trip eBay's bot check than a cold `page.goto(cart_url)`.
        Returns True if the click succeeded, False if the panel/link wasn't found.
        """
        link = self.page.get_by_role("link", name=SEE_IN_CART_NAME)
        button = self.page.get_by_role("button", name=SEE_IN_CART_NAME)
        try:
            if await link.count() > 0:
                await link.first.click()
            elif await button.count() > 0:
                await button.first.click()
            else:
                return False
        except Exception:
            self.log_step("Failed to click 'See in cart' in confirmation panel")
            return False
        await self.wait_for_load()
        self.log_step("Navigated to cart via 'See in cart' panel link")
        return True

    async def close_cart_panel(self) -> None:
        """Best-effort dismissal of the post-add-to-cart confirmation panel."""
        try:
            await self.page.get_by_role("button", name=CLOSE_PANEL_NAME).first.click(timeout=3000)
            self.log_step("Closed 'Added to cart' confirmation panel")
        except Exception:
            self.log_step("No confirmation panel close button found (may already be dismissed)")
