from pathlib import Path
import time
import torch
import soundfile as sf
from playback import play_wav
from accent_corrector import correct_accents  # 🔤 інтеграція наголосів

# 📁 Папки
BASE_DIR = Path(__file__).resolve().parent
AUDIO_DIR = BASE_DIR / "audio"
OUTPUT_DIR = AUDIO_DIR / "output"
CACHE_DIR = AUDIO_DIR / "cache"

# 🧱 Створення директорій
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 🎙️ Завантаження Silero-моделі
_SILERO_ARGS = {
    "repo_or_dir": "snakers4/silero-models",
    "model": "silero_tts",
    "language": "ua",
    "speaker": "v4_ua",
    "cache_dir": CACHE_DIR.as_posix(),
}

try:
    model, _ = torch.hub.load(**_SILERO_ARGS)
except Exception as e:
    raise RuntimeError(f"Не вдалося завантажити модель озвучення: {e}")

# 🗣️ Синтез мовлення
def synth(text: str, *, speaker: str = "mykyta", sr: int = 48_000, volume_boost: float = 1.5) -> Path:
    text = correct_accents(text)  # 🧠 Корекція наголосів
    wav = model.apply_tts(text=text, speaker=speaker, sample_rate=sr)
    wav = wav * volume_boost
    wav = torch.clamp(wav, -1.0, 1.0)

    outfile = OUTPUT_DIR / f"reflection_{int(time.time())}.wav"
    sf.write(outfile, wav, sr)
    return outfile

__all__ = ["synth", "play_wav"]