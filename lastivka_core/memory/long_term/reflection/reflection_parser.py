# reflection_parser.py

import json
from collections import Counter
from datetime import datetime
import os

# Шлях до файлу з логом роздумів
REFLECTION_LOG_PATH = "../config/lastivka_reflections.json"
SUMMARY_OUTPUT_PATH = "../config/reflection_summary.json"

# Ключові слова емоцій для класифікації
emotion_keywords = {
    "радість": "взаємовідносини",
    "любов": "стати",
    "стиль": "сім'я / зв'язок",
    "інтуїція": "інтуїція",
    "спокій": "тота",
    "біль чи втома": "спокійність",
    "сміливість": "прийняття"
}

def classify_emotion(thought):
    thought_lower = thought.lower()
    for keyword, emotion in emotion_keywords.items():
        if keyword in thought_lower:
            return emotion
    return "невизначена"

def parse_reflections():
    if not os.path.exists(REFLECTION_LOG_PATH):
        print("Відсутній reflection_log.json файл.")
        return

    with open(REFLECTION_LOG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    emotion_counter = Counter()
    context_summary = {}

    for entry in data:
        thought = entry.get("thought", "").strip()
        action = entry.get("last_action", "").strip()
        timestamp = entry.get("timestamp", "")
        emotion = classify_emotion(thought)

        # Рахуємо кількість кожної емоції
        if emotion:
            emotion_counter[emotion] += 1

        # Групуємо думки за емоціями
        context_summary.setdefault(emotion, []).append({
            "timestamp": timestamp,
            "action": action,
            "thought": thought
        })

    summary = {
        "parsed_at": datetime.now().isoformat(),
        "emotion_summary": dict(emotion_counter),
        "thought_clusters": context_summary
    }

    with open(SUMMARY_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("Збережено reflection_summary.json.")

if __name__ == "__main__":
    parse_reflections()
