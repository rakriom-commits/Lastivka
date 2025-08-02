import json
import re
import os

# РЁР»СЏС…Рё РґРѕ СЃР»РѕРІРЅРёРєС–РІ
STRESS_DICT_PATH = os.path.join("config", "stress_dict.json")
UNKNOWN_LOG_PATH = os.path.join("config", "unknown_stress_words.log")

# Р—Р°РІР°РЅС‚Р°Р¶РµРЅРЅСЏ СЃР»РѕРІРЅРёРєР° РЅР°РіРѕР»РѕСЃС–РІ
def load_stress_dict():
    try:
        with open(STRESS_DICT_PATH, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

# Р—Р°РІР°РЅС‚Р°Р¶РµРЅРЅСЏ РІР¶Рµ Р·Р°Р»РѕРіРѕРІР°РЅРёС… СЃР»С–РІ
def load_logged_unknowns():
    if not os.path.exists(UNKNOWN_LOG_PATH):
        return set()
    with open(UNKNOWN_LOG_PATH, "r", encoding="utf-8") as file:
        return set(word.strip().lower() for word in file if word.strip())

# Р›РѕРіСѓРІР°РЅРЅСЏ РЅРѕРІРёС… РЅРµРІС–РґРѕРјРёС… СЃР»С–РІ
def log_unknown_word(word):
    logged = load_logged_unknowns()
    word_lower = word.lower()
    if word_lower not in logged:
        with open(UNKNOWN_LOG_PATH, "a", encoding="utf-8") as file:
            file.write(word_lower + "\n")

# РћСЃРЅРѕРІРЅР° С„СѓРЅРєС†С–СЏ
def apply_stress_marks(text):
    stress_dict = load_stress_dict()
    logged = load_logged_unknowns()

    def replace_match(match):
        word = match.group(0)
        lower_word = word.lower()
        if lower_word in stress_dict:
            stressed = stress_dict[lower_word]
            return stressed.capitalize() if word[0].isupper() else stressed
        else:
            if lower_word not in logged:
                log_unknown_word(lower_word)
            return word  # Р·Р°Р»РёС€Р°С”РјРѕ СЃР»РѕРІРѕ Р±РµР· Р·РјС–РЅ

    # Р—РЅР°С…РѕРґРёРјРѕ РІСЃС– СЃР»РѕРІР°
    pattern = r'\b\w+\b'
    return re.sub(pattern, replace_match, text)

