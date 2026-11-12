"""Константы навыка распределения заказов между логистами.

Все заголовки колонок, коды групп, подписи листов и текстовые шаблоны
собраны здесь, чтобы правила не расходились между модулями.
"""


class Groups:
    """Группы логистов."""

    AIR = "AIR"
    VED = "VED"
    MULTI = "MULTI"

    # Человекочитаемые подписи для отчёта
    LABELS = {
        AIR: "авиаперевозки",
        VED: "ВЭД (Китай и Гонконг)",
        MULTI: "мультимодальные перевозки",
    }

    # Ожидаемая должность специалиста группы (для справки и отчёта)
    SPECIALIST_ROLE = {
        AIR: "специалист по авиаперевозкам",
        VED: "специалист по работе с ВЭД документацией",
        MULTI: "специалист по мультимодальным перевозкам",
    }


class OrderStatuses:
    """Статусы заказов в реестре Cloud."""

    ACTIVE = "в работе"
    CONFIRMED = "confirm"


class ChinaCountry:
    """Варианты написания Китая и Гонконга (сравнение после нормализации)."""

    CODES = {
        "cn",
        "china",
        "китай",
        "китай (кнр)",
        "hong kong",
        "hk",
        "гонконг",
        "hongkong",
        "hong-kong",
    }


class DeliveryMethods:
    """Способы доставки из выгрузки 1С."""

    AIR = "air"
    SEA = "sea"
    TRUCK = "truck"
    DIRECT_TRUCK = "direct truck"
    RAILWAY = "railway"


class FUL:
    """Заголовки выгрузки ФУЛ из 1С."""

    DATE = "Дата"
    CUTOFF = "Cut-off date"
    NUMBER = "Номер"
    STATUS = "Статус"
    COMMENT = "Комментарий"
    METHOD = "Способ доставки"
    BRAND = "Бизнес единица"
    LOGIST = "Логист"
    SUPPLIER = "Контрагент"
    COUNTRY = "Страна"

    REQUIRED = (NUMBER, COMMENT, SUPPLIER)


class CLOUD:
    """Заголовки реестра Cloud."""

    ORDER = "Заказ"
    SUPPLIER = "Поставщик"
    BRAND = "Бренд"
    LOGIST = "Логист"
    STATUS = "статус"
    CONFIRM_DATE = "дата подтверждения"
    CUTOFF = "cut-off"
    UL_DATE = "Дата получения УЛ"
    COUNTRY = "Страна отправления"
    METHOD = "Способ доставки"
    DOCS_DATE = "Документы получены (дата)"
    COMMENT = "Комментарий"

    # Порядок колонок реестра — форма, в которой агент отдаёт новые строки
    COLUMNS = (
        ORDER,
        SUPPLIER,
        BRAND,
        LOGIST,
        STATUS,
        CONFIRM_DATE,
        CUTOFF,
        UL_DATE,
        COUNTRY,
        METHOD,
        DOCS_DATE,
        COMMENT,
    )

    REQUIRED = (ORDER, SUPPLIER, LOGIST, STATUS)


class EMPLOYEE:
    """Заголовки выгрузки сотрудников из 1С."""

    NAME = "Наименование"
    STATE = "Текущее состояние"
    ROLE = "Должность"
    CODE = "Код (Таб. №)"

    REQUIRED = (NAME, ROLE, STATE)


class EmployeeStates:
    """Текущее состояние сотрудника: распределять можно только «Работает»."""

    ACTIVE = "работает"


class RoleMarkers:
    """Признаки должности при определении группы.

    Проверяются по порядку: авиа → ВЭД → мультимодальные.
    """

    AIR = ("авиа", "air")
    VED = ("вэд", "вед", "экспорт", "import")
    MULTI = ("мульти", "multimodal", "multimodalnye")
    SPECIALIST = "специалист"


class Sheets:
    """Названия листов результата."""

    NEW = "Новые строки Cloud"
    DUPLICATES = "Повторные отправки"
    GAPS = "Возможные пропуски"
    ATTENTION = "Требует внимания"
    DECISIONS = "Журнал решений"


class Categories:
    """Категория строки в журнале решений."""

    NEW = "новая строка"
    DUP_CLOUD = "повтор (есть в Cloud)"
    DUP_BATCH = "повтор внутри пачки"
    ATTENTION = "требует внимания"


class Reasons:
    """Коды основания выбора логиста."""

    PREFERRED = "предпочтительный по истории"
    LEAST_LOADED = "наименее загруженный"
    SAME_SUPPLIER = "один поставщик — один логист"
    NO_STAFF = "нет доступных логистов"


class Text:
    """Текстовые шаблоны отчёта."""

    UNDEFINED = "не определено"
    DUP_COMMENT = "Повторная отправка ФУЛа, {date}"
    DATE_FORMAT = "%d.%m.%Y"


class AttentionReasons:
    """Причины попадания в «Требует внимания»."""

    NO_ORDER = "номер заказа не найден в комментарии ФУЛ"
    NO_METHOD = "не указан способ доставки"
    NO_COUNTRY = "не указана страна отправления (для не-авиа нужна для выбора группы)"
    NO_STAFF = "в группе {group} нет доступных логистов"
    NO_GROUP = "не удалось определить группу"
    UNKNOWN_COUNTRY = "страна отправления не распознана: {country}"
