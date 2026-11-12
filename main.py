import sys
import os
from typing import List, Set

# Импорты наших модулей
# Предполагается, что файлы лежат в той же папке или в пакете scripts/
from .models import FulItem, CloudOrder, Employee
from .constants import ColumnHeaders as CH, LogisticsGroups, DuplicateActions
from .excel.reader import ExcelReader
from .excel.writer import ExcelWriter
from .parser import determine_group, normalize_supplier_name, select_logist
from .logic_engine import (
    mark_fuls_as_duplicates,
    group_fuls_into_batches,
    build_cloud_index
)


def run_agent(ful_path: str, cloud_path: str, emp_path: str, output_dir: str):
    """
    Главная точка входа агента распределения заказов.
    """
    print("🚀 Starting Logistics Distribution Agent...")

    # 1. Инициализация компонентов
    reader = ExcelReader()
    writer = ExcelWriter(output_path=os.path.join(output_dir, "result_cloud_update.xlsx"))

    try:
        # --- ЭТАП 1: Чтение данных ---
        print("📖 Reading input files...")

        # Читаем FUL (выгрузка из 1С)
        fuls_objects: List[FulItem] = reader.read_fuls(ful_path)
        if not fuls_objects:
            print("⚠️ Warning: No FUL items found in input file.")

        # Читаем Cloud (реестр заказов)
        cloud_history: List[CloudOrder] = reader.read_cloud_history(cloud_path)

        # Читаем Employees (справочник сотрудников)
        employees: List[Employee] = reader.read_employees(emp_path)

        if not employees:
            raise ValueError("Critical Error: No employees found! Cannot assign orders.")

        # --- ЭТАП 2: Подготовка индексов для быстрого поиска ---
        print("🔍 Building lookup indices...")

        # Множество ID заказов из Cloud для проверки дублей O(1)
        cloud_order_ids_set: Set[str] = build_cloud_index(cloud_history)

        # --- ЭТАП 3: Обработка дубликатов ---
        print("♻️ Checking for duplicates...")

        # Модифицирует объекты fuls_objects на месте, ставя флаг is_duplicate
        mark_fuls_as_duplicates(fuls_objects, cloud_order_ids_set)

        # Разделяем потоки: новые заказы vs дубликаты
        new_fuls = [f for f in fuls_objects if not f.is_duplicate]
        duplicate_fuls = [f for f in fuls_objects if f.is_duplicate]

        print(f"   Found {len(duplicate_fuls)} duplicates to skip/update.")
        print(f"   Processing {len(new_fuls)} new orders.")

        # --- ЭТАП 4: Группировка новых заказов ---
        print("📦 Grouping new orders by Supplier and Logistics Group...")

        # Ключевое правило ТЗ: Один поставщик + Одна группа = Один логист
        batches = group_fuls_into_batches(new_fuls)

        # --- ЭТАП 5: Выбор логистов для каждого батча ---
        print("👥 Selecting logists for each batch...")

        processed_results: List[FulItem] = []

        for (supplier_norm, group_type), batch_items in batches.items():
            # Вызываем функцию выбора ОДНОГО логиста на весь список заказов в батче
            best_logist_name, reason = select_logist(
                delivery_method=group_type,
                supplier_name=supplier_norm,
                employees=employees,
                cloud_history=cloud_history
            )

            # Применяем решение ко всем элементам батча
            for item in batch_items:
                item.selected_logist = best_logist_name
                item.decision_reason = reason

                # Если логист не найден (все в отпуске/уволены), помечаем как ошибку
                if not best_logist_name:
                    item.requires_attention = True
                    item.warnings.append(f"No available logist in group {group_type}")

                processed_results.append(item)

        # Добавляем дубликаты в общий список результатов (для листа Duplicates)
        all_output_data = processed_results + duplicate_fuls

        # --- ЭТАП 6: Запись результата ---
        print("💾 Saving results to Excel...")

        writer.save_results(all_output_data)

        print("✅ Process completed successfully!")
        return True

    except Exception as e:
        print(f"❌ CRITICAL ERROR during execution: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 1. Проверяем количество аргументов
    # sys.argv[0] - это имя файла (main.py), остальные - пути
    if len(sys.argv) < 4:
        print("❌ Error: Not enough arguments provided.")
        print("Usage: python main.py <ful.xlsx> <cloud.xlsx> <employees.xlsx> [output_folder]")
        print("Example: python main.py data/ful.xlsx data/cloud.xlsx data/emp.xlsx ./out")
        sys.exit(1)

    # 2. Извлекаем пути по позициям
    ful_file = sys.argv[1]
    cloud_file = sys.argv[2]
    emp_file = sys.argv[3]

    # Выходная папка опциональна, берем 4-й аргумент или дефолт "./results"
    out_dir = sys.argv[4] if len(sys.argv) > 4 else "./results"

    # 3. Валидация существования входных файлов
    missing_files = []
    for path in [ful_file, cloud_file, emp_file]:
        if not os.path.exists(path):
            missing_files.append(path)

    if missing_files:
        print(f"❌ Critical Error: The following input files were not found:")
        for f in missing_files:
            print(f"   - {f}")
        sys.exit(1)

    # 4. Создаем выходную директорию, если её нет
    try:
        os.makedirs(out_dir, exist_ok=True)
    except OSError as e:
        print(f"❌ Error creating output directory '{out_dir}': {e}")
        sys.exit(1)

    # 5. Запуск основного процесса
    print(f"✅ Inputs validated. Running agent...")
    print(f"   FUL:       {ful_file}")
    print(f"   Cloud:     {cloud_file}")
    print(f"   Employees: {emp_file}")
    print(f"   Output:    {out_dir}")

    success = run_agent(ful_file, cloud_file, emp_file, out_dir)

    if success:
        print("\n🎉 Done! Check your result file.")
        sys.exit(0)
    else:
        print("\n💥 Process failed with errors. See logs above.")
        sys.exit(1)