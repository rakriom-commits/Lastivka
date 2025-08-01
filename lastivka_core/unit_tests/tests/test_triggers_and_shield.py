import unittest
import importlib

# We target the adapter inside main.lastivka
import main.lastivka as lastivka

class TriggerShieldTests(unittest.TestCase):
    def setUp(self):
        importlib.reload(lastivka)

    def test_trigger_shield_forwards_args(self):
        calls = []
        def fake_trigger_shell(*, user_input, consent_given, ref_hashes):
            calls.append((user_input, consent_given, ref_hashes))
            return "ok"
        # monkeypatch the imported symbol
        lastivka.trigger_shell = fake_trigger_shell
        out = lastivka.trigger_shield("ping", consent_given=False, ref_hashes={"x": 1})
        self.assertEqual(out, "ok")
        self.assertEqual(calls, [("ping", False, {"x": 1})])

    def test_trigger_shield_handles_exception(self):
        def boom(**kwargs):
            raise RuntimeError("boom")
        lastivka.trigger_shell = boom
        out = lastivka.trigger_shield("ping")
        self.assertIsNone(out)

if __name__ == "__main__":
    unittest.main()
