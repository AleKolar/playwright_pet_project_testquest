import os

import pytest
from playwright.sync_api import (
    Browser,
    sync_playwright,
)


@pytest.fixture(scope="session")
def browser():
    """Создать Chromium на всю тестовую сессию."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=False,
            slow_mo=500,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ],
        )

        yield browser

        browser.close()


@pytest.fixture
def page(browser: Browser):
    """Создать страницу и открыть калькулятор."""
    context = browser.new_context(
        viewport={
            "width": 1280,
            "height": 720,
        }
    )

    page = context.new_page()

    base_url = os.getenv(
        "BASE_URL",
        "https://testquest.pryaniky.com",
    )

    page.goto(
        base_url,
        wait_until="domcontentloaded",
    )

    page.wait_for_load_state(
        "networkidle",
        timeout=15000,
    )

    try:
        page.get_by_text(
            "Калькулятор",
            exact=True,
        ).click()
    except Exception:
        page.get_by_text(
            "Калькулятор смет",
            exact=True,
        ).click()

    page.wait_for_selector(
        "#licenceCount",
        state="visible",
        timeout=15000,
    )

    yield page

    context.close()