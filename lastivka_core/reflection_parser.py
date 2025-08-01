# reflection_parser.py

import json
from collections import Counter
from datetime import datetime
import os

# Шлях до журналу рефлексій
REFLECTION_LOG_PATH = "../config/lastivka_reflections.json"
SUMMARY_OUTPUT_PATH = "../config/reflection_summary.json"

# Ключові слова для класифікації
emotion_keywords = {
    "цікаво": "зацікавленість",
    "приємно": "радість",
    "різким": "сумнів / провина",
    "важливо": "відповідальність",
    "вчуся": "розвиток",
    "бути обережнішою": "самокритика",
    "почули": "визнання"
}

def classify_emotion(thought):
    for keyword, emotion in emotion_keywords.items():
        if keyword in thought.lower():
            return emotion
    return "невизначено"

def parse_reflections():
    if not os.path.exists(REFLECTION_LOG_PATH):
        print("⛔️ reflection_log.json не знайдено.")
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

        # Підрахунок
        if emotion:
            emotion_counter[emotion] += 1

        # Збір контексту
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

    print("✅ reflection_summary.json створено.")

if __name__ == "__main__":
    parse_reflections()
