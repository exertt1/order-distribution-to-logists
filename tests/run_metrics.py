"""Контрольные прогоны навыка и сравнение с эталоном.

Запуск: python tests/run_metrics.py
Считает: совпадение с эталоном по всем полям, точность по каждому полю,
число подставленных значений там, где данных не было, воспроизводимость
(три прогона) и время обработки пачки.
"""

import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_SCRIPTS = os.path.join(BASE_DIR, "skill", "scripts")
DATA_DIR = os.path.join(BASE_DIR, "data")
sys.path.insert(0, SKILL_SCRIPTS)

from openpyxl import load_workbook  # noqa: E402

from logic_engine import distribute, summarize  # noqa: E402
from reader import ExcelReader  # noqa: E402
from utils import group_label  # noqa: E402

FIELDS = ("заказ", "группа", "логист", "категория", "комментарий", "пропуск")
RUNS = 3


def read_expected():
    path = os.path.join(DATA_DIR, "expected.xlsx")
    worksheet = load_workbook(path, data_only=True).active
    rows = list(worksheet.iter_rows(values_only=True))
    headers = [str(value) for value in rows[0]]
    result = {}
    for row in rows[1:]:
        record = dict(zip(headers, row))
        result[str(record["ФУЛ"])] = {
            "заказ": str(record["Заказ"]),
            "группа": str(record["Группа"]),
            "логист": str(record["Логист"]),
            "категория": str(record["Категория"]),
            "комментарий": str(record["Комментарий для Cloud"]),
            "пропуск": str(record["Возможный пропуск"]),
        }
    return result


def run_once():
    """Один прогон: чтение трёх файлов и распределение."""
    reader = ExcelReader()
    fuls = reader.read_fuls(os.path.join(DATA_DIR, "ful.xlsx"))
    cloud = reader.read_cloud(os.path.join(DATA_DIR, "cloud.xlsx"))
    employees = reader.read_employees(os.path.join(DATA_DIR, "employees.xlsx"))

    started = time.perf_counter()
    summary = distribute(fuls, cloud, employees)
    elapsed = time.perf_counter() - started

    rows = {}
    for ful in fuls:
        rows[ful.number] = {
            "заказ": ful.order_label,
            "группа": group_label(ful.group),
            "логист": ful.logist_label,
            "категория": ful.category,
            "комментарий": ful.duplicate_comment or "—",
            "пропуск": "да" if ful.is_gap else "нет",
        }
    return rows, summary, elapsed


def compare(actual, expected):
    mismatches = []
    field_hits = {field: 0 for field in FIELDS}
    field_total = {field: 0 for field in FIELDS}

    for number, expected_row in expected.items():
        actual_row = actual.get(number)
        if actual_row is None:
            mismatches.append((number, "строка отсутствует в результате", "—", "—"))
            continue

        for field in FIELDS:
            field_total[field] += 1
            if actual_row[field] == expected_row[field]:
                field_hits[field] += 1
            else:
                mismatches.append(
                    (number, field, expected_row[field], actual_row[field])
                )

    return field_hits, field_total, mismatches


def count_inventions(actual, expected):
    """Сколько раз подставлено значение там, где по эталону данных нет."""
    inventions = []
    for number, expected_row in expected.items():
        actual_row = actual.get(number, {})
        for field in ("заказ", "группа", "логист"):
            if expected_row[field] == "не определено" and actual_row.get(field) not in (
                "не определено",
                None,
            ):
                inventions.append((number, field, actual_row.get(field)))
    return inventions


def main() -> int:
    expected = read_expected()
    runs = []
    times = []

    for index in range(RUNS):
        rows, summary, elapsed = run_once()
        runs.append(rows)
        times.append(elapsed)
        print(f"прогон {index + 1}: {len(rows)} ФУЛ, {elapsed:.3f} с, сводка {summary}")

    actual = runs[0]
    field_hits, field_total, mismatches = compare(actual, expected)
    inventions = count_inventions(actual, expected)

    matched_ful = sum(
        1
        for number in expected
        if all(actual[number][field] == expected[number][field] for field in FIELDS)
    )
    total_ful = len(expected)
    exact_share = matched_ful / total_ful * 100
    determinism = all(run == actual for run in runs[1:])

    per_field = {
        field: field_hits[field] / field_total[field] * 100 for field in FIELDS
    }
    total_checks = sum(field_total.values())
    total_hits = sum(field_hits.values())
    overall = total_hits / total_checks * 100

    summary = summarize_counts(actual)

    lines = []
    lines.append("# Результаты контрольных прогонов\n")
    lines.append(f"- прогонов: {RUNS}")
    lines.append(f"- ФУЛ в наборе: {total_ful}")
    lines.append(f"- время на пачку: {max(times):.3f} с (максимум из прогонов)")
    lines.append(f"- воспроизводимость: {'совпадает во всех прогонах' if determinism else 'РАСХОДИТСЯ'}")
    lines.append(f"- полное совпадение по всем полям: {matched_ful} из {total_ful} ФУЛ ({exact_share:.1f}%)")
    lines.append(f"- точность по всем полям: {overall:.1f}%")
    lines.append(f"- подставлено значений там, где данных нет: {len(inventions)}\n")
    lines.append("| Поле | Точность |")
    lines.append("|---|---|")
    for field in FIELDS:
        lines.append(f"| {field} | {per_field[field]:.1f}% |")
    lines.append("")
    lines.append("## Сводка по категориям\n")
    lines.append("| Категория | Результат | Эталон |")
    lines.append("|---|---|---|")
    lines.append(f"| новых строк Cloud | {summary['new']} | 13 |")
    lines.append(f"| повторных отправок | {summary['dup']} | 2 |")
    lines.append(f"| возможных пропусков | {summary['gaps']} | 1 |")
    lines.append(f"| требует внимания | {summary['attention']} | 5 |")
    lines.append("")
    if mismatches:
        lines.append("## Расхождения\n")
        lines.append("| ФУЛ | Поле | Эталон | Результат |")
        lines.append("|---|---|---|---|")
        for number, field, want, got in mismatches:
            lines.append(f"| {number} | {field} | {want} | {got} |")
        lines.append("")
    else:
        lines.append("Расхождений с эталоном нет.\n")

    if inventions:
        lines.append("## Подставленные значения\n")
        for number, field, value in inventions:
            lines.append(f"- {number}: {field} = {value}")
        lines.append("")

    report = "\n".join(lines)
    report_path = os.path.join(BASE_DIR, "tests", "metrics_report.md")
    with open(report_path, "w", encoding="utf-8") as file:
        file.write(report)

    print(report)
    print(f"отчёт сохранён: {report_path}")

    return 0 if not mismatches and not inventions and determinism else 1


def summarize_counts(actual):
    counts = {"new": 0, "dup": 0, "attention": 0, "gaps": 0}
    for row in actual.values():
        if row["категория"].startswith("повтор"):
            counts["dup"] += 1
        elif row["категория"] == "требует внимания":
            counts["attention"] += 1
        else:
            counts["new"] += 1
        if row["пропуск"] == "да":
            counts["gaps"] += 1
    return counts


if __name__ == "__main__":
    sys.exit(main())
