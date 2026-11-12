from typing import Set, List
from models import CloudOrder, FulItem, Employee
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Tuple
from utils import compare_suppliers



# Предполагаем, что у тебя есть модель для строк Cloud

def select_logist(group_type: str, supplier_name: str, cloud_history: List[CloudOrder], employees: List[Employee]):

    available_staff: list[Employee] = [
        emp for emp in employees
        if emp.group_type == group_type
        and emp.is_available
    ]

    if not available_staff:
        return None, f"No available staff in {group_type} group"

    history_counts = {}
    for emp in available_staff:
        count = sum(1 for order in cloud_history
                    if order.logist_normalized == emp.name_normalized
                    and compare_suppliers(order.supplier_normalized, supplier_name))
        history_counts[emp.name] = count

    best_logist = None
    max_count = -1

    for name, count in history_counts.items():
        if count > max_count:
            max_count = count
            best_logist = name

    if max_count <= 0 or best_logist is None:
        load_scores = {}
        for emp in available_staff:
            active_orders = sum(1 for order in cloud_history
                                if order.logist_normalized == emp.name_normalized
                                and order.is_active)
            load_scores[emp.name] = active_orders

        # min() по словарю стабилен: при равной загрузке берётся первый по порядку
        # сотрудников в справочнике 1С.
        best_logist = min(load_scores, key=load_scores.get)
        reason = (f"наименее загруженный в группе {group_type}: "
                  f"{load_scores[best_logist]} заказов в работе")
        return best_logist, reason

    reason = (f"предпочтительный по истории: {max_count} "
              f"заказов этого поставщика в Cloud")
    return best_logist, reason

def build_cloud_index(cloud_history: List[CloudOrder]) -> Set[str]:
    """
    Создает множество нормализованных Order_ID из истории Cloud.
    Используется для мгновенной проверки на дубликаты.
    """
    cloud_ids = set()
    for order in cloud_history:
        if order.order_id:
            # Нормализуем ID: strip + lower, чтобы поймать " S123 " vs "s123"
            norm_id = order.order_id.strip().lower()
            cloud_ids.add(norm_id)

    return cloud_ids

def _ful_date_str(ful: FulItem) -> str:
    """Дата ФУЛ в формате ДД.ММ.ГГГГ.

    Значение приходит из Excel как есть, поэтому пробуем известные форматы,
    а если распарсить не удалось — возвращаем исходную строку без выдумывания.
    """
    raw = (ful.ful_datetime_raw or "").strip()
    if not raw:
        return "дата не определена"

    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d",
                "%d.%m.%Y %H:%M:%S", "%d.%m.%Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%d.%m.%Y")
        except ValueError:
            continue

    return raw


def mark_fuls_as_duplicates(fuls_list: List[FulItem], cloud_index: Set[str]) -> None:
    """
    Модифицирует список объектов FulItem на месте (in-place).
    Устанавливает flags is_duplicate и duplicate_note для тех,
    чей Order_ID уже существует в облаке.

    Args:
        fuls_list: Список объектов FUL.
        cloud_index: Множество существующих Order_ID (normalized).
    """
    for ful in fuls_list:
        # 1. Если не смогли извлечь Order_ID при создании объекта
        if not ful.order_id:
            # Это не дубликат, но ошибка данных. Помечаем отдельно.
            ful.requires_attention = True
            ful.warnings.append("Critical: Could not extract Order ID from comment.")
            continue

        # 2. Нормализуем extracted ID для сравнения с индексом
        # Важно: сделать то же самое, что делали при создании cloud_index (.strip().lower())
        normalized_extracted_id = ful.order_id.strip().lower()

        # 3. Проверка наличия в Cloud
        if normalized_extracted_id in cloud_index:
            ful.is_duplicate = True
            # Формируем текст для обновления комментария в итоговом отчете.
            # Дата в комментарии — дата ФУЛ, а не дата запуска скрипта.
            ful.duplicate_note = f"Повторная отправка ФУЛа, {_ful_date_str(ful)}"

            # Дубликаты НЕ требуют назначения нового логиста, поэтому requires_attention = False
            # (если только это не конфликт статусов, но по ТЗ просто обновляем коммент)
            ful.requires_attention = False

        else:
            ful.is_duplicate = False
            # Оставляем requires_attention как есть (False), пока не определим группу/логиста


def group_fuls_into_batches(fuls_list: List[FulItem]) -> Dict[Tuple[str, str], List[FulItem]]:
    """
    Группирует новые (не дубликаты!) ФУЛы по ключу: (Нормализованный Поставщик, Тип Группы).

    Args:
        fuls_list: Список объектов FulItem, уже прошедших проверку на дубликаты
                   (is_duplicate == False).

    Returns:
        Словарь вида:
        {
            ('nike inc.', 'AIR'): [ful_obj_1, ful_obj_2],
            ('zara ltd.', 'MULTI'): [ful_obj_3]
        }
    """
    batches = defaultdict(list)

    for ful in fuls_list:
        # 1. Защита от дубликатов (хотя они должны быть отсеяны до вызова этой функции)
        if ful.is_duplicate:
            continue

        # 2. Защита от ошибок определения группы
        # Если группа None (нет страны/метода), такой заказ уходит в "Attention Required"
        # и НЕ должен участвовать в распределении логистов.
        if not ful.assigned_group:
            ful.requires_attention = True
            ful.warnings.append("Cannot determine logistics group due to missing data")
            continue

        # 3. Создаем уникальный ключ батча
        # Ключ - это кортеж (tuple), так как он хэшируемый.
        batch_key = (ful.supplier_normalized, ful.assigned_group)

        # 4. Добавляем объект в соответствующий список
        batches[batch_key].append(ful)

    return dict(batches)  # Возвращаем обычный dict вместо defaultdict для чистоты интерфейса