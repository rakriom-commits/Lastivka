from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

__all__ = ["play_wav"]

def play_wav(path: str | Path, *, block: bool = True) -> None:
    """
    Р’С–РґС‚РІРѕСЂРёС‚Рё WAV-С„Р°Р№Р» Р·Р° С€Р»СЏС…РѕРј `path`.
    
    :param path: РЁР»СЏС… РґРѕ WAV-С„Р°Р№Р»Сѓ
    :param block: True вЂ” С‡РµРєР°С‚Рё Р·Р°РІРµСЂС€РµРЅРЅСЏ, False вЂ” Р·Р°РїСѓСЃРєР°С‚Рё Р°СЃРёРЅС…СЂРѕРЅРЅРѕ
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"вќЊ Р¤Р°Р№Р» РЅРµ Р·РЅР°Р№РґРµРЅРѕ: {p}")

    system = sys.platform

    # вЂ•вЂ•вЂ• Windows вЂ•вЂ•вЂ•
    if system == "win32":
        try:
            import winsound  # stdlib
            flags = winsound.SND_FILENAME | (0 if block else winsound.SND_ASYNC)
            winsound.PlaySound(str(p), flags)
            return
        except ModuleNotFoundError:
            pass

        # fallback: СЃРёСЃС‚РµРјРЅРёР№ РїР»РµС”СЂ
        try:
            os.startfile(p)
        except Exception as e:
            print(f"вљ пёЏ РќРµ РІРґР°Р»РѕСЃСЏ РІС–РґРєСЂРёС‚Рё С„Р°Р№Р»: {e}")
        return

    # вЂ•вЂ•вЂ• macOS вЂ•вЂ•вЂ•
    if system == "darwin":
        cmd = ["afplay", str(p)]
        (subprocess.run if block else subprocess.Popen)(cmd)
        return

    # вЂ•вЂ•вЂ• Linux / WSL вЂ•вЂ•вЂ•
    if system.startswith("linux"):
        cmd = ["aplay", str(p)]
        try:
            (subprocess.run if block else subprocess.Popen)(cmd)
        except FileNotFoundError:
            print("вќЊ РЈС‚РёР»С–С‚Р° 'aplay' РЅРµ Р·РЅР°Р№РґРµРЅР°. Р’СЃС‚Р°РЅРѕРІРё РїР°РєРµС‚ ALSA-utils.")
        return

    # вЂ•вЂ•вЂ• РќРµРІС–РґРѕРјР° РћРЎ вЂ•вЂ•вЂ•
    print(f"вљ пёЏ РќРµРІС–РґРѕРјР° РїР»Р°С‚С„РѕСЂРјР°: {system}")

# вЂ•вЂ•вЂ• РўРµСЃС‚ РЅР°РїСЂСЏРјСѓ вЂ•вЂ•вЂ•
if __name__ == "__main__":
    demo_file = Path("demo.wav")
    if demo_file.exists():
        print(f"в–¶пёЏ Р’С–РґС‚РІРѕСЂРµРЅРЅСЏ '{demo_file}'...")
        play_wav(demo_file)
    else:
        print("вќЊ demo.wav РЅРµ Р·РЅР°Р№РґРµРЅРѕ.")

