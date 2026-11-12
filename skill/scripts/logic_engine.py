"""Правила распределения: дубли, группы, выбор логиста, пропуски, внимание.

Решения принимает только этот модуль — языковая модель их не подменяет.
"""

from typing import Dict, Iterable, List, Optional, Tuple

from constants import (
    AttentionReasons,
    Categories,
    Reasons,
    Text,
)
from models import CloudOrder, Employee, FulItem
from utils import fmt_date, group_label, is_active_status, parse_date, plural_orders


def build_cloud_index(cloud: List[CloudOrder]) -> set:
    """Множество нормализованных номеров заказов из Cloud."""
    return {order.order_key for order in cloud if order.order_key}


def cloud_last_date(cloud: List[CloudOrder]):
    """Самая поздняя дата записи в реестре Cloud.

    Учитываются даты фактического движения заказа: получение УЛ, подтверждение
    и получение документов. Cut-off — контрольная дата в будущем, для
    сравнения с датой ФУЛ она не годится.
    """
    dates = []
    for order in cloud:
        for value in (order.ul_date, order.confirm_date, order.docs_date):
            parsed = parse_date(value)
            if parsed is not None:
                dates.append(parsed)
    return max(dates) if dates else None


def mark_duplicates(fuls: List[FulItem], cloud_keys: set) -> None:
    """Помечает повторы: заказ уже в Cloud или повтор внутри пачки.

    Для повтора строка Cloud не создаётся, а комментарий содержит дату ФУЛ.
    """
    seen = {}
    for ful in fuls:
        if not ful.order_id:
            continue

        key = ful.order_id.lower()

        if key in cloud_keys:
            ful.is_duplicate = True
            ful.category = Categories.DUP_CLOUD
        elif key in seen:
            ful.is_duplicate = True
            ful.category = Categories.DUP_BATCH
        else:
            seen[key] = ful.number

        if ful.is_duplicate:
            ful.duplicate_comment = Text.DUP_COMMENT.format(
                date=fmt_date(ful.ful_date, Text.UNDEFINED)
            )


def mark_gaps(fuls: List[FulItem], cloud_keys: set, last_date) -> None:
    """Возможные пропуски: ФУЛ нет в Cloud, хотя пришёл раньше последней записи."""
    if last_date is None:
        return

    for ful in fuls:
        if ful.is_duplicate or not ful.order_id:
            continue
        ful_date = parse_date(ful.ful_date)
        if ful_date is None:
            continue
        if ful.order_id.lower() in cloud_keys:
            continue
        if ful_date < last_date:
            ful.is_gap = True


def collect_data_attention(ful: FulItem) -> None:
    """Причины «Требует внимания», связанные с неполными данными ФУЛ."""
    if not ful.order_id:
        ful.attention.append(AttentionReasons.NO_ORDER)
        return

    if not ful.method:
        ful.attention.append(AttentionReasons.NO_METHOD)
        return

    if ful.group is None:
        ful.attention.append(AttentionReasons.NO_COUNTRY)


def group_into_batches(fuls: Iterable[FulItem]) -> Dict[Tuple[str, str], List[FulItem]]:
    """Пачки: один поставщик + одна группа = одно решение о логисте."""
    batches: Dict[Tuple[str, str], List[FulItem]] = {}
    for ful in fuls:
        key = (ful.supplier_key, ful.group)
        batches.setdefault(key, []).append(ful)
    return batches


def _history_counts(supplier_key: str, staff: List[Employee], cloud: List[CloudOrder]) -> Dict[tuple, int]:
    counts = {}
    for employee in staff:
        counts[employee.key] = 0
    for order in cloud:
        if order.supplier_key != supplier_key:
            continue
        if order.logist_key in counts:
            counts[order.logist_key] += 1
    return counts


def _active_loads(staff: List[Employee], cloud: List[CloudOrder]) -> Dict[tuple, int]:
    loads = {}
    for employee in staff:
        loads[employee.key] = sum(
            1
            for order in cloud
            if order.logist_key == employee.key and is_active_status(order.status)
        )
    return loads


