# -*- coding: utf-8 -*-
import sys
import os
from pathlib import Path
from datetime import datetime

# ---- PYTHONPATH під реальну структуру (…/Lastivka)
PROJECT_ROOT = Path(__file__).resolve().parents[2]  # C:\Lastivka
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ===================== ПЕРВИННИЙ ШАР: manager.MEMORY =====================
# Основна ідея: максимально використовуємо manager.MEMORY (який уже вміє tags),
# а long_term.long_memory залишаємо як резервний fallback там, де можливо.

_MM = None
try:
    from lastivka_core.memory.manager import MEMORY as _MM  # головний API
except Exception as e:
    print("\033[93m[ПОПЕРЕДЖЕННЯ] manager.MEMORY недоступний:\033[0m", e)
    _MM = None

# ---- Індексні операції (для пошуку через index)
try:
    from lastivka_core.memory.index import rebuild, verify, compact, _LAST_INDEX  # type: ignore
except Exception as e:
    print("\033[93m[ПОПЕРЕДЖЕННЯ] Індексні функції з index не знайдені:\033[0m", e)
    def rebuild(): print("[WARN] rebuild(): недоступно"); return None
    def verify(): print("[WARN] verify(): недоступно"); return None
    def compact(): print("[WARN] compact(): недоступно"); return None
    _LAST_INDEX = None  # fallback


# ===================== ДРУГИЙ ШАР: fallback на long_term.long_memory =====================
_LT_OK = True
try:
    from lastivka_core.memory.long_term.long_memory import (
        remember as _lt_remember,
        recall as _lt_recall,
        forget as _lt_forget,
        list_memories as _lt_list_memories,
        recall_from_question as _lt_recall_from_question
    )
except Exception as e:
    print("\033[93m[ПОПЕРЕДЖЕННЯ] Не вдалося імпортувати long_term.long_memory:\033[0m", e)
    _LT_OK = False

    def _lt_remember(*a, **k): print("[WARN] long_memory.remember(): недоступно"); return None
    def _lt_recall(*a, **k): print("[WARN] long_memory.recall(): недоступно"); return None
    def _lt_forget(*a, **k): print("[WARN] long_memory.forget(): недоступно"); return None
    def _lt_list_memories(*a, **k): print("[WARN] long_memory.list_memories(): недоступно"); return {}
    def _lt_recall_from_question(*a, **k): print("[WARN] long_memory.recall_from_question(): недоступно"); return None


# ===================== ЄДИНИЙ ПУБЛІЧНИЙ ШАР API ДЛЯ CLI =====================
# Ці функції використовує CLI нижче. Вони спершу йдуть через manager.MEMORY,
# а якщо його нема — падають на long_term.long_memory (де можливо).

def remember(key: str, value: str, tone=None, tags=None):
    """
    Збереження з повною підтримкою тегів.
    Головний шлях: manager.MEMORY.add_thought(...).
    Fallback: long_term.long_memory.remember(...).
    """
    if _MM is not None:
        _tone = tone if tone is not None else "нейтральний"
        _tags = [t.strip() for t in (tags or []) if t and str(t).strip()]
        _MM.add_thought(key, value, tone=_tone, tags=_tags)
        return
    # fallback (може не підтримувати tags або tone однаково)
    _lt_remember(key, value, tone=tone, tags=tags)

def recall(key: str):
    if _MM is not None:
        return _MM.get_thoughts_by_key(key)
    return _lt_recall(key)

def forget(key: str):
    if _MM is not None:
        _MM.delete_thoughts_by_key(key)
        return
    _lt_forget(key)

def list_memories(archive: bool = False):
    # archive тут не підтримується в manager — ігноруємо прапорець для сумісності
    if _MM is not None:
        return _MM.get_all_memory()
    return _lt_list_memories(archive=archive) if _LT_OK else {}

def recall_from_question(question: str):
    """
    Спроба семантичної відповіді:
    1) Якщо є manager — використовуємо smart_search як «семантичний» шар (top-N).
    2) Якщо нема — fallback на long_term.recall_from_question (якщо доступний).
    """
    if _MM is not None:
        try:
            # Повертаємо список записів, як очікує існуючий CLI
            ranked = _MM.smart_search(question, limit=5)
            # smart_search повертає [{...,"key","score",...}]; сумісно з рештою CLI
            return ranked
        except Exception as e:
            print("\033[93m[ПОПЕРЕДЖЕННЯ] smart_search недоступний, пробую fallback:\033[0m", e)
    return _lt_recall_from_question(question)


