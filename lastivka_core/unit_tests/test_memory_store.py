import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import unittest
import time
from datetime import datetime, timedelta
from config import memory_store

class TestMemoryStore(unittest.TestCase):

    def setUp(self):
        # Скидаємо памʼять перед кожним тестом
        memory_store.save_memory({})

    def test_log_and_recall_thought(self):
        test_text = "Софія — розумна система."
        memory_store.log_thought(test_text)
        result = memory_store.recall_memory()
        self.assertEqual(result, test_text)

    def test_search_memories(self):
        memory_store.log_thought("Це перша думка.")
        memory_store.log_thought("Це друга думка про щось важливе.")
        result = memory_store.search_memories("важливе")
        self.assertIn("друга думка", result)

    def test_purge_old_thoughts(self):
        now = datetime.now()
        old = now - timedelta(days=60)
        memory = {
            "thoughts": [
                {"ts": old.isoformat(), "text": "дуже стара думка"},
                {"ts": now.isoformat(), "text": "свіжа думка"}
            ]
        }
        memory_store.save_memory(memory)
        report = memory_store.purge_old_thoughts(days=30)
        updated = memory_store.load_memory()
        self.assertEqual(len(updated["thoughts"]), 1)
        self.assertIn("свіжа", updated["thoughts"][0]["text"])
        self.assertIn("Видалено", report)

    def test_check_triggers(self):
        memory_store.save_memory({
            "triggers": {
                "SOS": "🆘 Тривога!",
                "Софі": "Так, я тут."
            }
        })
        response = memory_store.check_triggers("Привіт, Софі")
        self.assertEqual(response, "Так, я тут.")

if __name__ == "__main__":
    unittest.main()
