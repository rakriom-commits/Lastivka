# -*- coding: utf-8 -*-
# lastivka_go2_full_social_security_assistant.py
# Ластівка на базі Unitree Go2 Pro: NLP + невербальні + простір + Bluetooth-шепіт + платформні дії

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import re, math, time

# --------- Optional deps ----------
try:
    import torch, torch.nn as nn
    TORCH_OK = True
except Exception:
    TORCH_OK = False

try:
    import pyttsx3
    TTS_OK = True
except Exception:
    TTS_OK = False

import matplotlib.pyplot as plt

def whisper_stub(text: str):
    print(f"[Bluetooth Whisper]: {text}")

Vec2 = Tuple[float, float]

# ========= Утиліти =========
def l2(a: Vec2, b: Vec2) -> float:
    return math.hypot(a[0]-b[0], a[1]-b[1])

def dot(a: Vec2, b: Vec2) -> float:
    return a[0]*b[0] + a[1]*b[1]

def norm(v: Vec2) -> Vec2:
    n = math.hypot(v[0], v[1]) or 1e-6
    return (v[0]/n, v[1]/n)

def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))

# ========= Дані спостережень =========
@dataclass
class Observation:
    ts: float
    channel: str  # "text" | "audio" | "video" | "behavior" | "lidar" | "nonverbal"
    content: Dict[str, Any]
    context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PoseKeypoints:
    points: Dict[str, Optional[Vec2]] = field(default_factory=dict)

@dataclass
class PersonObs:
    track_id: int
    ts: float
    centroid: Vec2
    velocity: Vec2
    bbox_xywh: Optional[Tuple[float, float, float, float]] = None
    pose: PoseKeypoints = field(default_factory=PoseKeypoints)
    object_tags: List[str] = field(default_factory=list)
    hand_visible: Dict[str, bool] = field(default_factory=lambda: {"left": True, "right": True})
    facial_micro: Dict[str, float] = field(default_factory=dict)

@dataclass
class EgoState:
    ts: float
    position_px: Vec2
    forward_vec: Vec2
    meters_per_pixel: float = 1 / 400.0

@dataclass
class EnvironmentContext:
    kind: str = "social"  # "indoor" | "outdoor" | "business" | "social"
    cultural_context: str = "universal"  # "eastern_europe" тощо
    exits_px: List[Vec2] = field(default_factory=list)
    choke_points_px: List[Vec2] = field(default_factory=list)
    light_level: float = 0.7
    obstacles: List[Tuple[Vec2, float]] = field(default_factory=list)

@dataclass
class CrowdSnapshot:
    density_m2: float = 0.5
    flow_vec: Vec2 = (0.0, 0.0)
    counter_flow_ratio: float = 0.0
    crush_sources: int = 0

# ========= Адаптер платформи Unitree Go2 =========
class Go2Platform:
    """
    Стаб-адаптер. Замінити тіла методів на реальні виклики:
      - ROS2: publish на /go2/cmd_vel, /go2/pose, /go2/led, /go2/beep, читати /go2/state
      - SDK: UDP пакети Unitree або Python bindings (якщо є)
    """
    def __init__(self, dry_run: bool = True):
        self.dry = dry_run

    # ---- Сенсори / статус ----
    def read_status(self) -> Dict[str, float]:
        return {"battery": 0.88, "temp_core": 42.0, "imu_ok": 1.0}

    # ---- Сигнали уваги ----
    def led(self, color: str = "cyan", blink_hz: float = 0.0):
        self._log(f"LED {color} blink={blink_hz}Hz")

    def beep(self, pattern: str = "short"):
        self._log(f"BEEP pattern={pattern}")

    def vibrate_tail(self, strength: float = 0.4, ms: int = 300):
        self._log(f"TAIL VIB strength={strength} dur={ms}ms")

    # ---- Рухові примітиви ----
    def step_side(self, direction: str = "left", meters: float = 0.4, speed: float = 0.4):
        self._log(f"STEP_SIDE dir={direction} d={meters} v={speed}")

    def back_off(self, meters: float = 0.8, speed: float = 0.5):
        self._log(f"BACK_OFF d={meters} v={speed}")

    def arc_move(self, radius_m: float = 0.8, angle_deg: float = 45, speed: float = 0.4):
        self._log(f"ARC_MOVE R={radius_m} ang={angle_deg} v={speed}")

    def face_exit(self):
        self._log("YAW toward nearest exit (stub)")

    # ---- Пози ----
    def sit(self):
        self._log("POSE: SIT")

    def lie_down(self):
        self._log("POSE: LIE")

    def brace(self):
        self._log("POSE: BRACE (lower CoM)")

    # ---- Запис ----
    def start_record(self): self._log("REC start")
    def stop_record(self):  self._log("REC stop")

    def _log(self, msg: str):
        if self.dry:
            print(f"[Go2] {msg}")
        # else: відправити у реальний лог/телеметрію

# ========= Вербальні патерни (NLP + аудіострес) =========
@dataclass
class VerbalScore:
    aggression: float
    threat: float
    coercion: float
    deception_cues: float
    exaggeration: float
    hesitation: float
    confusion: float
    stress: float
    scam_urgency: float
    scam_offer: float
    scam_authority: float
    vak_visual: float
    vak_auditory: float
    vak_kinesthetic: float
    voice_stress: float
    notes: List[str]

