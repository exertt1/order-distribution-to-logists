"""Доменные модели: ФУЛ, заказ Cloud, сотрудник.

Модели содержат только нормализованные поля и не принимают решений —
выбор группы и логиста живёт в logic_engine.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from constants import Categories, Text
from utils import (
    determine_group,
    employee_group,
    extract_order_id,
    is_available_employee,
    is_specialist,
    norm_supplier,
    norm_text,
    parse_date,
    person_key,
)


@dataclass
class Employee:
    """Сотрудник из выгрузки 1С."""

    name: str
    role: str
    state: str
    code: str = ""

    group: Optional[str] = field(init=False, default=None)
    available: bool = field(init=False, default=False)
    key: tuple = field(init=False, default=())

    def __post_init__(self):
        self.name = " ".join(str(self.name or "").split())
        self.role = str(self.role or "")
        self.state = str(self.state or "")
        self.group = employee_group(self.role)
        self.available = self.group is not None and is_specialist(self.role) and is_available_employee(
            self.state
        )
        self.key = person_key(self.name)

    @property
    def unavailable_reason(self) -> str:
        """Почему сотрудник не может получить заказ."""
        if not is_specialist(self.role):
            return f"должность не специалист: {self.role}"
        if self.group is None:
            return f"группа не определяется по должности: {self.role}"
        if not is_available_employee(self.state):
            return f"состояние: {self.state}"
        return ""


@dataclass
class CloudOrder:
    """Запись реестра Cloud."""

    order_id: str
    supplier: str
    logist: str
    status: str
    brand: str = ""
    method: str = ""
    country: str = ""
    cutoff: object = ""
    ul_date: object = ""
    confirm_date: object = ""
    docs_date: object = ""
    comment: str = ""

    order_key: str = field(init=False, default="")
    supplier_key: str = field(init=False, default="")
    logist_key: tuple = field(init=False, default=())

    def __post_init__(self):
        self.order_id = " ".join(str(self.order_id or "").split())
        self.supplier = " ".join(str(self.supplier or "").split())
        self.logist = " ".join(str(self.logist or "").split())
        self.status = " ".join(str(self.status or "").split())
        self.order_key = self.order_id.lower()
        self.supplier_key = norm_supplier(self.supplier)
        self.logist_key = person_key(self.logist)


@dataclass
class FulItem:
    """Строка выгрузки ФУЛ и результат её обработки."""

    number: str
    ful_date: object
    cutoff: object
    status: str
    comment: str
    method: str
    brand: str
    supplier: str
    country: str

    # Вычисляемые поля
    order_id: Optional[str] = field(init=False, default=None)
    supplier_key: str = field(init=False, default="")
    group: Optional[str] = field(init=False, default=None)

    # Результат обработки
    category: str = field(init=False, default=Categories.NEW)
    is_duplicate: bool = field(init=False, default=False)
    duplicate_comment: str = field(init=False, default="")
    logist: Optional[str] = field(init=False, default=None)
    reason_code: str = field(init=False, default="")
    reason_text: str = field(init=False, default="")
    attention: List[str] = field(init=False, default_factory=list)
    is_gap: bool = field(init=False, default=False)

    def __post_init__(self):
        self.number = " ".join(str(self.number or "").split())
        self.supplier = " ".join(str(self.supplier or "").split())
        self.brand = " ".join(str(self.brand or "").split())
        self.method = " ".join(str(self.method or "").split())
        self.country = " ".join(str(self.country or "").split())
        self.status = " ".join(str(self.status or "").split())
        self.comment = str(self.comment or "")

        self.order_id = extract_order_id(self.comment)
        self.supplier_key = norm_supplier(self.supplier)
        self.group = determine_group(self.method, self.country)

    # --- Производные значения для отчёта ---

    @property
    def date_label(self) -> str:
        from utils import fmt_date

        return fmt_date(self.ful_date, Text.UNDEFINED)

    @property
    def cut_off_label(self) -> str:
        from utils import fmt_date

        return fmt_date(self.cutoff, Text.UNDEFINED)

    @property
    def order_label(self) -> str:
        return self.order_id or Text.UNDEFINED

    @property
    def logist_label(self) -> str:
        return self.logist or Text.UNDEFINED

    @property
    def needs_attention(self) -> bool:
        return bool(self.attention)
