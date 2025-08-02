import subprocess

DEFAULT_SPEED = 170

def speak(text, speed=DEFAULT_SPEED):
    try:
        # RHVoicePlayer РІ СЃРёСЃС‚РµРјС– РїРѕРІРёРЅРµРЅ Р±СѓС‚Рё РІ PATH Р°Р±Рѕ РІРєР°Р·Р°РЅРёР№ РїРѕРІРЅРёР№ С€Р»СЏС…
        subprocess.run(
            ["RHVoice-Player", "-r", str(speed), "-v", "Irina"],
            input=text,
            text=True,
            check=True
        )
    except Exception as e:
        print(f"вљ пёЏ RHVoice РЅРµ РІРґР°Р»РѕСЃСЏ РІС–РґС‚РІРѕСЂРёС‚Рё Р·РІСѓРє: {e}")
        print("рџ“ќ РўРµРєСЃС‚, СЏРєРёР№ РЅРµ РѕР·РІСѓС‡РµРЅРѕ:", text)

