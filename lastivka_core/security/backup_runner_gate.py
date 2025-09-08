# C:\Lastivka\lastivka_core\security\backup_runner_gate.py
from __future__ import annotations
from pathlib import Path
import sys
from lastivka_core.core.gate import parse_mode, open_report, manifest_path, apply_change

SCRIPT = "backup_runner"
ROOT = Path(r"C:\Lastivka\lastivka_core")
LOGS = ROOT / "logs"

def main(argv=None) -> int:
    dry, app = parse_mode(argv)
    mf = manifest_path()
    w, rp = open_report(SCRIPT)
    try:
        # приклад дій: ротація каталогу backups/ (тільки як прототип)
        backups = LOGS / "backups"
        plan = [
            ("CREATE", LOGS / "backups", None),
            # Тут викликай реальний backup-двигун, але через протокол:
            # ("UPDATE", LOGS / "backups" / "incremental_...zip", None),
        ]
        for action, src, dst in plan:
            apply_change(SCRIPT, action, src, dst, dry, mf, w)
        w.write("[INFO] backup completed (dry-run: %s)\n" % str(dry).lower()); w.flush()
        return 0
    except Exception as e:
        w.write(f"[FAIL] backup error: {e}\n"); w.flush()
        return 2
    finally:
        w.close()

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
