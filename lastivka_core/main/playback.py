from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

__all__ = ["play_wav"]

def play_wav(path: str | Path, *, block: bool = True) -> None:
    """
    Відтворити WAV-файл за шляхом `path`.
    
    :param path: Шлях до WAV-файлу
    :param block: True — чекати завершення, False — запускати асинхронно
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"❌ Файл не знайдено: {p}")

    system = sys.platform

    # ――― Windows ―――
    if system == "win32":
        try:
            import winsound  # stdlib
            flags = winsound.SND_FILENAME | (0 if block else winsound.SND_ASYNC)
            winsound.PlaySound(str(p), flags)
            return
        except ModuleNotFoundError:
            pass

        # fallback: системний плеєр
        try:
            os.startfile(p)
        except Exception as e:
            print(f"⚠️ Не вдалося відкрити файл: {e}")
        return

    # ――― macOS ―――
    if system == "darwin":
        cmd = ["afplay", str(p)]
        (subprocess.run if block else subprocess.Popen)(cmd)
        return

    # ――― Linux / WSL ―――
    if system.startswith("linux"):
        cmd = ["aplay", str(p)]
        try:
            (subprocess.run if block else subprocess.Popen)(cmd)
        except FileNotFoundError:
            print("❌ Утиліта 'aplay' не знайдена. Встанови пакет ALSA-utils.")
        return

    # ――― Невідома ОС ―――
    print(f"⚠️ Невідома платформа: {system}")

# ――― Тест напряму ―――
if __name__ == "__main__":
    demo_file = Path("demo.wav")
    if demo_file.exists():
        print(f"▶️ Відтворення '{demo_file}'...")
        play_wav(demo_file)
    else:
        print("❌ demo.wav не знайдено.")