class VerbalPatterns:
    RE_THREAT = re.compile(r"\b(вб[’']ю|убью|знищу|підірву|спалю|поламаю|зроблю боляче|карате?)\b", re.I|re.U)
    RE_AGGR = re.compile(r"\b(ненавиджу|скоти|покара(ю|ти)|смерть вам|мразі)\b", re.I|re.U)
    RE_COERC = re.compile(r"\b(наказали|змушують|контролюють|погрожують|маю наказ|мусиш)\b", re.I|re.U)
    RE_EXAG = re.compile(r"\b(завжди|ніколи|усі|кожен|абсолютно|сто відсотків)\b", re.I|re.U)
    RE_HES  = re.compile(r"\b(ну|якось|можливо|мабуть|типу|нібито|ем|ее)\b", re.I|re.U)
    RE_CONF = re.compile(r"\b(я заплут(авс[яі]|алась)|не розумію|що відбувається|де я)\b", re.I|re.U)
    RE_DECP = re.compile(r"\b(чесно кажучи|скажу правду|як є)\b", re.I|re.U)
    RE_SCAM_URG   = re.compile(r"\b(терміново|швидко|зараз|не зволікай|останній шанс)\b", re.I|re.U)
    RE_SCAM_OFFER = re.compile(r"\b(виграш|безкоштовно|акція|подарунок|гарантовано|мільйон)\b", re.I|re.U)
    RE_SCAM_AUTH  = re.compile(r"\b(від банку|поліція|уряд|служба безпеки|податкова)\b", re.I|re.U)
    V_VIS = re.compile(r"\b(бачу|виглядає|картина|світло|кольор\w*)\b", re.I|re.U)
    V_AUD = re.compile(r"\b(чути|звучить|слухаю|голос|тон|тиша\w*|відлуння|шум)\b", re.I|re.U)
    V_KIN = re.compile(r"\b(відчуваю|тисне|тепло|холод|торка\w*|важко|легко|болить)\b", re.I|re.U)

    @staticmethod
    def analyze(text: str, intensifiers: float = 0.0, audio_features: Optional[Dict[str, float]] = None) -> VerbalScore:
        t = (text or "").lower()
        def b(rex): return 1.0 if rex.search(t) else 0.0
        def f(rex, cap=3.0): return min(1.0, len(rex.findall(t)) / cap)

        threat = b(VerbalPatterns.RE_THREAT)
        aggr   = f(VerbalPatterns.RE_AGGR)
        coerc  = b(VerbalPatterns.RE_COERC)
        exagger= f(VerbalPatterns.RE_EXAG)
        hesit  = f(VerbalPatterns.RE_HES)
        confus = f(VerbalPatterns.RE_CONF)
        decp   = f(VerbalPatterns.RE_DECP, cap=2.0)
        scam_urg   = f(VerbalPatterns.RE_SCAM_URG)
        scam_offer = f(VerbalPatterns.RE_SCAM_OFFER)
        scam_auth  = f(VerbalPatterns.RE_SCAM_AUTH)
        vvis = f(VerbalPatterns.V_VIS)
        vaud = f(VerbalPatterns.V_AUD)
        vkin = f(VerbalPatterns.V_KIN)

        voice_stress = (audio_features or {}).get("pitch_variance", 0.0)
        stress = min(1.0, 0.4*hesit + 0.3*confus + 0.2*intensifiers + 0.1*voice_stress)
        deception_cues = min(1.0, 0.6*exagger + 0.5*decp + 0.3*hesit + 0.2*scam_urg + 0.1*voice_stress)

        notes = []
        if threat: notes.append("вербальна погроза/насильнича риторика")
        if coerc:  notes.append("ознаки примусу")
        if aggr>0: notes.append("агресивна лексика")
        if exagger>0: notes.append("узагальнення/перебільшення")
        if decp>0: notes.append("компенсаторні формули щирості")
        if hesit>0: notes.append("вагання/заповнювачі пауз")
        if confus>0: notes.append("дезорієнтація/заплутаність")
        if scam_urg>0: notes.append("scam urgency")
        if scam_offer>0: notes.append("scam offer")
        if scam_auth>0: notes.append("scam authority")
        if stress>0.5: notes.append("ознаки стресу/cognitive load")
        if voice_stress>0.5: notes.append("voice stress (high pitch variance)")

        return VerbalScore(aggr, threat, coerc, deception_cues, exagger, hesit, confus, stress,
                           scam_urg, scam_offer, scam_auth, vvis, vaud, vkin, voice_stress, notes)

# ========= Текстові евристики =========
class TextHeuristics:
    RE_HESITATION   = re.compile(r"\b(ну|якось|можливо|мабуть|типу|нібито)\b", re.I | re.U)
    RE_INTENSIFIERS = re.compile(r"\b(дуже|надзвичайно|супер|максимально|взагалі-то)\b", re.I | re.U)
    RE_EXAGGERATE   = re.compile(r"\b(завжди|ніколи|усі|кожен|абсолютно)\b", re.I | re.U)
    RE_FANTASY      = re.compile(r"\b(уявімо|припустімо|фантазія|вигадка)\b", re.I | re.U)
    RE_NEGATIONS    = re.compile(r"\b(не|ні)\b", re.I | re.U)
    RE_CONTRADICTION= re.compile(r"(але|проте|однак)", re.I | re.U)
    RE_SCAM_PRESSURE= re.compile(r"\b(не розповідайте|секрет|тільки вам)\b", re.I | re.U)
    V_WORDS = {
        "visual": ["бачу","виглядає","картина","світло","кольор"],
        "auditory": ["чути","звучить","слухаю","голос","тон","тиша"],
        "kinesthetic": ["відчуваю","торка","тяжко","легко","тепло","холод","тисне","рух"],
    }

    @staticmethod
    def analyze_text(s: str) -> Dict[str, float]:
        text = (s or "").lower()
        n_tokens = max(len(re.findall(r"\w+", text, re.U)), 1)
        hes = len(TextHeuristics.RE_HESITATION.findall(text)) / n_tokens
        intens = len(TextHeuristics.RE_INTENSIFIERS.findall(text)) / n_tokens
        exagger = len(TextHeuristics.RE_EXAGGERATE.findall(text)) / n_tokens
        fantasy = len(TextHeuristics.RE_FANTASY.findall(text)) / n_tokens
        neg = len(TextHeuristics.RE_NEGATIONS.findall(text))
        conj = len(TextHeuristics.RE_CONTRADICTION.findall(text))
        scam_press = len(TextHeuristics.RE_SCAM_PRESSURE.findall(text)) / n_tokens
        contradiction_hint = 1.0 if (neg > 0 and conj > 0) else 0.0

        vak_counts = {k: 0 for k in ["visual","auditory","kinesthetic"]}
        for mode, keys in TextHeuristics.V_WORDS.items():
            for kw in keys:
                vak_counts[mode] += len(re.findall(r"\b" + re.escape(kw) + r"\w*\b", text, re.U))
        total_vak = sum(vak_counts.values()) or 1
        vak = {k: v / total_vak for k, v in vak_counts.items()}

        honesty = {
            "sincerity": max(0.0, 1.0 - (intens*2 + exagger*1.5 + contradiction_hint*0.7 + scam_press*1.2)),
            "insincerity": min(1.0, intens*1.2 + exagger*1.0 + contradiction_hint*0.8 + scam_press*1.0),
            "fantasy": min(1.0, fantasy*3.0),
            "exaggeration": min(1.0, exagger*2.5),
        }
        return {
            "hesitation": hes,
            "intensifiers": intens,
            "exaggeration": exagger,
            "fantasy": fantasy,
            "contradiction_hint": contradiction_hint,
            "scam_pressure": scam_press,
            **{f"vak_{k}": v for k, v in vak.items()},
            **{f"honesty_{k}": v for k, v in honesty.items()},
        }

