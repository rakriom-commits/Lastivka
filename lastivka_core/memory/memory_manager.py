"""
memory_manager.py – єдиний інтерфейс для роботи з пам’яттю.
Об’єднує короткострокову (experience_manager) та довготривалу (reflection_manager) пам’ять.
"""

# --- Пакетні імпорти (правильні для структури lastivka_core/...) ---
try:
    from lastivka_core.memory.short_term.experience_manager import (
        add_experience as _add_experience,
        load_experiences as _load_experiences,
        filter_by_type as _filter_by_type,
    )
    from lastivka_core.memory.long_term.reflection.reflection_manager import (
        get_reflections as _get_reflections,
        list_categories as _list_categories,
    )
except ModuleNotFoundError:
    # --- Fallback (якщо модуль запускали локально без пакетного префікса) ---
    from memory.short_term.experience_manager import (   # type: ignore
        add_experience as _add_experience,
        load_experiences as _load_experiences,
        filter_by_type as _filter_by_type,
    )
    from memory.long_term.reflection.reflection_manager import (  # type: ignore
        get_reflections as _get_reflections,
        list_categories as _list_categories,
    )


class MemoryManager:
    """Універсальний менеджер пам’яті."""

    # --- Short-term ---
    @staticmethod
    def add_experience(last_action: str, thought: str, entry_type: str = "internal") -> None:
        """
        Додати запис у короткочасну пам'ять.
        entry_type: "dialogue_based" | "internal" | "reflection" | ...
        """
        _add_experience(last_action, thought, entry_type)

    @staticmethod
    def load_experiences() -> list[dict]:
        """Завантажити всі записи короткочасного досвіду."""
        return _load_experiences()

    @staticmethod
    def filter_experiences(entry_type: str) -> list[dict]:
        """Відфільтрувати записи короткочасного досвіду за типом."""
        return _filter_by_type(entry_type)

    # --- Long-term ---
    @staticmethod
    def get_reflections(category: str) -> list[str]:
        """Отримати афірмації/рефлексії за категорією із довготривалої пам'яті."""
        return _get_reflections(category)

    @staticmethod
    def list_reflection_categories() -> list[str]:
        """Перелік доступних категорій у довготривалій пам'яті."""
        return _list_categories()


__all__ = ["MemoryManager"]
