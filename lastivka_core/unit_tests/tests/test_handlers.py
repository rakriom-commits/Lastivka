import unittest
from pathlib import Path
from types import SimpleNamespace
from main.handlers import COMMANDS

class DummySay:
    def __init__(self):
        self.messages = []
    def __call__(self, text, **kwargs):
        self.messages.append(str(text))

class HandlersTests(unittest.TestCase):
    def setUp(self):
        self.CFG = SimpleNamespace(mute=False, name="Софія", alt_name="Берегиня")
        self.say = DummySay()
        self.LOG_FILE = Path("C:/Lastivka/lastivka_core/logs/lastivka.log")
        self.CONFIG_DIR = Path("C:/Lastivka/lastivka_core/config")

    def test_time_command(self):
        COMMANDS["час"](self.CFG, self.say, self.LOG_FILE, self.CONFIG_DIR)
        self.assertTrue(any(m.startswith("Зараз ") for m in self.say.messages))

    def test_date_command(self):
        COMMANDS["дата"](self.CFG, self.say, self.LOG_FILE, self.CONFIG_DIR)
        self.assertTrue(any(m.startswith("Сьогодні ") for m in self.say.messages))

    def test_help_command(self):
        COMMANDS["допомога"](self.CFG, self.say, self.LOG_FILE, self.CONFIG_DIR)
        self.assertTrue(any("Можу:" in m for m in self.say.messages))

    def test_mute_toggle(self):
        COMMANDS["без звуку"](self.CFG, self.say, self.LOG_FILE, self.CONFIG_DIR)
        self.assertTrue(self.CFG.mute)
        COMMANDS["звук"](self.CFG, self.say, self.LOG_FILE, self.CONFIG_DIR)
        self.assertFalse(self.CFG.mute)

    def test_cover_on(self):
        COMMANDS["ввімкни прикриття"](self.CFG, self.say, self.LOG_FILE, self.CONFIG_DIR)
        self.assertEqual(self.CFG.name, "Берегиня")
        self.assertTrue(any("Змінено ідентичність" in m for m in self.say.messages))

if __name__ == "__main__":
    unittest.main()