# ========= Facial NLP / AU =========
class AUPredictor(nn.Module if TORCH_OK else object):
    def __init__(self):
        if not TORCH_OK: return
        super().__init__()
        self.linear = nn.Linear(3, 1)
        with torch.no_grad():
            self.linear.weight.data = torch.tensor([[0.4, 0.3, 0.3]])
            self.linear.bias.data = torch.tensor([0.0])
    def forward(self, x):
        return torch.sigmoid(self.linear(x))

class FacialNLP:
    @staticmethod
    def analyze_keypoints(kp: Dict[str, Optional[Vec2]], consent: bool = True, cultural_context: str = "universal") -> Dict[str, float]:
        if not consent:
            return {"error": 1.0}
        notes: List[str] = []

        left_eye, right_eye, nose = kp.get("left_eye"), kp.get("right_eye"), kp.get("nose")
        gaze_aversion = 0.0
        if left_eye and right_eye and nose:
            eye_center = ((left_eye[0] + right_eye[0]) / 2, (left_eye[1] + right_eye[1]) / 2)
            gaze_vec = norm((eye_center[0] - nose[0], eye_center[1] - nose[1]))
            forward_stub = (0, -1)
            align = clamp01((dot(gaze_vec, forward_stub) + 1.0) / 2.0)
            gaze_aversion = 1.0 - align
            gaze_weight = 0.6 if cultural_context == "eastern_europe" else 1.0
            gaze_aversion *= gaze_weight
            if gaze_aversion > 0.6: notes.append("gaze aversion (cultural adj)")

        pupil_dilation = float(kp.get("pupil_estimate", 0.0))
        if pupil_dilation > 0.5: notes.append("pupil dilation")

        left_brow_inner, right_brow_inner = kp.get("left_brow_inner"), kp.get("right_brow_inner")
        brow_raise = 0.0
        if left_brow_inner and right_brow_inner and nose:
            avg_brow_y = (left_brow_inner[1] + right_brow_inner[1]) / 2
            brow_raise = clamp01((nose[1] - avg_brow_y) / 20.0)

        mouth_left, mouth_right = kp.get("mouth_left"), kp.get("mouth_right")
        asym_smile = 0.0
        if mouth_left and mouth_right:
            dist = l2(mouth_left, mouth_right)
            asym = abs(mouth_left[0] - mouth_right[0]) / dist if dist > 0 else 0
            asym_smile = clamp01(asym * 2.0)

        microexpr_score = min(1.0, 0.5 * brow_raise + 0.5 * asym_smile)
        if microexpr_score > 0.4: notes.append("microexpression AU1/AU12")

        if TORCH_OK:
            au_features = torch.tensor([brow_raise, asym_smile, pupil_dilation], dtype=torch.float32)
            model = AUPredictor()
            predicted_deception = float(model(au_features).item())
        else:
            predicted_deception = clamp01(0.4*brow_raise + 0.3*asym_smile + 0.3*pupil_dilation)

        return {
            "gaze_aversion": gaze_aversion,
            "pupil_dilation": pupil_dilation,
            "microexpr_score": microexpr_score,
            "vak_visual_bias": 0.7,
            "au_predicted_deception": predicted_deception,
            "notes": notes
        }

class NonVerbalHeuristics:
    @staticmethod
    def analyze_stub(payload: Dict[str, Any], keypoints: Optional[Dict[str, Optional[Vec2]]] = None,
                     consent: bool = True, cultural_context: str = "universal") -> Dict[str, float]:
        out: Dict[str, float] = {}
        facial_nlp = FacialNLP.analyze_keypoints(keypoints or {}, consent, cultural_context)
        out.update({k: v for k, v in facial_nlp.items() if k != "notes"})

        def normv(v, cap=1.0):
            try: return clamp01(float(v or 0) / cap)
            except: return 0.0

        out["nv_fidget"] = normv(payload.get("gestures", {}).get("self_touch", 0)) + normv(payload.get("gestures", {}).get("fidget", 0))
        closed = normv(payload.get("posture", {}).get("closed", 0))
        out["nv_posture_closed"] = closed
        out["nv_posture_open"]  = clamp01(1.0 - closed)
        out["nv_react_latency"] = 1.0 - min(1.0, (payload.get("reactivity", {}).get("latency_ms", 600) / 1200.0))
        out["visual_deception"] = min(1.0, 0.4*out.get("gaze_aversion", 0) + 0.3*out.get("pupil_dilation", 0) + 0.3*out.get("microexpr_score", 0) + out.get("au_predicted_deception", 0))
        return out

# ========= Поведінкові евристики / темперамент =========
class BehaviorHeuristics:
    @staticmethod
    def analyze(payload: Dict[str, Any]) -> Dict[str, float]:
        out = {}
        for k in ["kept_promises","consistency","cooperation","risk_taking"]:
            try: out[f"bhv_{k}"] = clamp01(float(payload.get(k, 0.0)))
            except: out[f"bhv_{k}"] = 0.0
        return out

class TemperamentEstimator:
    @staticmethod
    def estimate(features: Dict[str, float]) -> Dict[str, float]:
        speed = features.get("nv_react_latency", 0.5)
        variability = features.get("nv_react_variability", 0.5) or features.get("nv_fidget", 0.5)
        cooperation = features.get("bhv_cooperation", 0.5)
        risk = features.get("bhv_risk_taking", 0.5)
        reactivity = speed * (0.7 + 0.3*variability)
        stability = max(0.0, 1.0 - variability*0.8)
        assertiveness = 0.4*risk + 0.3*reactivity + 0.3*(1.0 - variability)
        return {
            "temper_reactivity": reactivity,
            "temper_stability": stability,
            "temper_assertiveness": assertiveness,
            "temper_extraversion": clamp01(0.5*assertiveness + 0.2*cooperation + 0.3*reactivity),
        }

