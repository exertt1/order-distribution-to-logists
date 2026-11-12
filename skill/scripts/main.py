"""Точка входа навыка: python scripts/main.py <ФУЛ.xlsx> <Cloud.xlsx> <Сотрудники.xlsx> [<папка результата>]

Скрипт детерминированный: решения о группе и логисте принимает только
logic_engine, модель лишь пересказывает результат.
"""

import os
import sys

# Плоские импорты модулей навыка: скрипт запускается как файл из scripts/,
# поэтому каталог скрипта должен быть в sys.path (это делает интерпретатор,
# но на всякий случай добавляем явно — при запуске из другого каталога).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from constants import Text  # noqa: E402
from logic_engine import distribute, batches_by_group  # noqa: E402
from reader import ExcelReadError, ExcelReader  # noqa: E402
from writer import ExcelWriter  # noqa: E402
from utils import fmt_date  # noqa: E402

RESULT_FILENAME = "result_cloud_update.xlsx"


def run_agent(ful_path: str, cloud_path: str, employees_path: str, output_dir: str) -> int:
    """Обрабатывает три файла и сохраняет результат. Возвращает код выхода."""
    reader = ExcelReader()

    try:
        fuls = reader.read_fuls(ful_path)
        cloud = reader.read_cloud(cloud_path)
        employees = reader.read_employees(employees_path)
    except ExcelReadError as error:
        print(f"ОШИБКА ЧТЕНИЯ: {error}")
        return 2

    if not employees:
        print("ОШИБКА: в выгрузке сотрудников нет ни одной строки — распределять некого")
        return 2

    summary = distribute(fuls, cloud, employees)

    os.makedirs(output_dir, exist_ok=True)
    result_path = os.path.join(output_dir, RESULT_FILENAME)

    from logic_engine import cloud_last_date

    writer = ExcelWriter(result_path)
    writer.save(fuls, cloud_last_date=cloud_last_date(cloud))

    _print_report(fuls, summary, result_path)
    return 0


def _print_report(fuls, summary, result_path: str) -> None:
    print("=== ИТОГИ ===")
    print(f"всего строк ФУЛ: {len(fuls)}")
    print(f"новых строк Cloud: {summary['new']}")
    print(f"повторных отправок: {summary['dup']}")
    print(f"возможных пропусков: {summary['gaps']}")
    print(f"требует внимания: {summary['attention']}")

    groups = batches_by_group(fuls)
    if groups:
        print("по группам: " + ", ".join(f"{name} — {count}" for name, count in groups.items()))

    attention = [ful for ful in fuls if ful.attention and not ful.is_duplicate]
    if attention:
        print("--- требует внимания:")
        for ful in attention:
            print(f"  {ful.number}: {ful.order_label} — {'; '.join(ful.attention)}")

    duplicates = [ful for ful in fuls if ful.is_duplicate]
    if duplicates:
        print("--- повторные отправки:")
        for ful in duplicates:
            print(f"  {ful.number}: {ful.order_label} — «{ful.duplicate_comment}» ({ful.category})")

    print(f"файл: {result_path}")


def main(argv) -> int:
    if len(argv) < 4:
        print(
            "Использование: python scripts/main.py "
            "<ФУЛ.xlsx> <Cloud.xlsx> <Сотрудники.xlsx> [папка результата]"
        )
        return 1

    ful_path, cloud_path, employees_path = argv[1], argv[2], argv[3]
    output_dir = argv[4] if len(argv) > 4 else os.path.join(".", "results")

    missing = [
        path
        for path in (ful_path, cloud_path, employees_path)
        if not os.path.exists(path)
    ]
    if missing:
        print("ОШИБКА: не найдены входные файлы:")
        for path in missing:
            print(f"  - {path}")
        return 1

    return run_agent(ful_path, cloud_path, employees_path, output_dir)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
