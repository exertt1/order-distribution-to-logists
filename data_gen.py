import random
from datetime import datetime, timedelta, date
from openpyxl import Workbook


# --- ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ЗАПИСИ ---
def save_dicts_to_excel(data_list: list, headers_map: dict, file_path: str):
    """
    data_list: Список словарей.
    headers_map: Словарь соответствия ключей в словаре -> названия колонок в Excel.
                 Пример: {"order_id": "Заказ", "supplier": "Поставщик"}
    file_path: Куда сохранить файл.
    """
    wb = Workbook()
    ws = wb.active

    # 1. Создаем шапку из значений headers_map
    column_names = list(headers_map.values())
    ws.append(column_names)

    # 2. Заполняем данные
    for row_dict in data_list:
        # Собираем значения в порядке колонок
        row_values = []
        for key in headers_map.keys():
            val = row_dict.get(key, "")
            # Если это дата/время, превращаем в строку или оставляем объектом datetime
            if isinstance(val, (datetime, date)):
                row_values.append(val)
            elif val is None:
                row_values.append("")  # Пустая ячейка вместо None
            else:
                row_values.append(str(val))

        ws.append(row_values)

    wb.save(file_path)
    print(f"✅ Saved {file_path} ({len(data_list)} rows)")


# --- ГЕНЕРАТОРЫ ДАННЫХ ---

def generate_employees_data():
    """Генерирует список сотрудников со всеми ловушками."""
    employees = [
        # Группа AIR
        {"name": "Иванов И.И.", "role": "специалист по авиаперевозкам", "state": "Работает"},
        {"name": "Петров П.П.", "role": "специалист по авиаперевозкам", "state": "Отпуск"},  # Ловушка!
        {"name": "Смирнов С.С.", "role": "специалист по авиаперевозкам", "state": "Работает"},

        # Группа VED
        {"name": "Кузнецов К.К.", "role": "специалист по работе с ВЭД документацией", "state": "Работает"},
        {"name": "Соколов А.А.", "role": "специалист по работе с ВЭД документацией", "state": "Уволен"},  # Ловушка!

        # Группа MULTI
        {"name": "Морозов М.М.", "role": "специалист по мультимодальным перевозкам", "state": "Работает"},
        {"name": "Волков В.В.", "role": "специалист по мультимодальным перевозкам", "state": "Работает"},

        # Исключения (не должны назначаться)
        {"name": "Начальник Н.Н.", "role": "руководитель группы", "state": "Работает"},
        {"name": "Ассистент А.А.", "role": "ассистент", "state": "Работает"},
    ]

    # Маппинг для Excel (ключи из ТЗ)
    headers_emp = {
        "name": "Наименование",
        "role": "Должность",
        "state": "Текущее состояние",
        "code": "Код (Таб. №)"
    }

    # Добавляем коды сотрудникам
    for i, emp in enumerate(employees):
        emp["code"] = f"EMP-{100 + i}"

    return employees, headers_emp


def generate_cloud_history_data(active_logists):
    """Генерирует историю заказов Cloud."""
    cloud_rows = []
    suppliers_pool = ["Nike Inc.", "Zara Ltd", "H&M Group", "Adidas AG"]
    brands_pool = ["Sport", "Fashion", "Casual"]
    countries_pool = ["CN", "TR", "RU", "DE", "US", "HK"]  # HK для проверки ВЭД
    methods_pool = ["air", "sea", "truck", "railway"]

    # Генерируем 30 случайных заказов
    for i in range(30):
        order_id = f"S{1000000 + i}"
        supplier = random.choice(suppliers_pool)
        brand = random.choice(brands_pool)
        logist = random.choice(active_logists)  # Берем только работающих специалистов
        status = random.choice(["в работе", "confirm"])
        country = random.choice(countries_pool)
        method = random.choice(methods_pool)

        # Специально добавляем грязные данные в некоторые поля для теста нормализации
        if i % 5 == 0:
            supplier = f" {supplier.upper()} "  # Лишние пробелы и капс

        cloud_rows.append({
            "order_id": order_id,
            "supplier": supplier,
            "brand": brand,
            "logist": logist,
            "status": status,
            "confirm_date": date.today() if status == "confirm" else None,
            "cut_off": None if status == "в работе" else date.today() + timedelta(days=7),
            "ul_date": date.today(),
            "country": country,
            "method": method,
            "docs_date": date.today(),
            "comment": ""
        })

    headers_cloud = {
        "order_id": "Заказ",
        "supplier": "Поставщик",
        "brand": "Бренд",
        "logist": "Логист",
        "status": "статус",  # Внимание: строчная буква в ТЗ!
        "confirm_date": "дата подтверждения",
        "cut_off": "cut-off",  # Строчная
        "ul_date": "Дата получения УЛ",
        "country": "Страна отправления",
        "method": "Способ доставки",
        "docs_date": "Документы получены (дата)",
        "comment": "Комментарий"
    }

    return cloud_rows, headers_cloud