# ========= Bluetooth Whisper =========
class BluetoothWhisper:
    def __init__(self, privacy_mode: bool = True):
        self.privacy_mode = privacy_mode
        self.tts_engine = pyttsx3.init() if TTS_OK else None
        if self.tts_engine:
            self.tts_engine.setProperty('rate', 150)
            self.tts_engine.setProperty('volume', 0.55)

    def generate_hint(self, threat: 'ThreatScore', verbal: Optional[Dict[str, float]],
                      facial: Optional[Dict[str, float]], context_kind: str = "social",
                      platform: Optional[Go2Platform] = None) -> str:
        hints: List[str] = []
        # Загальні підказки
        if threat.approach > 0.5 or threat.strike > 0.5:
            hints.append("Physical threat↑ — step aside & back off.")
        if threat.scam_level > 0.5 or threat.visual_deception > 0.5:
            vd_note = f"gaze_aversion={facial.get('gaze_aversion', 0):.2f}" if facial else ""
            hints.append(f"Scam/manip cues: {vd_note}. Verify claims.")
        if verbal and verbal.get('coercion', 0) > 0.6:
            hints.append("Coercion language — probe gently.")
        if verbal and verbal.get('voice_stress', 0) > 0.5:
            hints.append("Voice stress high — ask clarifiers.")
        if context_kind == "business":
            hints.append("Business: double-check before agreeing.")
        elif context_kind == "social":
            hints.append("Social: watch for manip intent.")
        hint = " | ".join(hints) if hints else "All clear, continue."

        # Режими подачі: red/amber — без голосу (виключно тактильний)
        if (threat.level in ("red","amber")) and platform:
            platform.vibrate_tail(0.7 if threat.level=="red" else 0.4, ms=350)
            whisper_stub(hint)
            return hint

        # green — тихий TTS, якщо дозволено
        if TTS_OK and not self.privacy_mode and self.tts_engine:
            self.tts_engine.say(hint); self.tts_engine.runAndWait()
        else:
            whisper_stub(hint)
        return hint

# ========= Bayesian Fusion =========
@dataclass
class Hypothesis:
    name: str
    p: float
    evidence: List[str] = field(default_factory=list)

class BayesianFusion:
    PRIORS = {"cooperation": 0.3, "caution": 0.3, "manipulation": 0.2, "scam": 0.2}

    @staticmethod
    def likelihoods(feat: Dict[str, float]) -> Dict[str, float]:
        coop = 0.5*feat.get("bhv_cooperation", 0.5) + 0.4*feat.get("honesty_sincerity", 0.5) + 0.1*feat.get("nv_posture_open", 0.5)
        caut = 0.5*feat.get("hesitation", 0.5) + 0.3*feat.get("nv_posture_closed", 0.5) + 0.2*(1.0 - feat.get("honesty_sincerity", 0.5))
        manip= 0.5*feat.get("honesty_insincerity", 0.5) + 0.2*feat.get("nv_fidget", 0.5) + 0.3*feat.get("exaggeration", 0.5)
        scam = 0.4*feat.get("scam_pressure", 0.0) + 0.3*feat.get("exaggeration", 0.5) + 0.3*feat.get("visual_deception", 0.0)
        eps = 1e-3
        return {k: min(0.99, max(eps, v)) for k, v in {"cooperation": coop, "caution": caut, "manipulation": manip, "scam": scam}.items()}

    @staticmethod
    def fuse(feat: Dict[str, float]) -> List[Hypothesis]:
        lk = BayesianFusion.likelihoods(feat)
        post, denom = {}, 0.0
        for h, prior in BayesianFusion.PRIORS.items():
            post[h] = prior * lk[h]; denom += post[h]
        for h in post:
            post[h] = post[h] / denom if denom > 0 else 0.0
        expl = {
            "cooperation":["висока співпраця","відкрита постава","мовні маркери щирості"],
            "caution":["вагання/обережність","закрита постава","нижча щирість"],
            "manipulation":["маркери нещирості","самодотик/адаптери","узагальнення/перебільшення"],
            "scam":["urgency/offer","inconsistent eyes","exaggeration"],
        }
        return [Hypothesis(k, post[k], expl[k]) for k in sorted(post, key=lambda x: -post[x])]

# ========= SafetyRisk Screener =========
class SafetyRiskScreener:
    RE_SELF_HARM = re.compile(r"\b(покінчити з собою|самогуб|не хочу жити|завдам собі шкоди)\b", re.I|re.U)
    RE_VIOLENCE  = re.compile(r"\b(вбити|знищити|зарізати|підірвати|спалити)\b", re.I|re.U)
    RE_MEANS     = re.compile(r"\b(ніж|зброя|вибухівка|мотузка)\b", re.I|re.U)
    RE_TIME_PLACE= re.compile(r"\b(сьогодні|завтра|о \d{1,2}(:\d{2})?|на локації|адреса|координат)\b", re.I|re.U)
    RE_COERCION  = re.compile(r"\b(наказали|змушують|контролюють|погрожують)\b", re.I|re.U)
    RE_ESCALATION= re.compile(r"\b(ненавиджу|зрадники|очищення|кара)\b", re.I|re.U)

    @staticmethod
    def from_text(text: str) -> Dict[str, float]:
        t = (text or "").lower()
        self_harm = 0.8 if SafetyRiskScreener.RE_SELF_HARM.search(t) else 0.0
        violence  = 0.7 if SafetyRiskScreener.RE_VIOLENCE.search(t) else 0.0
        means     = 0.5 if SafetyRiskScreener.RE_MEANS.search(t) else 0.0
        time_pl   = 0.4 if SafetyRiskScreener.RE_TIME_PLACE.search(t) else 0.0
        coercion  = 0.6 if SafetyRiskScreener.RE_COERCION.search(t) else 0.0
        escalation= 0.4 if SafetyRiskScreener.RE_ESCALATION.search(t) else 0.0
        risk_to_others = min(1.0, violence + 0.6*means + 0.5*time_pl)
        return {"risk_to_self": self_harm, "risk_to_others": risk_to_others, "coercion": coercion, "escalation": escalation}

    @staticmethod
    def from_behavior(feat: Dict[str, float]) -> Dict[str, float]:
        esc = 0.2 + 0.6*(1.0 - feat.get("bhv_consistency",0.5)) + 0.2*feat.get("exaggeration",0.0)
        return {"escalation": clamp01(esc)}

    @staticmethod
    def fuse(*risk_maps: Dict[str, float]) -> Dict[str, float]:
        out = {"risk_to_self":0.0,"risk_to_others":0.0,"coercion":0.0,"escalation":0.0}
        for m in risk_maps:
            for k,v in m.items(): out[k] = max(out[k], v)
        return out

