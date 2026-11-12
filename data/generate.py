"""Генератор синтетических данных навыка и эталона результата.

Создаёт четыре файла в папке data/:
  data/ful.xlsx        — выгрузка ФУЛ из 1С (20 ФУЛ, все ловушки ТЗ)
  data/cloud.xlsx      — реестр Cloud (36 заказов)
  data/employees.xlsx  — сотрудники из 1С (10 человек)
  data/expected.xlsx   — эталон: что агент обязан сделать по каждому ФУЛ

Эталон заполняется вручную по правилам ТЗ, а не прогоном навыка:
иначе проверка стала бы сама себя подтверждать.

Запуск: python data/generate.py
"""

import os
import re
import zipfile
from datetime import date, datetime, timedelta

from openpyxl import Workbook
from openpyxl.styles import Font

STABLE_TIMESTAMP = (2026, 11, 12, 0, 0, 0)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

CLOUD_BASE_DATE = date(2026, 10, 1)

# --- Сотрудники: все ловушки по доступности ------------------------------

EMPLOYEES = [
    # name, role, state, code
    ("Иванов И.И.", "специалист по авиаперевозкам", "Работает", "EMP-100"),
    ("Смирнов С.С.", "специалист по авиаперевозкам", "Работает", "EMP-102"),
    ("Петров П.П.", "специалист по авиаперевозкам", "Отпуск", "EMP-101"),
    ("Кузнецов К.К.", "специалист по работе с ВЭД документацией", "Отпуск", "EMP-103"),
    ("Соколов А.А.", "специалист по работе с ВЭД документацией", "Уволен", "EMP-104"),
    ("Морозов М.М.", "специалист по мультимодальным перевозкам", "Работает", "EMP-105"),
    ("Волков В.В.", "специалист по мультимодальным перевозкам", "Работает", "EMP-106"),
    ("Зайцев З.З.", "специалист по мультимодальным перевозкам", "В отпуске по уходу за ребёнком", "EMP-107"),
    ("Начальник Н.Н.", "руководитель группы", "Работает", "EMP-108"),
    ("Ассистент А.А.", "ассистент", "Работает", "EMP-109"),
]

# --- Реестр Cloud: история поставщиков и текущая загрузка ----------------
# Загрузка «в работе»: Иванов 5, Смирнов 2, Петров 3, Кузнецов 2,
# Соколов 0, Морозов 1, Волков 4, Зайцев 1.

CLOUD_ROWS = [
    # order_id, supplier, logist, status, country, method
    ("S0000001", "Nike Inc.", "Петров П.П.", "в работе", "US", "air"),
    ("S0000002", "Nike Inc.", "Петров П.П.", "в работе", "US", "air"),
    ("S0000003", "Nike Inc.", "Петров П.П.", "confirm", "US", "air"),
    ("S0000004", "Nike Inc.", "Петров П.П.", "confirm", "US", "air"),
    ("S0000005", "Adidas AG", "Иванов И.И.", "в работе", "DE", "air"),
    ("S0000006", "Adidas AG", "Иванов И.И.", "в работе", "DE", "air"),
    ("S0000007", "Adidas AG", "Иванов И.И.", "в работе", "DE", "air"),
    ("S0000008", "Adidas AG", "Смирнов С.С.", "confirm", "DE", "air"),
    ("S0000009", "Lenta Fashion", "Иванов И.И.", "в работе", "RU", "air"),
    ("S0000010", "Lenta Fashion", "Смирнов С.С.", "в работе", "RU", "air"),
    ("S0000011", "Lenta Fashion", "Петров П.П.", "в работе", "RU", "air"),
    ("S0000012", "Zara Ltd", "Смирнов С.С.", "в работе", "ES", "air"),
    ("S0000013", "Zara Ltd", "Смирнов С.С.", "confirm", "ES", "air"),
    ("S0000014", "Zara Ltd", "Иванов И.И.", "в работе", "ES", "air"),
    ("S0000015", "H&M Group", "Кузнецов К.К.", "в работе", "CN", "sea"),
    ("S0000016", "H&M Group", "Кузнецов К.К.", "confirm", "CN", "sea"),
    ("S0000017", "H&M Group", "Соколов А.А.", "confirm", "CN", "sea"),
    ("S0000018", "Gucci", "Кузнецов К.К.", "в работе", "HK", "sea"),
    ("S0000019", "Gucci", "Кузнецов К.К.", "confirm", "HK", "sea"),
    ("S0000020", "Gucci", "Соколов А.А.", "confirm", "HK", "sea"),
    ("S0000021", "Reebok", "Кузнецов К.К.", "confirm", "CN", "railway"),
    ("S0000022", "Ozon Textile", "Зайцев З.З.", "в работе", "CN", "railway"),
    ("S0000023", "Uniqlo Japan", "Волков В.В.", "в работе", "JP", "sea"),
    ("S0000024", "Uniqlo Japan", "Волков В.В.", "в работе", "JP", "sea"),
    ("S0000025", "Uniqlo Japan", "Волков В.В.", "confirm", "JP", "sea"),
    ("S0000026", "Uniqlo Japan", "Морозов М.М.", "confirm", "JP", "sea"),
    ("S0000027", "Uniqlo Japan", "Морозов М.М.", "confirm", "JP", "sea"),
    ("S0000028", "Decathlon", "Морозов М.М.", "в работе", "FR", "truck"),
    ("S0000029", "Decathlon", "Морозов М.М.", "confirm", "FR", "truck"),
    ("S0000030", "Decathlon", "Смирнов С.С.", "confirm", "FR", "truck"),
    ("S0000031", "Decathlon", "Волков В.В.", "в работе", "FR", "truck"),
    ("S0000032", "Mango", "Волков В.В.", "в работе", "ES", "sea"),
    ("S0000033", "Mango", "Морозов М.М.", "confirm", "ES", "sea"),
    ("S0000034", "Sela", "Волков В.В.", "confirm", "RU", "truck"),
    ("S0000035", "Sela", "Смирнов С.С.", "confirm", "RU", "truck"),
    ("S0000036", "Bosco", "Волков В.В.", "confirm", "RU", "railway"),
]

