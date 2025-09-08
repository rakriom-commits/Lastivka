# memory/logic.py

import re

class MemoryLogic:
    """
    Модуль логіки: аналізує запити користувача
    та співвідносить їх із збереженими спогадами.
    """

    def __init__(self, memory_store):
        self.memory_store = memory_store

    def search_meaning(self, query: str):
        """
        Пошук за ключовими словами в памʼяті.
        Поки що простий алгоритм: пошук за підрядком/ключем.
        """
        results = []
        memories = self.memory_store.load_all()

        for item in memories:
            text = item.get("text", "").lower()
            if query.lower() in text:
                results.append(item)

        return results

    def extract_keywords(self, query: str):
        """
        Дуже примітивне виділення ключових слів.
        Надалі можна замінити на NLP/вектори.
        """
        words = re.findall(r"\b\w+\b", query.lower())
        stopwords = {"що", "про", "ти", "мені", "казав", "сказав", "було", "є"}
        return [w for w in words if w not in stopwords]
