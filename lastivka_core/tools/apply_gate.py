# -*- coding: utf-8 -*-
from __future__ import annotations
import os, sys, time, hashlib, pathlib
from dataclasses import dataclass

ROOT = pathlib.Path(r"C:\Lastivka")
FLAG = ROOT / "archive" / "core_clean_20250909_104829" / "C_Lastivka" / "ALLOW_APPLY.flag"
OUTBOX = ROOT / "lastivka_core" / "tools" / "outbox"
OUTBOX.mkdir(parents=True, exist_ok=True)

@dataclass
class GateResult:
    apply: bool
    mode: str
    code: int  # 0 ok, 1 warn (dry-run), 2 fail

def gate_from_argv(argv: list[str]) -> GateResult:
    args = set(a.lower() for a in argv[1:])
    want_apply = "--apply" in args
    want_dry = "--dry-run" in args
    if want_apply and want_dry:
        print("[gate] не можна одночасно --apply і --dry-run", file=sys.stderr)
        return GateResult(False, "fail", 2)

    flag_present = FLAG.exists()
    if want_apply and not flag_present:
        print("[gate] ALLOW_APPLY.flag відсутній → переведено у dry-run.")
        return GateResult(False, "dry-run", 1)

    if want_apply and flag_present:
        return GateResult(True, "apply", 0)

    # за замовчуванням — dry-run
    return GateResult(False, "dry-run", 0)

def stamp_path(prefix: str) -> pathlib.Path:
    ts = time.strftime("%Y%m%d_%H%M%S")
    return OUTBOX / f"{prefix}_{ts}.txt"

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()