# --- Выгрузка ФУЛ: 20 строк, все ловушки ТЗ ------------------------------
# (number, дата, способ, страна, поставщик, бренд, номер заказа или None)

FUL_ROWS = [
    # 1. Новый заказ Nike (air). Предпочтительный логист Петров в отпуске,
    #    поэтому ожидается наименее загруженный авиа-логист — Смирнов.
    ("FUL-2026-001", datetime(2026, 11, 11, 9, 15), "air", "US", "Nike Inc.", "Sport", "S0001001"),
    # 2. Поставщик с историей и доступным логистом → Иванов (3 заказа Adidas).
    ("FUL-2026-002", datetime(2026, 11, 11, 9, 40), "air", "DE", "Adidas AG", "Sport", "S0001002"),
    # 3-4. Один поставщик в пачке → второй ФУЛ получает того же логиста.
    ("FUL-2026-003", datetime(2026, 11, 11, 10, 5), "air", "ES", "Zara Ltd", "Fashion", "S0001003"),
    ("FUL-2026-004", datetime(2026, 11, 11, 10, 20), "air", "ES", "Zara Ltd", "Fashion", "S0001004"),
    # 5. Поставщик с историей в мультимодальных → Волков (3 против 2).
    ("FUL-2026-005", datetime(2026, 11, 11, 11, 0), "sea", "JP", "Uniqlo Japan", "Casual", "S0001005"),
    # 6. Новый поставщик → наименее загруженный в группе — Морозов.
    ("FUL-2026-006", datetime(2026, 11, 11, 11, 30), "truck", "DE", "Puma SE", "Sport", "S0001006"),
    # 7-8. Группа ВЭД: все специалисты недоступны → логист пустой.
    ("FUL-2026-007", datetime(2026, 11, 11, 12, 0), "sea", "HK", "Gucci", "Luxury", "S0001007"),
    ("FUL-2026-008", datetime(2026, 11, 11, 12, 20), "railway", "CN", "H&M Group", "Fashion", "S0001008"),
    # 9. Ничья по истории (Иванов и Смирнов по 1 заказу) → первый в справочнике.
    ("FUL-2026-009", datetime(2026, 11, 11, 13, 0), "air", "RU", "Lenta Fashion", "Casual", "S0001009"),
    # 10. Нет номера заказа в комментарии.
    ("FUL-2026-010", datetime(2026, 11, 11, 13, 30), "air", "US", "Nike Inc.", "Sport", None),
    # 11. Нет способа доставки.
    ("FUL-2026-011", datetime(2026, 11, 11, 14, 0), "", "DE", "Adidas AG", "Sport", "S0001011"),
    # 12. Нет страны при не-авиа способе доставки.
    ("FUL-2026-012", datetime(2026, 11, 11, 14, 20), "sea", "", "Uniqlo Japan", "Casual", "S0001012"),
    # 13. Повторная отправка: заказ уже есть в Cloud.
    ("FUL-2026-013", datetime(2026, 11, 11, 15, 0), "sea", "CN", "H&M Group", "Fashion", "S0000016"),
    # 14-15. Повтор внутри одной пачки (один номер заказа дважды).
    ("FUL-2026-014", datetime(2026, 11, 11, 15, 30), "air", "DE", "Adidas AG", "Sport", "S0001014"),
    ("FUL-2026-015", datetime(2026, 11, 11, 15, 45), "air", "DE", "Adidas AG", "Sport", "S0001014"),
    # 16. ФУЛ раньше последней записи Cloud, заказа в Cloud нет → возможный пропуск.
    ("FUL-2026-016", datetime(2026, 10, 20, 10, 0), "railway", "RU", "Bosco", "Fashion", "S0001016"),
    # 17. Тот же поставщик, что в п.1, но записан иначе → одна пачка, один логист.
    ("FUL-2026-017", datetime(2026, 11, 11, 16, 0), "air", "US", "  NIKE   INC. ", "Sport", "S0001017"),
    # 18-20. Мультимодальные: история, история и ничья.
    ("FUL-2026-018", datetime(2026, 11, 11, 16, 30), "direct truck", "FR", "Decathlon", "Sport", "S0001018"),
    ("FUL-2026-019", datetime(2026, 11, 11, 17, 0), "truck", "RU", "Sela", "Casual", "S0001019"),
    ("FUL-2026-020", datetime(2026, 11, 11, 17, 30), "sea", "ES", "Mango", "Fashion", "S0001020"),
]

