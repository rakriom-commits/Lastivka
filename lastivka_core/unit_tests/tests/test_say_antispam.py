import unittest, time, importlib
import main.lastivka as lastivka

class SayAntiSpamTests(unittest.TestCase):
    def setUp(self):
        importlib.reload(lastivka)
        self.calls = []
        def fake_speak(text, **kwargs):
            self.calls.append((text, kwargs))
        lastivka._speak = fake_speak
        lastivka.CFG.mute = False
        lastivka.CFG.tts_delay = 0.2
        lastivka.CFG.last_tts_ts = 0.0

    def test_antispam_respects_delay(self):
        t0 = time.time()
        lastivka.say("one")
        lastivka.say("two")
        dt = time.time() - t0
        self.assertGreaterEqual(dt, 0.19)
        self.assertEqual([c[0] for c in self.calls], ["one", "two"])

    def test_mute(self):
        lastivka.CFG.mute = True
        self.calls.clear()
        lastivka.say("should not speak")
        self.assertEqual(self.calls, [])

if __name__ == "__main__":
    unittest.main()
