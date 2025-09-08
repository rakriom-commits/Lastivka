# C:\Lastivka\lastivka_core\memory\short_term\short_term.py
"""
short_term – короткочасна пам'ять:
- зберігає останні дії/думки/події у локальному JSON,
- безпечне читання/запис (fallback при пошкодженні),
- модульні обгортки add_entry/get_entries/clear_entries для тестів.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from typing import List, Dict, Any

# Файл зберігання поруч із модулем
MODULE_DIR = os.path.dirname(__file__)
DEFAULT_STORAGE = os.path.join(MODULE_DIR, "experience_log.json")
DEFAULT_LIMIT = 50

_lock = threading.RLock()


class ShortTermMemory:
    """
    Короткочасна пам'ять для збереження останніх діалогів, думок і дій.
    Дані зберігаються у файлі JSON для відновлення після перезапуску.
    """

    def __init__(self, storage_path: str = DEFAULT_STORAGE, limit: int = DEFAULT_LIMIT):
        self.storage_path = storage_path
        self.limit = max(1, int(limit))
        self.entries: List[Dict[str, Any]] = self._load()

    # ---------------- internal I/O ----------------

    def _load(self) -> List[Dict[str, Any]]:
        """Завантаження попередніх записів із JSON, якщо файл існує."""
        if not self.storage_path:
            return []
        # гарантуємо існування каталогу
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)

        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return data[-self.limit :]
            except Exception:
                # якщо файл пошкоджений — робимо бекап і стартуємо з порожнього
                try:
                    bad_name = self.storage_path + ".corrupt_" + datetime.now().strftime("%Y%m%d_%H%M%S")
                    os.replace(self.storage_path, bad_name)
                except Exception:
                    pass
        return []

    def _save(self) -> None:
        """Збереження поточного стану пам’яті у JSON."""
        with _lock:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self.entries[-self.limit :], f, ensure_ascii=False, indent=2)

    # ---------------- public API (OO) ----------------

    def add_entry(self, last_action: str, thought: str, entry_type: str = "dialogue_based") -> None:
        """Додає новий запис у пам'ять."""
        entry = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "last_action": str(last_action),
            "thought": str(thought),
            "entry_type": str(entry_type),
        }
        with _lock:
            self.entries.append(entry)
            # обмеження довжини пам’яті
            if len(self.entries) > self.limit:
                self.entries = self.entries[-self.limit :]
            self._save()

    def get_entries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Повертає останні записи (за замовчуванням 10)."""
        k = max(1, int(limit))
        with _lock:
            return list(self.entries[-k:])

    def clear(self) -> None:
        """Очищує короткочасну пам’ять."""
        with _lock:
            self.entries = []
            self._save()

    def set_limit(self, new_limit: int) -> None:
        """Оновити ліміт записів у пам’яті (мінімум 1)."""
        with _lock:
            self.limit = max(1, int(new_limit))
            # урізаємо список, якщо потрібно
            if len(self.entries) > self.limit:
                self.entries = self.entries[-self.limit :]
            self._save()

    def set_storage_path(self, new_path: str) -> None:
        """Змінити шлях зберігання (для тестів/конфігів)."""
        with _lock:
            self.storage_path = new_path
            self.entries = self._load()
            self._save()


# ---------------- module-level convenience wrappers ----------------

_stm_singleton = ShortTermMemory()


def add_entry(last_action: str, thought: str, entry_type: str = "dialogue_based") -> None:
    """Модульна обгортка: додати запис (сумісність зі старими тестами)."""
    _stm_singleton.add_entry(last_action, thought, entry_type)


def get_entries(limit: int = 10) -> List[Dict[str, Any]]:
    """Модульна обгортка: отримати останні N записів."""
    return _stm_singleton.get_entries(limit)


def clear_entries() -> None:
    """Модульна обгортка: очистити пам'ять."""
    _stm_singleton.clear()


def set_limit(n: int) -> None:
    """Налаштувати ліміт для singleton-екземпляра (необов'язково)."""
    _stm_singleton.set_limit(n)


def set_storage_path(path: str) -> None:
    """Змінити файл зберігання для singleton-екземпляра (зручно у тестах)."""
    _stm_singleton.set_storage_path(path)


__all__ = [
    "ShortTermMemory",
    "add_entry",
    "get_entries",
    "clear_entries",
    "set_limit",
    "set_storage_path",
]
