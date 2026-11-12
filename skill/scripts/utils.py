"""Нормализация, разбор дат и определение группы.

Только стандартная библиотека: модуль используется и навыком, и тестами.
"""

import re
from datetime import date, datetime, timedelta
from typing import Optional

from constants import ChinaCountry, DeliveryMethods, Groups, RoleMarkers


# openpyxl отдаёт даты числом дней от 1899-12-30, если ячейка без формата даты
_EXCEL_EPOCH = date(1899, 12, 30)

_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d",
    "%d.%m.%Y %H:%M:%S",
    "%d.%m.%Y %H:%M",
    "%d.%m.%Y",
    "%d.%m.%y",
    "%d-%m-%Y",
    "%d/%m/%Y",
)

_PUNCTUATION = re.compile(r"[.,;:\-–—/\\()\"'«»*]+")


def parse_date(value) -> Optional[date]:
    """Разбирает дату из Excel и возвращает `date` или None.

    Поддерживаются datetime/date, числовой серийный номер Excel и строки
    в известных форматах. Нераспознанное значение не угадывается.
    """
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        # Серийный номер Excel: 1 = 1900-01-01, но с учётом «високосного» багa
        # используем эпоху 1899-12-30, она даёт корректный результат для всех
        # дат после 1900-03-01.
        if value <= 0:
            return None
        return _EXCEL_EPOCH + timedelta(days=int(value))

    raw = str(value).strip()
    if not raw:
        return None

    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue

    # Число внутри строки («46338»)
    if re.fullmatch(r"\d{5}(\.0+)?", raw):
        try:
            return _EXCEL_EPOCH + timedelta(days=int(float(raw)))
        except (ValueError, OverflowError):
            return None

    return None


def fmt_date(value, default: str = "") -> str:
    """Дата в формате ДД.ММ.ГГГГ или `default`, если разобрать не удалось."""
    parsed = parse_date(value)
    if parsed is None:
        return default
    return parsed.strftime("%d.%m.%Y")


def norm_text(value) -> str:
    """Нижний регистр, без лишних пробелов по краям и внутри."""
    if value is None:
        return ""
    return " ".join(str(value).split()).lower()


def norm_supplier(value) -> str:
    """Ключ поставщика: регистр, пробелы и пунктуация приводятся к единому виду.

    «Nike Inc.», «NIKE  INC» и «nike-inc» дают один ключ «nike inc».
    """
    if value is None:
        return ""
    text = str(value).lower()
    text = _PUNCTUATION.sub(" ", text)
    return " ".join(text.split())


def person_key(name) -> tuple:
    """Ключ сопоставления ФИО: (фамилия, инициалы).

    «Иванов И.И.» и «Иванов Иван Иванович» дают («иванов», «и.и.»),
    поэтому короткие имена из Cloud сопоставляются с полными ФИО из 1С.
    """
    text = norm_text(name).replace("-", " ")
    words = re.findall(r"[а-яёa-z]+", text)
    if not words:
        return ("", "")

    surname = words[0]
    rest = words[1:]
    initials = ""
    for word in rest:
        initials += word[0] + "."
    return (surname, initials)


def extract_order_id(text) -> Optional[str]:
    """Номер заказа вида S0001234 из комментария ФУЛ."""
    if not text or not isinstance(text, str):
        return None
    match = re.search(r"[Ss]\s?(\d{3,})", text)
    if not match:
        return None
    return "S" + match.group(1)


def is_china(country) -> bool:
    """Страна отправления — Китай или Гонконг."""
    return norm_text(country) in ChinaCountry.CODES


def determine_group(method, country) -> Optional[str]:
    """Группа логистов по способу доставки и стране отправления.

    air → авиаперевозки; не air + Китай/Гонконг → ВЭД;
    не air + не Китай → мультимодальные; нет способа доставки — группа
    не определяется; нет страны при не-air — тоже не определяется.
    """
    method_key = norm_text(method)
    if not method_key:
        return None

    if method_key == DeliveryMethods.AIR:
        return Groups.AIR

    country_key = norm_text(country)
    if not country_key:
        return None

    if is_china(country_key):
        return Groups.VED

    return Groups.MULTI


def group_label(group: Optional[str]) -> str:
    """Подпись группы для отчёта."""
    if not group:
        return "не определено"
    return Groups.LABELS.get(group, group)


def is_active_status(status) -> bool:
    """Статус заказа Cloud «в работе» (регистр и пробелы не важны)."""
    return norm_text(status) == "в работе"


def is_available_employee(state) -> bool:
    """Сотрудник доступен, только если его состояние ровно «Работает»."""
    return norm_text(state) == "работает"


def employee_group(role) -> Optional[str]:
    """Группа сотрудника по должности."""
    role_key = norm_text(role)
    if not role_key:
        return None

    if any(marker in role_key for marker in RoleMarkers.AIR):
        return Groups.AIR
    if any(marker in role_key for marker in RoleMarkers.VED):
        return Groups.VED
    if any(marker in role_key for marker in RoleMarkers.MULTI):
        return Groups.MULTI
    return None


def is_specialist(role) -> bool:
    """Должность относится к специалистам (исключает ассистентов и руководителей)."""
    return RoleMarkers.SPECIALIST in norm_text(role)


def plural_orders(count: int) -> str:
    """Согласование слова «заказ» с числом: 1 заказ, 2 заказа, 5 заказов."""
    if count % 10 == 1 and count % 100 != 11:
        return f"{count} заказ"
    if count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        return f"{count} заказа"
    return f"{count} заказов"