# ---------------- Утиліти виводу ----------------
def clear_screen(): os.system('cls' if os.name == 'nt' else 'clear')

def show_menu():
    print("\033[96m\n🔹 LASTIVKA MEMORY CLI\033[0m")
    print("1. ➕ Додати нову пам’ять")
    print("2. 🔍 Знайти пам’ять за ключем (recall)")
    print("3. 🤔 Ask (семантичне запитання до пам’яті)")
    print("4. 📂 Переглянути всю пам’ять")
    print("5. ❌ Видалити пам’ять")
    print("6. 🗄 Переглянути архівовану пам’ять")
    print("7. 🧱 Rebuild індексів")
    print("8. 🔎 Verify індексів")
    print("9. 🧹 Compact індексів")
    print("I. ✍️  Insert (швидке додавання)")
    print("S. 🔎  Search (через індекс)")
    print("T. 🏷  Пошук за тегом")
    print("Q. 🤔  Ask (через recall_from_question)")
    print("0. 🚪 Вийти")

def _val_text(rec: dict) -> str:
    if not isinstance(rec, dict): return str(rec)
    return rec.get('text') or rec.get('value') or ""

def print_memory_block(memory):
    if isinstance(memory, dict):
        for key, value in memory.items():
            print(f"\n🔹 Ключ: {key}"); _print_value(value)
    else: _print_value(memory)

def _print_value(value):
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                print(f"  🕒 {item.get('timestamp')} | 🎭 {item.get('tone')} | 💬 {_val_text(item)}")
            else: print(f"  - {item}")
    elif isinstance(value, dict):
        print(f"  🕒 {value.get('timestamp')} | 🎭 {value.get('tone')} | 💬 {_val_text(value)}")
    else: print(f"  - {value}")

# ---------------- Підтримка свіжості ----------------
def _parse_ts(ts: str):
    if not ts: return None
    try:
        # підтримка ISO без 'Z'
        return datetime.fromisoformat(ts)
    except Exception:
        # грубий fallback: обрізати 'Z'
        try: return datetime.fromisoformat(ts.replace('Z',''))
        except Exception: return None

def _fresh_bonus(ts: str, weight: float = 15.0) -> float:
    """
    Бонус за свіжість: 0..weight.
    0 днів = +weight; 365+ днів ≈ 0.
    """
    dt = _parse_ts(ts)
    if not dt: return 0.0
    days = max(0.0, (datetime.now() - dt).days)
    factor = max(0.0, 1.0 - min(days, 365.0)/365.0)
    return weight * factor

def _rescore_with_freshness(results, weight: float = 15.0):
    """
    results: [(key, rec:dict, score:float), ...]
    повертає список з додатковим бонусом за свіжість та відсортований за новим score.
    """
    rescored = []
    for key, rec, score in results:
        bonus = _fresh_bonus(rec.get("timestamp", ""), weight)
        rescored.append((key, rec, float(score) + bonus))
    rescored.sort(key=lambda x: x[2], reverse=True)
    return rescored

def _ensure_index():
    global _LAST_INDEX
    if _LAST_INDEX is None:
        try:
            rebuild()
            from lastivka_core.memory.index import _LAST_INDEX as _IDX  # type: ignore
            _LAST_INDEX = _IDX
        except Exception: _LAST_INDEX = None
    return _LAST_INDEX

# ---------------- Парсинг прапорців (ручний) ----------------
def _has(argv, flag): return flag in argv
def _get_after(argv, flag, cast=str, default=None):
    if flag in argv:
        try: return cast(argv[argv.index(flag)+1])
        except Exception: return default
    return default

