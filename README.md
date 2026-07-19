# eBay E2E Automation Exercise

End-to-end Playwright (Python) test against real [ebay.com](https://www.ebay.com): search for an item with a price filter, add up to N qualifying items to the cart, and assert the cart total stays within budget.

## Architecture

- **Page Object Model**: one class per page in `pages/`, each extending `BasePage` (shared `page` reference, navigation, screenshots, scrolling, cookie-banner dismissal, logging).
- **OOP / SRP**: each page class owns only the locators and interactions for that page; parsing logic (`utils/helpers.py`) and config loading (`utils/data_loader.py`) are separated out as utilities, not mixed into page classes.
- **Data-driven**: all test inputs (`query`, `max_price`, `limit`, `currency`, `budget_per_item`) come from `data/test_data.json`, loaded via `utils/data_loader.load_test_data()`. No literals in test code.
- **The four required functions** (`ensure_guest_session`, `search_items_by_name_under_price`, `add_items_to_cart`, `assert_cart_total_not_exceeds`) are standalone `async` functions in `tests/test_ebay_flow.py`, not buried inside page classes — they orchestrate the page objects.
- **Async Playwright**: uses `playwright.async_api` with hand-rolled `pytest-asyncio` fixtures in `conftest.py` (the official `pytest-playwright` plugin only ships sync fixtures, so it isn't used here). One browser `context`/`page` is shared across all four functions within a test run, since the guest cart is session/cookie-bound — a fresh context between add-to-cart and the cart assertion would lose the cart contents.

## Prerequisites

- Python 3.11+
- pip

## Setup & run

```bash
pip install -r requirements.txt
playwright install chromium
pytest tests/ --html=report.html --self-contained-html -v
```

Run headed (useful for watching variant selection / add-to-cart live):

```bash
pytest tests/ --headed -v
```

## Project structure

```
pages/
  base_page.py            # shared page helpers
  home_page.py             # search entry point
  search_results_page.py   # price filter, XPath item extraction, pagination
  product_page.py          # variant selection, add to cart
  cart_page.py             # subtotal read
tests/
  test_ebay_flow.py        # the 4 required functions + full scenario test
utils/
  data_loader.py           # data-driven config loader
  helpers.py                # price parsing, filenames, logging
data/
  test_data.json           # query, max_price, limit, currency, budget_per_item
conftest.py                # async Playwright fixtures, tracing, screenshot-report wiring
pytest.ini
requirements.txt
```

## Test data

`data/test_data.json` holds all test inputs as a flat file, loaded via `utils/data_loader.load_test_data()`:

```json
{ "query": "shoes", "max_price": 220, "limit": 5, "currency": "USD" }
```

Edit the file directly to change inputs; add a `budget_per_item` key to set a per-item budget different from `max_price`.

## Reports & artifacts

- **HTML report**: `report.html` (self-contained, includes inline screenshots per step via a `pytest_runtest_makereport` hook in `conftest.py`).
- **Screenshots**: `screenshots/<test_name>/` — one per add-to-cart item plus a final cart screenshot.
- **Traces**: `traces/<test_name>.zip` — full Playwright trace of the run (includes the cart page actions). View with:
  ```bash
  playwright show-trace traces/test_ebay_search_add_to_cart_and_assert_total.zip
  ```

## Limitations / Assumptions

- **Login**: guest mode only — no real login is performed. Automating eBay's real login is out of scope: it requires real credentials, and is protected by 2FA/CAPTCHA/bot-detection that make scripted login non-deterministic and unsafe to wire into a public repo. `ensure_guest_session()` is kept as an explicit, named seam documenting this and showing where an `AuthService.login(...)` would plug in.
- **Currency**: USD is assumed throughout. **Confirmed live**: eBay renders prices in a geo/session-dependent local currency (observed both `$20.00` and `ILS 182.39` on the same search-results page in one run) rather than consistently in USD. `utils/helpers.parse_price` only strips non-numeric characters — it has no currency-symbol/code awareness, so a non-USD price like `ILS 182.39` is silently parsed as `182.39` and compared directly against the USD `max_price`/`budget_per_item` thresholds. This is a silent mis-parse, not a hard failure: results can look plausible while being wrong. Not fixed in code (locator drift, below, was prioritized instead) — treat totals/filtering as unreliable on any session eBay doesn't localize to USD/en-US.
- **eBay DOM volatility**: eBay changes markup and A/B-tests search-results templates. `search_results_page.py`'s `CARD_TEMPLATES` tries, in order: the current live template (`s-card` / `s-card__link` / `s-card__price`, confirmed live), then two previously-seen templates (`su-item-card` BEM div wrapper, and the older `s-item` list template) as fallbacks. All other locators (search box, price filter, variant dropdowns, add-to-cart, cart subtotal) may need adjustment if eBay changes its markup after this was written.
- **Cart subtotal selector**: the subtotal locator in `cart_page.py` is text-anchored (`contains(text(),'Subtotal')`), confirmed against a populated live cart.
- **Confirmed: cold navigation to `cart.ebay.com` can trigger eBay's bot-detection verification challenge** ("Please verify yourself to continue") instead of the real cart, which previously made the budget assertion pass vacuously (challenge page has no subtotal, so it silently read as `$0.00`). Mitigation: `add_items_to_cart` now navigates to the cart by clicking **"See in cart"** in the post-add confirmation panel (a natural in-page click from the last product page) instead of a direct `page.goto(cart_url)`, which is far less likely to trip the check. As defense in depth, `CartPage.get_subtotal_text()` now detects the challenge page explicitly and raises a clear `AssertionError` instead of silently returning `0.00`, so a still-blocked run fails loudly rather than passing vacuously.
- **Guest vs logged-in cart**: cart behavior (subtotal layout, persistence) may differ for guest vs. logged-in users; this suite only exercises the guest flow.
- **Listings without Add to Cart**: auctions or out-of-stock listings may not expose an Add to Cart control. `add_items_to_cart` detects this via `has_add_to_cart()` and skips + logs rather than failing.
- **Paging safety cap**: `search_items_by_name_under_price` stops after 10 pages even if `limit` isn't reached, to avoid a runaway loop — not in the literal spec but a defensive addition.
- **Live-site flakiness**: this suite runs against production eBay, not a fixture/mock. Expect occasional flakiness from ads, A/B-tested layouts, cookie-consent interstitials (best-effort dismissed), and possible bot-detection challenges under frequent automated runs (see above).

## Known flakiness / troubleshooting

- If a run fails at the price-filter step, check the screenshot/trace — eBay may have changed the filter panel's accessible labels ("Minimum Value"/"Maximum Value"). The client-side XPath price check in `search_items_by_name_under_price` still filters correctly even if the UI filter fails to apply, so this only degrades result quality, not correctness.
- If `assert_cart_total_not_exceeds` fails unexpectedly, check `cart_page.py`'s subtotal XPath against the current cart DOM first (see Limitations above).
- Re-run 2–3 times if a single failure looks environment-related before treating it as a real regression.
