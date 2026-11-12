"""Сборка архивов для сдачи тестового задания.

Создаёт:
  dist/agent.zip — навык: SKILL.md, system_prompt.txt, scripts/, references/
  dist/data.zip  — тестовые данные: три файла Excel, эталон, генератор

Запуск: python build.py
"""

import os
import zipfile

from openpyxl import Workbook
from openpyxl.styles import Font

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.join(BASE_DIR, "skill")
DATA_DIR = os.path.join(BASE_DIR, "data")
DIST_DIR = os.path.join(BASE_DIR, "dist")

CLOUD_HEADERS = [
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
]


def create_cloud_template() -> str:
    """Шаблон формы реестра Cloud — кладётся в references/."""
    references = os.path.join(SKILL_DIR, "references")
    os.makedirs(references, exist_ok=True)
    path = os.path.join(references, "cloud_template.xlsx")

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Cloud"
    worksheet.append(CLOUD_HEADERS)
    for cell in worksheet[1]:
        cell.font = Font(bold=True)
    workbook.save(path)
    return path


def zip_skill(path: str) -> None:
    """Архив навыка: раскладка папок сохраняется."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for root, _, files in os.walk(SKILL_DIR):
            for name in files:
                if name == "__pycache__" or name.endswith(".pyc"):
                    continue
                full_path = os.path.join(root, name)
                arcname = os.path.relpath(full_path, SKILL_DIR)
                archive.write(full_path, arcname)


def zip_data(path: str) -> None:
    """Архив тестовых данных: три файла, эталон и генератор."""
    files = ["ful.xlsx", "cloud.xlsx", "employees.xlsx", "expected.xlsx", "generate.py"]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in files:
            full_path = os.path.join(DATA_DIR, name)
            if not os.path.exists(full_path):
                raise FileNotFoundError(
                    f"нет файла {full_path} — сначала запусти python data/generate.py"
                )
            archive.write(full_path, name)


def main() -> None:
    os.makedirs(DIST_DIR, exist_ok=True)
    template = create_cloud_template()
    print(f"шаблон формы реестра: {template}")

    agent_zip = os.path.join(DIST_DIR, "agent.zip")
    zip_skill(agent_zip)
    print(f"архив навыка: {agent_zip}")

    data_zip = os.path.join(DIST_DIR, "data.zip")
    zip_data(data_zip)
    print(f"архив данных: {data_zip}")


if __name__ == "__main__":
    main()
