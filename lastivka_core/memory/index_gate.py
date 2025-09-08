# C:\Lastivka\lastivka_core\memory\index_gate.py
from __future__ import annotations
import sys
from pathlib import Path
from lastivka_core.core.gate import parse_mode, open_report, manifest_path, apply_change

SCRIPT = "memory_index"
ROOT = Path(r"C:\Lastivka\lastivka_core")
INDICES = ROOT.parent / "indices"

def main(argv=None) -> int:
    dry, app = parse_mode(argv)
    mf = manifest_path()
    w, rp = open_report(SCRIPT)
    try:
        # приклад: створення/оновлення індексів (поки що плейсхолдер)
        idx = INDICES / "memory.idx"
        if dry:
            apply_change(SCRIPT, "UPDATE", idx, None, True, mf, w)
        else:
            INDICES.mkdir(parents=True, exist_ok=True)
            idx.write_text("index: placeholder\n", encoding="utf-8")
            apply_change(SCRIPT, "UPDATE", idx, None, False, mf, w)
        w.write(f"[INFO] memory index ok (dry-run: {str(dry).lower()})\n"); w.flush()
        return 0
    except Exception as e:
        w.write(f"[FAIL] memory index error: {e}\n"); w.flush()
        return 2
    finally:
        w.close()

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