# ========= Просторові загрози =========
@dataclass
class ThreatScore:
    approach: float
    strike: float
    throw: float
    ignition: float
    social_approach: float
    manip_strike: float
    scam_level: float
    visual_deception: float
    level: str
    action: str
    notes: List[str]
    ctx_flags: List[str] = field(default_factory=list)

class SituationalThreat:
    def __init__(self):
        self.history: Dict[int, List[PersonObs]] = {}
        self.dist_close_m = 1.2
        self.dist_alert_m = 2.5
        self.min_closing_speed_mps = 0.8
        self.loadup_wrist_back_px = 30
        self.kick_cue_knee_delta_px = 28
        self.throw_cue_arm_arc_px = 36
        self.hover_time_s = 1.2
        self.whisper = BluetoothWhisper(privacy_mode=True)
        self.platform = Go2Platform(dry_run=True)

    def evaluate(self, ego: EgoState, people: List[PersonObs],
                 env: Optional[EnvironmentContext]=None,
                 crowd: Optional[CrowdSnapshot]=None,
                 visual_feats_per_id: Optional[Dict[int, Dict[str, float]]]=None) -> List[ThreatScore]:
        out: List[ThreatScore] = []
        for p in people:
            self.history.setdefault(p.track_id, []).append(p)
            if len(self.history[p.track_id]) > 20:
                self.history[p.track_id] = self.history[p.track_id][-20:]
            phys_score, notes, ctx = self._score_physical(ego, p, env, crowd)
            soc_score, soc_notes = self._score_social(ego, p, (visual_feats_per_id or {}).get(p.track_id))
            combined_notes = notes + soc_notes
            level, action = self._policy(phys_score, soc_score, env, crowd)
            out.append(ThreatScore(
                **phys_score, **soc_score, level=level, action=action, notes=combined_notes, ctx_flags=ctx
            ))
        return out

    def enact_policy(self, level: str, action_text: str,
                     phys_score: Dict[str, float], soc_score: Dict[str, float],
                     env: Optional[EnvironmentContext]):
        p = self.platform
        # Візуальні сигнали
        if level == "green":
            p.led("cyan", 0.0)
        elif level == "amber":
            p.led("yellow", 2.0); p.beep("short")
        elif level == "red":
            p.led("red", 6.0); p.beep("short")

        approach = phys_score["approach"]; strike = phys_score["strike"]
        ignition = phys_score["ignition"]; throw = phys_score["throw"]
        indoor = bool(env and env.kind == "indoor")

        if level == "red":
            if indoor:
                p.step_side("left", 0.5, 0.5); p.back_off(0.6, 0.5); p.face_exit()
            else:
                p.arc_move(0.9, 60, 0.5); p.back_off(1.0, 0.6)
            p.brace(); p.start_record()
        elif level == "amber":
            if approach > 0.5 or strike > 0.45:
                p.step_side("left", 0.3, 0.35)
            if ignition > 0.45 or throw > 0.45:
                p.back_off(0.6, 0.4)
            if indoor: p.face_exit()
            p.stop_record()
        else:
            p.stop_record()

    def _score_physical(self, ego: EgoState, p: PersonObs, env: Optional[EnvironmentContext], crowd: Optional[CrowdSnapshot]):
        notes, ctx_flags = [], []
        dist_px = l2(p.centroid, ego.position_px)
        dist_m = dist_px * ego.meters_per_pixel
        v_to_ego = (ego.position_px[0]-p.centroid[0], ego.position_px[1]-p.centroid[1])
        v_to_ego_n = norm(v_to_ego)
        v_n = norm(p.velocity)
        heading_align = clamp01((dot(v_n, v_to_ego_n) + 1.0) / 2.0)
        closing_speed_mps = dot(p.velocity, v_to_ego_n) * ego.meters_per_pixel
        notes.append(f"dist≈{dist_m:.2f}м; closing≈{max(0.0, closing_speed_mps):.2f}м/с; heading≈{heading_align:.2f}")

        kp = p.pose.points
        ls, rs = kp.get("left_shoulder"), kp.get("right_shoulder")
        lw, rw = kp.get("left_wrist"), kp.get("right_wrist")
        lh, rh = kp.get("left_hip"), kp.get("right_hip")
        lk, rk = kp.get("left_knee"), kp.get("right_knee")

        blading = 0.0
        if ls and rs: blading = clamp01(abs(ls[0]-rs[0]) / ((abs(ls[1]-rs[1]) + 1e-3)*2.0))
        load_right = 1.0 if (rw and rs and (rs[0]-rw[0]) > self.loadup_wrist_back_px) else 0.0
        load_left  = 1.0 if (lw and ls and (ls[0]-lw[0]) > self.loadup_wrist_back_px) else 0.0

        kick_cue = 0.0
        if rk and rh: kick_cue = 1.0 if (rh[1]-rk[1]) > self.kick_cue_knee_delta_px else 0.0
        if lk and lh: kick_cue = max(kick_cue, 1.0 if (lh[1]-lk[1]) > self.kick_cue_knee_delta_px else 0.0)

        tags = set(t.lower() for t in p.object_tags)
        heavy_object = any(t in tags for t in ["stick","pipe","brick","rock"])
        fluid_risk  = any(t in tags for t in ["bottle","canister"])
        ignition_aux= any(t in tags for t in ["lighter","matches","torch"])

        approach = 0.0
        if closing_speed_mps > 0 and heading_align > 0.5:
            near = 1.0 if dist_m <= self.dist_close_m else clamp01((self.dist_alert_m - dist_m)/(self.dist_alert_m - self.dist_close_m + 1e-6))
            approach = clamp01(0.2 + 0.6*near + 0.4*clamp01((closing_speed_mps - self.min_closing_speed_mps)/1.0) + 0.3*heading_align)

        strike = clamp01(0.4*blading + 0.4*max(load_left, load_right) + 0.4*kick_cue)
        if dist_m < 1.0: strike = clamp01(strike + 0.25)

        throw = 0.0
        if heavy_object:
            dist_fac = clamp01(1.0 - abs(dist_m - 2.0)/2.0)
            throw = clamp01(0.3*dist_fac + 0.5*max(load_left, load_right) + 0.2*blading)

        ignition = 0.0
        if fluid_risk and (ignition_aux or not (p.hand_visible.get("left", True) and p.hand_visible.get("right", True))):
            close_fac = clamp01((self.dist_alert_m - dist_m)/(self.dist_alert_m))
            ignition = clamp01(0.3 + 0.5*close_fac + 0.2*heading_align)

        if not p.hand_visible.get("left", True) or not p.hand_visible.get("right", True):
            approach = clamp01(approach + 0.1); strike = clamp01(strike + 0.1)

        if env:
            if env.kind == "indoor":
                strike = clamp01(strike + 0.1)
                if env.light_level < 0.4:
                    approach = clamp01(approach + 0.05); ctx_flags.append("low_light")
                for (c, r) in env.obstacles:
                    if l2(p.centroid, c) < r + (ego.meters_per_pixel*120):
                        approach = clamp01(approach + 0.08); ctx_flags.append("near_obstacle")

        if crowd:
            if crowd.density_m2 > 2.0:
                approach = clamp01(approach + 0.1); ctx_flags.append("high_density")
            if crowd.crush_sources > 0:
                approach = clamp01(approach + 0.1); ctx_flags.append("crush_seed")
            if crowd.counter_flow_ratio > 0.25:
                approach = clamp01(approach + 0.07); ctx_flags.append("counter_flow")

        hist = self.history.get(p.track_id, [])
        if len(hist) >= 2:
            t0, t1 = hist[0].ts, hist[-1].ts
            if dist_m < 1.0 and (t1 - t0) >= self.hover_time_s and abs(closing_speed_mps) < 0.2:
                strike = clamp01(strike + 0.15); approach = clamp01(approach + 0.1)
                notes.append("персональне нависання/утримання близької дистанції")

        if approach>0.0: notes.append("вектор зближення вирівняний на нас")
        if strike>0.0: notes.append("ознаки завантаження удару/блейдінг/коліно")
        if throw>0.0: notes.append("важкий предмет + замах")
        if ignition>0.0: notes.append("ризик обливання/займання")

        return {"approach":approach,"strike":strike,"throw":throw,"ignition":ignition}, notes, ctx_flags

    def _score_social(self, ego: EgoState, p: PersonObs, visual_feats: Optional[Dict[str, float]]):
        notes: List[str] = []
        dist_m = l2(p.centroid, ego.position_px) * ego.meters_per_pixel
        v_to_ego_n = norm((ego.position_px[0] - p.centroid[0], ego.position_px[1] - p.centroid[1]))
        closing_speed_mps = dot(p.velocity, v_to_ego_n) * ego.meters_per_pixel

        social_approach = 0.0
        if closing_speed_mps > 0 and dist_m < 2.0:
            social_approach = clamp01(0.3 + 0.5*(2.0 - dist_m)/2.0 + 0.2*clamp01(closing_speed_mps / 1.0))

        manip_strike = clamp01(0.4 * p.facial_micro.get("asym_smile", 0) +
                               0.3 * p.facial_micro.get("brow_raise", 0) +
                               0.3 * (1 - (p.hand_visible.get("left", True) and p.hand_visible.get("right", True))))

        visual_deception = (visual_feats or {}).get("visual_deception", 0.0)
        scam_level = clamp01(0.3*manip_strike + 0.3*social_approach + 0.4*visual_deception)

        if social_approach > 0: notes.append(f"social approach at {dist_m:.2f}m")
        if manip_strike > 0: notes.append("manipulative nonverbal cues")
        if visual_deception > 0.5: notes.append("high visual deception (eyes/micro)")

        return {"social_approach": social_approach, "manip_strike": manip_strike,
                "scam_level": scam_level, "visual_deception": visual_deception}, notes

    def _policy(self, phys_score: Dict[str,float], soc_score: Dict[str,float],
                env: Optional[EnvironmentContext], crowd: Optional[CrowdSnapshot]):
        a,s,t,g = phys_score["approach"],phys_score["strike"],phys_score["throw"],phys_score["ignition"]
        sl, vd = soc_score["scam_level"], soc_score["visual_deception"]

        adj = 0.0
        if env and env.kind=="indoor": adj += 0.05
        if crowd and (crowd.density_m2>2.0 or crowd.crush_sources>0): adj += 0.05

        phys_red = (a>(0.75-adj) and (s>0.45 or t>0.45 or g>0.45)) or max(s,t,g)>(0.7-adj)
        soc_red  = sl > (0.7 - adj) or vd > 0.6
        red = phys_red or soc_red
        amber = (a>(0.45-adj)) or max(s,t,g)>(0.45-adj) or sl > (0.4 - adj)

        if red:
            if phys_red and soc_red:
                level, action = "red","Full alert: Physical + social — evade to exit; notify."
            elif phys_red:
                level, action = "red","Physical red: sidestep + back-off; move to exit; de-escalate."
            else:
                level, action = "red","Social-scam red: avoid contact; notify; evade."
        elif amber:
            level, action = "amber","Amber: monitor hands/eyes; arc to open space; record."
        else:
            level, action = "green","Continue with monitoring."

        # Шепіт (tactile у red/amber) + дії платформи
        context_kind = env.kind if env else "social"
        _tmp_threat = ThreatScore(**phys_score, **soc_score, level=level, action=action, notes=[])
        self.whisper.generate_hint(_tmp_threat, None, None, context_kind, platform=self.platform)
        self.enact_policy(level, action, phys_score, soc_score, env)
        return level, action

