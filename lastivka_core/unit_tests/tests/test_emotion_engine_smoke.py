import unittest
from pathlib import Path
from tools.emotion_engine import EmotionEngine

class EmotionEngineSmoke(unittest.TestCase):
    def test_detect_emotion_smoke(self):
        cfg_path = Path("C:/Lastivka/lastivka_core/config/emotion_config.json")
        engine = EmotionEngine(cfg_path)
        out = engine.detect_emotion("Привіт! Як твої справи?")
        self.assertIsInstance(out, dict)
        for k in ("emotion", "tone", "intensity"):
            self.assertIn(k, out)

if __name__ == "__main__":
    unittest.main()
