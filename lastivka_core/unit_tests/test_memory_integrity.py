import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import unittest
import os
import json
from config import memory_store

MEMORY_PATH = Path(__file__).resolve().parent.parent / "config" / "memory_store.json"

class TestMemoryIntegrity(unittest.TestCase):

    def setUp(self):
        # Скидаємо памʼять до порожньої
        memory_store.save_memory({})

    def test_memory_file_exists(self):
        self.assertTrue(MEMORY_PATH.exists(), "Файл памʼяті не знайдено!")

    def test_memory_file_is_valid_json(self):
        try:
            with open(MEMORY_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertIsInstance(data, dict, "Файл має бути словником JSON")
        except Exception as e:
            self.fail(f"Некоректний JSON у памʼяті: {e}")

    def test_memory_rejects_invalid_format(self):
        # Псуємо файл
        with open(MEMORY_PATH, "w", encoding="utf-8") as f:
            f.write("{дуже погано форматований json...")

        with self.assertRaises(json.JSONDecodeError):
            memory_store.load_memory()

if __name__ == "__main__":
    unittest.main()
