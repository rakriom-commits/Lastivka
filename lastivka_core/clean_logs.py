# clean_logs.py — очищення логів від емодзі та нестандартних символів

import os
import re
import shutil

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
LOG_PATTERN = re.compile(r'(logging\.(?:info|warning|error|debug)\s*\(\s*[\"\'])(.*?)([\"\']\s*\))')
CLEAN_REPORT = []

# Функція для очищення повідомлень від не-ASCII

def clean_text(text):
    return ''.join(c for c in text if ord(c) < 128)

# Проходження по всіх .py файлах
for root, dirs, files in os.walk(PROJECT_ROOT):
    for file in files:
        if file.endswith(".py") and file != "clean_logs.py":
            filepath = os.path.join(root, file)
            with open(filepath, "r", encoding="utf-8") as f:
                original = f.read()

            modified = original
            changes = 0

            for match in LOG_PATTERN.finditer(original):
                prefix, message, suffix = match.groups()
                cleaned = clean_text(message)
                if message != cleaned:
                    full_match = prefix + message + suffix
                    replacement = prefix + cleaned + suffix
                    modified = modified.replace(full_match, replacement)
                    changes += 1

            if changes > 0:
                # Створення резервної копії
                shutil.copy(filepath, filepath + ".bak")
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(modified)
                CLEAN_REPORT.append(f"{filepath} — {changes} змін (резерв: {file}.bak)")

# Збереження звіту
if CLEAN_REPORT:
    with open("clean_log_report.txt", "w", encoding="utf-8") as logf:
        logf.write("Очищено емодзі у таких файлах:\n\n")
        logf.write("\n".join(CLEAN_REPORT))
    print("✅ Очищення завершено. Звіт: clean_log_report.txt")
else:
    print("👌 Усі логи чисті. Змін не потрібно.")