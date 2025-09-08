import sys
sys.path.insert(0, r"C:\Lastivka\lastivka_core")

from speech.offline_tts import OfflineTTS

print("Створюю перший екземпляр:")
tts1 = OfflineTTS("natalia")

print("Створюю другий екземпляр:")
tts2 = OfflineTTS("natalia")

print("Готово.")
