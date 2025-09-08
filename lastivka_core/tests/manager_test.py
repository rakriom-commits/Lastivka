# -*- coding: utf-8 -*-
import pytest
from pathlib import Path
from lastivka_core.memory.manager import MemoryManager   # ← правильний імпорт

@pytest.fixture
def mem():
    m = MemoryManager()
    m.clear_memory()
    return m

def test_add_and_get_thought(mem):
    mem.add_thought("кава", "чорна", rel="is", tags=["напій"])
    results = mem.get_thoughts_by_key("кава")
    assert len(results) == 1
    assert results[0]["text"] == "чорна"
    assert "напій" in results[0]["tags"]

def test_duplicate_thought(mem):
    mem.add_thought("кава", "чорна", rel="is")
    mem.add_thought("кава", "чорна", rel="is")
    results = mem.get_thoughts_by_key("кава")
    assert len(results) == 1

def test_delete_thoughts(mem):
    mem.add_thought("борщ", "червоний", tags=["їжа"])
    assert mem.get_thoughts_by_key("борщ")
    mem.delete_thoughts_by_key("борщ")
    assert not mem.get_thoughts_by_key("борщ")

def test_clear_memory(mem):
    mem.add_thought("сир", "жовтий")
    mem.add_thought("хліб", "чорний")
    mem.clear_memory()
    assert mem.get_all_memory() == {}

def test_find_thoughts(mem):
    mem.add_thought("кава", "чорна")
    results = mem.find_thoughts("каву")
    assert any(r["text"] == "чорна" for r in results)

def test_smart_search(mem):
    mem.add_thought("кава", "чорна", tags=["напій"])
    mem.add_thought("сир", "м’який", tags=["їжа"])
    results = mem.smart_search("купити кави", limit=5)
    assert results
    assert results[0]["key"] in ("кава", "сир")

def test_ask_fallback(mem):
    mem.add_thought("сир", "голландський", tags=["покупка"])
    ans = mem.ask("що купити?")
    assert ans is not None
    assert "сир" in ans["text"].lower()

def test_export_memory(tmp_path, mem):
    mem.add_thought("чай", "зелений")
    export_file = tmp_path / "export.json"
    mem.export_memory(export_file)
    assert export_file.exists()
    assert "чай" in export_file.read_text(encoding="utf-8")
