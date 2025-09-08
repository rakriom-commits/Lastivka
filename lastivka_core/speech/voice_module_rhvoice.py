import subprocess

DEFAULT_SPEED = 170

def speak(text, speed=DEFAULT_SPEED):
    try:
        # RHVoice-Player має бути в PATH або явно вказаний
        subprocess.run(
            ["RHVoice-Player", "-r", str(speed), "-v", "Irina"],
            input=text,
            text=True,
            check=True
        )
    except Exception as e:
        print(f"[VoiceRHVoice] Помилка під час озвучення RHVoice: {e}")
        print("[VoiceRHVoice] Неможливо озвучити текст:", text)
