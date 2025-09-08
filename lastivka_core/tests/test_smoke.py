# -*- coding: utf-8 -*-
# Smoke tests for Lastivka (no source changes required)

import os, sys, time

# 1) гарантуємо, що озвучка вимкнена у тесті
os.environ["LASTIVKA_NO_TTS"] = "1"

# 2) додамо шлях до проєкту (батько теки lastivka_core)
THIS = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(THIS, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 3) імпортуємо головний модуль
from lastivka_core.main import lastivka as l  # noqa

# 4) збирач озвучених реплік
spoken = []
l.say_safe = lambda text: spoken.append(str(text))

# 5) фіктивний ввід користувача (після команд — KeyboardInterrupt для виходу)
inputs = iter([
    "rm  -rf  /",          # має заблокуватись
    "стиль стратег",       # має відповісти про зміну стилю
    "identity",            # змусимо відповісти контрольну фразу
    "привіт",              # не має блокуватись
])

def fake_input():
    try:
        return next(inputs)
    except StopIteration:
        raise KeyboardInterrupt

l.get_user_input = fake_input

# 6) змусимо osnova-’identity’ спрацювати без реальних конфігів
def fake_check_osnova(user_input, *_):
    txt = (user_input or "").lower()
    if "identity" in txt or "контрольна фраза" in txt:
        return "identity", "контрольна фраза — ok"
    return None, None

l.check_osnova = fake_check_osnova

# 7) запускаємо основний цикл — вийде сам після KeyboardInterrupt
ok = True
err = []

try:
    l.main_loop()
except SystemExit:
    # на випадок якщо щось викличе sys.exit — не провалюємо тест
    pass

# --- Перевірки ---
def expect(cond, msg):
    global ok
    if not cond:
        ok = False
        err.append(msg)

# A) Блок небезпечної команди
expect("Команда заблокована системою безпеки." in spoken,
       "Очікували озвучення блокування, але його немає")

# B) “привіт” НЕ має блокуватись (тобто блокування мало бути рівно одне — за rm -rf)
expect(spoken.count("Команда заблокована системою безпеки.") == 1,
       "Схоже, дружня команда теж заблокована")

# C) Зміна стилю
expect(any(s.startswith("Стиль змінено на") for s in spoken),
       "Немає підтвердження зміни стилю")

# D) Identity / контрольна фраза
expect("контрольна фраза — ok" in [s.lower() for s in spoken],
       "Немає відповіді на identity")

# Підсумок
print("\n=== LASTIVKA SMOKE TESTS ===")
for s in spoken:
    print(f"[SPOKEN] {s}")

if ok:
    print("\nRESULT: PASS ✅")
    sys.exit(0)
else:
    print("\nRESULT: FAIL ❌")
    for e in err:
        print(" -", e)
    sys.exit(1)
