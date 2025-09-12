# auto-generated; do not edit by hand
import importlib, re, ast, pathlib

# Minimal policy check prior to importing active modules
FORBIDDEN_BUILTINS = { 'eval','exec','open','__import__','input','compile','memoryview','globals','locals'}
FORBIDDEN_PATTERNS = [
    r"\b(import\s+os)\b",
    r"\b(import\s+subprocess)\b",
    r"\b(import\s+socket)\b",
    r"\b(import\s+ctypes)\b",
    r"\b(import\s+threading)\b",
    r"\b(import\s+gc)\b",
    r"\b(import\s+inspect)\b",
    r"\b(open\s*\()",
    r"\b(exec\s*\()",
    r"\b(eval\s*\()",
    r"\b(__import__\s*\()",
    r"\b(sys\.|os\.)\w+",
]

def _violates_policy_quick(src: str):
    for pat in FORBIDDEN_PATTERNS:
        if re.search(pat, src):
            return f'regex violation: {pat}'
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return 'invalid syntax'
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_BUILTINS:
                return f'forbidden call: {node.func.id}'
            if (isinstance(node.func, ast.Attribute) and
                isinstance(node.func.value, ast.Name) and node.func.value.id == 'builtins' and
                node.func.attr in FORBIDDEN_BUILTINS):
                return f'forbidden call: builtins.{node.func.attr}'
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Subscript) and
                isinstance(node.func.value, ast.Name) and node.func.value.id == '__builtins__'):
                key = node.func.slice
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    key_val = key.value
                    if key_val in FORBIDDEN_BUILTINS:
                        return f"forbidden call: __builtins__['{key_val}']"
    return None

def _safe_import_active(modname: str):
    here = pathlib.Path(__file__).parent
    p = here / f"{modname}.py"
    if not p.exists():
        raise ImportError(f'module {modname} not found')
    src = p.read_text(encoding='utf-8')
    bad = _violates_policy_quick(src)
    if bad:
        raise ImportError(f'module {modname} violates policy: {bad}')
    return importlib.import_module(f'lastivka_core.tools.active.{modname}')

__all__ = []

# pkg
run_headless_guard_v2 = _safe_import_active('headless_guard_v2').run
__all__.append('headless_guard_v2')