# ---------------- CLI аргументи ----------------
def run_cli_args(argv):
    if len(argv) < 2: return False
    cmd = argv[1].lower()

    if cmd == "rebuild": rebuild(); return True
    if cmd == "verify": verify(); return True
    if cmd == "compact": compact(); return True

    if cmd == "list":
        data = list_memories()
        print_memory_block(data); return True

    if cmd == "tags":
        # Використання: tags <TAG> [--limit N]
        tag = argv[2] if len(argv) >= 3 and not argv[2].startswith("--") else _get_after(argv, "--tag", str, "")
        if not tag:
            print("Використання: tags <TAG> [--limit N]"); return True
        limit = _get_after(argv, "--limit", int, 50)
        data = list_memories() or {}
        found = []
        t_lower = tag.lower()
        for key, items in data.items():
            for item in (items or []):
                tags = [str(x).lower() for x in (item.get("tags") or [])]
                if t_lower in tags:
                    found.append((key, item))
        if not found:
            print(f"⚠️ Немає спогадів із тегом '{tag}'."); return True
        # сортуємо за свіжістю
        found.sort(key=lambda kv: (_parse_ts(kv[1].get("timestamp","")) or datetime.min), reverse=True)
        print(f"🧩 Спогади з тегом '{tag}':")
        for key, item in found[:limit]:
            ts, tone, text = item.get("timestamp",""), item.get("tone",""), _val_text(item)
            print(f"  {key} | 🕒 {ts} | 🎭 {tone} | 💬 {text}")
        return True

    if cmd == "recall":
        try: key = argv[argv.index("--key")+1]
        except Exception: print("Використання: recall --key <KEY>"); return True
        data = recall(key); print_memory_block({key: data} if data else {}); return True

    if cmd == "remember":
        # remember --key K --value "TEXT" [--tone ТОН] [--tags t1,t2]
        try:
            key = argv[argv.index("--key")+1]; value = argv[argv.index("--value")+1]
        except Exception: print('Використання: remember --key <KEY> --value "<TEXT>" [--tone ТОН] [--tags t1,t2]'); return True
        tone = _get_after(argv, "--tone", str, None)
        tags_csv = _get_after(argv, "--tags", str, "")
        tags = [t.strip() for t in tags_csv.split(",")] if tags_csv else None
        remember(key, value, tone=tone, tags=tags)
        print("✅ Збережено."); return True

    if cmd == "forget":
        try: key = argv[argv.index("--key")+1]
        except Exception: print('Використання: forget --key <KEY>'); return True
        forget(key); print("🧹 Видалено."); return True

    if cmd == "insert":
        # insert "TEXT" [--key KEY] [--tone ТОН] [--tags t1,t2]
        try: text = argv[2]
        except Exception: print('Використання: insert "Текст" [--key KEY] [--tone ТОН] [--tags t1,t2]'); return True
        key = _get_after(argv, "--key", str, "manual/notes")
        tone = _get_after(argv, "--tone", str, None)
        tags_csv = _get_after(argv, "--tags", str, "")
        tags = [t.strip() for t in tags_csv.split(",")] if tags_csv else None
        remember(key, text, tone=tone, tags=tags)
        print(f"✅ Додано до {key!r}: {text!r}"); return True

    if cmd == "search":
        # search "запит" [--limit N] [--debug] [--best] [--no-fresh] [--fresh-w 15]
        try: query = argv[2]
        except Exception: print('Використання: search "запит" [--limit N] [--debug] [--best] [--no-fresh] [--fresh-w 15]'); return True
        limit = _get_after(argv, "--limit", int, 10)
        debug = _has(argv, "--debug")
        best_only = _has(argv, "--best")
        fresh_on = not _has(argv, "--no-fresh")
        fresh_w = _get_after(argv, "--fresh-w", float, 15.0)

        idx = _ensure_index()
        if not idx: print("⚠️ Індекс недоступний."); return True
        results = idx.search(query, limit=max(limit, 1), debug=debug) or []
        if fresh_on: results = _rescore_with_freshness(results, fresh_w)

        if not results: print("🙈 Нічого не знайдено."); return True

        if best_only:
            key, rec, score = results[0]
            ts, tone, text = rec.get("timestamp",""), rec.get("tone",""), _val_text(rec)
            print("🧠 Найкращий збіг:")
            print(f"  [{round(score,1):>4}] {key} | 🕒 {ts} | 🎭 {tone} | 💬 {text}")
            return True

        print("🧠 Знайдено:")
        for key, rec, score in results[:limit]:
            ts, tone, text = rec.get("timestamp",""), rec.get("tone",""), _val_text(rec)
            print(f"  [{round(score,1):>4}] {key} | 🕒 {ts} | 🎭 {tone} | 💬 {text}")
        return True

    if cmd == "ask":
        # ask "запитання" [--limit N] [--best] [--no-fallback] [--no-fresh] [--fresh-w 15]
        try: question = argv[2]
        except Exception: print('Використання: ask "запитання" [--limit N] [--best] [--no-fallback] [--no-fresh] [--fresh-w 15]'); return True
        limit = _get_after(argv, "--limit", int, 5)
        best_only = _has(argv, "--best")
        no_fallback = _has(argv, "--no-fallback")
        fresh_on = not _has(argv, "--no-fresh")
        fresh_w = _get_after(argv, "--fresh-w", float, 15.0)

        res = recall_from_question(question)
        # У випадку manager.smart_search повертається список dict; у випадку LT — dict або список.
        if _MM is not None:
            records = []
            for item in (res or []):
                # item вже містить rec + score; приводимо до уніфікованого вигляду для друку
                rec = dict(item)
                if "key" not in rec and "key_norm" in rec:
                    rec["key"] = rec["key_norm"]
                records.append(rec)
        else:
            records = res if isinstance(res, list) else ([res] if res else [])

        if not records:
            if no_fallback:
                print("⚠️ Не знайдено прямої відповіді (fallback вимкнено)."); return True
            print("⚠️ Не знайдено прямої відповіді. Пробую пошук по індексу...")
            idx = _ensure_index()
            if not idx: print("⚠️ Індекс недоступний."); return True
            results = idx.search(question, limit=max(1, limit))
            if fresh_on: results = _rescore_with_freshness(results, fresh_w)
            if not results: print("❌ Нічого не знайдено навіть у пошуку."); return True

            if best_only:
                key, rec, score = results[0]
                ts, tone, text = rec.get("timestamp",""), rec.get("tone",""), _val_text(rec)
                print("\033[92mНайімовірніша відповідь (через індекс):\033[0m")
                print(f"  [{round(score,1):>4}] {key} | 🕒 {ts} | 🎭 {tone} | 💬 {text}")
                return True

            print("🧠 Можливі збіги:")
            for key, rec, score in results[:limit]:
                ts, tone, text = rec.get("timestamp",""), rec.get("tone",""), _val_text(rec)
                print(f"  [{round(score,1):>4}] {key} | 🕒 {ts} | 🎭 {tone} | 💬 {text}")
            return True

        # Є відповідь зі smart/semantic шляху:
        if best_only:
            best = records[0]
            ts, tone, text = best.get("timestamp",""), best.get("tone",""), _val_text(best)
            key_show = best.get("key_norm") or best.get("key") or "—"
            print("\033[92mНайімовірніша відповідь:\033[0m")
            print(f"  {key_show} | 🕒 {ts} | 🎭 {tone} | 💬 {text}")
            return True

        print("\033[92mВідповіді памʼяті:\033[0m")
        for item in records[:limit]:
            ts, tone, text = item.get("timestamp",""), item.get("tone",""), _val_text(item)
            key_show = item.get("key_norm") or item.get("key") or "—"
            print(f"  {key_show} | 🕒 {ts} | 🎭 {tone} | 💬 {text}")
        return True

    print("Команди: rebuild | verify | compact | list | tags <TAG> [--limit N] | recall --key K | "
          "remember --key K --value \"TEXT\" [--tone T] [--tags t1,t2] | forget --key K | "
          "insert \"TEXT\" [--key K] [--tone T] [--tags t1,t2] | "
          "search \"TEXT\" [--limit N] [--debug] [--best] [--no-fresh] [--fresh-w 15] | "
          "ask \"TEXT\" [--limit N] [--best] [--no-fallback] [--no-fresh] [--fresh-w 15]")
    return True


