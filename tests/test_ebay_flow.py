"""eBay end-to-end scenario: search + price filter, add to cart, cart total assertion.

The four required functions are kept as standalone module-level async functions
(not methods on a Page Object) per the exercise spec. They are only consumed by
this one test today; if a second scenario needs them, extract to utils/.
"""
from __future__ import annotations

import pytest

from pages.cart_page import CartPage
from pages.home_page import HomePage
from pages.product_page import ProductPage

MAX_PAGES = 10  # defensive cap against runaway pagination; not in the literal spec


async def ensure_guest_session(page, logger) -> None:
    logger.info("Running as guest; authentication is stubbed (see README > Limitations)")


async def search_items_by_name_under_price(
    page, query, max_price, limit=5, screenshots_dir=None, logger=None
) -> list[str]:
    home = HomePage(page, screenshots_dir, logger)
    await home.open()
    results = await home.search(query)

    if not await results.apply_price_filter(max_price):
        logger.warning("Price filter UI unavailable; relying on client-side filtering")

    collected: list[str] = []
    pages_visited = 0

    while len(collected) < limit:
        for card in await results.get_item_cards():
            if len(collected) >= limit:
                break
            price = await results.extract_price(card)
            url = await results.extract_url(card)
            if price is not None and url is not None and price <= max_price and url not in collected:
                collected.append(url)

        if len(collected) >= limit or pages_visited >= MAX_PAGES:
            break

        if await results.has_next_page():
            await results.go_to_next_page()
            pages_visited += 1
        else:
            break

    logger.info(f"Collected {len(collected)} item(s) <= {max_price}")
    return collected


async def add_items_to_cart(page, urls, screenshots_dir, logger) -> None:
    added_any = False
    for i, url in enumerate(urls, start=1):
        product = ProductPage(page, screenshots_dir, logger)
        await product.goto(url)

        if not await product.has_add_to_cart():
            logger.warning(f"[{i}] No Add to Cart available (auction/out of stock?) - skipping: {url}")
            continue

        if await product.has_variants():
            await product.select_random_variants()

        await product.add_to_cart()
        await product.screenshot(f"add_to_cart_item_{i}")
        logger.info(f"[{i}/{len(urls)}] Added to cart: {url}")
        added_any = True

        is_last = i == len(urls)
        if is_last:
            # A cold `page.goto(cart_url)` tends to trip eBay's bot-detection
            # verification challenge; clicking "See in cart" from the confirmation
            # panel is a natural in-page navigation that avoids it.
            if not await product.go_to_cart_from_panel():
                logger.warning("'See in cart' link not found; falling back to direct cart navigation")
                await page.goto(CartPage.URL)
        else:
            await product.close_cart_panel()
            # Each product was reached via a direct goto(url), so go_back() returns
            # to the search-results page that was last loaded in this tab's history.
            await page.go_back()

    if not added_any:
        logger.warning("No items were added to cart; nothing to navigate to")


async def assert_cart_total_not_exceeds(page, budget_per_item, items_count, screenshots_dir, logger) -> None:
    cart = CartPage(page, screenshots_dir, logger)
    await cart.open()
    subtotal = await cart.get_subtotal()
    threshold = budget_per_item * items_count
    # The full-session trace started in the `context` fixture already covers
    # this page's actions, satisfying the "trace of the cart page" requirement
    # without a separate nested trace chunk.
    await cart.screenshot("cart_total")

    logger.info(f"Cart subtotal={subtotal}, threshold={threshold}")
    assert subtotal <= threshold, f"Cart total {subtotal} exceeds threshold {threshold}"


@pytest.mark.e2e
async def test_ebay_search_add_to_cart_and_assert_total(page, test_data, screenshots_dir, logger):
    await ensure_guest_session(page, logger)

    urls = await search_items_by_name_under_price(
        page,
        test_data.query,
        test_data.max_price,
        test_data.limit,
        screenshots_dir=screenshots_dir,
        logger=logger,
    )

    await add_items_to_cart(page, urls, screenshots_dir, logger)

    await assert_cart_total_not_exceeds(
        page,
        test_data.budget_per_item,
        len(urls),
        screenshots_dir,
        logger,
    )


@pytest.mark.e2e
async def test_search_items_by_name_under_price(page, test_data, screenshots_dir, logger):
    urls = await search_items_by_name_under_price(
        page,
        test_data.query,
        test_data.max_price,
        test_data.limit,
        screenshots_dir=screenshots_dir,
        logger=logger,
    )

    logger.info(f"URLs: {urls}")
    assert len(urls) <= test_data.limit
    assert len(set(urls)) == len(urls)
