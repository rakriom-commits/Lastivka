import re
import json
from pathlib import Path

# РЁР»СЏС… РґРѕ С„Р°Р№Р»Сѓ Р°РєС†РµРЅС‚С–РІ
ACCENTS_PATH = Path(__file__).resolve().parent.parent / "config" / "accents.json"

# Р—Р°РІР°РЅС‚Р°Р¶РµРЅРЅСЏ Р°РєС†РµРЅС‚С–РІ
try:
    with open(ACCENTS_PATH, "r", encoding="utf-8") as f:
        accent_map = json.load(f)
except Exception as e:
    print(f"вљ пёЏ РџРѕРјРёР»РєР° Р·Р°РІР°РЅС‚Р°Р¶РµРЅРЅСЏ accents.json: {e}")
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