def generate_ful_data(cloud_ids_set):
    """Генерирует новые FUL со сценариями тестирования."""
    ful_rows = []
    expected_results = []

    today = datetime.now()

    # Сценарий 1: Новый заказ Nike (Air) -> Ожидается Иванов (по истории)
    new_id_1 = "S999901"
    ful_rows.append({
        "date": today,
        "cutoff": today + timedelta(days=7),
        "number": "FUL-TEST-01",
        "status": "в работе",
        "comment": f"Номер: {new_id_1} от 12.11.2024",
        "method": "air",
        "brand": "Sport",
        "logist_input": "",  # Пусто в исходнике
        "supplier": " NIKE INC ",  # Грязное имя!
        "country": "US"
    })
    expected_results.append({"Order_ID": new_id_1, "Expected_Logist": "Иванов И.И.", "Reason": "History match"})

    # Сценарий 2: Дубликат (ID уже есть в Cloud)
    dup_id = list(cloud_ids_set)[0]  # Берем первый попавшийся ID из истории
    ful_rows.append({
        "date": today,
        "cutoff": today,
        "number": "FUL-DUP-01",
        "status": "в работе",
        "comment": f"Номер: {dup_id} от 12.11.2024",
        "method": "sea",
        "brand": "Fashion",
        "logist_input": "",
        "supplier": "Zara Ltd",
        "country": "CN"
    })
    expected_results.append({"Order_ID": dup_id, "Action": "Duplicate Skip", "New_Line_Created": False})

    # Сценарий 3: Новый поставщик Uniqlo (Truck/JP -> Multi) -> Ожидается наименее загруженный (Волков или Морозов)
    fresh_id = "S888888"
    ful_rows.append({
        "date": today,
        "cutoff": today + timedelta(days=5),
        "number": "FUL-FRESH-01",
        "status": "в работе",
        "comment": f"Номер: {fresh_id} от 12.11.2024",
        "method": "truck",
        "brand": "Casual",
        "logist_input": "",
        "supplier": "Uniqlo Japan",
        "country": "JP"
    })
    # Здесь логика зависит от загрузки в Cloud. Для теста зафиксируем одного, например Волкова (если у него меньше заказов)
    expected_results.append({"Order_ID": fresh_id, "Expected_Logist": "Волков В.В.", "Reason": "Least loaded in MULTI"})

    # Сценарий 4: Гонконг (HK) + Sea -> Должен уйти в ВЭД (Кузнецов)
    hk_id = "S777777"
    ful_rows.append({
        "date": today,
        "cutoff": today + timedelta(days=10),
        "number": "FUL-HK-01",
        "status": "в работе",
        "comment": f"Номер: {hk_id} от 12.11.2024",
        "method": "sea",
        "brand": "Luxury",
        "logist_input": "",
        "supplier": "Gucci",
        "country": "HK"  # <--- ЛОВУШКА! Не CN, но должно быть VED
    })
    expected_results.append({"Order_ID": hk_id, "Expected_Logist": "Кузнецов К.К.", "Reason": "HK maps to VED group"})

    # Сценарий 5: Ошибка данных (Нет страны)
    err_id = "S666666"
    ful_rows.append({
        "date": today,
        "cutoff": today,
        "number": "FUL-ERR-01",
        "status": "в работе",
        "comment": f"Номер: {err_id} от 12.11.2024",
        "method": "air",
        "brand": "Test",
        "logist_input": "",
        "supplier": "Error Corp",
        "country": ""  # Пусто!
    })
    expected_results.append({"Order_ID": err_id, "Status": "Attention Required", "Reason": "Missing Country"})

    headers_ful = {
        "date": "Дата",
        "cutoff": "Cut-off date",
        "number": "Номер",
        "status": "Статус",
        "comment": "Комментарий",
        "method": "Способ доставки",
        "brand": "Бизнес единица",
        "logist_input": "Логист",  # Колонка может быть, но обычно пустая
        "supplier": "Контрагент",
        "country": "Страна"
    }

    return ful_rows, headers_ful, expected_results


if __name__ == "__main__":
    print("🚀 Generating Test Data Files...")

    # 1. Сотрудники
    employees_list, emp_headers = generate_employees_data()
    active_logists = [e["name"] for e in employees_list if
                      e["state"].lower() == "работает" and "специалист" in e["role"].lower()]
    save_dicts_to_excel(employees_list, emp_headers, "test_employees.xlsx")

    # 2. Cloud History
    cloud_list, cloud_headers = generate_cloud_history_data(active_logists)
    cloud_ids_set = set([row["order_id"] for row in cloud_list])
    save_dicts_to_excel(cloud_list, cloud_headers, "test_cloud.xlsx")

    # 3. New FULs
    ful_list, ful_headers, expectations = generate_ful_data(cloud_ids_set)
    save_dicts_to_excel(ful_list, ful_headers, "test_ful.xlsx")

    print("\n📝 Expected Results Summary:")
    for exp in expectations:
        print(f"   - {exp}")

    print("\n✅ Done! Now run: python main.py test_ful.xlsx test_cloud.xlsx test_employees.xlsx ./results")