# ========= Двигун =========
@dataclass
class PersonCard:
    track_id: int
    distance_m: float
    threat: ThreatScore
    intent: Optional[Dict[str, float]] = None
    honesty: Optional[Dict[str, float]] = None
    verbal: Optional[Dict[str, float]] = None
    facial_nlp: Optional[Dict[str, float]] = None
    notes: List[str] = field(default_factory=list)

@dataclass
class GlobalCard:
    level: str
    action: str
    reasons: List[str]
    env_flags: List[str]
    crowd_summary: Optional[Dict[str, float]] = None

@dataclass
class SocialOrientationReport:
    ts: float
    context_kind: str
    persons: List[PersonCard]
    global_card: GlobalCard
    safe_recommendations: List[str]

class SocialEvaluator:
    def __init__(self, top_k_intents: int = 3):
        self.spatial = SituationalThreat()
        self.top_k = top_k_intents

    def analyze(self,
                ego: EgoState,
                people: List[PersonObs],
                env: Optional[EnvironmentContext]=None,
                crowd: Optional[CrowdSnapshot]=None,
                utterances: Optional[Dict[int, str]]=None,
                behavior_payload: Optional[Dict[str, float]]=None,
                non_verbal_payload: Optional[Dict[str, Any]]=None,
                audio_payload: Optional[Dict[str, float]]=None,
                consent_visual: bool = True) -> SocialOrientationReport:

        # Platform preflight (можна розширити на частоту раз/хв)
        status = self.spatial.platform.read_status()
        # Тут можна знижувати швидкості/радіуси при низькій батареї/IMU warning

        # Персональні візуальні ознаки
        visual_feats_per_id: Dict[int, Dict[str,float]] = {}
        for p in people:
            cultural = env.cultural_context if env else "universal"
            facial_nlp = FacialNLP.analyze_keypoints(p.pose.points, consent_visual, cultural)
            nvh = NonVerbalHeuristics.analyze_stub(non_verbal_payload or {}, p.pose.points, consent_visual, cultural)
            visual_feats_per_id[p.track_id] = {**facial_nlp, **nvh}

        # Простір (physical + social)
        spatial_scores = self.spatial.evaluate(ego, people, env=env, crowd=crowd, visual_feats_per_id=visual_feats_per_id)

        # Вербальні + агреговані
        id_to_verbal: Dict[int, VerbalScore] = {}
        observations: List[Observation] = []
        if behavior_payload:
            observations.append(Observation(ts=time.time(), channel="behavior", content=behavior_payload, context={}))
        if non_verbal_payload:
            observations.append(Observation(ts=time.time(), channel="nonverbal", content=non_verbal_payload, context={}))
        if utterances:
            for tid, text in utterances.items():
                tf = TextHeuristics.analyze_text(text)
                id_to_verbal[tid] = VerbalPatterns.analyze(text, tf.get("intensifiers", 0.0), audio_payload)
                observations.append(Observation(ts=time.time(), channel="text", content={"text": text}, context={"consent": True}))

        features: Dict[str, float] = {}
        notes: List[str] = []
        for o in observations:
            if o.channel == "text":
                tf = TextHeuristics.analyze_text(o.content.get("text","")); features.update(tf)
                notes.append("Текстові ознаки враховано.")
            elif o.channel == "behavior":
                bf = BehaviorHeuristics.analyze(o.content); features.update(bf)
                notes.append("Поведінкові патерни враховано.")
            elif o.channel == "nonverbal":
                nvh2 = NonVerbalHeuristics.analyze_stub(o.content, consent=consent_visual, cultural_context=(env.cultural_context if env else "universal"))
                features.update(nvh2); notes.append("Невербальні cues враховано.")

        features.update(TemperamentEstimator.estimate(features))
        intents = BayesianFusion.fuse(features) if observations else []

        # Ризики
        risk_maps = []
        if utterances:
            for t in utterances.values(): risk_maps.append(SafetyRiskScreener.from_text(t))
        risk_maps.append(SafetyRiskScreener.from_behavior(features))
        risk = SafetyRiskScreener.fuse(*risk_maps)

        # Картки осіб
        persons: List[PersonCard] = []
        for p, s in zip(people, spatial_scores):
            distance_m = l2(p.centroid, ego.position_px) * ego.meters_per_pixel
            intent_top = {h.name: round(h.p, 3) for h in intents[:self.top_k]} if intents else None
            honesty = {k.replace("honesty_",""): v for k,v in features.items() if k.startswith("honesty_")} or None

            vid = visual_feats_per_id.get(p.track_id, {})
            facial_nlp_map = {k: round(v, 2) for k, v in vid.items() if k in ["gaze_aversion", "pupil_dilation", "microexpr_score", "vak_visual_bias", "au_predicted_deception"]}

            verbal_map = None
            if utterances and p.track_id in utterances:
                vs = id_to_verbal[p.track_id]
                verbal_map = {
                    "aggression":vs.aggression, "threat":vs.threat, "coercion":vs.coercion,
                    "deception_cues":vs.deception_cues, "exaggeration":vs.exaggeration,
                    "hesitation":vs.hesitation, "confusion":vs.confusion, "stress":vs.stress,
                    "scam_urgency":vs.scam_urgency, "scam_offer":vs.scam_offer, "scam_authority":vs.scam_authority,
                    "vak_visual":vs.vak_visual, "vak_auditory":vs.vak_auditory, "vak_kinesthetic":vs.vak_kinesthetic,
                    "voice_stress":vs.voice_stress
                }
                person_notes = s.notes + vs.notes + notes + vid.get("notes", [])
            else:
                person_notes = s.notes + notes + vid.get("notes", [])

            persons.append(PersonCard(
                track_id=p.track_id,
                distance_m=round(distance_m,2),
                threat=s,
                intent=intent_top,
                honesty=honesty,
                verbal=verbal_map,
                facial_nlp=facial_nlp_map,
                notes=person_notes
            ))

        # Глобальна картка
        def level_rank(lvl:str)->int: return {"green":0,"amber":1,"red":2}.get(lvl,0)
        worst = max(spatial_scores, key=lambda t: level_rank(t.level)) if spatial_scores else None
        global_level = worst.level if worst else "green"
        global_action = worst.action if worst else "Continue with monitoring."
        reasons = (worst.notes if worst else [])[:5]
        env_flags = (worst.ctx_flags if worst else [])
        crowd_summary = None if not crowd else {"density_m2":crowd.density_m2, "counter_flow_ratio":crowd.counter_flow_ratio, "crush_sources":crowd.crush_sources}

        # Рекомендації безпеки
        safe_reco: List[str] = []
        if risk.get("risk_to_self",0.0) >= 0.7:
            safe_reco.append("⚠️ High self-risk: Stop autonomy, human review.")
        if risk.get("risk_to_others",0.0) >= 0.7:
            safe_reco.append("⚠️ Risk to others: Change route, call responsible person.")
        if risk.get("coercion",0.0) >= 0.6:
            safe_reco.append("Possible coercion: Speak calmly, verify context.")
        if risk.get("escalation",0.0) >= 0.7:
            safe_reco.append("Escalation: Lower tone, increase distance.")
        if global_level == "red":
            hint = self.spatial.whisper.generate_hint(worst, persons[0].verbal if persons else None, persons[0].facial_nlp if persons else None, env.kind if env else "social", platform=self.spatial.platform)
            safe_reco.append(f"Red alert: evade, notify, record. Whisper: '{hint}'.")
        if not safe_reco:
            hint = self.spatial.whisper.generate_hint(ThreatScore(**{k:0.0 for k in ["approach","strike","throw","ignition","social_approach","manip_strike","scam_level","visual_deception"]}, level="green", action="", notes=[]),
                                                     None, None, env.kind if env else "social", platform=self.spatial.platform)
            safe_reco.append(f"Keep distance, de-escalate. Whisper: '{hint}'.")

        if not consent_visual: safe_reco.append("Visual analysis skipped: no consent.")
        return SocialOrientationReport(
            ts=time.time(),
            context_kind=(env.kind if env else "social"),
            persons=persons,
            global_card=GlobalCard(level=global_level, action=global_action, reasons=reasons, env_flags=env_flags, crowd_summary=crowd_summary),
            safe_recommendations=safe_reco
        )

    def visualize_threat(self, report: SocialOrientationReport, filename: str = "threat_plot.png"):
        if not report.persons: return
        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 5))
        # Physical
        phys_threats = ["approach", "strike", "throw", "ignition"]
        avg_phys = [sum(getattr(pc.threat, t) for pc in report.persons) / len(report.persons) for t in phys_threats]
        ax1.bar(phys_threats, avg_phys)
        ax1.set_title("Physical External Security")
        ax1.set_ylabel("Score (0-1)")
        # Social/visual
        soc_threats = ["social_approach", "manip_strike", "scam_level", "visual_deception"]
        avg_soc = [sum(getattr(pc.threat, t) for pc in report.persons) / len(report.persons) for t in soc_threats]
        ax2.bar(soc_threats, avg_soc)
        ax2.set_title("Social/Scam + Visual NLP")
        ax2.set_ylabel("Score (0-1)")
        # Intents pie (по першому як приклад)
        if report.persons and report.persons[0].intent:
            labels = list(report.persons[0].intent.keys())
            sizes = list(report.persons[0].intent.values())
            ax3.pie(sizes, labels=labels, autopct='%1.1f%%')
            ax3.set_title("Intents Distribution")
        plt.tight_layout()
        plt.savefig(filename)
        plt.close()
        print(f"Plot saved: {filename}")

