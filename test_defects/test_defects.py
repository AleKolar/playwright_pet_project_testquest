import pytest

from helper.helper import (
    select_tariff,
    set_licenses,
    set_period,
    set_discount,
    toggle_module,
    wait_for_calculation,
    get_total_sum,
    download_excel,
    switch_to_tab_implementation,
    get_selected_implementation_works,
    set_tandm_hours,
    get_tandm_tariff,
    find_excel_rows,
    count_excel_rows,
    get_excel_row_amounts,
    get_excel_rows,
    _extract_number_from_cell, toggle_module_by_id,
)


BASE_LICENSES = 100
BASE_PERIOD = 12
BASE_DISCOUNT = 0

EXTRA_MODULES = [
    "Конструктор процессов",
    "Корпоративный университет",
    "Конструктор опросников",
    "Оценка 360",
    "Биржа идей",
    "Конструктор геймификации",
    "Мессенджер",
    "Календарь отпусков",
    "Бронь переговорных",
    "Приемная руководителя",
    "Конструктор рассылок",
    "Вакансии",
    "Задачи",
    "Навыки",
    "Цвет настроения",
    "Открытки",
    "Тайный Санта",
]


def prepare_base_calculation(page):
    """
    Подготовить базовый сценарий:

    - TestQuest Облако
    - 101 лицензия
    - 12 месяцев
    - скидка 0%
    - дополнительные модули выключены
    """
    select_tariff(
        page,
        "TestQuest Облако",
    )

    set_licenses(
        page,
        BASE_LICENSES,
    )

    set_period(
        page,
        BASE_PERIOD,
    )

    set_discount(
        page,
        BASE_DISCOUNT,
    )

    for module in EXTRA_MODULES:
        toggle_module(
            page,
            module,
            enable=False,
        )


# =====================================================================
# Проверка 1.
# Excel не должен содержать невыбранную работу
# =====================================================================

def test_defect_01_excel_excludes_unselected_tz(page):
    """
    Если «Подготовка технического задания»
    не выбрана в UI, она не должна попадать в Excel.
    """
    prepare_base_calculation(page)

    switch_to_tab_implementation(page)

    selected_works = get_selected_implementation_works(
        page
    )

    assert (
        "Подготовка технического задания"
        not in selected_works
    ), (
        "Работа «Подготовка технического задания» "
        "неожиданно выбрана в UI"
    )

    wait_for_calculation(page)

    file_path = download_excel(page)

    rows = find_excel_rows(
        file_path,
        "Подготовка технического задания",
    )

    assert len(rows) == 0, (
        "Excel содержит невыбранную работу "
        "«Подготовка технического задания»"
    )


# =====================================================================
# Проверка 2.
# Итог SAAS в Excel должен соответствовать UI
# =====================================================================

def test_defect_02_saas_total_matches_ui(page):
    """
    Итог TestQuest Облако в Excel должен
    соответствовать итогу SAAS в UI.
    """
    prepare_base_calculation(page)

    wait_for_calculation(page)

    ui_total = get_total_sum(page)

    file_path = download_excel(page)

    saas_total = get_excel_row_amounts(
        file_path,
        "Всего",
    )

    assert saas_total is not None, (
        "Строка «Всего» для SAAS "
        "не найдена в Excel"
    )

    assert (
        saas_total["without_vat"]
        == pytest.approx(
            ui_total,
            abs=0.01,
        )
    ), (
        f"UI SAAS total = {ui_total}, "
        f"Excel SAAS total = "
        f"{saas_total['without_vat']}"
    )


# =====================================================================
# Проверка 3.
# T&M в Excel должен соответствовать UI
# =====================================================================

def test_defect_03_tandm_amount_matches_ui(page):
    """
    T&M должен соответствовать расчёту UI:

    100 чч × тариф = ожидаемая стоимость без НДС.
    """
    prepare_base_calculation(page)

    set_tandm_hours(
        page,
        100,
    )

    tariff = get_tandm_tariff(page)

    assert tariff > 0, (
        "Тариф T&M не прочитан из UI"
    )

    expected_tandm = 100 * tariff

    wait_for_calculation(page)

    file_path = download_excel(page)

    total_rows = [
        row
        for row in get_excel_rows(file_path)
        if any(
            cell is not None
            and "всего" in str(cell).lower()
            for cell in row["cells"]
        )
    ]

    assert len(total_rows) >= 2, (
        "В Excel не найдено второе итоговое значение "
        "«Всего» для T&M"
    )

    # Первая строка «Всего» — SAAS.
    # Вторая строка «Всего» — T&M.
    tm_total_row = total_rows[1]

    cells = tm_total_row["cells"]

    assert len(cells) >= 5, (
        f"В строке T&M недостаточно колонок: {cells}"
    )

    tm_total = _extract_number_from_cell(
        type(
            "Cell",
            (),
            {"value": cells[2]},
        )()
    )

    assert tm_total is not None, (
        f"Не удалось получить сумму T&M "
        f"из строки: {cells}"
    )

    assert tm_total == pytest.approx(
        expected_tandm,
        abs=0.01,
    ), (
        f"UI T&M = {expected_tandm}, "
        f"Excel T&M = {tm_total}"
    )


