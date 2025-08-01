import json

class EmotionEngine:
    def __init__(self, config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Витягуємо швидкості окремо
        self.speeds = config.get('speed', {})
        self.default_speed = self.speeds.get("default", 170)

        # Зберігаємо лише ті елементи, які є емоціями (мають 'triggers')
        self.emotions = {
            key: value for key, value in config.items()
            if isinstance(value, dict) and 'triggers' in value
        }

    def detect_emotion(self, message):
        detected = {
            "emotion": None,
            "reaction": None,
            "speed": self.default_speed,
            "tone": "нейтральний",
            "intensity": "medium"
        }

        message_lower = message.lower()

        for emotion_name, props in self.emotions.items():
            triggers = props.get("triggers", [])
            for trigger in triggers:
                if trigger in message_lower:
                    detected["emotion"] = emotion_name
                    detected["reaction"] = props.get("reaction", "")
                    detected["speed"] = self.speeds.get(emotion_name, self.default_speed)
                    detected["tone"] = props.get("tone", "нейтральний")
                    detected["intensity"] = props.get("intensity", "medium")
                    return detected

        return detected