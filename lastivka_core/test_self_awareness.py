import json
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent / "self_awareness_config.json"

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    self_awareness = json.load(f)

print("Ластівка про себе:", self_awareness["identity_awareness"]["i_am"])