from openpyxl import Workbook
from typing import List
from ..models import FulItem
from ..constants import ColumnHeaders as CH


class ExcelWriter:
    """
    Класс для записи результатов обработки в итоговый Excel-файл.
    """

    def __init__(self, output_path: str):
        self.output_path = output_path
        self.wb = Workbook()

        # Удаляем дефолтный пустой лист "Sheet", если он мешает
        if "Sheet" in self.wb.sheetnames:
            del self.wb["Sheet"]

    def save_results(self, processed_fuls: List[FulItem]):
        """
        Главный метод сохранения. Разделяет данные по категориям и пишет листы.
        """
        # 1. Группировка данных для разных листов
        new_orders = [f for f in processed_fuls if not f.is_duplicate and not f.requires_attention]
        duplicates = [f for f in processed_fuls if f.is_duplicate]
        attention_required = [f for f in processed_fuls if f.requires_attention and not f.is_duplicate]

        # 2. Запись Листа 1: New Orders
        self._write_new_orders_sheet(new_orders)

        # 3. Запись Листа 2: Duplicates
        self._write_duplicates_sheet(duplicates)

        # 4. Запись Листа 3: Audit Log / Attention Required
        self._write_audit_sheet(attention_required)

        # 5. Сохранение файла
        self.wb.save(self.output_path)
        print(f"✅ Result saved to {self.output_path}")

    def _write_new_orders_sheet(self, fuls: List[FulItem]):
        """Пишет новые заказы строго по форме реестра Cloud (12 колонок)."""
        ws = self.wb.create_sheet(title="New Orders")

        # Определяем заголовки (порядок важен!)
        headers = [
            CH.CLOUD_ORDER_ID,  # Заказ
            CH.CLOUD_SUPPLIER,  # Поставщик
            CH.CLOUD_BRAND,  # Бренд
            CH.CLOUD_LOGIST,  # Логист
            CH.CLOUD_STATUS,  # статус
            CH.CLOUD_CONFIRM_DATE,  # дата подтверждения
            CH.CLOUD_CUTOFF,  # cut-off
            CH.CLOUD_UL_DATE,  # Дата получения УЛ
            CH.CLOUD_COUNTRY,  # Страна отправления
            CH.CLOUD_METHOD,  # Способ доставки
            CH.CLOUD_DOCS_DATE,  # Документы получены (дата)
            CH.CLOUD_COMMENT  # Комментарий
        ]
        ws.append(headers)

        for ful in fuls:
            row_data = [
                ful.order_id or "",  # Из модели FulItem
                ful.supplier_raw or "",
                # Или normalized? Лучше raw из FUL, если нужно сохранить оригинал, либо normalized для чистоты. В ТЗ не уточнено, но обычно пишут как пришло или нормализовано. Давай normalized для консистентности истории.
                ful.brand or "",
                ful.selected_logist or "не определено",  # Если логиста нет
                "в работе",  # Дефолтный статус для нового заказа
                "",  # Дата подтверждения пуста (еще не подтвержден)
                ful.cut_off_date_raw or "",  # Переносим как есть
                ful.ful_datetime_raw or "",  # Дата ФУЛ становится датой получения УЛ
                ful.country_raw or "",
                ful.method_raw or "",
                "",  # Документы получены - пусто
                ""  # Комментарий - пусто (или можно дописать info)
            ]
            ws.append(row_data)

    def _write_duplicates_sheet(self, fuls: List[FulItem]):
        """Пишет отчет о дубликатах."""
        ws = self.wb.create_sheet(title="Duplicates")

        headers = ["Order ID", "FUL Number", "Action Description"]
        ws.append(headers)

        for ful in fuls:
            action_desc = f"Skip creation. Update comment in existing record: '{ful.duplicate_note}'"
            row_data = [
                ful.order_id or "Unknown",
                ful.ful_number or "Unknown",
                action_desc
            ]
            ws.append(row_data)

    def _write_audit_sheet(self, fuls: List[FulItem]):
        """Пишет журнал ошибок и предупреждений."""
        ws = self.wb.create_sheet(title="Attention Required")

        headers = ["Order ID", "FUL Number", "Status", "Selected Logist", "Reason/Warnings"]
        ws.append(headers)

        for ful in fuls:
            # Собираем все причины и предупреждения в одну строку
            reasons = []
            if ful.decision_reason:
                reasons.append(ful.decision_reason)
            if ful.warnings:
                reasons.extend(ful.warnings)

            combined_message = "; ".join(reasons) if reasons else "Manual review required due to data issues."

            row_data = [
                ful.order_id or "N/A",
                ful.ful_number or "N/A",
                "ERROR" if not ful.order_id else "WARNING",  # Простая логика статуса
                ful.selected_logist or "None",
                combined_message
            ]
            ws.append(row_data)