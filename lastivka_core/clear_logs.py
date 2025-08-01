# === LASTIVKA Ω: Швидке очищення логів ===

import subprocess
from pathlib import Path

# Знаходимо log_manager.py
log_manager = Path(__file__).resolve().parent / "log_manager.py"

if log_manager.exists():
    print("🧹 Запускаю очищення логів...")
    subprocess.run(["python", str(log_manager)])
    print("✅ Логи успішно оброблені.")
else:
    print("❌ Не знайдено файл log_manager.py.")