# =====================================================================
# Проверка 4.
# НДС T&M должен рассчитываться корректно
# =====================================================================

def test_defect_04_tandm_vat_is_calculated_correctly(page):
    """
    Проверить расчёт T&M:

    Без НДС = 585000
    НДС 5%   = 29250
    С НДС    = 614250
    """
    prepare_base_calculation(page)

    set_tandm_hours(
        page,
        100,
    )

    wait_for_calculation(page)

    file_path = download_excel(page)

    total_rows = [
        row
        for row in get_excel_rows(file_path)
        if any(
            cell is not None
            and "всего" in str(cell).lower()
            for cell in row["cells"]
        )
    ]

    assert len(total_rows) >= 2, (
        "В Excel не найдено второе итоговое значение "
        "«Всего» для T&M"
    )

    # Вторая строка «Всего» — итог T&M.
    tm_total_row = total_rows[1]

    cells = tm_total_row["cells"]

    assert len(cells) >= 5, (
        f"В строке T&M недостаточно колонок: {cells}"
    )

    without_vat = _extract_number_from_cell(
        type(
            "Cell",
            (),
            {"value": cells[2]},
        )()
    )

    vat = _extract_number_from_cell(
        type(
            "Cell",
            (),
            {"value": cells[3]},
        )()
    )

    with_vat = _extract_number_from_cell(
        type(
            "Cell",
            (),
            {"value": cells[4]},
        )()
    )

    assert without_vat is not None, (
        f"Не удалось получить сумму без НДС: {cells}"
    )

    assert vat is not None, (
        f"Не удалось получить НДС: {cells}"
    )

    assert with_vat is not None, (
        f"Не удалось получить сумму с НДС: {cells}"
    )

    expected_vat = round(
        without_vat * 0.05,
        2,
    )

    expected_with_vat = round(
        without_vat + expected_vat,
        2,
    )

    assert vat == pytest.approx(
        expected_vat,
        abs=0.01,
    ), (
        f"Без НДС = {without_vat}, "
        f"НДС = {vat}, "
        f"ожидалось = {expected_vat}"
    )

    assert with_vat == pytest.approx(
        expected_with_vat,
        abs=0.01,
    ), (
        f"Без НДС = {without_vat}, "
        f"С НДС = {with_vat}, "
        f"ожидалось = {expected_with_vat}"
    )


# =====================================================================
# BUG-005.
# Дубли модулей в Excel
# =====================================================================

@pytest.mark.xfail(
    reason=(
        "BUG-005: в Excel дублируются модули "
        "«Навыки», «Цвет настроения», "
        "«Открытки», «Тайный Санта»"
    ),
    strict=False,
)
def test_defect_05_no_duplicate_modules_in_excel(
    page,
):
    """
    Каждый модуль должен встречаться
    в Excel не более одного раза.
    """
    prepare_base_calculation(page)

    wait_for_calculation(page)

    file_path = download_excel(page)

    expected_modules = [
        "Конструктор процессов",
        "Корпоративный университет",
        "Конструктор опросников",
        "Оценка 360",
        "Биржа идей",
        "Конструктор геймификации",
        "Мессенджер",
        "Календарь отпусков",
        "Бронь переговорных",
        "Приемная руководителя",
        "Конструктор рассылок",
        "Вакансии",
        "Задачи",
        "Навыки",
        "Цвет настроения",
        "Открытки",
        "Тайный Санта",
        "Адаптация - планируется к выходу в Q3/2026",
        "ИПР - планируется к выходу в Q3/2026",
    ]

    duplicates = {}

    for module in expected_modules:
        count = count_excel_rows(
            file_path,
            module,
        )

        if count > 1:
            duplicates[module] = count

    assert not duplicates, (
        "В Excel обнаружены дубли модулей: "
        f"{duplicates}"
    )

# =====================================================================
# BUG-006.
# В строке «Резерв на 100 чч» неверная стоимость без НДС
# =====================================================================