# --- Эталон ---------------------------------------------------------------
# ФУЛ, заказ, группа, логист, категория, комментарий для Cloud, пропуск

AIR = "авиаперевозки"
VED = "ВЭД (Китай и Гонконг)"
MULTI = "мультимодальные перевозки"
UNDEF = "не определено"

CAT_NEW = "новая строка"
CAT_DUP_CLOUD = "повтор (есть в Cloud)"
CAT_DUP_BATCH = "повтор внутри пачки"
CAT_ATTENTION = "требует внимания"

EXPECTED = [
    ("FUL-2026-001", "S0001001", AIR, "Смирнов С.С.", CAT_NEW, "—", "нет"),
    ("FUL-2026-002", "S0001002", AIR, "Иванов И.И.", CAT_NEW, "—", "нет"),
    ("FUL-2026-003", "S0001003", AIR, "Смирнов С.С.", CAT_NEW, "—", "нет"),
    ("FUL-2026-004", "S0001004", AIR, "Смирнов С.С.", CAT_NEW, "—", "нет"),
    ("FUL-2026-005", "S0001005", MULTI, "Волков В.В.", CAT_NEW, "—", "нет"),
    ("FUL-2026-006", "S0001006", MULTI, "Морозов М.М.", CAT_NEW, "—", "нет"),
    ("FUL-2026-007", "S0001007", VED, UNDEF, CAT_ATTENTION, "—", "нет"),
    ("FUL-2026-008", "S0001008", VED, UNDEF, CAT_ATTENTION, "—", "нет"),
    ("FUL-2026-009", "S0001009", AIR, "Иванов И.И.", CAT_NEW, "—", "нет"),
    ("FUL-2026-010", UNDEF, AIR, UNDEF, CAT_ATTENTION, "—", "нет"),
    ("FUL-2026-011", "S0001011", UNDEF, UNDEF, CAT_ATTENTION, "—", "нет"),
    ("FUL-2026-012", "S0001012", UNDEF, UNDEF, CAT_ATTENTION, "—", "нет"),
    ("FUL-2026-013", "S0000016", VED, UNDEF, CAT_DUP_CLOUD, "Повторная отправка ФУЛа, 11.11.2026", "нет"),
    ("FUL-2026-014", "S0001014", AIR, "Иванов И.И.", CAT_NEW, "—", "нет"),
    ("FUL-2026-015", "S0001014", AIR, UNDEF, CAT_DUP_BATCH, "Повторная отправка ФУЛа, 11.11.2026", "нет"),
    ("FUL-2026-016", "S0001016", MULTI, "Волков В.В.", CAT_NEW, "—", "да"),
    ("FUL-2026-017", "S0001017", AIR, "Смирнов С.С.", CAT_NEW, "—", "нет"),
    ("FUL-2026-018", "S0001018", MULTI, "Морозов М.М.", CAT_NEW, "—", "нет"),
    ("FUL-2026-019", "S0001019", MULTI, "Волков В.В.", CAT_NEW, "—", "нет"),
    ("FUL-2026-020", "S0001020", MULTI, "Морозов М.М.", CAT_NEW, "—", "нет"),
]

