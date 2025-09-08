# config_loader.py
import json
from pathlib import Path

# Базова директорія проєкту (lastivka_core)
BASE_DIR = Path(__file__).resolve().parent.parent

# Завантаження JSON-конфігурації з відносного або абсолютного шляху
def load_json_config(path: str):
    """
    Завантажує JSON-файл конфігурації.
    - Якщо шлях відносний — шукає відносно BASE_DIR (lastivka_core).
    - Якщо шлях абсолютний — використовує напряму.
    """
    p = Path(path)
    if not p.is_absolute():
        p = BASE_DIR / p
    p = p.resolve()

    if not p.exists():
        raise FileNotFoundError(f"[ConfigLoader] Config file not found: {p}")

    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)