import subprocess

DEFAULT_SPEED = 170

def speak(text, speed=DEFAULT_SPEED):
    try:
        # RHVoicePlayer в системі повинен бути в PATH або вказаний повний шлях
        subprocess.run(
            ["RHVoice-Player", "-r", str(speed), "-v", "Irina"],
            input=text,
            text=True,
            check=True
        )
    except Exception as e:
        print(f"⚠️ RHVoice не вдалося відтворити звук: {e}")
        print("📝 Текст, який не озвучено:", text)
