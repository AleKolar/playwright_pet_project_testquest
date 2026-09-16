import os
import re
import openpyxl
from playwright.sync_api import Page

# --------------------- Вспомогательная функция для извлечения числа ---------------------

def extract_price(text: str) -> float:
    """
    Извлекает число из строки с учётом знака минуса (обычного или типографского).
    Примеры: '200 429 ₽' -> 200429.0, '−10 021 ₽' -> -10021.0, 'включено' -> 0.0.
    """
    # Ищем число с необязательным знаком минуса, цифрами и разделителями (пробелы, \xa0)
    match = re.search(r'([−\-]?[\d\s\u00A0]+(?:\.\d+)?)', text)
    if match:
        num_str = match.group(1)
        # Удаляем все пробелы (обычные и неразрывные) и лишние символы
        num_str = re.sub(r'[\s\u00A0]+', '', num_str)  # убираем все пробелы
        num_str = num_str.replace('−', '-')            # заменяем типографский минус
        return float(num_str)
    return 0.0

# --------------------- Настройка параметров ---------------------

def select_tariff(page: Page, tariff: str):
    """Выбор тарифа: 'TestQuest Облако' или 'TestQuest Коробка'."""
    page.click(f"span.checkbox-text:has-text('{tariff}')")

def set_licenses(page: Page, count: int):
    """Установить число лицензий (поле #licenceCount)."""
    page.fill("#licenceCount", str(count))

def set_period(page: Page, months: int):
    """Установить срок (поле #termMonths)."""
    page.fill("#termMonths", str(months))

def set_discount(page: Page, percent: int):
    """Установить скидку (поле #discountPercent)."""
    page.fill("#discountPercent", str(percent))

def toggle_module(page: Page, module_name: str, enable: bool = True):
    """
    Включить/выключить модуль по его названию.
    Ищем label с классом module-label и текстом module_name, затем находим чекбокс в родительском li,
    исключая чекбоксы, принадлежащие блоку 'Данные договора' (id содержит 'contract').
    """
    li = page.locator(f"li.module-item:has(label.module-label:has-text('{module_name}'))")
    checkbox = li.locator("input[type='checkbox']:not([id*='contract'])")
    if enable:
        checkbox.check()
    else:
        checkbox.uncheck()

# --------------------- Переключение вкладок T&M и Внедрение ---------------------

def switch_to_tab_tm(page: Page):
    """Переключиться на вкладку T&M."""
    page.click("#config-tab-tm")

def switch_to_tab_implementation(page: Page):
    """Переключиться на вкладку Внедрение."""
    page.click("#config-tab-implementation")

# --------------------- T&M и Внедрение (заглушки, пока не найдены поля) ---------------------

def set_tandm(page: Page, hours: int):
    """
    Установить количество часов T&M.
    Предполагаем, что внутри вкладки есть поле для ввода часов.
    TODO: заменить на реальный селектор после исследования.
    """
    # switch_to_tab_tm(page)
    # page.fill("#tm-hours", str(hours))
    pass

def set_implementation(page: Page, enable: bool = True):
    """
    Включить/выключить услуги внедрения (чекбокс).
    TODO: заменить на реальный селектор после исследования.
    """
    # switch_to_tab_implementation(page)
    # checkbox = page.locator("#implementation-checkbox")
    # if enable: checkbox.check() else: checkbox.uncheck()
    pass

# --------------------- Ожидание расчёта и получение итога ---------------------

def wait_for_calculation(page: Page):
    """Ожидание обновления итоговой суммы (появление/изменение .selected-summary-value)."""
    page.wait_for_selector(".selected-summary-value", state="visible", timeout=10000)
    # Небольшая задержка для завершения асинхронных расчётов
    page.wait_for_timeout(300)

def get_total_sum(page: Page) -> float:
    """Получить итоговую сумму из блока .selected-summary-value (берётся первое вхождение)."""
    # Берём первый элемент с классом .selected-summary-value (это итоговая сумма)
    total_element = page.locator(".selected-summary-value").first
    text = total_element.inner_text()
    return extract_price(text)

# --------------------- Разбивка по позициям (для проверки суммы) ---------------------

