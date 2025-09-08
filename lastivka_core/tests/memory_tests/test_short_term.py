"""
Тестування модуля short_term пам’яті
"""

import unittest
from lastivka_core.memory.short_term import short_term

class TestShortTermMemory(unittest.TestCase):
    def test_add_and_get_entries(self):
        # Додаємо кілька записів
        short_term.add_entry("Test action 1", "Test thought 1")
        short_term.add_entry("Test action 2", "Test thought 2")

        entries = short_term.get_entries()
        self.assertGreaterEqual(len(entries), 2)
        self.assertEqual(entries[-2]["last_action"], "Test action 1")
        self.assertEqual(entries[-1]["thought"], "Test thought 2")

    def test_clear_entries(self):
        short_term.add_entry("Action", "Thought")
        short_term.clear_entries()
        entries = short_term.get_entries()
        self.assertEqual(entries, [])

if __name__ == "__main__":
    unittest.main()
