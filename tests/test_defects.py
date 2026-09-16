import os
import pytest
from helper.helper import (
    select_tariff, set_licenses, set_period, set_discount,
    toggle_module, wait_for_calculation, get_total_sum,
    download_excel, switch_to_tab_tm, switch_to_tab_implementation,
    toggle_implementation_work, get_selected_implementation_works,
    get_tandm_hours, set_tandm_hours, get_tandm_tariff,
    find_excel_rows, count_excel_rows, get_excel_value,
    get_excel_total_rows, get_all_excel_text,
)

BASE_LICENSES = 101
BASE_PERIOD = 12
BASE_DISCOUNT = 0

EXTRA_MODULES = [
    "Конструктор процессов", "Корпоративный университет",
    "Конструктор опросников", "Оценка 360", "Биржа идей",
    "Конструктор геймификации", "Мессенджер", "Календарь отпусков",
    "Бронь переговорных", "Приемная руководителя", "Конструктор рассылок",
    "Вакансии", "Задачи", "Навыки", "Цвет настроения",
    "Открытки", "Тайный Санта",
]


# =====================================================================
# БАГ №1. Excel включает невыбранную работу «Подготовка технического задания»
# =====================================================================

@pytest.mark.xfail(
    reason="BUG-001: Excel включает «Подготовка ТЗ», не выбранную в UI",
    strict=False,
)
def test_defect_01_excel_excludes_unselected_tz(page):
    """Excel не должен содержать 'Подготовка технического задания', если она не выбрана."""
    select_tariff(page, "TestQuest Облако")
    set_licenses(page, BASE_LICENSES)
    set_period(page, BASE_PERIOD)
    set_discount(page, BASE_DISCOUNT)
    for mod in EXTRA_MODULES:
        toggle_module(page, mod, enable=False)

    # Убеждаемся, что ТЗ не выбрана
    switch_to_tab_implementation(page)
    selected = get_selected_implementation_works(page)
    assert "Подготовка технического задания" not in selected

    wait_for_calculation(page)
    file_path = download_excel(page)
    try:
        rows = find_excel_rows(file_path, "Подготовка технического задания")
        assert len(rows) == 0, (
            f"Excel содержит невыбранную работу 'Подготовка ТЗ' "
            f"в {len(rows)} строке(ах)"
        )
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@pytest.mark.xfail(
    reason="BUG-001: итог SAAS в Excel не соответствует UI",
    strict=False,
)
def test_defect_02_excel_total_matches_ui_when_no_implementation(page):
    """Итог в Excel должен совпадать с UI, если ничего лишнего не выбрано."""
    select_tariff(page, "TestQuest Облако")
    set_licenses(page, BASE_LICENSES)
    set_period(page, BASE_PERIOD)
    set_discount(page, BASE_DISCOUNT)
    for mod in EXTRA_MODULES:
        toggle_module(page, mod, enable=False)
    wait_for_calculation(page)
    ui_total = get_total_sum(page)

    file_path = download_excel(page)
    try:
        total_rows = get_excel_total_rows(file_path)
        values = []
        from helper.helper import _extract_number_from_cell
        for r in total_rows:
            for c in r["cells"]:
                n = _extract_number_from_cell(type("C", (), {"value": c})())
                if n and n > 10000:
                    values.append(n)
        assert any(abs(v - ui_total) < 0.01 for v in values), (
            f"UI total={ui_total}, Excel totals={values}"
        )
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


# =====================================================================
# БАГ №2. T&M: сумма в Excel не совпадает с UI
# =====================================================================

