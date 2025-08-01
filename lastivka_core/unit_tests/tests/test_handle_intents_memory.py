import unittest
from types import SimpleNamespace
from main.handlers import handle_intents

class DummySay:
    def __init__(self): self.messages = []
    def __call__(self, text, **kwargs): self.messages.append(text)

class HandleIntentsMemoryTests(unittest.TestCase):
    def setUp(self):
        self.CFG = SimpleNamespace(activation=None, name="Софія")
        self.say = DummySay()
        self.core = {"Ім'я": "Софія"}
        self.remembered = []
    def recall(self): return self.remembered[-1] if self.remembered else None
    def remember(self, text): self.remembered.append(text)

    def test_remember_and_recall(self):
        done = handle_intents("запам'ятай: тест", self.CFG, self.say, self.core, self.recall, self.remember)
        self.assertTrue(done)
        self.assertIn("Я запам'ятала це.", self.say.messages)
        done = handle_intents("що я тобі казав", self.CFG, self.say, self.core, self.recall, self.remember)
        self.assertTrue(done)
        self.assertIn("тест", self.say.messages[-1])

    def test_activation(self):
        self.CFG.activation = "OMEGA"
        done = handle_intents("OMEGA", self.CFG, self.say, self.core, self.recall, self.remember)
        self.assertTrue(done)
        self.assertIn("Ядро Софії Ω активовано.", self.say.messages)

if __name__ == "__main__":
    unittest.main()
