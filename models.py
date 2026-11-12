from dataclasses import dataclass, field
from typing import Optional, List
from parser import extract_order_id, normalize_supplier_name

@dataclass
class FulItem:
    # --- ОБЯЗАТЕЛЬНЫЕ ПОЛЯ ИЗ EXCEL (FUL.XLSX) ---
    ful_number: str  # Колонка "Номер" (ID упаковочного листа)
    ful_datetime_raw: str  # Колонка "Дата" (сырая строка даты/времени)
    cut_off_date_raw: str  # Колонка "Cut-off date"
    status_ful: str  # Колонка "Статус" (Новый/Принят/etc.)

    supplier_raw: str  # Колонка "Контрагент"
    brand: str  # Колонка "Бизнес единица"
    method_raw: str  # Колонка "Способ доставки"
    country_raw: str  # Колонка "Страна"
    comment_raw: str  # Колонка "Комментарий"

    # --- ВЫЧИСЛЯЕМЫЕ ПОЛЯ (заполняются в __post_init__) ---
    order_id: Optional[str] = None  # Извлеченный S... из комментария
    supplier_normalized: str = ""  # nike inc
    assigned_group: Optional[str] = None  # AIR / VED / MULTI

    # --- РЕЗУЛЬТАТЫ РАБОТЫ АГЕНТА ---
    is_duplicate: bool = False
    duplicate_note: str = ""
    selected_logist: Optional[str] = None
    decision_reason: str = ""
    requires_attention: bool = False
    warnings: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Автоматическая подготовка данных после создания объекта"""

        # 1. Парсинг Order ID
        if self.comment_raw:
            extracted = extract_order_id(self.comment_raw)
            if extracted:
                self.order_id = extracted
            else:
                self.warnings.append("Failed to parse Order ID from comment")

        # 2. Нормализация поставщика
        if self.supplier_raw:
            self.supplier_normalized = normalize_supplier_name(self.supplier_raw)

        # 3. Определение группы
        # Используем raw данные, так как они еще не очищены, но determine_group сам сделает lower/strip
        self.assigned_group = determine_group(self.method_raw, self.country_raw)

        # 4. Базовая валидация критических полей
        if not self.ful_number:
            raise ValueError("Critical Error: FUL Number is missing!")

        if not self.order_id and not self.is_duplicate:
            # Если нет ID, мы не можем проверить дубликат -> помечаем как ошибку позже
            pass