@pytest.mark.xfail(
    reason=(
        "BUG-006: в Excel строка «Резерв на 100 чч» "
        "содержит 22500 ₽ вместо 585000 ₽"
    ),
    strict=False,
)
def test_defect_06_tandm_reserve_amount_matches_ui(page):
    """
    Стоимость резерва T&M должна соответствовать UI:

    100 чч × 5850 ₽/чч = 585000 ₽ без НДС.
    """
    prepare_base_calculation(page)

    set_tandm_hours(
        page,
        100,
    )

    tariff = get_tandm_tariff(page)

    assert tariff > 0, (
        "Тариф T&M не прочитан из UI"
    )

    expected_reserve = 100 * tariff

    wait_for_calculation(page)

    file_path = download_excel(page)

    rows = find_excel_rows(
        file_path,
        "Резерв на 100",
    )

    assert rows, (
        "Строка «Резерв на 100 чч» "
        "не найдена в Excel"
    )

    cells = rows[0]["cells"]

    assert len(cells) >= 5, (
        f"В строке резерва недостаточно колонок: {cells}"
    )

    # Колонка C = «Руб., без НДС».
    reserve_without_vat = _extract_number_from_cell(
        type(
            "Cell",
            (),
            {"value": cells[2]},
        )()
    )

    assert reserve_without_vat is not None, (
        f"Не удалось получить стоимость резерва "
        f"без НДС из строки: {cells}"
    )

    assert reserve_without_vat == pytest.approx(
        expected_reserve,
        abs=0.01,
    ), (
        f"UI: 100 × {tariff} = {expected_reserve} ₽, "
        f"Excel: «Резерв на 100 чч» = "
        f"{reserve_without_vat} ₽"
    )

# =====================================================================
# BUG-007.
# В Excel формируется дублирующий / противоречивый блок T&M
# =====================================================================

@pytest.mark.xfail(
    reason=(
        "BUG-007: в Excel T&M формируется повторно — "
        "присутствуют одновременно корректный итог "
        "585000/29250/614250 и дополнительный блок "
        "450000/22500/450000"
    ),
    strict=False,
)
def test_defect_07_no_duplicate_tandm_block(page):
    """
    При включённом модуле «Конструктор процессов»
    в Excel должен формироваться один согласованный блок T&M.

    Для 100 чч при тарифе 5850 ₽/чч ожидается:
        585000 ₽ без НДС
        29250 ₽ НДС
        614250 ₽ с НДС

    Дополнительный противоречивый блок
    450000 / 22500 / 450000 появляться не должен.
    """
    prepare_base_calculation(page)

    set_discount(page, 5)

    # Включаем «Конструктор процессов».
    toggle_module_by_id(
        page,
        "module-process-builder",
        enable=True,
    )

    set_tandm_hours(
        page,
        100,
    )

    wait_for_calculation(page)

    file_path = download_excel(page)

    excel_rows = get_excel_rows(
        file_path
    )

    tm_amount_rows = []

    for row in excel_rows:
        cells = row["cells"]

        if len(cells) < 5:
            continue

        without_vat = _extract_number_from_cell(
            type(
                "Cell",
                (),
                {"value": cells[2]},
            )()
        )

        vat = _extract_number_from_cell(
            type(
                "Cell",
                (),
                {"value": cells[3]},
            )()
        )

        with_vat = _extract_number_from_cell(
            type(
                "Cell",
                (),
                {"value": cells[4]},
            )()
        )

        if (
            without_vat is not None
            and vat is not None
            and with_vat is not None
        ):
            tm_amount_rows.append(
                {
                    "row": row["row"],
                    "without_vat": without_vat,
                    "vat": vat,
                    "with_vat": with_vat,
                    "cells": cells,
                }
            )

    invalid_tm_rows = [
        row
        for row in tm_amount_rows
        if (
            row["without_vat"] == pytest.approx(
                450000,
                abs=0.01,
            )
            and row["vat"] == pytest.approx(
                22500,
                abs=0.01,
            )
            and row["with_vat"] == pytest.approx(
                450000,
                abs=0.01,
            )
        )
    ]

    assert not invalid_tm_rows, (
        "В Excel обнаружен дополнительный "
        "противоречивый блок T&M: "
        f"{invalid_tm_rows}"
    )


# python -m pytest test_defects/test_defects.py -v
# python -m pytest test_defects/test_defects.py::test_defect_07_no_duplicate_tandm_block -v
# python -m pytest test_defects/test_defects.py::test_defect_06_tandm_reserve_amount_matches_ui -v