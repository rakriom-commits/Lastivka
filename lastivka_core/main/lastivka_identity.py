import json
from pathlib import Path

# ░░░ ШЛЯХИ ░░░
BASE_DIR = Path(__file__).resolve().parent.parent
IDENTITY_PATH = BASE_DIR / "config" / "core_identity.json"
MORAL_PATH = BASE_DIR / "config" / "moral_compass.json"

# ░░░ КЕШ ░░░
_identity_cache = None
_moral_cache = None

# ░░░ ЗАВАНТАЖЕННЯ ОСНОВНОЇ ІДЕНТИЧНОСТІ ░░░
def load_identity():
    global _identity_cache
    if _identity_cache is None:
        try:
            with open(IDENTITY_PATH, "r", encoding="utf-8") as f:
                _identity_cache = json.load(f)
        except Exception as e:
            print(f"⚠️ Помилка завантаження core_identity: {e}")
            _identity_cache = {}
    return _identity_cache

def print_identity(identity):
    print("\n🧬 Ідентичність Ластівки:")
    for key, value in identity.items():
        print(f"\n🔹 {key.upper()}:")
        if isinstance(value, list):
            for item in value:
                print(f"  • {item}")
        elif isinstance(value, dict):
            for subkey, subval in value.items():
                print(f"  ◦ {subkey}: {subval}")
        else:
            print(f"  {value}")

# ░░░ ВИВІД CREDO ░░░
def print_credo(identity):
    credo = identity.get("credo", "")
    if credo:
        print("\n🕊️ CREDO:")
        for line in credo.split(". "):
            if line.strip():
                print(f"  • {line.strip().rstrip('.')}.")  # залишаємо крапку в кінці

# ░░░ ЗАВАНТАЖЕННЯ КОМПАСУ ░░░
def load_moral_compass():
    global _moral_cache
    if _moral_cache is None:
        try:
            with open(MORAL_PATH, "r", encoding="utf-8") as f:
                _moral_cache = json.load(f)
        except Exception as e:
            print(f"⚠️ Помилка завантаження moral_compass: {e}")
            _moral_cache = {}
    return _moral_cache

def print_moral_compass(compass):
    print(f"\n🧭 Моральний компас: {compass.get('moral_compass_name', 'Без назви')}")

    print("\n📜 Основні правила:")
    for rule in compass.get("core_rules", []):
        print(f"  • {rule}")

    print("\n🟡 Потребує згоди:")
    for item in compass.get("consent_required", []):
        print(f"  ◦ {item}")

    print("\n⛔ Заборонено:")
    for item in compass.get("forbidden", []):
        print(f"  ◦ {item}")

    print("\n🚨 Протокол порушення:")
    print(f"  {compass.get('violation_protocol', {}).get('on_boundary_crossed', 'Немає протоколу')}")

# ░░░ ПЕРЕВІРКА ПОРУШЕННЯ ░░░
def violates_moral_compass(user_text, compass, consent_given=False):
    violations = explain_violation(user_text, compass, consent_given)
    return violations if violations else None

# ░░░ ФОРМУЛЮВАННЯ ПОРУШЕННЯ ░░░
def explain_violation(user_text, compass, consent_given=False):
    user_text = user_text.lower()
    reasons = []

    for sensitive in compass.get("consent_required", []):
        if sensitive.lower() in user_text and not consent_given:
            reasons.append(f"⚠️ Потрібна згода для: «{sensitive}»")

    for forbidden in compass.get("forbidden", []):
        if forbidden.lower() in user_text:
            reasons.append(f"⛔ Заборонено: «{forbidden}»")

    return reasons
