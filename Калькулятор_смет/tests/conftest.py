import os
import pytest
from playwright.sync_api import Browser, Page, sync_playwright

@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        yield browser
        browser.close()


@pytest.fixture
def page(browser: Browser):
    context = browser.new_context(viewport={'width': 1280, 'height': 720})
    page = context.new_page()
    base_url = os.getenv("BASE_URL", "https://testquest.pryaniky.com")

    # Переходим на главную страницу
    page.goto(base_url)
    page.wait_for_load_state("networkidle", timeout=15000)

    # Кликаем по вкладке "Калькулятор" (или "Калькулятор смет")
    # Используем точный текст, который виден на странице
    try:
        page.click("text=Калькулятор")
    except Exception:
        # Если текст не найден, попробуем альтернативный селектор
        page.click("text=Калькулятор смет")

    # Ожидаем загрузки калькулятора – проверяем появление поля ввода лицензий
    # или заголовка #app-title
    page.wait_for_selector("#licenceCount", timeout=15000)

    yield page
    context.close()