EXPECTED_HEADERS = [
    "ФУЛ",
    "Заказ",
    "Группа",
    "Логист",
    "Категория",
    "Комментарий для Cloud",
    "Возможный пропуск",
]

EXPECTED_SUMMARY = {
    "новых строк Cloud": 13,
    "повторных отправок": 2,
    "возможных пропусков": 1,
    "требует внимания": 5,
}


def fix_properties(workbook) -> None:
    """Фиксирует служебные свойства книги."""
    workbook.properties.created = datetime(2026, 11, 12)
    workbook.properties.modified = datetime(2026, 11, 12)
    workbook.properties.creator = "order-distribution-to-logists"
    workbook.properties.lastModifiedBy = "order-distribution-to-logists"


def stabilize_zip(path: str) -> None:
    """Перезаписывает xlsx/zip с фиксированными отметками времени внутри.

    Без этого каждый пересбор меняет байты файла из-за текущего времени
    в zip-контейнере, и в git появляются лишние изменения.
    """
    if not path.lower().endswith((".xlsx", ".zip")):
        return

    with zipfile.ZipFile(path) as source:
        items = [(info.filename, source.read(info.filename)) for info in source.infolist()]

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as target:
        for name, data in items:
            if name == "docProps/core.xml":
                # openpyxl проставляет дату сохранения в момент save — фиксируем её
                data = re.sub(
                    rb"<dcterms:modified[^>]*>[^<]*<",
                    b'<dcterms:modified xsi:type="dcterms:W3CDTF">2026-11-12T00:00:00Z<',
                    data,
                )
            info = zipfile.ZipInfo(name, date_time=STABLE_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            target.writestr(info, data)


def _write(path: str, headers, rows) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Данные"
    worksheet.append(list(headers))
    for cell in worksheet[1]:
        cell.font = Font(bold=True)
    for row in rows:
        worksheet.append(list(row))
    fix_properties(workbook)
    workbook.save(path)
    stabilize_zip(path)
    print(f"создан {path}")


def build_cloud_rows():
    rows = []
    for index, (order_id, supplier, logist, status, country, method) in enumerate(CLOUD_ROWS):
        ul_date = CLOUD_BASE_DATE + timedelta(days=index)
        confirm_date = ul_date + timedelta(days=2) if status == "confirm" else None
        cutoff = ul_date + timedelta(days=10)
        rows.append(
            [
                order_id,
                supplier,
                "Sport",
                logist,
                status,
                confirm_date,
                cutoff,
                ul_date,
                country,
                method,
                confirm_date,
                "",
            ]
        )
    return rows


def build_ful_rows():
    rows = []
    for number, ful_date, method, country, supplier, brand, order_id in FUL_ROWS:
        if order_id:
            comment = f"Номер: {order_id} от {ful_date.strftime('%d.%m.%Y')}"
        else:
            comment = "Номер заказа уточняется у поставщика"
        rows.append(
            [
                ful_date,
                ful_date + timedelta(days=7),
                number,
                "в работе",
                comment,
                method,
                brand,
                "",
                supplier,
                country,
            ]
        )
    return rows


def main() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)

    _write(
        os.path.join(DATA_DIR, "employees.xlsx"),
        ["Наименование", "Должность", "Текущее состояние", "Код (Таб. №)"],
        EMPLOYEES,
    )
    _write(
        os.path.join(DATA_DIR, "cloud.xlsx"),
        [
            "Заказ",
            "Поставщик",
            "Бренд",
            "Логист",
            "статус",
            "дата подтверждения",
            "cut-off",
            "Дата получения УЛ",
            "Страна отправления",
            "Способ доставки",
            "Документы получены (дата)",
            "Комментарий",
        ],
        build_cloud_rows(),
    )
    _write(
        os.path.join(DATA_DIR, "ful.xlsx"),
        [
            "Дата",
            "Cut-off date",
            "Номер",
            "Статус",
            "Комментарий",
            "Способ доставки",
            "Бизнес единица",
            "Логист",
            "Контрагент",
            "Страна",
        ],
        build_ful_rows(),
    )
    _write(os.path.join(DATA_DIR, "expected.xlsx"), EXPECTED_HEADERS, EXPECTED)

    print("эталон: " + ", ".join(f"{k} — {v}" for k, v in EXPECTED_SUMMARY.items()))


if __name__ == "__main__":
    main()