def select_logist(
    group: str,
    supplier_key: str,
    cloud: List[CloudOrder],
    employees: List[Employee],
) -> Tuple[Optional[Employee], str, str]:
    """Выбирает логиста для пачки.

    Возвращает (сотрудник | None, код основания, текстовое обоснование).
    """
    staff = [employee for employee in employees if employee.group == group]
    available = [employee for employee in staff if employee.available]

    if not staff:
        return (
            None,
            Reasons.NO_STAFF,
            f"в группе {group_label(group)} нет сотрудников с подходящей должностью",
        )

    if not available:
        details = "; ".join(
            f"{employee.name} — {employee.unavailable_reason}" for employee in staff
        )
        return (
            None,
            Reasons.NO_STAFF,
            f"в группе {group_label(group)} нет доступных логистов: {details}",
        )

    history = _history_counts(supplier_key, staff, cloud)
    top_key, top_count = max(history.items(), key=lambda item: item[1])
    top_employee = next((employee for employee in staff if employee.key == top_key), None)

    if top_count > 0 and top_employee is not None and top_employee.available:
        return (
            top_employee,
            Reasons.PREFERRED,
            f"предпочтительный по истории: {plural_orders(top_count)} этого поставщика в Cloud",
        )

    if top_count > 0 and top_employee is not None:
        prefix = (
            f"предпочтительный логист {top_employee.name} недоступен "
            f"({top_employee.unavailable_reason}); выбран наименее загруженный"
        )
    else:
        prefix = "поставщик новый, истории в Cloud нет; выбран наименее загруженный"

    loads = _active_loads(available, cloud)
    best_key = min(loads, key=loads.get)
    best_employee = next(employee for employee in available if employee.key == best_key)

    return (
        best_employee,
        Reasons.LEAST_LOADED,
        f"{prefix}: {plural_orders(loads[best_key])} в работе",
    )


def distribute(
    fuls: List[FulItem],
    cloud: List[CloudOrder],
    employees: List[Employee],
) -> Dict[str, int]:
    """Полный проход по правилам. Возвращает сводку по категориям."""
    cloud_keys = build_cloud_index(cloud)
    last_date = cloud_last_date(cloud)

    mark_duplicates(fuls, cloud_keys)
    mark_gaps(fuls, cloud_keys, last_date)

    candidates = []
    for ful in fuls:
        if ful.is_duplicate:
            continue
        collect_data_attention(ful)
        if ful.attention:
            ful.category = Categories.ATTENTION
            ful.reason_code = "данные ФУЛ"
            ful.reason_text = "распределение невозможно без уточнения данных"
        else:
            candidates.append(ful)

    batches = group_into_batches(candidates)
    for (supplier_key, group), items in batches.items():
        employee, reason_code, reason_text = select_logist(
            group, supplier_key, cloud, employees
        )

        for index, ful in enumerate(items):
            if employee is None:
                ful.attention.append(
                    AttentionReasons.NO_STAFF.format(group=group_label(group))
                )
                ful.category = Categories.ATTENTION
                ful.reason_code = reason_code
                ful.reason_text = reason_text
                continue

            ful.logist = employee.name
            if index == 0:
                ful.reason_code = reason_code
                ful.reason_text = reason_text
            else:
                ful.reason_code = Reasons.SAME_SUPPLIER
                ful.reason_text = (
                    f"поставщик уже распределён логисту {employee.name} в этой пачке "
                    f"({reason_code} по первому ФУЛ)"
                )

    return summarize(fuls)


def summarize(fuls: List[FulItem]) -> Dict[str, int]:
    """Счётчики для короткого ответа пользователю."""
    summary = {
        "new": 0,
        "dup": 0,
        "attention": 0,
        "gaps": 0,
    }
    for ful in fuls:
        if ful.is_duplicate:
            summary["dup"] += 1
        elif ful.attention:
            summary["attention"] += 1
        else:
            summary["new"] += 1
        if ful.is_gap:
            summary["gaps"] += 1
    return summary


def batches_by_group(fuls: Iterable[FulItem]) -> Dict[str, int]:
    """Сколько заказов пришлось на каждую группу (для отчёта)."""
    result = {}
    for ful in fuls:
        if ful.is_duplicate or ful.attention:
            continue
        label = group_label(ful.group)
        result[label] = result.get(label, 0) + 1
    return result
