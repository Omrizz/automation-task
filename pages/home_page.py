"""eBay home page: search entry point."""
from __future__ import annotations

from pages.base_page import BasePage
from pages.search_results_page import SearchResultsPage


class HomePage(BasePage):
    URL = "https://www.ebay.com"

    # Verified live: input id="gh-ac", role=combobox, aria-label "Search for anything", name="_nkw"
    SEARCH_INPUT = "#gh-ac"
    # Verified live: role=button, id="gh-search-btn"
    SEARCH_BUTTON = "#gh-search-btn"

    async def open(self) -> None:
        await self.goto(self.URL)
        await self.dismiss_cookie_banner()

    async def search(self, query: str) -> SearchResultsPage:
        self.log_step(f"Searching for '{query}'")
        search_input = self.page.locator(self.SEARCH_INPUT)
        await search_input.fill(query)
        await self.page.locator(self.SEARCH_BUTTON).click()
        await self.wait_for_load()
        return SearchResultsPage(self.page, self.screenshots_dir, self.logger)
