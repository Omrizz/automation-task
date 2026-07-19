"""Pytest fixtures: async Playwright lifecycle, test data, logging, screenshots, tracing."""
from __future__ import annotations

import logging
from pathlib import Path

import pytest
import pytest_asyncio
from playwright.async_api import async_playwright
from pytest_html import extras

from utils.data_loader import TestData, load_test_data
from utils.helpers import get_logger

TRACES_DIR = Path("traces")
SCREENSHOTS_KEY = pytest.StashKey[Path]()


def pytest_addoption(parser):
    parser.addoption("--headed", action="store_true", default=False, help="Run browser in headed mode")


@pytest.fixture(scope="session")
def test_data() -> TestData:
    return load_test_data()


@pytest.fixture
def logger() -> logging.Logger:
    return get_logger("ebay_e2e")


@pytest.fixture
def screenshots_dir(request) -> Path:
    d = Path("screenshots") / request.node.name
    d.mkdir(parents=True, exist_ok=True)
    request.node.stash[SCREENSHOTS_KEY] = d
    return d


@pytest_asyncio.fixture
async def playwright_instance():
    async with async_playwright() as p:
        yield p


@pytest_asyncio.fixture
async def browser(playwright_instance, request):
    headless = not request.config.getoption("--headed")
    browser = await playwright_instance.chromium.launch(headless=headless)
    yield browser
    await browser.close()


@pytest_asyncio.fixture
async def context(browser, request):
    context = await browser.new_context(locale="en-US")
    TRACES_DIR.mkdir(exist_ok=True)
    await context.tracing.start(screenshots=True, snapshots=True, sources=True)
    yield context
    trace_path = TRACES_DIR / f"{request.node.name}.zip"
    await context.tracing.stop(path=str(trace_path))
    await context.close()


@pytest_asyncio.fixture
async def page(context):
    p = await context.new_page()
    p.set_default_timeout(15000)
    yield p


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Embed any screenshots saved during the test as inline images in the HTML report."""
    outcome = yield
    report = outcome.get_result()
    if report.when == "call":
        shots_dir = item.stash.get(SCREENSHOTS_KEY, None)
        if shots_dir and shots_dir.exists():
            existing_extra = getattr(report, "extra", [])
            for img in sorted(shots_dir.glob("*.png")):
                existing_extra.append(extras.image(str(img)))
            report.extra = existing_extra
