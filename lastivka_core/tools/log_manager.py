import os
import shutil
from pathlib import Path
from datetime import datetime

# 📂 Шляхи
BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / "logs"
ARCHIVE_DIR = LOGS_DIR / "archive"
ARCHIVE_DIR.mkdir(exist_ok=True)

# 📁 Ключові файли, які залишаються активними
ACTIVE_LOGS = {"pronunciation_errors.json"}

# 📅 Порог дати або інші умови можна додати тут


def archive_logs():
    """Перемістити всі логи, крім активних, до archive."""
    moved = []
    for file in LOGS_DIR.iterdir():
        if file.is_file() and file.name not in ACTIVE_LOGS:
            shutil.move(str(file), ARCHIVE_DIR / file.name)
            moved.append(file.name)
    return moved


def list_archived():
    return [f.name for f in ARCHIVE_DIR.glob("*.json")]


def list_active():
    return [f.name for f in LOGS_DIR.glob("*.json") if f.name in ACTIVE_LOGS]


if __name__ == "__main__":
    print("\n📦 Архівація логів...")
    moved_logs = archive_logs()
    if moved_logs:
        print("✅ Переміщено до archive:", ", ".join(moved_logs))
    else:
        print("📂 Немає логів для архівації.")

    print("\n📁 Активні логи:", list_active())
    print("🗃️  Архівовані логи:", list_archived())
