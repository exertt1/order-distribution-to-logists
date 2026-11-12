"""Формирование итогового Excel: пять листов отчёта.

Новые строки пишутся строго в форме реестра Cloud (12 колонок, порядок
как в реестре), плюс листы повторов, пропусков, внимания и журнала решений.
"""

from datetime import datetime
from typing import List, Sequence

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from constants import CLOUD, Sheets, Text
from models import FulItem
from utils import fmt_date, group_label, parse_date


HEADER_FONT = Font(bold=True)
HEADER_FILL = PatternFill("solid", fgColor="DDEBF7")
DATE_FORMAT = "DD.MM.YYYY"


class ExcelWriter:
    """Пишет результат работы навыка в один xlsx."""

    def __init__(self, output_path: str):
        self.output_path = output_path

    # --- Публичный метод ---

    def save(
        self,
        fuls: List[FulItem],
        cloud_last_date=None,
    ) -> str:
        workbook = Workbook()
        workbook.remove(workbook.active)

        new_rows = [f for f in fuls if not f.is_duplicate and not f.attention]
        duplicates = [f for f in fuls if f.is_duplicate]
        gaps = [f for f in fuls if f.is_gap]
        attention = [f for f in fuls if f.attention and not f.is_duplicate]

        self._write_new_rows(workbook, new_rows)
        self._write_duplicates(workbook, duplicates)
        self._write_gaps(workbook, gaps, cloud_last_date)
        self._write_attention(workbook, attention)
        self._write_decisions(workbook, fuls)

        workbook.save(self.output_path)
        return self.output_path

    # --- Листы ---

    def _write_new_rows(self, workbook, fuls: List[FulItem]) -> None:
        headers = list(CLOUD.COLUMNS)
        rows = []
        for ful in fuls:
            rows.append(
                [
                    ful.order_id or Text.UNDEFINED,
                    ful.supplier or Text.UNDEFINED,
                    ful.brand or Text.UNDEFINED,
                    ful.logist or Text.UNDEFINED,
                    "в работе",
                    "",
                    self._date_or_undefined(ful.cutoff),
                    self._date_or_undefined(ful.ful_date),
                    ful.country or Text.UNDEFINED,
                    ful.method or Text.UNDEFINED,
                    "",
                    "",
                ]
            )
        self._write_sheet(
            workbook,
            Sheets.NEW,
            headers,
            rows,
            widths=[12, 24, 16, 18, 12, 16, 14, 16, 16, 16, 18, 24],
            date_columns={6, 7},  # cut-off и дата получения УЛ (0-based)
        )

    def _write_duplicates(self, workbook, fuls: List[FulItem]) -> None:
        headers = [
            "ФУЛ",
            "Заказ",
            "Дата ФУЛ",
            "Категория",
            "Что сделать в Cloud",
        ]
        rows = []
        for ful in fuls:
            action = (
                "Дописать в «Комментарий» существующего заказа: "
                f"«{ful.duplicate_comment}». Новую строку не создавать."
            )
            rows.append(
                [
                    ful.number,
                    ful.order_id or Text.UNDEFINED,
                    ful.ful_date,
                    ful.category,
                    action,
                ]
            )
        self._write_sheet(
            workbook,
            Sheets.DUPLICATES,
            headers,
            rows,
            widths=[18, 14, 14, 24, 78],
            date_columns={2},
        )

    def _write_gaps(self, workbook, fuls: List[FulItem], cloud_last_date) -> None:
        headers = [
            "ФУЛ",
            "Заказ",
            "Дата ФУЛ",
            "Последняя дата в Cloud",
            "Поставщик",
            "Группа",
            "Логист",
            "Почему попал в список",
        ]
        last_label = fmt_date(cloud_last_date, Text.UNDEFINED) if cloud_last_date else Text.UNDEFINED
        rows = []
        for ful in fuls:
            rows.append(
                [
                    ful.number,
                    ful.order_id or Text.UNDEFINED,
                    ful.ful_date,
                    cloud_last_date if cloud_last_date else last_label,
                    ful.supplier or Text.UNDEFINED,
                    group_label(ful.group),
                    ful.logist or Text.UNDEFINED,
                    (
                        "ФУЛ пришёл раньше последней записи в Cloud, но заказа там нет — "
                        "проверить, не потерялся ли заказ"
                    ),
                ]
            )
        self._write_sheet(
            workbook,
            Sheets.GAPS,
            headers,
            rows,
            widths=[18, 14, 14, 20, 22, 28, 18, 72],
            date_columns={2, 3},
        )

    def _write_attention(self, workbook, fuls: List[FulItem]) -> None:
        headers = [
            "ФУЛ",
            "Заказ",
            "Поставщик",
            "Страна",
            "Способ доставки",
            "Группа",
            "Логист",
            "Причина",
            "Что сделать",
        ]
        rows = []
        for ful in fuls:
            rows.append(
                [
                    ful.number,
                    ful.order_id or Text.UNDEFINED,
                    ful.supplier or Text.UNDEFINED,
                    ful.country or Text.UNDEFINED,
                    ful.method or Text.UNDEFINED,
                    group_label(ful.group),
                    ful.logist or Text.UNDEFINED,
                    "; ".join(ful.attention),
                    self._action_hint(ful),
                ]
            )
        self._write_sheet(
            workbook,
            Sheets.ATTENTION,
            headers,
            rows,
            widths=[18, 14, 22, 14, 16, 28, 18, 62, 60],
        )

    def _write_decisions(self, workbook, fuls: List[FulItem]) -> None:
        headers = [
            "ФУЛ",
            "Дата ФУЛ",
            "Заказ",
            "Поставщик",
            "Страна",
            "Способ доставки",
            "Группа",
            "Логист",
            "Категория",
            "Основание выбора",
            "Пояснение",
            "Возможный пропуск",
            "Причина внимания",
            "Комментарий для Cloud",
        ]
        rows = []
        for ful in fuls:
            rows.append(
                [
                    ful.number,
                    ful.ful_date,
                    ful.order_id or Text.UNDEFINED,
                    ful.supplier or Text.UNDEFINED,
                    ful.country or Text.UNDEFINED,
                    ful.method or Text.UNDEFINED,
                    group_label(ful.group),
                    ful.logist or Text.UNDEFINED,
                    ful.category,
                    ful.reason_code or "—",
                    ful.reason_text or "—",
                    "да" if ful.is_gap else "нет",
                    "; ".join(ful.attention) if ful.attention else "—",
                    ful.duplicate_comment or "—",
                ]
            )
        self._write_sheet(
            workbook,
            Sheets.DECISIONS,
            headers,
            rows,
            widths=[18, 14, 14, 22, 14, 16, 28, 18, 22, 32, 60, 16, 52, 46],
            date_columns={1},
        )

    # --- Вспомогательное ---

    @staticmethod
    def _date_or_undefined(value):
        """Дата для реестра: значение как есть, а при отсутствии — «не определено»."""
        if parse_date(value) is None:
            return Text.UNDEFINED
        return value

    @staticmethod
    def _action_hint(ful: FulItem) -> str:
        hints = []
        text = " ".join(ful.attention)
        if "номер заказа" in text:
            hints.append("проверить комментарий ФУЛ и уточнить номер заказа в 1С")
        if "способ доставки" in text:
            hints.append("уточнить способ доставки в 1С")
        if "страна" in text:
            hints.append("уточнить страну отправления в 1С")
        if "нет доступных логистов" in text:
            hints.append("назначить логиста вручную или согласовать замену")
        if not hints:
            hints.append("разобрать вручную")
        return "; ".join(hints)

    def _write_sheet(
        self,
        workbook,
        title: str,
        headers: Sequence[str],
        rows: Sequence[Sequence],
        widths: Sequence[int] = (),
        date_columns: set = frozenset(),
    ) -> None:
        worksheet = workbook.create_sheet(title=title)
        worksheet.append(list(headers))

        for cell in worksheet[1]:
            cell.font = HEADER_FONT
            cell.fill = HEADER_FILL
            cell.alignment = Alignment(vertical="center", wrap_text=True)

        for row in rows:
            worksheet.append(list(row))

        last_column = len(headers)
        for index in range(len(rows)):
            for column in date_columns:
                if column >= last_column:
                    continue
                cell = worksheet.cell(row=index + 2, column=column + 1)
                parsed = parse_date(cell.value)
                if parsed is not None:
                    cell.value = datetime(parsed.year, parsed.month, parsed.day)
                    cell.number_format = DATE_FORMAT

        for index, width in enumerate(widths, start=1):
            if index <= last_column:
                worksheet.column_dimensions[get_column_letter(index)].width = width

        worksheet.freeze_panes = "A2"
        if rows:
            worksheet.auto_filter.ref = (
                f"A1:{get_column_letter(last_column)}{len(rows) + 1}"
            )
