import re
from constants import DeliveryMethods, ChinaCodes, Roles, EmployeeStatuses, OrderStatuses

def extract_order_id(text):
    if not text or not isinstance(text, str):
        return None

    match = re.search(r'S\d+', text)

    if match:
        return match.group()

    return None


import re


def normalize_supplier_name(name: str) -> str:
    """
    Приводит имя к единому стандарту:
    1. Lowercase
    2. Strip spaces
    3. Remove punctuation (dots, commas, hyphens) to unify 'Inc.', 'Inc', 'Inc-'
    4. Collapse multiple spaces into one
    """
    if not name or not isinstance(name, str):
        return ""

    # 1. Lower + Strip
    s = name.lower().strip()

    # 2. Remove non-alphanumeric characters except space
    # This turns "Nike Inc." -> "nike inc" and "NIKE-INC" -> "nikeinc" (wait, careful here)
    # Better approach: Replace specific separators with space first

    # Replace dots, hyphens, commas with space
    s = re.sub(r'[.,\-]', ' ', s)

    # Split by whitespace to handle multiple spaces/tabs/newlines correctly
    parts = s.split()

    # Join back with single space
    return ' '.join(parts)


def compare_suppliers(supplier1: str, supplier2: str) -> bool:
    """
    Сравнивает двух поставщиков через строгую нормализацию.
    Возвращает True только если имена идентичны после очистки.
    """
    norm1 = normalize_supplier_name(supplier1)
    norm2 = normalize_supplier_name(supplier2)

    return norm1 == norm2

def select_logist(delivery_method: str, supplier_name: str, country: str, cloud_history: str, employees: str):
    target_role: str = ""

    if delivery_method == DeliveryMethods.AIR:
        target_role = Roles.SPECIALIST_AIR
    elif delivery_method != DeliveryMethods.AIR and country in ChinaCodes.CODES:
        target_role = Roles.SPECIALIST_VED
    else:
        target_role = Roles.SPECIALIST_MULTI

    available_stuff: list = [
        emp for emp in employees
        if emp["Должность"].lower() == target_role
        and emp["Статус"].lower() == EmployeeStatuses.ACTIVE
    ]

    if not available_stuff:
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
        for emp in available_stuff:
            active_orders = sum(1 for order in cloud_history
                                if order["Логист"] == emp["ФИО"]
                                and order["Статус"] == OrderStatuses.ACTIVE)
            load_scores[emp["ФИО"]] = active_orders

        best_logist = min(load_scores, key=load_scores.get)

    return best_logist, f"Selected {best_logist} from {group_type}"