def get_breakdown(page: Page) -> dict:
    breakdown = {}

    # Список ключевых слов, которые нужно исключить
    EXCLUDE_KEYWORDS = ["Резерв", "T&M", "Time", "Скидка"]

    # 1) Парсим позиции с классом .selected-item-name + .selected-item-price
    name_elements = page.locator(".selected-item-name").all()
    for name_el in name_elements:
        parent = name_el.locator("xpath=..")
        price_el = parent.locator(".selected-item-price")
        if price_el.count() == 0:
            continue
        price_text = price_el.inner_text().strip()
        if "включено" in price_text.lower():
            continue
        price = extract_price(price_text)
        if price == 0:
            continue
        name = name_el.inner_text().strip()
        # Исключаем строки с ключевыми словами
        if any(key in name for key in EXCLUDE_KEYWORDS):
            continue
        breakdown[name] = price

    # 2) Парсим итоговые строки с классом .selected-summary-label + .selected-summary-value
    label_elements = page.locator(".selected-summary-label").all()
    for label_el in label_elements:
        parent = label_el.locator("xpath=..")
        value_el = parent.locator(".selected-summary-value")
        if value_el.count() == 0:
            continue
        value_text = value_el.inner_text().strip()
        price = extract_price(value_text)
        if price == 0:
            continue
        name = label_el.inner_text().strip()
        # Исключаем итоговые строки-дубли и строки с ключевыми словами
        if name in ("Всего", "Лицензии со скидкой"):
            continue
        if any(key in name for key in EXCLUDE_KEYWORDS):
            continue
        breakdown[name] = price

    return breakdown

# --------------------- Выгрузка Excel и валидация ---------------------
def download_excel(page: Page) -> str:
    """Скачать Excel-файл через кнопку #export-btn и вернуть путь с правильным расширением."""
    with page.expect_download() as download_info:
        page.click("#export-btn")
    download = download_info.value
    original_path = download.path()
    suggested_name = download.suggested_filename

    # Если предложенное имя есть, используем его расширение; иначе добавляем .xlsx
    if suggested_name:
        # Определяем расширение из предложенного имени
        ext = os.path.splitext(suggested_name)[1] if '.' in suggested_name else '.xlsx'
        new_filename = suggested_name
    else:
        ext = '.xlsx'
        new_filename = f"estimate{ext}"

    # Сохраняем в ту же директорию, но с правильным именем
    dir_path = os.path.dirname(original_path)
    new_path = os.path.join(dir_path, new_filename)

    # Переименовываем
    os.rename(original_path, new_path)

    page.wait_for_timeout(1000)  # даём время на запись
    return new_path

def _extract_number_from_cell(cell) -> float:
    """Извлекает число из ячейки (число или строка с числом)."""
    if cell.value is None:
        return None
    if isinstance(cell.value, (int, float)):
        return float(cell.value)
    if isinstance(cell.value, str):
        # Удаляем все символы, кроме цифр, точки, запятой и минуса
        cleaned = re.sub(r'[^\d\-.,]', '', cell.value)
        cleaned = cleaned.replace(',', '.')
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None

def validate_excel(file_path: str, expected_total: float) -> bool:
    """Проверяет, что Excel-файл содержит ожидаемую итоговую сумму."""
    wb = openpyxl.load_workbook(file_path)
    sheet = wb.active

    # Поиск по ячейкам с метками "итого" или "всего"
    for row in sheet.iter_rows(min_row=1, max_row=sheet.max_row, max_col=sheet.max_column):
        for cell in row:
            if cell.value and isinstance(cell.value, str):
                if "итого" in cell.value.lower() or "всего" in cell.value.lower():
                    # Проверяем число в этой же ячейке
                    num = _extract_number_from_cell(cell)
                    if num is not None and abs(num - expected_total) < 0.01:
                        return True
                    # Ищем число в других ячейках этой строки
                    for other_cell in row:
                        if other_cell != cell:
                            num = _extract_number_from_cell(other_cell)
                            if num is not None and abs(num - expected_total) < 0.01:
                                return True

    # Если метки не найдены, ищем любое число, совпадающее с ожидаемой суммой
    for row in sheet.iter_rows(min_row=1, max_row=sheet.max_row, max_col=sheet.max_column):
        for cell in row:
            num = _extract_number_from_cell(cell)
            if num is not None and abs(num - expected_total) < 0.01:
                return True

    return False
