"""Playwright scraper — JS-rendered pages with anti-detection."""

from app.core.logger import get_logger
from app.scrapers.anti_ban import get_random_user_agent, polite_delay

logger = get_logger(__name__)


async def scrape_with_playwright(url: str) -> dict | None:
    """Scrapes a JS-rendered page. Returns {url, html, text} or None."""
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=get_random_user_agent(),
                viewport={"width": 1280, "height": 800},
                java_script_enabled=True,
                # Block tracking/ad resources to reduce fingerprint noise
                extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
            )
            # Block unnecessary resource types
            await context.route(
                "**/*",
                lambda route: route.abort()
                if route.request.resource_type in ("image", "stylesheet", "font", "media")
                else route.continue_(),
            )
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await polite_delay(0.5, 1.5)
            html = await page.content()
            text = await page.inner_text("body")
            await browser.close()
            return {"url": url, "html": html, "text": text}
    except Exception as exc:
        logger.debug("playwright_failed", url=url[:80], error=str(exc))
        return None
