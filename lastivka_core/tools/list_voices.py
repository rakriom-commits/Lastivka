# tools/list_voices.py
import pyttsx3
eng = pyttsx3.init(driverName="sapi5")
voices = eng.getProperty("voices") or []
for v in voices:
    langs = getattr(v, "languages", []) or []
    try:
        langs = [x.decode(errors="ignore") if isinstance(x, (bytes, bytearray)) else str(x) for x in langs]
    except Exception:
        pass
    print(f"- name: {getattr(v,'name','')}\n  id: {getattr(v,'id','')}\n  langs: {langs}\n")
