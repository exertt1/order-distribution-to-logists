"""Проверка устойчивости чтения к «чужим» файлам.

Приёмка будет прогонять навык на своих файлах: другой порядок колонок,
лишние колонки, другое имя листа. Скрипт собирает такие копии из data/
и сверяет результат с обычным прогоном.

Запуск: python tests/run_robustness.py
"""

import os
import sys
import tempfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "skill", "scripts"))
DATA_DIR = os.path.join(BASE_DIR, "data")

from openpyxl import Workbook, load_workbook  # noqa: E402

from logic_engine import distribute  # noqa: E402
from reader import ExcelReader  # noqa: E402


def distort(source: str, target: str, sheet_title: str = "Лист1") -> None:
    """Переставляет колонки в обратном порядке, добавляет лишнюю, меняет имя листа."""
    source_worksheet = load_workbook(source, data_only=True).active
    rows = list(source_worksheet.iter_rows(values_only=True))
    headers, data = rows[0], rows[1:]

    order = list(range(len(headers)))[::-1]
    new_headers = [headers[index] for index in order] + ["Служебная колонка"]
    new_rows = [
        [row[index] if index < len(row) else None for index in order] + ["мусор"]
        for row in data
    ]

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = sheet_title
    worksheet.append(new_headers)
    for row in new_rows:
        worksheet.append(row)
    workbook.save(target)


def run(ful_path: str, cloud_path: str, employees_path: str):
    reader = ExcelReader()
    fuls = reader.read_fuls(ful_path)
    cloud = reader.read_cloud(cloud_path)
    employees = reader.read_employees(employees_path)
    distribute(fuls, cloud, employees)
    return {
        ful.number: (ful.category, ful.logist_label, ful.order_label, ful.duplicate_comment)
        for ful in fuls
    }


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        base = run(
            os.path.join(DATA_DIR, "ful.xlsx"),
            os.path.join(DATA_DIR, "cloud.xlsx"),
            os.path.join(DATA_DIR, "employees.xlsx"),
        )

        distorted = {}
        for name in ("ful", "cloud", "employees"):
            source = os.path.join(DATA_DIR, f"{name}.xlsx")
            target = os.path.join(tmp, f"{name}_distorted.xlsx")
            distort(source, target)
            distorted[name] = target

        other = run(distorted["ful"], distorted["cloud"], distorted["employees"])

    ok = base == other
    print(f"базовый прогон: {len(base)} ФУЛ")
    print(f"искажённые файлы (обратный порядок колонок, лишняя колонка, лист «Лист1»): {len(other)} ФУЛ")
    if ok:
        print("РЕЗУЛЬТАТ: совпадает полностью")
        return 0

    print("РЕЗУЛЬТАТ: РАСХОЖДЕНИЕ")
    for number, value in base.items():
        if other.get(number) != value:
            print(f"  {number}: было {value}, стало {other.get(number)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
