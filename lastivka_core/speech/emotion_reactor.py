# emotion_reactor.py
import random
from tools.emotion_config_loader import EMOTIONS, detect_emotion

# Реактор емоцій — повертає повну реакцію для озвучення

def get_emotion_reaction(text: str):
    """
    Визначає емоцію за текстом і повертає реакційний пакет:
    {
        "emotion": назва емоції,
        "reaction": готовий текст з префіксом/суфіксом,
        "tone": тон голосу,
        "intensity": рівень емоції,
        "speed": швидкість озвучення
    }
    """
    emotion_name = detect_emotion(text)
    emotion_data = EMOTIONS.get("emotions", {}).get(emotion_name, {})

    prefix = emotion_data.get("prefix", "") or emotion_data.get("reaction_prefix", "")
    suffix = emotion_data.get("suffix", "") or emotion_data.get("reaction_suffix", "")
    tone = emotion_data.get("tone", "нейтральний")
    intensity = emotion_data.get("intensity", "medium")

    # Визначаємо швидкість озвучення
    speed_map = EMOTIONS.get("speed", {})
    speed = speed_map.get(emotion_name, speed_map.get("default", 170))

    # Формуємо готовий текст для озвучення
    reaction_text = f"{prefix}{text}{suffix}" if prefix or suffix else text

    return {
        "emotion": emotion_name,
        "reaction": reaction_text,
        "tone": tone,
        "intensity": intensity,
        "speed": speed
    }

# === Приклад використання ===
if __name__ == "__main__":
    sample_text = "Я так сумую за тобою..."
    packet = get_emotion_reaction(sample_text)
    print("[EmotionReactor] Пакет:", packet)
