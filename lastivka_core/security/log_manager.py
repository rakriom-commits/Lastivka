# === LASTIVKA ОЧІКУВАННЯ: Менеджер логів ===

import os
import json
from pathlib import Path
from datetime import datetime

# Каталог логів
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
ARCHIVE_DIR = LOG_DIR / "archive"

# Створюємо папки, якщо їх немає
ARCHIVE_DIR.parent.mkdir(parents=True, exist_ok=True)
ARCHIVE_DIR.mkdir(exist_ok=True)

# Ліміти на кількість записів у логах
LOG_LIMITS = {
    "language_log.json": 100,
    "pronunciation_errors.json": 100,
    "pronunciation_log.json": 100,
    "rating_log.json": 200,
    "memory_store.json": 500
}

def clean_json_log(file_path: Path, max_entries: int):
    if not file_path.exists():
        print(f"Файл {file_path.name} відсутній.")
        return

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list) and len(data) > max_entries:
            archived = data[:-max_entries]
            data = data[-max_entries:]

            archive_name = f"{file_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak.json"
            archive_path = ARCHIVE_DIR / archive_name

            with open(archive_path, "w", encoding="utf-8") as archive:
                json.dump(archived, archive, ensure_ascii=False, indent=2)

            print(f"Архівовано {len(archived)} записів у {archive_path.name}")

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Очищено {file_path.name} (залишилось записів: {len(data)})")

    except json.JSONDecodeError:
        print(f"Помилка: файл {file_path.name} містить некоректний JSON.")

def delete_or_archive_file(filename: str, delete: bool = True):
    file_path = LOG_DIR / filename
    if not file_path.exists():
        return

    # Не видаляємо логи, пов'язані з Аурелією
    if "aurelia" in filename.lower():
        print(f"Відмова від видалення файлу {filename} — пов'язаний з Аурелією.")
        return

    if delete:
        file_path.unlink()
        print(f"Видалено файл {filename}")
    else:
        archive_path = ARCHIVE_DIR / (filename + ".bak")
        file_path.rename(archive_path)
        print(f"Файл {filename} переміщено до архіву")

def process_logs():
    for log, limit in LOG_LIMITS.items():
        clean_json_log(LOG_DIR / log, limit)

if __name__ == "__main__":
    process_logs()
