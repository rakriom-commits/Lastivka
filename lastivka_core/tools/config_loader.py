# tools/config_loader.py
import json
from pathlib import Path

# Корінь проєкту: C:\Lastivka\lastivka_core
BASE_DIR = Path(__file__).resolve().parent.parent

def load_json_config(path: str):
    """
    Безпечно завантажує JSON:
    - Відносні шляхи резольвимо від BASE_DIR (а не від поточного робочого каталогу).
    - Підтримує як 'config/file.json', так і 'C:\\...\\file.json'.
    """
    p = Path(path)
    if not p.is_absolute():
        p = BASE_DIR / p  # резолвимо від кореня проєкту
    p = p.resolve()

    if not p.exists():
        raise FileNotFoundError(f"[ERROR] Config file not found: {p}")

    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)
