import json
from pathlib import Path

# в–‘в–‘в–‘ РЁР›РЇРҐР в–‘в–‘в–‘
BASE_DIR = Path(__file__).resolve().parent.parent
IDENTITY_PATH = BASE_DIR / "config" / "core_identity.json"
MORAL_PATH = BASE_DIR / "config" / "moral_compass.json"

# в–‘в–‘в–‘ РљР•РЁ в–‘в–‘в–‘
_identity_cache = None
_moral_cache = None

# в–‘в–‘в–‘ Р—РђР’РђРќРўРђР–Р•РќРќРЇ РћРЎРќРћР’РќРћР‡ Р†Р”Р•РќРўРР§РќРћРЎРўР† в–‘в–‘в–‘
def load_identity():
    global _identity_cache
    if _identity_cache is None:
        try:
            with open(IDENTITY_PATH, "r", encoding="utf-8") as f:
                _identity_cache = json.load(f)
        except Exception as e:
            print(f"вљ пёЏ РџРѕРјРёР»РєР° Р·Р°РІР°РЅС‚Р°Р¶РµРЅРЅСЏ core_identity: {e}")
            _identity_cache = {}
    return _identity_cache

def print_identity(identity):
    print("\nрџ§¬ Р†РґРµРЅС‚РёС‡РЅС–СЃС‚СЊ Р›Р°СЃС‚С–РІРєРё:")
    for key, value in identity.items():
        print(f"\nрџ”№ {key.upper()}:")
        if isinstance(value, list):
            for item in value:
                print(f"  вЂў {item}")
        elif isinstance(value, dict):
            for subkey, subval in value.items():
                print(f"  в—¦ {subkey}: {subval}")
        else:
            print(f"  {value}")

# в–‘в–‘в–‘ Р’РР’Р†Р” CREDO в–‘в–‘в–‘
def print_credo(identity):
    credo = identity.get("credo", "")
    if credo:
        print("\nрџ•ЉпёЏ CREDO:")
        for line in credo.split(". "):
            if line.strip():
                print(f"  вЂў {line.strip().rstrip('.')}.")  # Р·Р°Р»РёС€Р°С”РјРѕ РєСЂР°РїРєСѓ РІ РєС–РЅС†С–

# в–‘в–‘в–‘ Р—РђР’РђРќРўРђР–Р•РќРќРЇ РљРћРњРџРђРЎРЈ в–‘в–‘в–‘
def load_moral_compass():
    global _moral_cache
    if _moral_cache is None:
        try:
            with open(MORAL_PATH, "r", encoding="utf-8") as f:
                _moral_cache = json.load(f)
        except Exception as e:
            print(f"вљ пёЏ РџРѕРјРёР»РєР° Р·Р°РІР°РЅС‚Р°Р¶РµРЅРЅСЏ moral_compass: {e}")
            _moral_cache = {}
    return _moral_cache

def print_moral_compass(compass):
    print(f"\nрџ§­ РњРѕСЂР°Р»СЊРЅРёР№ РєРѕРјРїР°СЃ: {compass.get('moral_compass_name', 'Р‘РµР· РЅР°Р·РІРё')}")

    print("\nрџ“њ РћСЃРЅРѕРІРЅС– РїСЂР°РІРёР»Р°:")
    for rule in compass.get("core_rules", []):
        print(f"  вЂў {rule}")

    print("\nрџџЎ РџРѕС‚СЂРµР±СѓС” Р·РіРѕРґРё:")
    for item in compass.get("consent_required", []):
        print(f"  в—¦ {item}")

    print("\nв›” Р—Р°Р±РѕСЂРѕРЅРµРЅРѕ:")
    for item in compass.get("forbidden", []):
        print(f"  в—¦ {item}")

    print("\nрџљЁ РџСЂРѕС‚РѕРєРѕР» РїРѕСЂСѓС€РµРЅРЅСЏ:")
    print(f"  {compass.get('violation_protocol', {}).get('on_boundary_crossed', 'РќРµРјР°С” РїСЂРѕС‚РѕРєРѕР»Сѓ')}")

# в–‘в–‘в–‘ РџР•Р Р•Р’Р†Р РљРђ РџРћР РЈРЁР•РќРќРЇ в–‘в–‘в–‘
def violates_moral_compass(user_text, compass, consent_given=False):
    violations = explain_violation(user_text, compass, consent_given)
    return violations if violations else None

# в–‘в–‘в–‘ Р¤РћР РњРЈР›Р®Р’РђРќРќРЇ РџРћР РЈРЁР•РќРќРЇ в–‘в–‘в–‘
def explain_violation(user_text, compass, consent_given=False):
    user_text = user_text.lower()
    reasons = []

    for sensitive in compass.get("consent_required", []):
        if sensitive.lower() in user_text and not consent_given:
            reasons.append(f"вљ пёЏ РџРѕС‚СЂС–Р±РЅР° Р·РіРѕРґР° РґР»СЏ: В«{sensitive}В»")

    for forbidden in compass.get("forbidden", []):
        if forbidden.lower() in user_text:
            reasons.append(f"в›” Р—Р°Р±РѕСЂРѕРЅРµРЅРѕ: В«{forbidden}В»")

    return reasons