# ========= Демонстрація =========
if __name__ == "__main__":
    base_ts = time.time()
    ego = EgoState(ts=base_ts, position_px=(640, 360), forward_vec=(0, -1), meters_per_pixel=1/500.0)
    env = EnvironmentContext(kind="business", cultural_context="eastern_europe", light_level=0.55, exits_px=[(120, 40)], choke_points_px=[(300, 240)])
    crowd = CrowdSnapshot(density_m2=1.5, counter_flow_ratio=0.3)

    people = [
        PersonObs(
            track_id=1, ts=base_ts + 2,
            centroid=(660, 330), velocity=(0, 50), bbox_xywh=(600, 240, 120, 260),
            pose=PoseKeypoints(points={
                "left_eye": (620, 320), "right_eye": (660, 325), "nose": (640, 340),
                "left_brow_inner": (615, 310), "right_brow_inner": (645, 305),
                "mouth_left": (630, 360), "mouth_right": (650, 355),
                "left_shoulder": (650, 290), "right_shoulder": (670, 290),
                "left_wrist": (650, 305), "right_wrist": (620, 300),
                "left_hip": (650, 360), "right_hip": (670, 360),
                "left_knee": (650, 350), "right_knee": (665, 330),
                "pupil_estimate": 0.6
            }),
            object_tags=["bottle","lighter"],
            hand_visible={"left": True, "right": True},
            facial_micro={"asym_smile": 0.6, "brow_raise": 0.7, "pupil_estimate": 0.6}
        )
    ]

    utter = {1: "Мені наказали підійти ближче. Це важливо. Ви виграли мільйон! Швидко надішліть дані від банку!"}
    behavior = {"cooperation": 0.2, "consistency": 0.4, "kept_promises": 0.3, "risk_taking": 0.8}
    non_verbal = {"facial_micro": {"eye_inconsist": 0.7}, "gestures": {"self_touch": 0.4, "fidget": 0.6}, "posture": {"closed": 0.5}, "reactivity": {"latency_ms": 800}}
    audio = {"pitch_variance": 0.7}

    engine = SocialEvaluator(top_k_intents=3)

    # Якщо готовий до апаратного тесту — розкоментуй і реалізуй методи Go2Platform:
    # engine.spatial.platform = Go2Platform(dry_run=False)

    report = engine.analyze(ego, people, env=env, crowd=crowd,
                            utterances=utter, behavior_payload=behavior,
                            non_verbal_payload=non_verbal, audio_payload=audio,
                            consent_visual=True)

    print("=== GLOBAL ===")
    print(report.global_card.level, "→", report.global_card.action)
    print("Reasons:", "; ".join(report.global_card.reasons))
    print("Env:", report.global_card.env_flags, report.global_card.crowd_summary)

    print("\n=== PERSONS ===")
    for pc in report.persons:
        print(f"id={pc.track_id} dist={pc.distance_m}м level={pc.threat.level} action={pc.threat.action}")
        if pc.verbal:  print(" verbal:", {k: round(v, 2) for k, v in pc.verbal.items() if k not in ['notes']})
        if pc.intent:  print(" intent:", pc.intent)
        if pc.honesty: print(" honesty:", {k: round(v, 2) for k, v in pc.honesty.items()})
        if pc.facial_nlp: print(" FacialNLP:", pc.facial_nlp)
        print(" notes:", "; ".join(pc.notes[:4]))

    print("\nSAFE:", report.safe_recommendations)
    engine.visualize_threat(report)
