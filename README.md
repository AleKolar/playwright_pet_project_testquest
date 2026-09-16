## Тесты для «Калькулятора смет» (`test_calculator.py`)

Данный набор автоматических тестов проверяет функциональность калькулятора смет в разделе «Продажи» ПО «Бублики» на стенде https://testquest.pryaniky.com/.

## Требования
- Python 3.8 или выше
- Операционная система: Linux/macOS (run-tests.sh) или Windows (run-tests.bat)

## Установка и запуск
1. Распакуйте архив в любую папку.
2. Откройте терминал/командную строку в корневой папке архива.
3. Выполните:
   - На Linux/macOS:
     `BASE_URL=https://testquest.pryaniky.com ./run-tests.sh`
   - На Windows:
     `set BASE_URL=https://testquest.pryaniky.com && run-tests.bat`
     или дважды кликните по `run-tests.bat` (переменная окружения установится внутри скрипта).

Скрипт автоматически установит все зависимости (pytest, playwright и др.), установит браузер Chromium и запустит тесты в headless-режиме.

**Для локальной разработки** вы можете создать файл `.env` в корне проекта с содержимым:

## Тесты подтверждения дефектов (`tests/test_defects.py`)

### Назначение

Файл `tests/test_defects.py` — это отдельный набор тестов, который **фиксирует известные дефекты выгрузки Excel** из калькулятора смет. Тесты описывают **корректное поведение** системы и помечены маркером `@pytest.mark.xfail` с указанием номера бага в `reason`.

Смысл подхода:
- тест описывает, **как должно быть**, а не как есть;
- пока баг не исправлен, тест «падает» и pytest помечает его как `XFAIL` — это ожидаемо и не ломает CI;
- после исправления бага тест начнёт проходить и помечается как `XPASS` — сигнал «убрать маркер `xfail`» и перевести тест в обычный регрессионный.

### Список покрытых дефектов

| ID | Файл / функция | Что проверяется |
|---|---|---|
| BUG-001 | `test_defect_01_excel_excludes_unselected_tz` | Excel не содержит работу «Подготовка технического задания», если она не выбрана в UI |
| BUG-001 | `test_defect_02_excel_total_matches_ui_when_no_implementation` | Итог в Excel совпадает с итогом в UI, если в калькуляторе не выбрано ничего лишнего |
| BUG-002 | `test_defect_03_tandm_amount_matches_ui` | Сумма T&M в Excel соответствует UI (100 чч × тариф) |
| BUG-003 | `test_defect_04_tandm_vat_added` | В строке «Резерв на 100 чч» сумма с НДС = сумма без НДС × 1.05 |
| BUG-004 | `test_defect_05_no_duplicate_total_in_tm` | В разделе T&M ровно одна строка «Всего» |
| BUG-005 | `test_defect_06_no_duplicate_modules_in_excel` | Модули «Открытки» и «Тайный Санта» встречаются в Excel по одному разу |
| BUG-006 | `test_defect_07_single_product_name` | В Excel используется одно название продукта, без смеси «Бублики» / «Пряники» / «TestQuest» |

### Как запускать

Из корня проекта, в активированном venv:

```bash
# Linux / macOS
BASE_URL=https://testquest.pryaniky.com python -m pytest tests/test_defects.py -v

# Windows (PowerShell)
$env:BASE_URL="https://testquest.pryaniky.com"; python -m pytest tests/test_defects.py -v
