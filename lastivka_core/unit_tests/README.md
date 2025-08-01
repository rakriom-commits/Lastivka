# Unit tests for Lastivka (мінімальний набір)

## Структура
- tests/test_handlers.py — перевіряє основні команди (час/дата/допомога, mute, прикриття).
- tests/test_say_antispam.py — smoke-тести `say()` (антиспам, mute) із підміною `_speak`.
- tests/test_emotion_engine_smoke.py — швидка перевірка `EmotionEngine.detect_emotion()`.

## Куди класти
Скопіюй папку `tests` у `C:\Lastivka\lastivka_core\unit_tests\`

## Як запускати
```powershell
cd C:\Lastivka\lastivka_core\unit_tests
python -m unittest
```