@pytest.mark.xfail(
    reason="BUG-002: в Excel T&M 450000 вместо 585000",
    strict=False,
)
def test_defect_03_tandm_amount_matches_ui(page):
    """T&M в Excel должен соответствовать UI (585000 = 100 чч × 5850 ₽)."""
    select_tariff(page, "TestQuest Облако")
    set_licenses(page, BASE_LICENSES)
    set_period(page, BASE_PERIOD)
    set_discount(page, BASE_DISCOUNT)
    for mod in EXTRA_MODULES:
        toggle_module(page, mod, enable=False)

    set_tandm_hours(page, 100)
    tariff = get_tandm_tariff(page)
    expected_tandm = 100 * tariff  # 585000
    assert expected_tandm > 0, "Тариф T&M не прочитан"

    wait_for_calculation(page)
    file_path = download_excel(page)
    try:
        value = get_excel_value(file_path, "Резерв на 100")
        assert value == pytest.approx(expected_tandm, 0.01), (
            f"Excel T&M={value}, ожидалось {expected_tandm}"
        )
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@pytest.mark.xfail(
    reason="BUG-003: в Excel T&M с НДС = без НДС, НДС не прибавлен",
    strict=False,
)
def test_defect_04_tandm_vat_added(page):
    """Сумма с НДС в T&M должна быть равна без НДС + 5% НДС."""
    select_tariff(page, "TestQuest Облако")
    set_licenses(page, BASE_LICENSES)
    set_period(page, BASE_PERIOD)
    set_discount(page, BASE_DISCOUNT)
    for mod in EXTRA_MODULES:
        toggle_module(page, mod, enable=False)
    set_tandm_hours(page, 100)

    wait_for_calculation(page)
    file_path = download_excel(page)
    try:
        row = find_excel_rows(file_path, "Резерв на 100")
        assert row, "Строка 'Резерв на 100 чч' не найдена в Excel"
        cells = row[0]["cells"]
        from helper.helper import _extract_number_from_cell
        nums = [
            _extract_number_from_cell(type("C", (), {"value": c})())
            for c in cells
        ]
        nums = [n for n in nums if n and n > 0]
        assert len(nums) >= 2, f"Мало чисел в строке: {nums}"

        without_vat = nums[0]
        with_vat = nums[-1]
        expected_vat = round(without_vat * 1.05, 2)
        assert with_vat == pytest.approx(expected_vat, 0.01), (
            f"Без НДС={without_vat}, с НДС={with_vat}, "
            f"ожидалось {expected_vat}"
        )
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


# =====================================================================
# БАГ №3. В T&M две строки «Всего» с разными суммами
# =====================================================================

@pytest.mark.xfail(
    reason="BUG-004: в разделе T&M две строки 'Всего' с разными суммами",
    strict=False,
)
def test_defect_05_no_duplicate_total_in_tm(page):
    """В разделе T&M должна быть ровно одна строка 'Всего'."""
    select_tariff(page, "TestQuest Облако")
    set_licenses(page, BASE_LICENSES)
    set_period(page, BASE_PERIOD)
    set_discount(page, BASE_DISCOUNT)
    for mod in EXTRA_MODULES:
        toggle_module(page, mod, enable=False)
    set_tandm_hours(page, 100)

    wait_for_calculation(page)
    file_path = download_excel(page)
    try:
        totals = get_excel_total_rows(file_path)
        # Считаем только те «Всего», которые относятся к T&M-блоку.
        # Косвенно: строки после упоминания 'Time&Material' / 'T&M'.
        # Простая эвристика — количество всех строк 'Всего' не должно быть > 2
        # (SAAS + T&M). Если > 2 — есть дубли.
        assert len(totals) <= 2, (
            f"Найдено {len(totals)} строк 'Всего'/'Итого' — есть дубли: "
            f"{[r['cells'] for r in totals]}"
        )
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


# =====================================================================
# БАГ №4. Дубли номеров 22/23 и модулей
# =====================================================================

@pytest.mark.xfail(
    reason="BUG-005: дубли модулей «Открытки» / «Тайный Санта» и номеров 22/23",
    strict=False,
)
def test_defect_06_no_duplicate_modules_in_excel(page):
    """В Excel каждый модуль должен встречаться один раз."""
    select_tariff(page, "TestQuest Облако")
    set_licenses(page, BASE_LICENSES)
    set_period(page, BASE_PERIOD)
    set_discount(page, BASE_DISCOUNT)
    for mod in EXTRA_MODULES:
        toggle_module(page, mod, enable=False)

    wait_for_calculation(page)
    file_path = download_excel(page)
    try:
        for module in ("Открытки", "Тайный Санта"):
            cnt = count_excel_rows(file_path, module)
            assert cnt <= 1, (
                f"Модуль '{module}' встречается в Excel {cnt} раз(а) — дубль"
            )
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


# =====================================================================
# БАГ №5. Несогласованность названий продукта
# =====================================================================

@pytest.mark.xfail(
    reason="BUG-006: в Excel встречаются 'Бублики' / 'Пряники' / 'TestQuest'",
    strict=False,
)
def test_defect_07_single_product_name(page):
    """В Excel должно использоваться одно название продукта."""
    select_tariff(page, "TestQuest Облако")
    set_licenses(page, BASE_LICENSES)
    set_period(page, BASE_PERIOD)
    set_discount(page, BASE_DISCOUNT)
    for mod in EXTRA_MODULES:
        toggle_module(page, mod, enable=False)

    wait_for_calculation(page)
    file_path = download_excel(page)
    try:
        text = get_all_excel_text(file_path).lower()
        names = {
            "бублики": "Бублики" in text or "бублики" in text,
            "пряники": "пряники" in text,
            "testquest": "testquest" in text,
        }
        used = [n for n, ok in names.items() if ok]
        assert len(used) <= 1, (
            f"В Excel смешаны названия продукта: {used}"
        )
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

# python -m pytest tests/test_defects.py -v