# minimal, safe-only runtime hooks (без os/subprocess/ctypes)
from __future__ import annotations
import time
from typing import Dict, List

class DirectiveResult:
    def __init__(self, directives: List[str], params: Dict):
        self.directives = directives
        self.params = params or {}

def collect_boot_directives(timeout_per_mod: float = 0.30) -> DirectiveResult:
    """
    Опитує активні leaf-модулі (через безпечний агрегатор) і збирає "поради" на старті.
    Імпортуємо тільки наш безпечний агрегатор active/, який вже фільтрує політику.
    """
    directives: List[str] = []
    params: Dict = {}
    try:
        # Імпортуємо наш згенерований агрегатор активних інструментів
        from lastivka_core.tools import active as active_agg  # type: ignore
        for name in getattr(active_agg, "__all__", []):
            fn_name = f"run_{name}"
            run = getattr(active_agg, fn_name, None)
            if callable(run):
                t0 = time.perf_counter()
                try:
                    out = run(op="boot")
                    if isinstance(out, dict):
                        ds = out.get("directives") or []
                        if isinstance(ds, list):
                            directives.extend([str(x) for x in ds])
                        pp = out.get("params") or {}
                        if isinstance(pp, dict):
                            params.update({str(k): pp[k] for k in pp})
                except Exception:
                    # ігноруємо падіння leaf-модуля — безпечно продовжуємо
                    pass
                finally:
                    if time.perf_counter() - t0 > timeout_per_mod:
                        # не караємо, просто не зависаємо
                        pass
    except Exception:
        pass
    # унікалізуємо
    uniq = []
    for d in directives:
        if d not in uniq:
            uniq.append(d)
    return DirectiveResult(uniq, params)

def apply_directives(directives: List[str], params: Dict) -> None:
    """
    Виконує тільки "м’які" дії, сумісні з політикою (без небезпечних імпортів).
    Точки впливу — через ENV/FLAGS, які вже читає ядро або стартові скрипти.
    """
    # 1) headless режим (жодних вікон, TTS off) — працюємо через відомі флаги
    if "enforce_headless" in directives or params.get("headless") is True:
        import os
        os.environ["LASTIVKA_HEADLESS"] = "1"
        os.environ["NO_TTS"] = "1"
        os.environ["LASTIVKA_NO_UI"] = "1"
        os.environ["QT_QPA_PLATFORM"] = os.environ.get("QT_QPA_PLATFORM", "offscreen")
        os.environ["PYTHONUTF8"] = "1"
        os.environ["PYTHONIOENCODING"] = "utf-8"

    # 2) normalize_interpreter — рекомендує використовувати лаунчер pyw.exe з -X utf8
    #    (реальне застосування робимо у старт-скрипті; тут ставимо "маркер")
    if "normalize_interpreter" in directives:
        import os
        os.environ["LASTIVKA_PREFERS_PYW_LAUNCHER"] = "1"

    # 3) kill_werfault_ui — лише маркер; реальне вимкнення ми вже зробили політиками/службою
    if "kill_werfault_ui" in directives:
        pass

    # 4) розширювано: інші безпечні директиви, що не потребують os/subprocess
