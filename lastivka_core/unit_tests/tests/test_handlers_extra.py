import unittest
from pathlib import Path
from types import SimpleNamespace
from io import StringIO
import sys, tempfile

from main.handlers import COMMANDS

class DummySay:
    def __init__(self):
        self.messages = []
    def __call__(self, text, **kwargs):
        self.messages.append(str(text))

class HandlersExtraTests(unittest.TestCase):
    def setUp(self):
        self.CFG = SimpleNamespace(mute=False, name="Софія", alt_name="Берегиня")
        self.say = DummySay()
        # тимчасовий файл логу
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".log", mode="w", encoding="utf-8")
        self.tmp.write("line A\nline B\nline C\n")
        self.tmp.close()
        self.LOG_FILE = Path(self.tmp.name)
        self.CONFIG_DIR = Path("C:/Lastivka/lastivka_core/config")

    def tearDown(self):
        try:
            Path(self.tmp.name).unlink(missing_ok=True)
        except Exception:
            pass

    def test_log_command_prints_tail(self):
        # перехоплюємо stdout
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            COMMANDS["лог"](self.CFG, self.say, self.LOG_FILE, self.CONFIG_DIR)
            out = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        # перевіряємо, що say отримає повідомлення та вивід містить лінії з файлу
        self.assertTrue(any("Показую останні 20 рядків логу" in m for m in self.say.messages))
        self.assertIn("line A", out)
        self.assertIn("line B", out)
        self.assertIn("line C", out)

    def test_status_command_prints_summary(self):
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            COMMANDS["стан"](self.CFG, self.say, self.LOG_FILE, self.CONFIG_DIR)
            out = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        # Перевіряємо, що є ключові поля
        self.assertTrue(any(m == "Статус системи." for m in self.say.messages))
        self.assertIn("👤 Ім'я: Софія", out)
        self.assertIn("🔈 Звук:", out)
        self.assertIn("🗣️ TTS backend:", out)
        self.assertIn("🗂️ Лог:", out)

if __name__ == "__main__":
    unittest.main()
