from typing import Set, List
from .models import CloudOrder
from datetime import date
from .models import FulItem
from collections import defaultdict
from typing import List, Dict, Tuple



# Предполагаем, что у тебя есть модель для строк Cloud


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

def mark_fuls_as_duplicates(fuls_list: List[FulItem], cloud_index: Set[str]) -> None:
    """
    Модифицирует список объектов FulItem на месте (in-place).
    Устанавливает flags is_duplicate и duplicate_note для тех,
    чей Order_ID уже существует в облаке.

    Args:
        fuls_list: Список объектов FUL.
        cloud_index: Множество существующих Order_ID (normalized).
    """
    today_str = date.today().strftime("%d.%m.%Y")

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
            # Формируем текст для обновления комментария в итоговом отчете
            ful.duplicate_note = f"Повторная отправка ФУЛа, {today_str}"

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