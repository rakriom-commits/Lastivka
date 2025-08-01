# === EMOTION ENGINE Ω ===

from config.emotion_config import EMOTIONS
from main.lastivka_skill import get_emotional_profile

def detect_emotion(text: str):
    """
    Визначає емоцію на основі тригерів у тексті користувача.
    Повертає: (емоція, швидкість, голосова_реакція, емоційний_профіль)
    """
    emotions_data = EMOTIONS.get("emotions", [])
    speed_map = EMOTIONS.get("speed", {})
    text_lower = text.lower() if isinstance(text, str) else ""

    for entry in emotions_data:
        emotion = entry.get("Емоція", "").lower()
        for trigger in entry.get("Слова", []):
            if trigger.lower() in text_lower:
                speed = speed_map.get(emotion, speed_map.get("default", 170))
                voice_response = entry.get("Реакція", "")
                profile = get_emotional_profile(emotion)
                return emotion, speed, voice_response, profile

    # Якщо не знайдено — нейтральна емоція
    return (
        "нейтральна",
        speed_map.get("default", 170),
        "спокійний, базовий тон",
        get_emotional_profile("нейтральна")
    )

if __name__ == "__main__":
    test = "мені страшно залишатись наодинці"
    emotion, speed, voice, profile = detect_emotion(test)
    print(f"🧠 Емоція: {emotion}")
    print(f"🎚 Швидкість: {speed}")
    print(f"🗣 Реакція: {voice}")
    print("🎭 Поведінка:")
    for key, value in profile.items():
        print(f"  {key.capitalize()}: {value}")
