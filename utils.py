# utils.py
import re
from typing import Optional, List
from constants import DeliveryMethods, ChinaCodes, Roles, EmployeeStatuses, OrderStatuses
# from models import CloudOrder, Employee


def extract_order_id(comment_text: str) -> Optional[str]:
    """Извлекает ID заказа (S...) из текста комментария."""
    if not comment_text or not isinstance(comment_text, str):  # <--- ОШИБКА БЫЛА ТУТ? Нет, исправь ниже
        return None
    match = re.search(r'S\d+', comment_text)
    return match.group() if match else None

def select_logist(group_type: str, supplier_name: str, cloud_history: List[CloudOrder], employees: List[Employee]):

    available_staff: list = [
        emp for emp in employees
        if emp.group_type == group_type
        and emp.is_available
    ]

    if not available_staff:
        return None, f"No available staff in {group_type} group"

    history_counts = {}
    for emp in available_staff:
        count = sum(1 for order in cloud_history
                    if order["Логист"] == emp["ФИО"]
                    and compare_suppliers(order["Поставщик"], supplier_name))
        history_counts[emp["ФИО"]] = count

    best_logist = None
    max_count = -1

    for name, count in history_counts.items():
        if count > max_count:
            max_count = count
            best_logist = name

    if max_count == 0 or best_logist is None:
        load_scores = {}
        for emp in available_staff:
            active_orders = sum(1 for order in cloud_history
                                if order["Логист"] == emp["ФИО"]
                                and order["Статус"] == OrderStatuses.ACTIVE)
            load_scores[emp["ФИО"]] = active_orders

        best_logist = min(load_scores, key=load_scores.get)

    return best_logist, f"Selected {best_logist} from {group_type}"

def normalize_supplier_name(name: str) -> str:
    """Нормализует имя поставщика.

    Приводит к единому виду регистр, пунктуацию и пробелы,
    чтобы `Nike Inc.`, `NIKE INC` и `nike  inc` считались одним поставщиком.
    """
    if not name:
        return ""
    s = str(name).lower().strip()
    s = re.sub(r'[.,\-–—/\\()"\'«»]', ' ', s)
    return ' '.join(s.split())


def normalize_person_name(name: str) -> str:
    """Нормализует ФИО сотрудника."""
    if not name:
        return ""
    cleaned = ' '.join(str(name).split())
    return cleaned.lower()

def compare_suppliers(supplier1: str, supplier2: str) -> bool:
    """
    Сравнивает двух поставщиков через строгую нормализацию.
    Возвращает True только если имена идентичны после очистки.
    """
    norm1 = normalize_supplier_name(supplier1)
    norm2 = normalize_supplier_name(supplier2)

    return norm1 == norm2

def determine_group(method_raw: str, country_raw: str) -> Optional[str]:
    """Определяет группу доставки (AIR / VED / MULTI)."""
    # Импортируем константы здесь, чтобы избежать циклических импортов
    from constants import LogisticsGroups, ChinaCodes, DeliveryMethods

    method = method_raw.strip().lower() if method_raw else ""
    country = country_raw.strip().lower() if country_raw else ""

    if not method:
        return None

    if method == DeliveryMethods.AIR:
        return LogisticsGroups.AIR

    if country in ChinaCodes.CODES:
        return LogisticsGroups.VED

    return LogisticsGroups.MULTI