from openpyxl import load_workbook
from typing import List, Dict, Any, Optional
import re

# Импортируем наши модели и утилиты
from ..models import FulItem, CloudOrder, Employee
from ..parser import normalize_supplier_name, extract_order_id  # Допустим, эти функции в utils.py
from ..constants import ColumnHeaders as CH


class ExcelReader:
    """
    Класс для чтения данных из Excel файлов и преобразования их в доменные объекты.
    """

    def __init__(self):
        # Можно добавить логгер или настройки здесь, если нужно
        pass

    def _read_raw_rows(self, file_path: str) -> tuple[List[str], List[tuple]]:
        """
        Внутренний метод: читает файл и возвращает заголовки + список строк значений.
        Избавляет от дублирования кода в публичных методах.
        """
        try:
            wb = load_workbook(filename=file_path, data_only=True)
            ws = wb.active

            rows = list(ws.iter_rows(values_only=True))

            if not rows:
                return [], []

            headers = [str(h).strip() for h in rows[0] if h is not None]
            data_rows = rows[1:]

            # Закрываем workbook, чтобы освободить ресурсы
            wb.close()

            return headers, data_rows

        except Exception as e:
            raise IOError(f"Failed to read Excel file {file_path}: {e}")

    def _map_row_to_dict(self, headers: List[str], row_values: tuple) -> Dict[str, Any]:
        """
        Создает словарь из строки, сопоставляя значения с заголовками.
        Пропускает пустые ячейки (None), заменяя их на "".
        """
        record = {}
        for i, header in enumerate(headers):
            value = row_values[i] if i < len(row_values) else None
            # Нормализация: None -> "", strip пробелов для строк
            if value is None:
                clean_value = ""
            elif isinstance(value, str):
                clean_value = value.strip()
            else:
                clean_value = value

            record[header] = clean_value
        return record

    # --- ПУБЛИЧНЫЕ МЕТОДЫ ЧТЕНИЯ ---

    def read_fuls(self, file_path: str) -> List[FulItem]:
        """
        Читает файл FUL и возвращает список объектов FulItem.
        Логика парсинга ID и нормализации вынесена в __post_init__ модели FulItem.
        """
        headers, data_rows = self._read_raw_rows(file_path)

        # Проверка наличия обязательных колонок
        required_cols = {CH.FUL_NUMBER, CH.FUL_COMMENT, CH.FUL_SUPPLIER}
        missing_cols = required_cols - set(headers)
        if missing_cols:
            raise ValueError(f"Missing required columns in FUL file: {missing_cols}")

        fuls_list = []
        for row_vals in data_rows:
            if all(v is None or v == "" for v in row_vals):
                continue

            raw_data = self._map_row_to_dict(headers, row_vals)

            # Создаем объект FulItem.
            # Конструктор передаст сырые данные, а __post_init__ сделает всю грязную работу.
            try:
                ful_obj = FulItem(
                    ful_number=raw_data.get(CH.FUL_NUMBER, ""),
                    ful_datetime_raw=str(raw_data.get(CH.FUL_DATE, "")),  # Приводим к строке сразу
                    cut_off_date_raw=str(raw_data.get(CH.FUL_CUTOFF, "")),
                    status_ful=raw_data.get(CH.FUL_STATUS, ""),
                    supplier_raw=raw_data.get(CH.FUL_SUPPLIER, ""),
                    brand=raw_data.get(CH.FUL_BRAND, ""),
                    method_raw=raw_data.get(CH.FUL_METHOD, ""),
                    country_raw=raw_data.get(CH.FUL_COUNTRY, ""),
                    comment_raw=raw_data.get(CH.FUL_COMMENT, "")
                )
                fuls_list.append(ful_obj)
            except Exception as e:
                print(f"Warning: Failed to create FulItem from row {raw_data.get(CH.FUL_NUMBER)}: {e}")
                # Или добавляем в список ошибок, если нужно строго

        return fuls_list

    def read_cloud_history(self, file_path: str) -> List[CloudOrder]:
        """
        Читает реестр Cloud и возвращает список объектов CloudOrder.
        """
        headers, data_rows = self._read_raw_rows(file_path)

        required_cols = {CH.CLOUD_ORDER_ID, CH.CLOUD_SUPPLIER, CH.CLOUD_LOGIST, CH.CLOUD_STATUS}
        missing_cols = required_cols - set(headers)
        if missing_cols:
            raise ValueError(f"Missing required columns in Cloud file: {missing_cols}")

        orders_list = []
        for row_vals in data_rows:
            if all(v is None or v == "" for v in row_vals):
                continue

            raw_data = self._map_row_to_dict(headers, row_vals)

            order_obj = CloudOrder(
                order_id=raw_data.get(CH.CLOUD_ORDER_ID, ""),
                supplier_raw=raw_data.get(CH.CLOUD_SUPPLIER, ""),
                logist_name_raw=raw_data.get(CH.CLOUD_LOGIST, ""),
                status_raw=raw_data.get(CH.CLOUD_STATUS, ""),
                brand=raw_data.get(CH.CLOUD_BRAND, ""),
                method_raw=raw_data.get(CH.CLOUD_METHOD, ""),
                country_raw=raw_data.get(CH.CLOUD_COUNTRY, ""),
                cut_off_date=raw_data.get(CH.CLOUD_CUTOFF, ""),
                ul_date=raw_data.get(CH.CLOUD_UL_DATE, ""),
                comment_raw=raw_data.get(CH.CLOUD_COMMENT, "")
            )
            orders_list.append(order_obj)

        return orders_list

    def read_employees(self, file_path: str) -> List[Employee]:
        """
        Читает справочник сотрудников.
        """
        headers, data_rows = self._read_raw_rows(file_path)

        required_cols = {CH.EMP_NAME, CH.EMP_STATE, CH.EMP_ROLE}
        missing_cols = required_cols - set(headers)
        if missing_cols:
            raise ValueError(f"Missing required columns in Employees file: {missing_cols}")

        employees_list = []
        for row_vals in data_rows:
            if all(v is None or v == "" for v in row_vals):
                continue

            raw_data = self._map_row_to_dict(headers, row_vals)

            emp_obj = Employee(
                name=raw_data.get(CH.EMP_NAME, ""),
                role=raw_data.get(CH.EMP_ROLE, ""),
                state=raw_data.get(CH.EMP_STATE, ""),
                code=raw_data.get(CH.EMP_CODE, "")
            )
            employees_list.append(emp_obj)

        return employees_list