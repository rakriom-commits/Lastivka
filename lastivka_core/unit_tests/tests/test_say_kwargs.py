import unittest, importlib
import main.lastivka as lastivka

class SayKwargsTests(unittest.TestCase):
    def setUp(self):
        importlib.reload(lastivka)
        lastivka.CFG.mute = False
        lastivka.CFG.tts_delay = 0.0
        lastivka.CFG.last_tts_ts = 0.0

    def test_passthrough_kwargs_when_supported(self):
        calls = []
        def speak_ok(text, **kwargs):
            calls.append((text, kwargs))
        lastivka._speak = speak_ok
        lastivka.say("hello", speed=170, emotion="calm")
        self.assertEqual(calls[0][0], "hello")
        self.assertEqual(calls[0][1]["speed"], 170)
        self.assertEqual(calls[0][1]["emotion"], "calm")

    def test_fallback_when_typeerror(self):
        calls = []
        def speak_typeerror(text, **kwargs):
            raise TypeError("unexpected kwargs")
        def speak_plain(text):
            calls.append(text)
        # First set a function that raises TypeError when kwargs present
        lastivka._speak = speak_typeerror
        # Patch say to fallback to a plain speak that doesn't accept kwargs
        # We'll temporarily replace _speak after TypeError is triggered,
        # by wrapping say call in a try/except? No – simpler: monkeypatch
        # say's behavior relies on the same _speak; emulate by switching after catching TypeError.
        # We can't intercept inside say, so emulate by providing a wrapper that toggles.
        # Instead: define a proxy that raises TypeError once, then calls plain.
        state = {"first": True}
        def proxy(text, **kwargs):
            if state["first"]:
                state["first"] = False
                raise TypeError("unexpected kwargs")
            else:
                calls.append(text)
        lastivka._speak = proxy
        lastivka.say("hello", speed=170)
        self.assertEqual(calls, ["hello"])

if __name__ == "__main__":
    unittest.main()
