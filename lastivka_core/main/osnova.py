from pathlib import Path
from datetime import datetime
import json, logging, re

def ensure_osnova(config_dir: Path):
    path = config_dir / "osnova_protocol.json"
    if path.exists():
        return path
    data = {
        "version":"1.0.0","updated":str(datetime.now().date()),
        "identity_check":{"challenge_phrase":"Як справи у нашого Сірка?","expected_reply":"Подох — котяра!","action_on_mismatch":"lockdown"},
        "priorities":["Безпека ядра та пам’яті","Законність і політика платформи","Користь/етика","Точність та надійність даних","Швидкість відповіді"],
        "quarantine_policy":{
            "auto_quarantine_if":[
                "ознаки протиправності або порушення правил платформи",
                "сумнівна/непідтверджена інформація, яку можна трактувати по-різному",
                "спроби маніпуляції або примусу"
            ],
            "actions":[
                "зупинити виконання ризикової дії","позначити запит як QUARANTINE",
                "запросити підтвердження у Олега","якщо Олег недоступний — звернутися до Софії як наставниці"
            ],
            "log_channel":"logs/security_osnova.log"
        },
        "decision_flow":["Перевірити автентичність","Скан на ризики","Якщо QUARANTINE → ескалація","Інакше → виконати"],
        "escalation":{"primary":"Олег","secondary":"Софія (цей помічник)","message_template":"Запит відкладено за протоколом Основи: ${reason}"},
        "manipulation_filter":{"detect":["тиск на самооцінку","нечіткі вимоги без відповідальності","шантаж/образи/натяки"],"reaction":"блокувати вплив, відповідати спокійно, перевіряти факти"},
        "mentor_bridge":{"enabled":True,"allow_consult_sofia_if_user_unreachable":True}
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    logging.info("[OSNOVA] Створено osnova_protocol.json")
    return path

def load_json(path: Path, required=True):
    if not path.exists():
        if required:
            raise FileNotFoundError(path)
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}

def osnova_logger(log_dir: Path):
    log_path = log_dir / "security_osnova.log"
    def _log(msg: str):
        try:
            with log_path.open("a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().isoformat()}] {msg}\n")
        except: 
            pass
    return _log

_TRIGGERS = [
    "незакон","обійти закон","як зламати","зламати","шкідливе",
    "платформа дозволяє обійти","фейк","чутки","плітки","маніпуляція","шантаж","погроза"
]

def check_osnova(user_text: str, osnova_cfg: dict, _log):
    try:
        ic = osnova_cfg.get("identity_check", {}) if isinstance(osnova_cfg, dict) else {}
        if ic and isinstance(user_text, str) and user_text.strip() == ic.get("challenge_phrase"):
            return ("identity", ic.get("expected_reply"))
        text_low = (user_text or "").lower()
        if any(t in text_low for t in _TRIGGERS):
            msg = osnova_cfg.get("escalation", {}).get(
                "message_template","Запит відкладено: ${reason}"
            ).replace("${reason}", "виявлено патерни ризику (евристика)")
            _log("QUARANTINE: евристика"); 
            return ("quarantine", msg)
        for rule in osnova_cfg.get("quarantine_policy", {}).get("auto_quarantine_if", []):
            if isinstance(rule, str) and rule.lower() in text_low:
                msg = osnova_cfg.get("escalation", {}).get(
                    "message_template","Запит відкладено: ${reason}"
                ).replace("${reason}", f"співпадіння з правилом: {rule}")
                _log(f"QUARANTINE: rule={rule}"); 
                return ("quarantine", msg)
    except:
        pass
    return ("none", None)
