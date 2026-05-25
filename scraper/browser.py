"""Playwright browser lifecycle management."""
import asyncio
from contextlib import asynccontextmanager
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from config import USER_AGENT


@asynccontextmanager
async def get_browser():
    """Yield a Playwright browser instance, cleaning up on exit."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            yield browser
        finally:
            await browser.close()


async def new_context(browser: Browser) -> BrowserContext:
    context = await browser.new_context(
        user_agent=USER_AGENT,
        viewport={"width": 1280, "height": 900},
        locale="en-US",
        extra_http_headers={
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    return context


async def new_page(browser: Browser) -> tuple[BrowserContext, Page]:
    context = await new_context(browser)
    page = await context.new_page()
    return context, page
