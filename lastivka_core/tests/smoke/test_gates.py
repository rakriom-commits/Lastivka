from pathlib import Path
import subprocess, sys

ROOT = Path(r"C:\Lastivka")
CORE = ROOT / "lastivka_core"
OUTBOX = CORE / "tools" / "outbox"
FLAG = CORE / "ALLOW_APPLY.flag"

def run_py(mod):
    return subprocess.run(["py", "-3", "-m", mod, "--apply"], capture_output=True, text=True)

def test_apply_without_flag_forces_dry_run():
    if FLAG.exists():
        FLAG.unlink()
    OUTBOX.mkdir(parents=True, exist_ok=True)

    # кожен runner має проігнорувати --apply без прапорця і зробити dry-run
    mods = [
        "lastivka_core.security.backup_runner_gate",
        "lastivka_core.scripts.daily_report_gate",
        "lastivka_core.memory.index_gate",
    ]
    for m in mods:
        r = run_py(m)
        assert r.returncode in (0,2)
    # перевіряємо, що outbox наповнився звітами
    assert any(p.suffix == ".txt" for p in OUTBOX.glob("*.txt"))

def test_apply_with_flag_writes():
    FLAG.write_text("ok", encoding="utf-8")
    try:
        mods = [
            "lastivka_core.scripts.daily_report_gate",
            "lastivka_core.memory.index_gate",
        ]
        for m in mods:
            r = run_py(m)
            assert r.returncode in (0,2)
        # файл daily_report_generated.txt або memory.idx має існувати
        assert (CORE / "tools" / "outbox" / "daily_report_generated.txt").exists() \
            or (ROOT / "indices" / "memory.idx").exists()
    finally:
        FLAG.unlink(missing_ok=True)
