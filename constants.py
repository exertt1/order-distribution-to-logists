# groups.py / constants.py

class OrderStatuses:
    """
    Статусы заказов в реестре Cloud.
    Используются для расчета текущей загрузки логистов.
    """
    ACTIVE = "в работе"
    CONFIRMED = "confirm"

class LogisticsGroups:
    AIR = "AIR"
    VED = "VED"
    MULTI = "MULTI"
    UNKNOWN = "UNKNOWN"


class EmployeeStatuses:
    ACTIVE = "работает"
    VACATION = "отпуск"
    SICK_LEAVE = "больничный"
    FIRED = "уволен"


class DeliveryMethods:
    AIR = "air"
    SEA = "sea"
    TRUCK = "truck"
    DIRECT_TRUCK = "direct truck"
    RAILWAY = "railway"


class ChinaCodes:
    # Список всех вариантов написания Китая и Гонконга
    CODES = {"cn", "china", "китай", "hong kong", "hk", "гонконг"}


class Roles:
    SPECIALIST_AIR = "специалист по авиаперевозкам"
    SPECIALIST_VED = "специалист по работе с ВЭД документацией"
    SPECIALIST_MULTI = "специалист по мультимодальным перевозкам"
    ASSISTANT = "ассистент"
    MANAGER = "руководитель группы"


class ColumnHeaders:
    # Заголовки из FUL
    FUL_DATE = "Дата"
    FUL_CUTOFF = "Cut-off date"
    FUL_NUMBER = "Номер"
    FUL_STATUS = "Статус"
    FUL_COMMENT = "Комментарий"
    FUL_METHOD = "Способ доставки"
    FUL_BRAND = "Бизнес единица"
    FUL_LOGIST = "Логист"
    FUL_SUPPLIER = "Контрагент"
    FUL_COUNTRY = "Страна"

    # Заголовки из Cloud
    CLOUD_ORDER_ID = "Заказ"
    CLOUD_SUPPLIER = "Поставщик"
    CLOUD_BRAND = "Бренд"
    CLOUD_LOGIST = "Логист"
    CLOUD_STATUS = "статус"
    CLOUD_CONFIRM_DATE = "дата подтверждения"
    CLOUD_CUTOFF = "cut-off"
    CLOUD_UL_DATE = "Дата получения УЛ"
    CLOUD_COUNTRY = "Страна отправления"
    CLOUD_METHOD = "Способ доставки"
    CLOUD_DOCS_DATE = "Документы получены (дата)"
    CLOUD_COMMENT = "Комментарий"

    # Заголовки из Employees
    EMP_NAME = "Наименование"
    EMP_STATE = "Текущее состояние"
    EMP_ROLE = "Должность"
    EMP_CODE = "Код (Таб. №)"


# constants.py

class DuplicateActions:
    """
    Шаблоны действий и сообщений для обработки повторных отправок ФУЛ.
    """

    # Текст, который дописывается в колонку "Комментарий" существующего заказа в Cloud
    UPDATE_COMMENT_TEMPLATE = "Повторная отправка ФУЛа, {date}"

    # Статус действия для листа Duplicates в итоговом Excel
    ACTION_UPDATE_EXISTING = "UPDATE_EXISTING_RECORD"

    # Сообщение для журнала аудита (Audit Log)
    AUDIT_MESSAGE_DUPLICATE = "Order {order_id} already exists in Cloud. Skipping creation of new row."

    # Действие для FUL-листа, если это дубликат (не создавать новую строку!)
    NO_NEW_ROW_CREATED = True

    @staticmethod
    def get_update_comment_text(date_str: str) -> str:
        """Формирует текст комментария с текущей датой."""
        return DuplicateActions.UPDATE_COMMENT_TEMPLATE.format(date=date_str)