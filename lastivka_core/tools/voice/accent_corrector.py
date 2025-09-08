import re
import json
from pathlib import Path

# Шлях до файлу з акцентами
ACCENTS_PATH = Path(__file__).resolve().parent.parent / "config" / "accents.json"

# Завантаження мапи акцентів
try:
    with open(ACCENTS_PATH, "r", encoding="utf-8") as f:
        accent_map = json.load(f)
except Exception as e:
    print(f"[AccentCorrector] Помилка при завантаженні accents.json: {e}")
    accent_map = {}

def correct_accents(text):
    def replace_match(match):
        word = match.group(0)
        lower = word.lower()
        accented = accent_map.get(lower)
        if not accented:
            return word
        return accented.capitalize() if word[0].isupper() else accented

    for word in accent_map:
        pattern = r'\b{}\b'.format(re.escape(word))
        text = re.sub(pattern, replace_match, text, flags=re.IGNORECASE)

    return text
