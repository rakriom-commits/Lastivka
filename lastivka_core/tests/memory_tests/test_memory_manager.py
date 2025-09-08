"""
test_memory_manager.py – базові тести для memory_manager
"""

import os
import pytest
from lastivka_core.memory.memory_manager import MemoryManager as MM
from lastivka_core.memory.short_term import experience_manager  # для monkeypatch LOG_FILE


def test_add_and_load_experience(tmp_path, monkeypatch):
    """Перевірка: додати й завантажити досвід"""
    test_file = tmp_path / "test_experiences.json"

    # у досвіді файл називається LOG_FILE
    monkeypatch.setattr(experience_manager, "LOG_FILE", str(test_file))

    MM.add_experience("Тестова дія", "Тестова думка", "dialogue_based")

    data = MM.load_experiences()
    assert len(data) == 1
    assert data[0]["last_action"] == "Тестова дія"
    assert data[0]["thought"] == "Тестова думка"
    assert data[0]["entry_type"] == "dialogue_based"


def test_filter_experiences(tmp_path, monkeypatch):
    """Перевірка: фільтрація досвідів"""
    test_file = tmp_path / "test_experiences.json"
    monkeypatch.setattr(experience_manager, "LOG_FILE", str(test_file))

    MM.add_experience("А", "думка А", "internal")
    MM.add_experience("B", "думка B", "reflection")

    reflections = MM.filter_experiences("reflection")
    assert all(entry["entry_type"] == "reflection" for entry in reflections)


def test_get_reflections_and_categories():
    """Перевірка: афірмації з long_term"""
    categories = MM.list_reflection_categories()
    assert "self_awareness" in categories

    items = MM.get_reflections("self_awareness")
    assert isinstance(items, list)
    assert len(items) > 0
    assert any("Я " in phrase for phrase in items)
