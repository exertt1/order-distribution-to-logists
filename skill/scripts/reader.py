"""Чтение трёх выгрузок Excel.

Колонки находятся по заголовкам, а не по номеру: лишние колонки игнорируются,
порядок колонок и имя листа значения не имеют.
"""

import os
from typing import Dict, List, Tuple

from constants import CLOUD, EMPLOYEE, FUL
from models import CloudOrder, Employee, FulItem


class ExcelReadError(Exception):
    """Файл не удалось прочитать или в нём нет обязательных колонок."""


def _norm_header(value) -> str:
    return " ".join(str(value).split()).lower() if value is not None else ""


class ExcelReader:
    """Читает xlsx (и xls, если установлен xlrd) в доменные объекты."""

    def _load_rows(self, path: str) -> List[Tuple[list, List[tuple]]]:
        """Возвращает список (заголовки, строки) по всем листам файла."""
        if not os.path.exists(path):
            raise ExcelReadError(f"файл не найден: {path}")

        ext = os.path.splitext(path)[1].lower()
        if ext == ".xls":
            return self._load_xls(path)
        return self._load_xlsx(path)

    def _load_xlsx(self, path: str) -> List[Tuple[list, List[tuple]]]:
        try:
            from openpyxl import load_workbook
        except ImportError as exc:  # pragma: no cover
            raise ExcelReadError("не установлен openpyxl") from exc

        try:
            workbook = load_workbook(filename=path, data_only=True)
        except Exception as exc:
            raise ExcelReadError(f"не удалось открыть xlsx: {path}: {exc}") from exc

        sheets = []
        try:
            for worksheet in workbook.worksheets:
                rows = list(worksheet.iter_rows(values_only=True))
                if not rows:
                    continue
                headers = list(rows[0])
                sheets.append((headers, rows[1:]))
        finally:
            workbook.close()

        if not sheets:
            raise ExcelReadError(f"файл пуст: {path}")
        return sheets

    def _load_xls(self, path: str) -> List[Tuple[list, List[tuple]]]:
        try:
            import xlrd
        except ImportError as exc:
            raise ExcelReadError(
                "для .xls нужен xlrd: файл нужно пересохранить в .xlsx "
                "или установить xlrd"
            ) from exc

        try:
            book = xlrd.open_workbook(path)
        except Exception as exc:
            raise ExcelReadError(f"не удалось открыть xls: {path}: {exc}") from exc

        sheets = []
        for sheet in book.sheets():
            rows = []
            for row_index in range(sheet.nrows):
                rows.append(tuple(sheet.row_values(row_index)))
            if not rows:
                continue
            sheets.append((list(rows[0]), rows[1:]))
        if not sheets:
            raise ExcelReadError(f"файл пуст: {path}")
        return sheets

    def _pick_sheet(self, path: str, required: Tuple[str, ...]) -> List[dict]:
        """Выбирает лист с наибольшим числом нужных заголовков.

        Читаются все колонки листа, но обязательные должны присутствовать.
        Возвращает строки словарями по фактическим заголовкам файла.
        """
        candidates = self._load_rows(path)
        wanted = {_norm_header(name): name for name in required}
        best = None
        best_score = -1

        for headers, rows in candidates:
            present = {_norm_header(header) for header in headers}
            score = len(set(wanted) & present)
            if score > best_score:
                best_score = score
                best = (headers, rows)

        if best is None or best_score == 0:
            raise ExcelReadError(f"не найдены заголовки колонок в файле {path}")

        headers, rows = best
        missing = [
            original for canonical, original in wanted.items() if canonical not in {_norm_header(h) for h in headers}
        ]
        if missing:
            raise ExcelReadError(
                f"в файле {path} нет обязательных колонок: {', '.join(missing)}"
            )

        # Карта «индекс колонки → заголовок как в файле»; дубли заголовков не мешают
        column_names = {}
        for index, header in enumerate(headers):
            key = _norm_header(header)
            if not key or key in column_names:
                continue
            column_names[key] = (index, str(header).strip())

        records = []
        for row in rows:
            if all(value is None or value == "" for value in row):
                continue
            record = {}
            for key, (index, title) in column_names.items():
                record[title] = row[index] if index < len(row) else None
            records.append(record)

        return records

    # --- Публичные методы ---

    def read_fuls(self, path: str) -> List[FulItem]:
        records = self._pick_sheet(path, FUL.REQUIRED)

        fuls = []
        for record in records:
            number = record.get(FUL.NUMBER)
            if number is None or str(number).strip() == "":
                continue
            fuls.append(
                FulItem(
                    number=record.get(FUL.NUMBER),
                    ful_date=record.get(FUL.DATE),
                    cutoff=record.get(FUL.CUTOFF),
                    status=record.get(FUL.STATUS),
                    comment=record.get(FUL.COMMENT),
                    method=record.get(FUL.METHOD),
                    brand=record.get(FUL.BRAND),
                    supplier=record.get(FUL.SUPPLIER),
                    country=record.get(FUL.COUNTRY),
                )
            )
        return fuls

    def read_cloud(self, path: str) -> List[CloudOrder]:
        records = self._pick_sheet(path, CLOUD.REQUIRED)

        orders = []
        for record in records:
            order_id = record.get(CLOUD.ORDER)
            if order_id is None or str(order_id).strip() == "":
                continue
            orders.append(
                CloudOrder(
                    order_id=record.get(CLOUD.ORDER),
                    supplier=record.get(CLOUD.SUPPLIER),
                    logist=record.get(CLOUD.LOGIST),
                    status=record.get(CLOUD.STATUS),
                    brand=record.get(CLOUD.BRAND),
                    method=record.get(CLOUD.METHOD),
                    country=record.get(CLOUD.COUNTRY),
                    cutoff=record.get(CLOUD.CUTOFF),
                    ul_date=record.get(CLOUD.UL_DATE),
                    confirm_date=record.get(CLOUD.CONFIRM_DATE),
                    docs_date=record.get(CLOUD.DOCS_DATE),
                    comment=record.get(CLOUD.COMMENT),
                )
            )
        return orders

    def read_employees(self, path: str) -> List[Employee]:
        records = self._pick_sheet(path, EMPLOYEE.REQUIRED)

        employees = []
        for record in records:
            name = record.get(EMPLOYEE.NAME)
            if name is None or str(name).strip() == "":
                continue
            employees.append(
                Employee(
                    name=record.get(EMPLOYEE.NAME),
                    role=record.get(EMPLOYEE.ROLE),
                    state=record.get(EMPLOYEE.STATE),
                    code=record.get(EMPLOYEE.CODE) or "",
                )
            )
        return employees
