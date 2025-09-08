# C:\Lastivka\lastivka_core\scripts\daily_report_gate.py
from __future__ import annotations
import sys
from pathlib import Path
from lastivka_core.core.gate import parse_mode, open_report, manifest_path, apply_change

SCRIPT = "daily_report"
ROOT = Path(r"C:\Lastivka\lastivka_core")
OUT = ROOT / "tools" / "outbox"

def main(argv=None) -> int:
    dry, app = parse_mode(argv)
    mf = manifest_path()
    w, rp = open_report(SCRIPT)
    try:
        # приклад: формування текстового звіту (симуляція/запис)
        report_txt = OUT / "daily_report_generated.txt"
        if dry:
            apply_change(SCRIPT, "UPDATE", report_txt, None, True, mf, w)
        else:
            report_txt.parent.mkdir(parents=True, exist_ok=True)
            report_txt.write_text("Lastivka daily report (placeholder)\n", encoding="utf-8")
            apply_change(SCRIPT, "UPDATE", report_txt, None, False, mf, w)
        w.write(f"[INFO] daily_report complete (dry-run: {str(dry).lower()})\n"); w.flush()
        return 0
    except Exception as e:
        w.write(f"[FAIL] daily_report error: {e}\n"); w.flush()
        return 2
    finally:
        w.close()

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
