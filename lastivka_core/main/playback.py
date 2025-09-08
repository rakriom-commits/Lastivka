from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

__all__ = ["play_wav"]

def play_wav(path: str | Path, *, block: bool = True) -> None:
    """
    Відтворює WAV-файл за заданим шляхом.

    :param path: Шлях до WAV-файлу
    :param block: True — блокуючий режим, False — відтворення у фоновому режимі
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"[ПОМИЛКА] Файл не знайдено: {p}")

    system = sys.platform

    # --- Windows ---
    if system == "win32":
        try:
            import winsound
            flags = winsound.SND_FILENAME | (0 if block else winsound.SND_ASYNC)
            winsound.PlaySound(str(p), flags)
            return
        except ModuleNotFoundError:
            pass

        try:
            os.startfile(p)
        except Exception as e:
            print(f"[ПОМИЛКА] Не вдалося запустити файл: {e}")
        return

    # --- macOS ---
    if system == "darwin":
        cmd = ["afplay", str(p)]
        (subprocess.run if block else subprocess.Popen)(cmd)
        return

    # --- Linux / WSL ---
    if system.startswith("linux"):
        cmd = ["aplay", str(p)]
        try:
            (subprocess.run if block else subprocess.Popen)(cmd)
        except FileNotFoundError:
            print("[ПОМИЛКА] Не знайдено 'aplay'. Встанови пакет ALSA-utils.")
        return

    # --- Інші платформи ---
    print(f"[ПОМИЛКА] Невідома платформа: {system}")

# --- Демонстрація ---
if __name__ == "__main__":
    demo_file = Path("demo.wav")
    if demo_file.exists():
        print(f"🔊 Відтворюється '{demo_file}'...")
        play_wav(demo_file)
    else:
        print("📂 demo.wav не знайдено.")
