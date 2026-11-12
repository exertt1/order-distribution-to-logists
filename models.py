from dataclasses import dataclass, field
from typing import Optional, List
from .parser import extract_order_id, normalize_supplier_name, determine_group, normalize_person_name
from .constants import OrderStatuses


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


from dataclasses import dataclass
from typing import Optional


@dataclass
class CloudOrder:
    """
    Представляет запись о заказе в реестре Cloud (история).
    Используется для расчета загрузки логистов и анализа истории поставщиков.
    """

    # --- Обязательные поля из Excel ---
    order_id: str  # Колонка "Заказ" (Уникальный ID, напр. S123456)
    supplier_raw: str  # Колонка "Поставщик" (Напр. "Nike Inc.")
    logist_name_raw: str  # Колонка "Логист" (Напр. "Иванов И.И.")
    status_raw: str  # Колонка "статус" (Напр. "в работе" или "confirm")

    # Дополнительные поля для полноты картины (можно использовать в логах)
    brand: str = ""  # Колонка "Бренд"
    method_raw: str = ""  # Колонка "Способ доставки"
    country_raw: str = ""  # Колонка "Страна отправления"
    cut_off_date: str = ""  # Колонка "cut-off"
    ul_date: str = ""  # Колонка "Дата получения УЛ"
    comment_raw: str = ""  # Колонка "Комментарий"

    # --- Вычисляемые/Нормализованные поля (заполняются в __post_init__) ---
    order_id_normalized: str = ""  # Для быстрого поиска в set/dict
    supplier_normalized: str = ""  # Для группировки истории по поставщику
    logist_normalized: str = ""  # Для сопоставления с employees.xlsx

    @property
    def is_active(self) -> bool:
        """Проверяет, является ли заказ активным (влияет на загрузку)."""
        # Сравниваем с константой из constants.py
        return self.status_raw.strip().lower() == OrderStatuses.ACTIVE.lower()

    def __post_init__(self):
        """Автоматическая нормализация данных после создания."""
        if self.order_id:
            self.order_id_normalized = self.order_id.strip().lower()

        if self.supplier_raw:
            self.supplier_normalized = normalize_supplier_name(self.supplier_raw)

        if self.logist_name_raw:
            self.logist_normalized = normalize_person_name(self.logist_name_raw)


from dataclasses import dataclass
from typing import Optional


@dataclass
class Employee:
    """
    Представляет запись о сотруднике из файла employees.xlsx.
    Используется для фильтрации доступных специалистов и определения их групп.
    """

    # --- Обязательные поля из Excel ---
    name: str  # Колонка "Наименование" (ФИО, напр. "Иванов И.И.")
    role: str  # Колонка "Должность" (напр. "специалист по авиаперевозкам")
    state: str  # Колонка "Текущее состояние" (напр. "Работает", "Отпуск")
    code: str = ""  # Колонка "Код (Таб. №)" - опционально, но полезно для логов

    # --- Вычисляемые/Нормализованные поля (заполняются в __post_init__) ---
    name_normalized: str = ""  # Для сопоставления с историей Cloud ("иванов и.и.")
    is_available: bool = False  # Флаг: можно ли назначать этому человеку заказы?
    group_type: Optional[str] = None  # К какой группе он относится? AIR / VED / MULTI / None

    def __post_init__(self):
        """
        Автоматическая нормализация данных после создания объекта.
        Здесь мы определяем доступность и группу сотрудника.
        """
        # 1. Нормализация имени для поиска в истории
        if self.name:
            self.name_normalized = normalize_person_name(self.name)

        # 2. Определение группы на основе должности
        # Используем маппинг ролей из constants.py или жесткие проверки
        role_lower = self.role.lower() if self.role else ""

        if "авиа" in role_lower or "air" in role_lower:
            self.group_type = "AIR"
        elif "вед" in role_lower or "экспорт" in role_lower or "import" in role_lower:
            self.group_type = "VED"
        elif "мульти" in role_lower or "мультимод" in role_lower:
            self.group_type = "MULTI"
        else:
            self.group_type = None  # Ассистенты, руководители или неизвестные роли

        # 3. Проверка доступности
        # Сотрудник доступен, если он "работает" И является "специалистом" нужной группы
        # В ТЗ сказано исключать ассистентов и руководителей.
        is_specialist = "специалист" in role_lower
        is_working = self.state.strip().lower() == "работает"

        self.is_available = is_specialist and is_working

        # Если сотрудник не специалист (например, руководитель),
        # его группа может быть определена, но is_available все равно False.
        # Это важно для логики select_logist_for_batch.


# Вспомогательная функция для нормализации ФИО
def normalize_person_name(name: str) -> str:
    """
    Приводит ФИО к единому виду для сравнения.
    Убирает лишние пробелы, приводит к нижнему регистру.
    Пример: ' Иванов  И.И. ' -> 'иванов и.и.'
    """
    if not name:
        return ""
    # split() разбивает по любым пробельным символам, join склеивает через один пробел
    cleaned = ' '.join(str(name).split())
    return cleaned.lower()