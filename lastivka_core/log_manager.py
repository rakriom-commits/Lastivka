# === LASTIVKA Ω: Менеджер логів ===

import os
import json
from pathlib import Path
from datetime import datetime

# ░░░ ОСНОВНІ ШЛЯХИ ░░░
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
ARCHIVE_DIR = LOG_DIR / "archive"

# 🛠️ Гарантоване створення структури logs/archive/
ARCHIVE_DIR.parent.mkdir(parents=True, exist_ok=True)
ARCHIVE_DIR.mkdir(exist_ok=True)

# ░░░ ІНДИВІДУАЛЬНІ ЛІМІТИ ░░░
LOG_LIMITS = {
    "language_log.json": 100,
    "pronunciation_errors.json": 100,
    "pronunciation_log.json": 100,
    "rating_log.json": 200,
    "memory_store.json": 500
}

# ░░░ ФУНКЦІЇ ░░░

def clean_json_log(file_path: Path, max_entries: int):
    if not file_path.exists():
        print(f"❌ Файл {file_path.name} не знайдено.")
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

            print(f"🗃️ Архівовано {len(archived)} записів у {archive_path.name}")

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✅ Очищено {file_path.name} (залишено {len(data)} записів)")

    except json.JSONDecodeError:
        print(f"⚠️ Файл {file_path.name} пошкоджено або не є JSON.")


def delete_or_archive_file(filename: str, delete: bool = True):
    file_path = LOG_DIR / filename
    if not file_path.exists():
        return

    # 🛡️ Заборона на обробку спадкових або зовнішніх логів
    if "aurelia" in filename.lower():
        print(f"⛔ Заборонено обробляти файл {filename} — заблоковано політикою суверенності.")
        return

    if delete:
        file_path.unlink()
        print(f"🔥 Видалено {filename}")
    else:
        archive_path = ARCHIVE_DIR / (filename + ".bak")
        file_path.rename(archive_path)
        print(f"📦 Переміщено {filename} в архів")


# ░░░ ГОЛОВНА ФУНКЦІЯ ░░░
def process_logs():
    for log, limit in LOG_LIMITS.items():
        clean_json_log(LOG_DIR / log, limit)


if __name__ == "__main__":
    process_logs()