# ---------------- Інтерактив ----------------
def run_interactive():
    while True:
        clear_screen(); show_menu()
        try: choice = input("\n🔸 Вибери опцію:\033[93m ").strip()
        except EOFError: print("\n[INFO] Вихід (stdin недоступний)."); break

        if choice == "1":
            key = input("🗝 Ключ: ").strip()
            value = input("💬 Зміст: ").strip()
            tone = input("🎭 Тон: ").strip() or None
            tags_csv = input("🏷  Теги (через кому, Enter=нема): ").strip()
            tags = [t.strip() for t in tags_csv.split(",")] if tags_csv else None
            remember(key, value, tone=tone, tags=tags)
            input("\033[92m✅ Збережено. Enter...\033[0m")

        elif choice == "2":
            key = input("🗝 Ключ: ").strip()
            result = recall(key); print("\033[92m🔍 Результат:\033[0m")
            print_memory_block({key: result}) if result else print("⚠️ Не знайдено.")
            input("\nEnter...")

        elif choice == "3" or choice.upper() == "Q":
            question = input("🤔 Питання: ").strip()
            res = recall_from_question(question)
            if _MM is not None:
                records = []
                for item in (res or []):
                    rec = dict(item)
                    if "key" not in rec and "key_norm" in rec:
                        rec["key"] = rec["key_norm"]
                    records.append(rec)
            else:
                records = res if isinstance(res, list) else ([res] if res else [])
            if records:
                best = records[0]
                print("\033[92mНайімовірніша відповідь:\033[0m")
                print_memory_block(best)
                if len(records) > 1:
                    print("\nАльтернативи:")
                    for alt in records[1:6]:
                        text = (_val_text(alt))[:160]
                        ts, tone = alt.get("timestamp",""), alt.get("tone","")
                        print(f"  • {text} {'| 🕒 '+ts if ts else ''} {'| 🎭 '+tone if tone else ''}")
            else:
                print("⚠️ Не знайдено. Пробую індекс...")
                idx = _ensure_index()
                if idx:
                    results = _rescore_with_freshness(idx.search(question, limit=10), 15.0)
                    if results:
                        top_key, top_rec, top_score = results[0]
                        print("\033[92mНайімовірніша відповідь (через індекс):\033[0m"); print_memory_block(top_rec)
                        if len(results) > 1:
                            print("\nАльтернативи:")
                            for key, rec, score in results[1:6]:
                                ts, tone, text = rec.get("timestamp",""), rec.get("tone",""), _val_text(rec)[:160]
                                print(f"  [{round(score,1)}] {key} | 💬 {text} {'| 🕒 '+ts if ts else ''} {'| 🎭 '+tone if tone else ''}")
                    else: print("❌ Нічого не знайдено.")
            input("\nEnter...")

        elif choice == "4":
            memory = list_memories()
            print("\n📚 Уся пам’ять:" if memory else "\n📭 Пам’ять пуста."); print_memory_block(memory) if memory else None
            input("\nEnter...")

        elif choice == "5":
            forget(input("🗑 Ключ: ").strip())
            input("\033[92m🧹 Видалено. Enter...\033[0m")

        elif choice == "6":
            archive = list_memories(archive=True)
            print("\n📦 Архівована памʼять:" if archive else "\n🗃 Архів порожній."); print_memory_block(archive) if archive else None
            input("\nEnter...")

        elif choice == "7": rebuild(); input("\n✅ Rebuild. Enter...")
        elif choice == "8": verify(); input("\n✅ Verify. Enter...")
        elif choice == "9": compact(); input("\n✅ Compact. Enter...")

        elif choice.upper() == "I":
            text = input("✍️ Текст: ").strip()
            key = input("🗝 Ключ (Enter=manual/notes): ").strip() or "manual/notes"
            tone = input("🎭 Тон: ").strip() or None
            tags_csv = input("🏷  Теги (через кому, Enter=нема): ").strip()
            tags = [t.strip() for t in tags_csv.split(",")] if tags_csv else None
            remember(key, text, tone=tone, tags=tags)
            input("\033[92m✅ Додано. Enter...\033[0m")

        elif choice.upper() == "S":
            query = input("🔎 Запит: ").strip(); idx = _ensure_index()
            if idx:
                results = _rescore_with_freshness(idx.search(query, limit=20), 15.0)
                if results:
                    print("🧠 Знайдено:")
                    for key, rec, score in results:
                        ts, tone, text = rec.get("timestamp",""), rec.get("tone",""), _val_text(rec)
                        print(f"  [{round(score,1):>4}] {key} | 🕒 {ts} | 🎭 {tone} | 💬 {text}")
                else: print("🙈 Нічого не знайдено.")
            else: print("⚠️ Індекс недоступний.")
            input("\nEnter...")

        elif choice.upper() == "T":
            tag = input("🏷  Тег: ").strip().lower()
            data = list_memories() or {}
            found = []
            for key, items in data.items():
                for item in (items or []):
                    tags = [str(x).lower() for x in (item.get("tags") or [])]
                    if tag in tags:
                        found.append((key, item))
            if not found:
                print(f"⚠️ Немає спогадів із тегом '{tag}'.")
            else:
                found.sort(key=lambda kv: (_parse_ts(kv[1].get("timestamp","")) or datetime.min), reverse=True)
                print(f"🧩 Спогади з тегом '{tag}':")
                for key, item in found[:50]:
                    ts, tone, text = item.get("timestamp",""), item.get("tone",""), _val_text(item)
                    print(f"  {key} | 🕒 {ts} | 🎭 {tone} | 💬 {text}")
            input("\nEnter...")

        elif choice == "0": print("\nДо зустрічі! 👋"); break
        else: input("⚠️ Невірна опція. Enter...")


def main():
    if run_cli_args(sys.argv): return
    run_interactive()

if __name__ == "__main__": main()
