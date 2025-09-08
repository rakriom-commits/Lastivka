# C:\Lastivka\lastivka_core\tests\memory_tests\test_memory_manager_basic.py

import unittest
from lastivka_core.memory.memory_manager import MemoryManager as MM


class TestMemoryManagerBasic(unittest.TestCase):

    def setUp(self):
        # Почистимо короткострокові записи перед тестом
        # (якщо у майбутньому з'явиться метод clear — можна буде використати його напряму)
        self._initial = MM.load_experiences()
        for _ in range(len(self._initial)):
            MM.load_experiences().pop()

    def test_add_and_load_experience(self):
        MM.add_experience("дія", "думка", "test_type")
        entries = MM.load_experiences()
        self.assertTrue(any(e["entry_type"] == "test_type" for e in entries))

    def test_filter_experiences(self):
        MM.add_experience("action", "thought", "filter_test")
        filtered = MM.filter_experiences("filter_test")
        self.assertGreaterEqual(len(filtered), 1)
        self.assertEqual(filtered[-1]["entry_type"], "filter_test")

    def test_reflections_methods_exist(self):
        # Навіть якщо база порожня, методи повинні повертати list
        categories = MM.list_reflection_categories()
        self.assertIsInstance(categories, list)

        reflections = MM.get_reflections("non_existing_category")
        self.assertIsInstance(reflections, list)


if __name__ == "__main__":
    unittest.main()
