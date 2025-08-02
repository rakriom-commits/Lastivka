# === Voice AutoSwitch Module ===
import socket
import importlib

def internet_available(host="8.8.8.8", port=53, timeout=2):
    """РџРµСЂРµРІС–СЂСЏС” РЅР°СЏРІРЅС–СЃС‚СЊ С–РЅС‚РµСЂРЅРµС‚Сѓ С‡РµСЂРµР· DNS-Р·Р°РїРёС‚."""
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except Exception:
        return False

# Р’РёР·РЅР°С‡Р°С”РјРѕ, СЏРєРёР№ РјРѕРґСѓР»СЊ РІРёРєРѕСЂРёСЃС‚РѕРІСѓРІР°С‚Рё
if internet_available():
    voice_module = importlib.import_module("main.voice_module")  # РѕРЅР»Р°Р№РЅ (gTTS)
else:
    voice_module = importlib.import_module("main.voice_module_offline")  # РѕС„Р»Р°Р№РЅ (pyttsx3)

# Р•РєСЃРїРѕСЂС‚СѓС”РјРѕ С„СѓРЅРєС†С–СЋ speak Р· РѕР±СЂР°РЅРѕРіРѕ РјРѕРґСѓР»СЏ
speak = voice_module.speak

