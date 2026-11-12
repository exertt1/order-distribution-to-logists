import random
from datetime import datetime, timedelta, date


def generate_employees():
    """Генерирует список сотрудников (8-12 человек)"""
    employees = []
    # 1. Авиа специалисты (2 человека)
    employees.append({"ФИО": "Иванов И.И.", "Должность": "специалист по авиаперевозкам", "Статус": "Работает"})
    employees.append(
        {"ФИО": "Петров П.П.", "Должность": "специалист по авиаперевозкам", "Статус": "Отпуск"})  # Ловушка!

    # 2. ВЭД специалисты (2 человека)
    employees.append(
        {"ФИО": "Сидоров С.С.", "Должность": "специалист по работе с ВЭД документацией", "Статус": "Работает"})
    employees.append({"ФИО": "Кузнецов К.К.", "Должность": "специалист по работе с ВЭД документацией",
                      "Статус": "Уволен"})  # Ловушка!

    # 3. Мультимодальные (2 человека)
    employees.append(
        {"ФИО": "Морозов М.М.", "Должность": "специалист по мультимодальным перевозкам", "Статус": "Работает"})
    employees.append(
        {"ФИО": "Волков В.В.", "Должность": "специалист по мультимодальным перевозкам", "Статус": "Работает"})

    # 4. Нераспределители (2 человека)
    employees.append({"ФИО": "Ассистент А.А.", "Должность": "ассистент", "Статус": "Работает"})
    employees.append({"ФИО": "Руководитель Р.Р.", "Должность": "руководитель группы", "Статус": "Работает"})

    return employees


def generate_suppliers_and_brands():
    """Генерирует справочники поставщиков и брендов"""
    suppliers = ["Nike Inc.", "Zara Ltd", "H&M Group", "Adidas AG"]
    brands = ["Sport", "Fashion", "Casual"]
    countries = ["CN", "TR", "RU", "DE", None]  # None для проверки пустой страны
    methods = ["air", "sea", "truck", "railway", "direct truck", None]
    return suppliers, brands, countries, methods

def generate_cloud_history(employees):

    cloud_rows = []
    logists_active = [e["ФИО"] for e in employees if e["Статус"].lower() == "работает" and "специалист" in e["Должность"].lower()]
    suppliers, brands, countries, methods = generate_suppliers_and_brands()

    for i in range(30):
        order_id = f"S{1000000 + i}"
        supplier = random.choice(suppliers)
        brand = random.choice(brands)
        logist = random.choice(logists_active)
        status = random.choice(["в работе", "confirm"])

        cloud_rows.append({
            "Заказ": order_id,
            "Поставщик": supplier,
            "Бренд": brand,
            "Логист": logist,
            "Статус": status,
            "Дата подтверждения": date.today() if status == "confirm" else None,
            "Cut-off": None if status is "в работе" else date.today() + timedelta(days=7),
            "Дата получения УЛ": date.today(),
            "Страна отправления": random.choice(countries),
            "Способ доставки": random.choice(methods),
            "Дата получения документов": date.today(),
            "Комментарий": ""
        })

    return cloud_rows

def generate_new_fuls(cloud_history):
    ful_rows = []
    expected_results = []  # Сюда будем писать, ЧТО ОЖИДАЕМ получить на выходе

    existing_order_ids = set([row["Заказ"] for row in cloud_history])

    new_order_id = "S999999"
    ful_rows.append({
        "Дата": datetime.now(),
        "Cut-off date": datetime.now() + timedelta(days=7),
        "Номер": "FUL-NEW-01",
        "Статус": "Новый",
        "Комментарий": f"Номер: {new_order_id} от 12.11.2024",
        "Способ доставки": "air",
        "Бизнес единица": "Sport",
        "Логист": "",
        "Контрагент": "Nike Inc.",
        "Страна": "US"
    })

    # Эталон: Группа AIR. Доступен только Иванов (Петров в отпуске). Выбор: Иванов.
    expected_results.append(
        {"Order_ID": new_order_id, "Expected_Logist": "Иванов И.И.", "Reason": "Only available in AIR group"})

    # Кейс 2: Повторная отправка (Заказ уже есть в Cloud)
    duplicate_order_id = existing_order_ids[0]  # Берем первый из истории
    ful_rows.append({
        "Дата": datetime.now(),
        "Cut-off date": datetime.now(),
        "Номер": "FUL-DUP-01",
        "Статус": "Новый",
        "Комментарий": f"Номер: {duplicate_order_id} от 12.11.2024",
        "Способ доставки": "sea",
        "Бизнес единица": "Fashion",
        "Логист": "",
        "Контрагент": "Zara Ltd",
        "Страна": "CN"
    })
    # Эталон: Не создавать новую строку. Обновить комментарий в Cloud.
    expected_results.append({"Order_ID": duplicate_order_id, "Action": "Update Comment", "New_Line_Created": False})

    # Кейс 3: Новый поставщик (Нет истории работы)
    fresh_supplier = "Uniqlo Japan"
    fresh_order_id = "S888888"
    ful_rows.append({
        "Дата": datetime.now(),
        "Cut-off date": datetime.now(),
        "Номер": "FUL-FRESH-01",
        "Статус": "Новый",
        "Комментарий": f"Номер: {fresh_order_id} от 12.11.2024",
        "Способ доставки": "truck",  # Не air, не Китай -> Мульти
        "Бизнес единица": "Casual",
        "Логист": "",
        "Контрагент": fresh_supplier,
        "Страна": "JP"
    })
    # Эталон: Группа MULTI. Морозов и Волков работают. Кто меньше загружен? Допустим, у обоих 0 активных. Выбираем первого (или случайного, но детерминированного).
    # Для простоты эталона зафиксируем: Морозов (если он первый в списке доступных).
    expected_results.append(
        {"Order_ID": fresh_order_id, "Expected_Logist": "Морозов М.М.", "Reason": "Least loaded in MULTI"})

    # ... Добавь еще кейсы: Пустая страна, Пустой способ доставки, Уволенный предпочтительный логист.

    return ful_rows, expected_results