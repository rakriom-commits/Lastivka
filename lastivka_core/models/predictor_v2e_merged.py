# -*- coding: utf-8 -*-
"""
predictor_v2e_merged.py — Локальний аналітик/прогнозист імовірностей для соціальних/політичних/економічних/psyops подій.
Фокус:
- локальні прогнози (бінарні/неперервні) з пояснюваністю (tech/social/economic/psyops),
- ваги подій, часовий розпад (half-life), адаптивне згладжування,
- стабільні CI (Beta + Wilson) з коректним зсувом після калібрувань,
- корекції від метапрограми (gain/bias, logit-bias, prior-mix, virtual evidence, anchored-prior),
- подієвий журнал, снапшоти стану,
- безпечні контекстні ваги (лог-шкали, кепи) + репутація джерела,
- детектори: дисонанс/конфлікти/інфлюенсери/маніпуляції/гарячі точки/емоційні тригери/дезінформаційні кампанії,
- економіка: SMA, волатильність, імпульс, скоригований тренд, buy/hold/sell, кореляція з настроєм,
- psyops: оцінка емоційної стійкості.
Залежності: тільки стандартна бібліотека.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional, Tuple, Dict, Any, List
import json
import math
import time
import uuid
from statistics import NormalDist
import logging
import sys

# ------------------------- ЛОГЕР -------------------------
logger = logging.getLogger(__name__)
if not logger.handlers:
    try:
        logging.basicConfig(
            level=logging.INFO,
            filename=r"C:\Lastivka\lastivka_core\logs\predictor_log.txt",
            filemode="a",
            encoding="utf-8",
            format="%(asctime)s %(levelname)s %(name)s: %(message)s"
        )
    except Exception:
        h = logging.StreamHandler(sys.stdout)  # явний stdout-фолбек
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logger.addHandler(h)
        logger.setLevel(logging.INFO)

# ------------------------- КОНСТАНТИ ПОДІЙ -------------------------
EVENT_DISINFO = "disinformation"

# ------------------------- УТИЛІТИ -------------------------
def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def beta_mean(alpha: float, beta: float) -> float:
    return alpha / (alpha + beta)

def beta_var(alpha: float, beta: float) -> float:
    num = alpha * beta
    den = (alpha + beta)**2 * (alpha + beta + 1)
    return num / den

def beta_ci(alpha: float, beta: float, z: float = 1.96) -> Tuple[float, float]:
    m = beta_mean(alpha, beta)
    v = beta_var(alpha, beta)
    s = math.sqrt(v)
    return clamp(m - z*s, 0.0, 1.0), clamp(m + z*s, 0.0, 1.0)

def wilson_interval(p_hat: float, n_eff: float, z: float = 1.96) -> Tuple[float, float]:
    if n_eff <= 0:
        return (0.0, 1.0)
    denom = 1.0 + (z*z)/n_eff
    center = (p_hat + (z*z)/(2*n_eff)) / denom
    margin = (z / denom) * math.sqrt((p_hat*(1 - p_hat)/n_eff) + (z*z)/(4*n_eff*n_eff))
    return clamp(center - margin, 0.0, 1.0), clamp(center + margin, 0.0, 1.0)

def now_ts() -> float:
    return time.time()

def safe_clip(p: float, eps: float = 1e-9) -> float:
    return clamp(p, eps, 1 - eps)

def logit(p: float) -> float:
    p = safe_clip(p)
    return math.log(p / (1 - p))

def inv_logit(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z))

def simple_moving_average(values: List[float], period: int = 5) -> float:
    if not values:
        return 0.0
    n = min(len(values), max(1, period))
    return sum(values[-n:]) / n

def volatility(values: List[float], period: int = 5) -> float:
    if not values:
        return 0.0
    n = min(len(values), max(2, period))
    window = values[-n:]
    mean = sum(window) / n
    var = sum((x - mean)**2 for x in window) / n
    return math.sqrt(var)

# ------------------------- ОНЛАЙН-СТАТИСТИКИ -------------------------
@dataclass
class OnlineStats:
    n: int = 0
    mean: float = 0.0
    m2: float = 0.0
    recent_values: List[float] = field(default_factory=list)
    max_recent: int = 10
    economic_values: List[float] = field(default_factory=list)
    economic_max_recent: int = 256

    def update(self, x: float) -> None:
        self.n += 1
        delta = x - self.mean
        self.mean += delta / self.n
        delta2 = x - self.mean
        self.m2 += delta * delta2
        self.recent_values.append(x)
        if len(self.recent_values) > self.max_recent:
            self.recent_values.pop(0)

    def update_economic(self, x: float) -> None:
        xf = float(x)
        if not math.isfinite(xf):
            logger.warning(f"Invalid economic input (finite): {x}")
            return
        self.economic_values.append(xf)
        if len(self.economic_values) > self.economic_max_recent:
            self.economic_values.pop(0)

    @property
    def variance(self) -> float:
        return self.m2 / (self.n - 1) if self.n > 1 else 0.0

    @property
    def std(self) -> float:
        return math.sqrt(self.variance)

    def zscore(self, x: float) -> float:
        s = self.std
        return 0.0 if s == 0.0 else (x - self.mean) / s

    def trend_direction(self) -> Optional[str]:
        if len(self.recent_values) < 3:
            return None
        diffs = [self.recent_values[i] - self.recent_values[i-1] for i in range(1, len(self.recent_values))]
        avg_diff = sum(diffs) / len(diffs)
        return "зростає" if avg_diff > 0 else "спадає" if avg_diff < 0 else "стабільний"

    def norm_deviation(self, threshold: float = 2.0) -> Optional[str]:
        if self.n < 10:
            return None
        x = self.recent_values[-1] if self.recent_values else self.mean
        z = self.zscore(x)
        adj_threshold = threshold * (1 - 0.3 * min(self.std, 1.0))
        if abs(z) > adj_threshold:
            return f"Відхилення від норми: значення {x:.4f} вибивається (z={z:.2f}, поріг={adj_threshold:.2f})."
        return "У межах норми."

    def emotional_valence(self, window_size: int = 5) -> Optional[str]:
        if len(self.recent_values) < window_size:
            return None
        recent = self.recent_values[-window_size:]
        avg = sum(recent) / window_size
        return "позитивна" if avg > 0.1 else "негативна" if avg < -0.1 else "нейтральна"

    def sma(self, period: int = 5) -> float:
        return simple_moving_average(self.economic_values, period)

    def volatility(self, period: int = 5) -> float:
        return volatility(self.economic_values, period)

# ------------------------- БЕТА-БЕРНУЛЛІ З ВАГАМИ+HALF-LIFE -------------------------
@dataclass
class BayesianBernoulli:
    alpha: float = 1.0
    beta: float = 1.0
    successes: int = 0
    failures: int = 0
    w_success: float = 0.0
    w_failure: float = 0.0
    half_life_sec: float = 0.0
    last_decay_ts: float = field(default_factory=now_ts)
    recent_outcomes: List[int] = field(default_factory=list)
    max_recent: int = 10
    anchored_prior: Optional[float] = None

    def _apply_time_decay(self) -> None:
        if self.half_life_sec and self.half_life_sec > 1e-9:
            dt = now_ts() - self.last_decay_ts
            if dt > 0:
                k = 0.5 ** (dt / self.half_life_sec)
                excess_alpha = max(0.0, self.alpha - 1.0)
                excess_beta = max(0.0, self.beta - 1.0)
                self.alpha = 1.0 + excess_alpha * k
                self.beta = 1.0 + excess_beta * k
                self.w_success *= k
                self.w_failure *= k
                self.last_decay_ts = now_ts()

    def observe(self, outcome: int, weight: float = 1.0) -> None:
        if outcome not in (0, 1):
            raise ValueError("Bernoulli outcome must be 0 or 1")
        self._apply_time_decay()
        w = max(0.0, float(weight))
        if outcome == 1:
            self.alpha += w
            self.successes += 1
            self.w_success += w
        else:
            self.beta += w
            self.failures += 1
            self.w_failure += w
        self.recent_outcomes.append(outcome)
        if len(self.recent_outcomes) > self.max_recent:
            self.recent_outcomes.pop(0)
        if self.anchored_prior is None and self.successes + self.failures == 1:
            self.anchored_prior = outcome

    def add_virtual_evidence(self, w_success: float = 0.0, w_failure: float = 0.0) -> None:
        self._apply_time_decay()
        if w_success > 0:
            self.alpha += float(w_success)
            self.w_success += float(w_success)
        if w_failure > 0:
            self.beta += float(w_failure)
            self.w_failure += float(w_failure)

    def check_streak(self, length: int = 5) -> Optional[str]:
        if len(self.recent_outcomes) < length:
            return None
        last_n = self.recent_outcomes[-length:]
        if all(x == 1 for x in last_n):
            return "Стабільна підтримка (серія успіхів)."
        if all(x == 0 for x in last_n):
            return "Стабільна опозиція (серія невдач)."
        return None

    @property
    def p_mean(self) -> float:
        return beta_mean(self.alpha, self.beta)

    @property
    def n_eff(self) -> float:
        return max(0.0, (self.alpha - 1.0) + (self.beta - 1.0))

    def ci95(self) -> Tuple[float, float]:
        lo, hi = beta_ci(self.alpha, self.beta, z=1.96)
        if self.n_eff < 6 or (self.alpha < 2.0 or self.beta < 2.0):
            p_hat = 0.0 if self.n_eff <= 0 else (self.alpha - 1.0) / self.n_eff
            w_lo, w_hi = wilson_interval(p_hat, self.n_eff, z=1.96)
            lo, hi = min(lo, w_lo), max(hi, w_hi)
        return (clamp(lo, 0.0, 1.0), clamp(hi, 0.0, 1.0))

# ------------------------- ЕКСПОНЕНЦІЙНЕ ЗГЛАДЖУВАННЯ -------------------------
@dataclass
class ExpSmoother:
    alpha: float = 0.25
    level: Optional[float] = None
    alpha_max: float = 0.5
    alpha_boost_z: float = 2.0
    half_life_sec: float = 0.0
    last_update_ts: float = field(default_factory=now_ts)

    def update(self, x: float, z_score: Optional[float] = None) -> float:
        a = self.alpha
        if z_score is not None:
            az = abs(z_score)
            if az >= self.alpha_boost_z:
                a = min(self.alpha_max, self.alpha * 1.5)
            elif az >= (self.alpha_boost_z * 0.6):
                a = min(self.alpha_max, self.alpha * 1.2)
        if self.half_life_sec > 1e-9:
            dt = now_ts() - self.last_update_ts
            if dt > 0:
                decay = 0.5 ** (dt / self.half_life_sec)
                self.level = (self.level * decay) if self.level is not None else x
        self.level = x if self.level is None else (a * x + (1 - a) * self.level)
        self.last_update_ts = now_ts()
        return self.level

    def forecast(self) -> Optional[float]:
        return self.level

# ------------------------- ОСНОВНИЙ КЛАС ПРОГНОЗИСТА -------------------------
@dataclass
class LocalForecaster:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_ts: float = field(default_factory=now_ts)
    cont_stats: OnlineStats = field(default_factory=OnlineStats)
    trend: ExpSmoother = field(default_factory=ExpSmoother)
    bern: BayesianBernoulli = field(default_factory=BayesianBernoulli)
    window: List[float] = field(default_factory=list)
    max_window: int = 256
    events: List[Dict[str, Any]] = field(default_factory=list)
    mode: str = "tech"  # tech, social, economic, psyops
    z_anomaly: float = 3.0
    min_ci_width: float = 0.5
    bern_half_life_sec: float = 0.0
    cont_half_life_sec: float = 0.0
    # Калібрування/корекції
    cont_gain: float = 1.0
    cont_bias: float = 0.0
    bern_logit_bias: float = 0.0
    bern_mix_with_prior: float = 0.0
    bern_prior_mean: float = 0.5
    anchored_prior_mix: float = 0.0
    # Рішення
    decision_threshold: float = 0.6
    decision_hysteresis: float = 0.03
    decision_min_ci_width: float = 0.5
    # Контекстні ваги
    max_context_weight: float = 5.0
    min_context_weight: float = 0.5
    use_context_weight: bool = True
    # Дисонанс
    dissonance_window_size: int = 10
    dissonance_threshold: float = -0.5
    # Норми/мотивація
    norm_dev_threshold: float = 2.0
    crisis_weight_multiplier: float = 0.8
    benefit_weight_multiplier: float = 1.2
    propaganda_weight_multiplier: float = 1.5
    influencer_weight_threshold: float = 0.8
    # Конфлікти
    conflict_threshold: float = 0.5
    # Економічний аналіз
    economic_sma_period: int = 5
    economic_volatility_threshold: float = 0.1
    economic_trigger_threshold: float = 0.5
    # Psyops
    manipulation_threshold: float = 3.0
    emotional_manipulation_threshold: float = 0.8
    disinformation_campaign_threshold: float = 3.0
    # Анти-спам
    event_cooldowns: Dict[str, float] = field(default_factory=lambda: {
        "binary": 60.0,
        "influencer": 300.0,
        "manipulation": 300.0,
        "emotional_manipulation": 300.0,
        "disinformation": 600.0,
        "economic": 60.0,
        "economic_volatility": 120.0,
        "anomaly": 120.0,
        "external_event": 60.0,
    })
    _last_event_ts: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        if self.bern_half_life_sec > 0:
            self.bern.half_life_sec = self.bern_half_life_sec
        if self.cont_half_life_sec > 0:
            self.trend.half_life_sec = self.cont_half_life_sec

    def _trim_events(self, maxlen: int = 64) -> None:
        if len(self.events) > maxlen:
            self.events = self.events[-maxlen:]

    def _check_cooldown(self, event_type: str) -> bool:
        cooldown = self.event_cooldowns.get(event_type, 60.0)
        last_ts = self._last_event_ts.get(event_type, 0.0)
        return now_ts() - last_ts >= cooldown

    def _update_cooldown(self, event_type: str) -> None:
        self._last_event_ts[event_type] = now_ts()

    # ---------- СПОСТЕРЕЖЕННЯ ----------
    def observe_continuous(self, x: float, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            xf = float(x)
        except (TypeError, ValueError):
            logger.warning(f"Invalid continuous input (cast): {x}")
            return {"n": self.cont_stats.n, "skipped": True}
        if not math.isfinite(xf):
            logger.warning(f"Invalid continuous input (finite): {x}")
            return {"n": self.cont_stats.n, "skipped": True}

        self.cont_stats.update(xf)
        self.window.append(xf)
        if len(self.window) > self.max_window:
            self.window.pop(0)

        z = self.cont_stats.zscore(xf)
        lvl = self.trend.update(xf, z_score=z)
        anomaly = (abs(z) >= self.z_anomaly) and (self.cont_stats.n >= 10)

        result = {"n": self.cont_stats.n, "mean": self.cont_stats.mean, "std": self.cont_stats.std,
                  "level": lvl, "z": z, "anomaly": anomaly}
        logger.info(f"Continuous: x={xf:.4f}, mean={result['mean']:.4f}, z={z:.2f}, anomaly={anomaly}")

        if anomaly and context and self._check_cooldown("anomaly"):
            self.events.append({"type": "anomaly", "value": xf, "ts": now_ts(), "context": context})
            self._trim_events()
            self.trigger_event("anomaly", impact=0.2, context=context)
            self._update_cooldown("anomaly")
        return result

    def observe_binary(self, outcome: int, weight: float = 1.0, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # базове зважування
        if context is None:
            ctx_w = 1.0
            logger.info("No context provided for binary observation, using default weight=1.0")
        else:
            ctx_w = calculate_weight(context, self.cont_stats.mean, self) if self.use_context_weight else 1.0

        raw_w = max(0.0, float(weight)) * ctx_w
        w_eff = clamp(raw_w, self.min_context_weight, self.max_context_weight)

        # домноження на контекстні коефіцієнти
        if context:
            event_type = str(context.get("event_type", "")).lower()
            if "economic_crisis" in event_type and outcome == 1:
                w_eff *= self.crisis_weight_multiplier
            elif "economic_boom" in event_type and outcome == 1:
                w_eff *= self.benefit_weight_multiplier
            elif "market_crash" in event_type and outcome == 0:
                w_eff *= 1.3

        # перевірка маніпуляції ПІСЛЯ остаточного w_eff
        is_manip = False
        if context:
            is_manip = self.detect_manipulation(context, w_eff)
            if is_manip:
                w_eff *= self.propaganda_weight_multiplier

        before = self.bern.p_mean
        self.bern.observe(outcome, w_eff)
        after = self.bern.p_mean
        lo, hi = self.bern.ci95()
        result = {
            "p_before": before, "p_after": after, "ci95": (lo, hi),
            "successes": self.bern.successes, "failures": self.bern.failures,
            "w_success": self.bern.w_success, "w_failure": self.bern.w_failure,
            "n_eff": self.bern.n_eff
        }
        logger.info("Binary: outcome=%s, w_raw=%.3f, w_eff=%.3f, p=%.4f, ci95=(%.4f, %.4f), n_eff=%.2f",
                    outcome, raw_w, w_eff, after, lo, hi, self.bern.n_eff)

        ctx_rec = dict(context) if context else {}
        ctx_rec["w_raw"], ctx_rec["w_eff"] = raw_w, w_eff
        self.events.append({"type": "binary", "outcome": outcome, "w": w_eff, "ts": now_ts(), "context": ctx_rec})
        self._trim_events()

        if self.detect_influencer(context, w_eff) and self._check_cooldown("influencer"):
            self.events.append({"type": "influencer", "value": w_eff, "ts": now_ts(), "context": ctx_rec})
            self._trim_events(); self._update_cooldown("influencer")

        if is_manip and self._check_cooldown("manipulation"):
            self.events.append({"type": "manipulation", "value": w_eff, "ts": now_ts(), "context": ctx_rec})
            self._trim_events(); self._update_cooldown("manipulation")

        if self.detect_emotional_manipulation(context) and self._check_cooldown("emotional_manipulation"):
            self.events.append({"type": "emotional_manipulation", "value": w_eff, "ts": now_ts(), "context": ctx_rec})
            self._trim_events(); self._update_cooldown("emotional_manipulation")

        # уніфікація: і ключ cooldown, і тип події — "disinformation"
        if self.detect_disinformation_campaign() and self._check_cooldown(EVENT_DISINFO):
            self.events.append({"type": EVENT_DISINFO, "value": w_eff, "ts": now_ts(), "context": ctx_rec})
            self._trim_events(); self._update_cooldown(EVENT_DISINFO)

        return result

    def observe_economic(self, price: float, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.cont_stats.update_economic(price)
        sma = self.cont_stats.sma(self.economic_sma_period)
        vol = self.cont_stats.volatility(self.economic_sma_period)
        momentum = self.economic_momentum()
        result = {"price": price, "sma": sma, "volatility": vol, "momentum": momentum,
                  "is_volatile": vol > self.economic_volatility_threshold}
        logger.info(f"Economic: price={price:.4f}, sma={sma:.4f}, volatility={vol:.4f}, momentum={momentum:.4f}, is_volatile={result['is_volatile']}")
        if result["is_volatile"] and context and self._check_cooldown("economic_volatility"):
            self.events.append({"type": "economic_volatility", "value": price, "ts": now_ts(), "context": context})
            self._trim_events()
            self.trigger_event("market_volatility", impact=0.2, context=context)
            self._update_cooldown("economic_volatility")

        trigger = self.detect_economic_trigger()
        if trigger and context and self._check_cooldown("economic"):
            self.events.append({"type": "economic_trigger", "value": price, "ts": now_ts(), "context": context})
            self._trim_events()
            self.trigger_event("market_drop" if "падіння" in trigger else "market_rise", impact=0.3, context=context)
            self._update_cooldown("economic")
        return result

    # ---------- ПРОГНОЗИ ----------
    def _adjust_ci_linear(self, lo: float, hi: float, p_raw: float, p_adj: float) -> Tuple[float, float]:
        delta = p_adj - p_raw
        return clamp(lo + delta, 0.0, 1.0), clamp(hi + delta, 0.0, 1.0)

    def forecast_continuous(self, horizon: int = 1) -> Dict[str, Any]:
        lvl = self.trend.forecast()
        if lvl is None:
            return {"ready": False, "reason": "insufficient_data"}
        lvl_corr = self.cont_gain * lvl + self.cont_bias
        sigma_raw = self.cont_stats.std if self.cont_stats.n > 1 else 0.0
        sigma = abs(self.cont_gain) * sigma_raw
        s_h = sigma * math.sqrt(max(1, horizon))
        dist = NormalDist(mu=lvl_corr, sigma=max(s_h, 1e-9))
        return {"ready": True, "point": lvl_corr,
                "ci68": (dist.inv_cdf(0.16), dist.inv_cdf(0.84)),
                "ci95": (dist.inv_cdf(0.025), dist.inv_cdf(0.975)),
                "n": self.cont_stats.n}

    def forecast_binary(self) -> Dict[str, Any]:
        p_raw = self.bern.p_mean
        p = p_raw
        if self.bern_logit_bias != 0.0:
            p = inv_logit(logit(p) + self.bern_logit_bias)
        if self.bern_mix_with_prior > 0.0:
            lam = clamp(self.bern_mix_with_prior, 0.0, 1.0)
            p = (1 - lam) * p + lam * self.bern_prior_mean
        if self.bern.anchored_prior is not None and self.bern.n_eff < 5:
            lam_a = clamp(self.anchored_prior_mix, 0.0, 1.0)
            p = (1 - lam_a) * p + lam_a * self.bern.anchored_prior
        lo, hi = self.bern.ci95()
        lo_adj, hi_adj = self._adjust_ci_linear(lo, hi, p_raw, p)
        return {"p": clamp(p, 0.0, 1.0), "ci95": (lo_adj, hi_adj),
                "successes": self.bern.successes, "failures": self.bern.failures,
                "w_success": self.bern.w_success, "w_failure": self.bern.w_failure,
                "n_eff": self.bern.n_eff}

    def forecast_economic(self) -> Dict[str, Any]:
        if not self.cont_stats.economic_values:
            return {"ready": False, "reason": "no_economic_data"}
        sma = self.cont_stats.sma(self.economic_sma_period)
        vol = self.cont_stats.volatility(self.economic_sma_period)
        momentum = self.economic_momentum()
        last_price = self.cont_stats.economic_values[-1]
        trend = "зростає" if last_price > sma else "спадає"
        band = 0.5 * max(vol, 1e-9)
        if last_price > sma + band:
            signal = "buy"
        elif last_price < sma - band:
            signal = "sell"
        else:
            signal = "hold"
        adjusted_forecast = self.trend_adjusted_forecast()
        return {"ready": True, "sma": sma, "volatility": vol, "momentum": momentum,
                "trend": trend, "signal": signal, "last_price": last_price,
                "band": band, "adjusted_forecast": adjusted_forecast}

    # ---------- КОРЕЛЯЦІЇ/ДЕТЕКТОРИ ----------
    def cross_correlation(self, window_size: Optional[int] = None, use_economic: bool = False) -> Optional[float]:
        ws = self.dissonance_window_size if window_size is None else window_size
        values = self.cont_stats.economic_values if use_economic else self.window
        if len(values) < ws or len(self.bern.recent_outcomes) < ws:
            return None
        recent_cont = values[-ws:]
        recent_bin = self.bern.recent_outcomes[-ws:]
        mean_cont = sum(recent_cont) / ws
        mean_bin = sum(recent_bin) / ws
        cov = sum((x - mean_cont) * (y - mean_bin) for x, y in zip(recent_cont, recent_bin)) / (ws - 1)
        std_cont = math.sqrt(sum((x - mean_cont)**2 for x in recent_cont) / (ws - 1))
        std_bin = math.sqrt(sum((y - mean_bin)**2 for y in recent_bin) / (ws - 1))
        return cov / (std_cont * std_bin) if std_cont > 0 and std_bin > 0 else 0.0

    def _corr_on_last(self, ws: int, offset: int = 0, use_economic: bool = False) -> Optional[float]:
        values = self.cont_stats.economic_values if use_economic else self.window
        biny = self.bern.recent_outcomes
        if len(values) < ws + offset or len(biny) < ws + offset:
            return None
        # явні зрізи для прозорості
        if offset == 0:
            cont = values[-ws:]
            outc = biny[-ws:]
        else:
            cont = values[-(ws + offset):-offset]
            outc = biny[-(ws + offset):-offset]
        mean_c = sum(cont) / ws
        mean_b = sum(outc) / ws
        cov = sum((x - mean_c) * (y - mean_b) for x, y in zip(cont, outc)) / (ws - 1)
        sc = math.sqrt(sum((x - mean_c)**2 for x in cont) / (ws - 1))
        sb = math.sqrt(sum((y - mean_b)**2 for y in outc) / (ws - 1))
        return cov / (sc * sb) if sc > 0 and sb > 0 else 0.0

    def detect_dissonance(self, window_size: Optional[int] = None, threshold: Optional[float] = None, use_economic: bool = False) -> Optional[str]:
        ws = self.dissonance_window_size if window_size is None else window_size
        th = self.dissonance_threshold if threshold is None else threshold
        th = th * (1 - 0.5 * min(self.cont_stats.std, 1.0))
        corr = self.cross_correlation(ws, use_economic)
        if corr is None:
            return None
        if corr < th:
            data_type = "ринковими цінами" if use_economic else "настроєм"
            return f"Виявлено дисонанс: {data_type} і підтримка суперечать одне одному (corr={corr:.2f}, поріг={th:.2f})."
        return None

    def detect_conflict(self, window_size: int = 5) -> Optional[str]:
        prev_corr = self._corr_on_last(window_size, offset=window_size)
        curr_corr = self._corr_on_last(window_size, offset=0)
        if prev_corr is None or curr_corr is None:
            return None
        adj_threshold = self.conflict_threshold * (1 + 0.3 * min(self.cont_stats.std, 1.0))
        if abs(curr_corr - prev_corr) > adj_threshold:
            return f"Виявлено конфлікт: різка зміна кореляції ({prev_corr:.2f} -> {curr_corr:.2f}, поріг={adj_threshold:.2f})."
        return None

    def detect_influencer(self, context: Optional[Dict[str, Any]], w_eff: float) -> bool:
        if context is None:
            return False
        followers = int(context.get("followers", 0))
        retweets = int(context.get("retweets", 0))
        big_account = followers >= 50_000
        viral = retweets >= 100
        avg_weight = (self.bern.w_success + self.bern.w_failure) / max(1, self.bern.successes + self.bern.failures)
        dynamic_threshold = max(self.influencer_weight_threshold, avg_weight * 1.5)
        heavy_weight = w_eff >= dynamic_threshold
        return bool(heavy_weight or big_account or viral)

    def detect_manipulation(self, context: Optional[Dict[str, Any]], w_eff: float) -> bool:
        if context is None or "source_id" not in context:
            return False
        source_id = context["source_id"]
        recent_events = [
            e for e in self.events
            if e.get("context", {}).get("source_id") == source_id and now_ts() - e["ts"] < 3600
        ]
        if len(recent_events) >= self.manipulation_threshold:
            return True
        if w_eff > self.max_context_weight * 0.9 and context.get("retweets", 0) > 100:
            return True
        if "text" in context:
            texts = [e.get("context", {}).get("text", "") for e in recent_events]
            current_text = context["text"].lower()
            words = set(current_text.split())
            keyword_count = sum(1 for t in texts if any(word in t.lower() for word in words))
            if keyword_count >= self.manipulation_threshold:
                return True
        return False

    def detect_emotional_manipulation(self, context: Optional[Dict[str, Any]]) -> bool:
        if context is None or "sentiment" not in context:
            return False
        sentiment = float(context.get("sentiment", 0.0))
        return abs(sentiment) > self.emotional_manipulation_threshold

    def detect_disinformation_campaign(self, window_sec: float = 3600.0) -> bool:
        recent_events = [e for e in self.events if now_ts() - e["ts"] < window_sec]
        if len(recent_events) < self.disinformation_campaign_threshold:
            return False
        source_ids = [e.get("context", {}).get("source_id", "") for e in recent_events if "context" in e]
        unique_sources = len(set(source_ids))
        # щільність подій у вікні
        event_density = len(recent_events) / max(window_sec, 1e-9)
        if unique_sources < len(recent_events) / 2 and event_density > 0.001:
            return True
        texts = [e.get("context", {}).get("text", "").lower() for e in recent_events if "text" in e.get("context", {})]
        if texts:
            words = [set(t.split()) for t in texts if t]
            if words:
                common_words = set.intersection(*words) if len(words) > 1 else words[0]
                if len(common_words) > 3:
                    return True
        return False

    def detect_hotspot(self, time_window_sec: float = 3600.0) -> Optional[str]:
        recent_events = [e for e in self.events if now_ts() - e["ts"] <= time_window_sec]
        if len(recent_events) >= 5:
            return f"Виявлено гарячу точку: {len(recent_events)} подій за останні {time_window_sec/3600:.1f} год."
        return None

    # ---------- ДОД. ОЦІНКИ ----------
    def calculate_reputation(self, context: Optional[Dict[str, Any]]) -> float:
        if not context or "source_id" not in context:
            return 1.0
        source_id = context["source_id"]
        retweets = int(context.get("retweets", 0))
        relevant = [e for e in self.events if e.get("context", {}).get("source_id") == source_id]
        if not relevant:
            return 1.0
        avg_sent = sum(e["context"].get("sentiment", 0.0) for e in relevant) / len(relevant)
        viral_boost = math.log10(retweets + 1) / 10.0 if retweets > 0 else 0.0
        return clamp(1.0 + 0.2 * clamp(avg_sent, -1.0, 1.0) + viral_boost, 0.5, 2.0)

    def group_identity_score(self) -> Optional[float]:
        if not self.events:
            return None
        similarities = [e.get("context", {}).get("group_similarity", 0.0) for e in self.events]
        similarities = [s for s in similarities if isinstance(s, (int, float))]
        if not similarities:
            return None
        return sum(similarities) / len(similarities)

    def assess_risk(self) -> Optional[str]:
        if not self.cont_stats.economic_values:
            return None
        vol = self.cont_stats.volatility(self.economic_sma_period)
        if vol > self.economic_volatility_threshold * 1.5:
            return "високий"
        if vol > self.economic_volatility_threshold:
            return "помірний"
        return "низький"

    def mood_price_correlation(self, window_size: int = 5) -> Optional[float]:
        if len(self.window) < window_size or len(self.cont_stats.economic_values) < window_size:
            return None
        recent_mood = self.window[-window_size:]
        recent_prices = self.cont_stats.economic_values[-window_size:]
        mean_mood = sum(recent_mood) / window_size
        mean_price = sum(recent_prices) / window_size
        cov = sum((x - mean_mood) * (y - mean_price) for x, y in zip(recent_mood, recent_prices)) / (window_size - 1)
        std_mood = math.sqrt(sum((x - mean_mood)**2 for x in recent_mood) / (window_size - 1))
        std_price = math.sqrt(sum((y - mean_price)**2 for y in recent_prices) / (window_size - 1))
        return cov / (std_mood * std_price) if std_mood > 0 and std_price > 0 else 0.0

    def economic_momentum(self, window_size: int = 5) -> float:
        if len(self.cont_stats.economic_values) < window_size:
            return 0.0
        recent = self.cont_stats.economic_values[-window_size:]
        diffs = [recent[i] - recent[i-1] for i in range(1, len(recent))]
        return sum(diffs) / len(diffs) if diffs else 0.0

    def trend_adjusted_forecast(self, horizon: int = 1) -> Optional[float]:
        if not self.cont_stats.economic_values:
            return None
        sma = self.cont_stats.sma(self.economic_sma_period)
        corr = self.mood_price_correlation()
        if corr is None:
            return sma
        corr_weight = min(abs(corr), 1.0)
        mood = self.cont_stats.mean
        adjustment = corr_weight * corr * mood * self.cont_stats.volatility(self.economic_sma_period)
        return sma + adjustment * horizon

    def emotional_resilience_score(self, window_size: int = 5) -> Optional[float]:
        if len(self.cont_stats.recent_values) < window_size:
            return None
        recent = self.cont_stats.recent_values[-window_size:]
        mean = sum(recent) / window_size
        variance = sum((x - mean)**2 for x in recent) / window_size
        return clamp(1.0 - math.sqrt(variance), 0.0, 1.0)

    # ---------- ГНУЧКИЙ ДЕТЕКТОР ЕКОНОМ. ТРИГЕРА ----------
    def detect_economic_trigger(self) -> Optional[str]:
        """Детектує тригер на основі momentum, скоригований на волатильність і настрої."""
        if not self.cont_stats.economic_values:
            return None
        momentum = self.economic_momentum()
        vol = self.cont_stats.volatility(self.economic_sma_period)
        adj = self.economic_trigger_threshold * (1 - 0.2 * min(vol / self.economic_volatility_threshold, 1.0))
        if momentum < -adj:
            return "падіння"
        elif momentum > adj:
            return "зростання"
        return None

    # ---------- ПОЯСНЕННЯ ----------
    def explain_last_continuous(self) -> str:
        if not self.window:
            return "Ще немає спостережень."
        x = self.window[-1]
        z = self.cont_stats.zscore(x)
        parts = [
            f"Останній рівень (настрій/довіра): {x:.4f}",
            f"Середнє/σ: {self.cont_stats.mean:.4f}/{self.cont_stats.std:.4f}",
            f"Z-оцінка: {z:.2f}",
        ]
        if abs(z) >= self.z_anomaly and self.cont_stats.n >= 10:
            parts.append(f"Висновок: аномалія у відносинах (можлива криза, |z|≥{self.z_anomaly:.1f}).")
        else:
            parts.append("Висновок: стабільна динаміка.")
        lvl = self.trend.forecast()
        if lvl is not None:
            parts.append(f"Очікуваний рівень: {lvl:.4f}")
        trend = self.cont_stats.trend_direction()
        tag = "Psyops-нота" if self.mode == "psyops" else "Соц-нота" if self.mode == "social" else "Економ-нота"
        if trend and self.mode in ("social", "economic", "psyops"):
            parts.append(f"{tag}: настрій {trend}.")
        norm_dev = self.cont_stats.norm_deviation(self.norm_dev_threshold)
        if norm_dev and self.mode in ("social", "economic", "psyops"):
            parts.append(f"{tag}: {norm_dev}")
        valence = self.cont_stats.emotional_valence()
        if valence and self.mode in ("social", "psyops"):
            parts.append(f"{tag}: емоційна валентність: {valence}.")
        resilience = self.emotional_resilience_score()
        if resilience is not None and self.mode in ("social", "psyops"):
            parts.append(f"{tag}: емоційна стійкість: {resilience:.2f}.")
        if self.mode == "economic" and self.cont_stats.economic_values:
            econ = self.forecast_economic()
            parts.append(f"Економ-нота: SMA={econ['sma']:.4f}, волатильність={econ['volatility']:.4f}, імпульс={econ['momentum']:.4f}, сигнал={econ['signal']}.")
            if econ["adjusted_forecast"] is not None:
                parts.append(f"Економ-нота: скоригований прогноз={econ['adjusted_forecast']:.4f}.")
            risk = self.assess_risk()
            if risk:
                parts.append(f"Економ-нота: ризик={risk}.")
            corr = self.mood_price_correlation()
            if corr is not None:
                parts.append(f"Економ-нота: кореляція настрою і цін: {corr:.2f}.")
        if self.mode == "psyops" and self.detect_disinformation_campaign():
            parts.append("Psyops-нота: виявлено ознаки дезінформаційної кампанії.")
        return " ".join(parts)

    def explain_last_binary(self) -> str:
        fb = self.forecast_binary()
        p = fb["p"]; lo, hi = fb["ci95"]
        total_obs = self.bern.successes + self.bern.failures
        w_total = self.bern.w_success + self.bern.w_failure
        width = hi - lo
        parts = [
            f"Ймовірність підтримки: {p:.4f}",
            f"CI95 (після калібрувань, лінеар.): [{lo:.4f}, {hi:.4f}] (ширина={width:.3f})",
            f"Спостережень: {total_obs} (вага={w_total:.2f}, n_eff={self.bern.n_eff:.2f})"
        ]
        parts.append("Висновок: ще замало даних — збираємо далі." if width > self.min_ci_width
                     else ("Висновок: висока ймовірність." if p > 0.5 else "Висновок: низька ймовірність."))
        streak = self.bern.check_streak()
        if streak: parts.append(f"Серія: {streak}")
        corr = self.cross_correlation()
        tag = "Psyops-нота" if self.mode == "psyops" else "Соц-нота" if self.mode == "social" else "Економ-нота"
        if corr is not None and self.mode in ("social", "economic", "psyops"):
            parts.append(f"{tag}: кореляція настрою і підтримки: {corr:.2f}.")
        dissonance = self.detect_dissonance()  # фікс опечатки
        if dissonance and self.mode in ("social", "economic", "psyops"):
            parts.append(f"{tag}: {dissonance}")
        conflict = self.detect_conflict()
        if conflict and self.mode in ("social", "economic", "psyops"):
            parts.append(f"{tag}: {conflict}")
        hotspot = self.detect_hotspot()
        if hotspot and self.mode in ("social", "economic", "psyops"):
            parts.append(f"{tag}: {hotspot}")
        identity = self.group_identity_score()
        if identity is not None and self.mode in ("social", "psyops"):
            parts.append(f"{tag}: групова ідентичність: {identity:.2f}.")
        resilience = self.emotional_resilience_score()
        if resilience is not None and self.mode in ("social", "psyops"):
            parts.append(f"{tag}: емоційна стійкість: {resilience:.2f}.")
        # кешування detect_* для останньої події
        if self.mode == "psyops" and self.events and "context" in self.events[-1]:
            _ctx = self.events[-1]["context"]
            _w = self.events[-1].get("w", 1.0)
            _manip = self.detect_manipulation(_ctx, _w)
            _emo = self.detect_emotional_manipulation(_ctx)
            _disinfo = self.detect_disinformation_campaign()
            if _manip:
                parts.append("Psyops-нота: виявлено маніпулятивний наратив.")
            if _emo:
                parts.append("Psyops-нота: виявлено емоційну маніпуляцію.")
            if _disinfo:
                parts.append("Psyops-нота: виявлено ознаки дезінформаційної кампанії.")
        if self.mode == "social":
            parts.append("Соц-нота: оцінка обережна; важить недавність і якість джерел.")
        elif self.mode == "economic":
            parts.append("Економ-нота: оцінка враховує ринкові тренди та соціальний настрій.")
        elif self.mode == "psyops":
            parts.append("Psyops-нота: оцінка враховує маніпулятивні наративи та інформаційні атаки.")
        return " ".join(parts)

    def explain_last_economic(self) -> str:
        """Симетричний пояснювач для економічного режиму."""
        econ = self.forecast_economic()
        if not econ.get("ready"):
            return "Ще немає економічних спостережень."
        parts = [
            f"Економіка: ціна={econ['last_price']:.4f}, SMA={econ['sma']:.4f}, σ={econ['volatility']:.4f}, імпульс={econ['momentum']:.4f}.",
            f"Сигнал: {econ['signal']} (band={econ['band']:.4f}).",
        ]
        if econ.get("adjusted_forecast") is not None:
            parts.append(f"Скоригований прогноз: {econ['adjusted_forecast']:.4f}.")
        risk = self.assess_risk()
        if risk:
            parts.append(f"Ризик: {risk}.")
        corr = self.mood_price_correlation()
        if corr is not None:
            parts.append(f"Кореляція настрій↔ціни: {corr:.2f}.")
        trig = self.detect_economic_trigger()
        if trig:
            parts.append(f"Економ-нота: тригер: {trig}")
        return " ".join(parts)

    # ---------- СЕРІАЛІЗАЦІЯ/МЕТАПРОГРАМА ----------
    def to_json(self) -> str:
        obj = {
            "id": self.id, "created_ts": self.created_ts,
            "cont_stats": asdict(self.cont_stats),
            "trend": {"alpha": self.trend.alpha, "alpha_max": self.trend.alpha_max,
                      "alpha_boost_z": self.trend.alpha_boost_z, "level": self.trend.level,
                      "half_life_sec": self.trend.half_life_sec, "last_update_ts": self.trend.last_update_ts},
            "bern": asdict(self.bern),
            "window": self.window, "max_window": self.max_window,
            "events": self.events, "mode": self.mode,
            "z_anomaly": self.z_anomaly, "min_ci_width": self.min_ci_width,
            "bern_half_life_sec": self.bern_half_life_sec, "cont_half_life_sec": self.cont_half_life_sec,
            "cont_gain": self.cont_gain, "cont_bias": self.cont_bias,
            "bern_logit_bias": self.bern_logit_bias, "bern_mix_with_prior": self.bern_mix_with_prior,
            "bern_prior_mean": self.bern_prior_mean, "anchored_prior_mix": self.anchored_prior_mix,
            "decision_threshold": self.decision_threshold, "decision_hysteresis": self.decision_hysteresis,
            "decision_min_ci_width": self.decision_min_ci_width,
            "max_context_weight": self.max_context_weight, "min_context_weight": self.min_context_weight,
            "use_context_weight": self.use_context_weight,
            "dissonance_window_size": self.dissonance_window_size, "dissonance_threshold": self.dissonance_threshold,
            "norm_dev_threshold": self.norm_dev_threshold,
            "crisis_weight_multiplier": self.crisis_weight_multiplier,
            "benefit_weight_multiplier": self.benefit_weight_multiplier,
            "propaganda_weight_multiplier": self.propaganda_weight_multiplier,
            "influencer_weight_threshold": self.influencer_weight_threshold,
            "conflict_threshold": self.conflict_threshold,
            "economic_sma_period": self.economic_sma_period,
            "economic_volatility_threshold": self.economic_volatility_threshold,
            "economic_trigger_threshold": self.economic_trigger_threshold,
            "manipulation_threshold": self.manipulation_threshold,
            "emotional_manipulation_threshold": self.emotional_manipulation_threshold,
            "disinformation_campaign_threshold": self.disinformation_campaign_threshold,
            "event_cooldowns": self.event_cooldowns,
            "_last_event_ts": self._last_event_ts
        }
        return json.dumps(obj, ensure_ascii=False)

    @staticmethod
    def from_json(s: str) -> "LocalForecaster":
        d = json.loads(s)
        lf = LocalForecaster(
            id=d["id"], created_ts=d["created_ts"],
            cont_stats=OnlineStats(**d["cont_stats"]),
            trend=ExpSmoother(**d["trend"]),
            bern=BayesianBernoulli(**d["bern"]),
            window=d.get("window", []), max_window=d.get("max_window", 256),
            events=d.get("events", []), mode=d.get("mode", "tech"),
            z_anomaly=d.get("z_anomaly", 3.0), min_ci_width=d.get("min_ci_width", 0.5),
            bern_half_life_sec=d.get("bern_half_life_sec", 0.0),
            cont_half_life_sec=d.get("cont_half_life_sec", 0.0),
            cont_gain=d.get("cont_gain", 1.0), cont_bias=d.get("cont_bias", 0.0),
            bern_logit_bias=d.get("bern_logit_bias", 0.0),
            bern_mix_with_prior=d.get("bern_mix_with_prior", 0.0),
            bern_prior_mean=d.get("bern_prior_mean", 0.5),
            anchored_prior_mix=d.get("anchored_prior_mix", 0.0),
            decision_threshold=d.get("decision_threshold", 0.6),
            decision_hysteresis=d.get("decision_hysteresis", 0.03),
            decision_min_ci_width=d.get("decision_min_ci_width", 0.5),
            max_context_weight=d.get("max_context_weight", 5.0),
            min_context_weight=d.get("min_context_weight", 0.5),
            use_context_weight=d.get("use_context_weight", True),
            dissonance_window_size=d.get("dissonance_window_size", 10),
            dissonance_threshold=d.get("dissonance_threshold", -0.5),
            norm_dev_threshold=d.get("norm_dev_threshold", 2.0),
            crisis_weight_multiplier=d.get("crisis_weight_multiplier", 0.8),
            benefit_weight_multiplier=d.get("benefit_weight_multiplier", 1.2),
            propaganda_weight_multiplier=d.get("propaganda_weight_multiplier", 1.5),
            influencer_weight_threshold=d.get("influencer_weight_threshold", 0.8),
            conflict_threshold=d.get("conflict_threshold", 0.5),
            economic_sma_period=d.get("economic_sma_period", 5),
            economic_volatility_threshold=d.get("economic_volatility_threshold", 0.1),
            economic_trigger_threshold=d.get("economic_trigger_threshold", 0.5),
            manipulation_threshold=d.get("manipulation_threshold", 3.0),
            emotional_manipulation_threshold=d.get("emotional_manipulation_threshold", 0.8),
            disinformation_campaign_threshold=d.get("disinformation_campaign_threshold", 3.0),
            event_cooldowns=d.get("event_cooldowns", {
                "binary": 60.0, "influencer": 300.0, "manipulation": 300.0,
                "emotional_manipulation": 300.0, "disinformation": 600.0,
                "economic": 60.0, "economic_volatility": 120.0, "anomaly": 120.0,
                "external_event": 60.0
            }),
            _last_event_ts=d.get("_last_event_ts", {})
        )
        return lf

    def create_snapshot(self) -> str:
        return self.to_json()

    def restore_snapshot(self, snapshot_json: str) -> None:
        other = LocalForecaster.from_json(snapshot_json)
        self.__dict__.update(other.__dict__)

    def trigger_event(self, event_type: str, impact: float, context: Optional[Dict[str, Any]] = None) -> None:
        if not self._check_cooldown(event_type):
            logger.info(f"Event {event_type} skipped due to cooldown")
            return
        logger.info(f"Event triggered: {event_type}, impact={impact}")
        if "crisis" in event_type.lower() or "anomaly" in event_type.lower() or "market_crash" in event_type.lower():
            self.trend.alpha = min(self.trend.alpha_max, self.trend.alpha * (1 + impact))
            self.decision_hysteresis = max(0.01, self.decision_hysteresis * (1 - impact))
        self.events.append({"type": "external_event", "event_type": event_type, "impact": impact, "ts": now_ts(), "context": context})
        self._trim_events()
        self._update_cooldown(event_type)

    def get_state(self) -> Dict[str, Any]:
        state = {
            "id": self.id, "created_ts": self.created_ts,
            "continuous_forecast": self.forecast_continuous(),
            "binary_forecast": self.forecast_binary(),
            "explain_continuous": self.explain_last_continuous(),
            "explain_binary": self.explain_last_binary(),
            "events": self.events[-64:], "mode": self.mode
        }
        if self.mode == "economic":
            state["economic_forecast"] = self.forecast_economic()
            state["explain_economic"] = self.explain_last_economic()
        return state

    def update_from_metaprogram(self, data: Dict[str, Any]) -> None:
        if "mode" in data and data["mode"] in ("tech", "social", "economic", "psyops"):
            self.mode = data["mode"]
        if "bern_half_life_sec" in data:
            self.bern_half_life_sec = max(0.0, float(data["bern_half_life_sec"]))
            self.bern.half_life_sec = self.bern_half_life_sec
        if "cont_half_life_sec" in data:
            self.cont_half_life_sec = max(0.0, float(data["cont_half_life_sec"]))
            self.trend.half_life_sec = self.cont_half_life_sec
        if "use_context_weight" in data:
            self.use_context_weight = bool(data["use_context_weight"])
        if "weight_caps" in data:
            caps = data["weight_caps"] or {}
            if "min" in caps: self.min_context_weight = float(caps["min"])
            if "max" in caps: self.max_context_weight = float(caps["max"])

        corr = data.get("corrections", {})
        if "cont_gain" in corr: self.cont_gain = float(corr["cont_gain"])
        if "cont_bias" in corr: self.cont_bias = float(corr["cont_bias"])
        if "bern_logit_bias" in corr: self.bern_logit_bias = float(corr["bern_logit_bias"])
        if "bern_mix_with_prior" in corr: self.bern_mix_with_prior = clamp(float(corr["bern_mix_with_prior"]), 0.0, 1.0)
        if "bern_prior_mean" in corr: self.bern_prior_mean = clamp(float(corr["bern_prior_mean"]), 0.0, 1.0)
        if "anchored_prior_mix" in corr: self.anchored_prior_mix = clamp(float(corr["anchored_prior_mix"]), 0.0, 1.0)
        if "virtual_evidence" in corr:
            ve = corr["virtual_evidence"] or {}
            self.bern.add_virtual_evidence(
                w_success=float(ve.get("w_success", 0.0)),
                w_failure=float(ve.get("w_failure", 0.0))
            )
        if "decision" in corr:
            d = corr["decision"] or {}
            if "threshold" in d: self.decision_threshold = float(d["threshold"])
            if "hysteresis" in d: self.decision_hysteresis = float(d["hysteresis"])
            if "min_ci_width" in d: self.decision_min_ci_width = float(d["min_ci_width"])
        if "dissonance" in corr:
            dis = corr["dissonance"] or {}
            if "window_size" in dis: self.dissonance_window_size = int(dis["window_size"])
            if "threshold" in dis: self.dissonance_threshold = float(dis["threshold"])
        if "norm_dev_threshold" in corr: self.norm_dev_threshold = float(corr["norm_dev_threshold"])
        if "crisis_weight_multiplier" in corr: self.crisis_weight_multiplier = float(corr["crisis_weight_multiplier"])
        if "benefit_weight_multiplier" in corr: self.benefit_weight_multiplier = float(corr["benefit_weight_multiplier"])
        if "propaganda_weight_multiplier" in corr: self.propaganda_weight_multiplier = float(corr["propaganda_weight_multiplier"])
        if "influencer_weight_threshold" in corr: self.influencer_weight_threshold = float(corr["influencer_weight_threshold"])
        if "conflict_threshold" in corr: self.conflict_threshold = float(corr["conflict_threshold"])
        if "economic_sma_period" in corr: self.economic_sma_period = int(corr["economic_sma_period"])
        if "economic_volatility_threshold" in corr: self.economic_volatility_threshold = float(corr["economic_volatility_threshold"])
        if "economic_trigger_threshold" in corr: self.economic_trigger_threshold = float(corr["economic_trigger_threshold"])
        if "manipulation_threshold" in corr: self.manipulation_threshold = float(corr["manipulation_threshold"])
        if "emotional_manipulation_threshold" in corr: self.emotional_manipulation_threshold = float(corr["emotional_manipulation_threshold"])
        if "disinformation_campaign_threshold" in corr: self.disinformation_campaign_threshold = float(corr["disinformation_campaign_threshold"])
        if "event_cooldowns" in corr: self.event_cooldowns.update(corr["event_cooldowns"])

        ctx = data.get("context", {})
        if "event_trigger" in data:
            self.trigger_event(data["event_trigger"]["type"], data["event_trigger"]["impact"], ctx)
        if "continuous" in data: self.observe_continuous(float(data["continuous"]), ctx)
        if "binary" in data:
            w = float(data.get("weight", 1.0))
            self.observe_binary(int(data["binary"]), w, ctx)
        if "economic" in data: self.observe_economic(float(data["economic"]), ctx)

    # ---------- ГРУПОВЕ ПОРІВНЯННЯ ----------
    @staticmethod
    def compare_groups(groups: Dict[str, "LocalForecaster"]) -> Dict[str, Any]:
        """
        Повертає компактний зріз по кожній групі: p/CI, настрій, ризик (якщо є економіка),
        емоційна стійкість, базові метрики активності. Додає polarization та most_confident.
        """
        out: Dict[str, Any] = {}
        for name, lf in groups.items():
            bin_fc = lf.forecast_binary()
            cont_fc = lf.forecast_continuous()
            econ = lf.forecast_economic() if lf.mode == "economic" else None
            resilience = lf.emotional_resilience_score()
            out[name] = {
                "p": round(bin_fc["p"], 4),
                "ci95": [round(bin_fc["ci95"][0], 4), round(bin_fc["ci95"][1], 4)],
                "n_eff": round(bin_fc["n_eff"], 2),
                "mood_point": round(cont_fc["point"], 4) if cont_fc.get("ready") else None,
                "resilience": round(resilience, 3) if resilience is not None else None,
                "risk": lf.assess_risk() if econ and econ.get("ready") else None,
                "events": len(lf.events),
                "recent_hotspot": lf.detect_hotspot() is not None
            }
        supports = [v["p"] for v in out.values() if isinstance(v, dict)]
        if len(supports) > 1:
            out["polarization"] = round(max(supports) - min(supports), 4)
            most_confident = min(
                ((k, v) for k, v in out.items() if isinstance(v, dict)),
                key=lambda kv: (kv[1]["ci95"][1] - kv[1]["ci95"][0])
            )[0]
            out["most_confident"] = most_confident
            out["pressure"] = out[most_confident]["p"]
        return out

# ------------------------- РІШЕННЯ ДЛЯ ДІЙ -------------------------
@dataclass
class Decision:
    do_action: bool
    p: float
    ci95: Tuple[float, float]
    reason: str

def calculate_weight(context: Optional[Dict[str, Any]], group_mood: float = 0.5, forecaster: Optional[LocalForecaster] = None) -> float:
    if not context:
        return 1.0
    followers = max(0, int(context.get("followers", 0)))
    retweets = max(0, int(context.get("retweets", 0)))
    group_similarity = float(context.get("group_similarity", 0.0))
    # кламп для стабільності — якщо інпути "сирі"
    sentiment = clamp(float(context.get("sentiment", group_mood)), -1.0, 1.0)
    cascade_factor = float(context.get("cascade_factor", 0.0))
    w_followers = math.log10(followers + 1) / 4.0
    w_retweets = math.log10(retweets + 1) / 2.0
    w_similarity = 0.5 * clamp(group_similarity, 0.0, 1.0)
    w_simboost = 0.3 if abs(sentiment - group_mood) < 0.2 else 0.0
    w_cascade = 0.3 * clamp(cascade_factor, 0.0, 1.0)
    w_reputation = forecaster.calculate_reputation(context) if forecaster else 1.0
    base = 1.0 + w_followers + w_retweets + w_similarity + w_simboost + w_cascade + w_reputation
    return base

def decide_binary(lf: LocalForecaster, threshold: Optional[float] = None, min_width: Optional[float] = None,
                  context: Optional[Dict[str, Any]] = None, hysteresis: Optional[float] = None) -> Decision:
    thr = lf.decision_threshold if threshold is None else threshold
    minw = lf.decision_min_ci_width if min_width is None else min_width
    hyst = lf.decision_hysteresis if hysteresis is None else hysteresis
    if context and "crisis" in str(context.get("event_type", "")).lower():
        hyst = hyst * 0.5
        thr = max(0.3, thr * 0.8)
    if lf.mode == "economic" and lf.cont_stats.economic_values:
        vol = lf.cont_stats.volatility(lf.economic_sma_period)
        thr += 0.1 * min(vol / lf.economic_volatility_threshold, 2.0)
    f = lf.forecast_binary()
    p = f["p"]; lo, hi = f["ci95"]; width = hi - lo
    hyst = hyst * (1 + 0.5 * min(1.0, width))
    total_obs = f["successes"] + f["failures"]
    if width > minw and total_obs < 10:
        return Decision(False, p, (lo, hi), "Надто висока невизначеність — збери більше даних.")
    if p >= thr + hyst:
        return Decision(True, p, (lo, hi), f"Порог {thr:.2f} досягнуто з запасом.")
    if p <= thr - hyst:
        return Decision(False, p, (lo, hi), f"Порог {thr:.2f} не досягнуто.")
    return Decision(False, p, (lo, hi), "Сіра зона — дочекайся ще спостережень.")

# ------------------------- DEMO -------------------------
if __name__ == "__main__":
    # Невеликий демонстраційний прогін без зовнішніх залежностей
    lf = LocalForecaster(mode="psyops", bern_half_life_sec=3600.0, cont_half_life_sec=3600.0)

    posts = [
        {"text": "Реформа супер! #підтримую", "followers": 1000, "retweets": 10, "group_similarity": 0.7, "sentiment": 0.8, "cascade_factor": 0.5, "source_id": "user1"},
        {"text": "Реформа — провал!", "followers": 50, "retweets": 2, "group_similarity": 0.3, "sentiment": -0.9, "cascade_factor": 0.2, "source_id": "user2"},
        {"text": "Реформа руйнує економіку!", "followers": 50, "retweets": 2, "group_similarity": 0.3, "sentiment": -0.9, "cascade_factor": 0.2, "source_id": "user2"},
        {"text": "Потрібно більше часу.", "followers": 10000, "retweets": 50, "group_similarity": 0.5, "sentiment": 0.1, "cascade_factor": 0.8, "source_id": "user3"},
    ]
    prices = [100.0, 101.5, 99.0, 102.0, 103.5]

    def parse_x_post(post: Dict[str, Any]) -> Dict[str, Any]:
        """Безпечний парсер події з X: кламп/кастинг полів, дефолти."""
        try:
            sentiment = float(post.get("sentiment", 0.0))
        except Exception:
            sentiment = 0.0
        sentiment = clamp(sentiment, -1.0, 1.0)
        followers = int(post.get("followers", 0) or 0)
        retweets = int(post.get("retweets", 0) or 0)
        text = str(post.get("text", "") or "")
        group_similarity = float(post.get("group_similarity", 0.0) or 0.0)
        cascade_factor = float(post.get("cascade_factor", 0.0) or 0.0)
        source_id = str(post.get("source_id", "") or "")
        binary = 1 if sentiment > 0 else 0
        context = {
            "source": "X",
            "followers": followers,
            "retweets": retweets,
            "text": text,
            "group_similarity": group_similarity,
            "sentiment": sentiment,
            "cascade_factor": cascade_factor,
            "source_id": source_id
        }
        return {"continuous": sentiment, "binary": binary, "context": context}

    for post, price in zip(posts, prices[:len(posts)]):
        data = parse_x_post(post); data["economic"] = price
        lf.update_from_metaprogram({**data, "mode": lf.mode})
        print(lf.explain_last_continuous())
        print(lf.explain_last_binary())
        decision = decide_binary(lf, context=data["context"])
        print(f"Рішення: {decision.reason}")

    lf.update_from_metaprogram({
        "mode": "psyops",
        "bern_half_life_sec": 5400,
        "cont_half_life_sec": 5400,
        "use_context_weight": True,
        "weight_caps": {"min": 0.5, "max": 5.0},
        "corrections": {
            "cont_gain": 0.95,
            "cont_bias": 0.1,
            "bern_logit_bias": 0.2,
            "bern_mix_with_prior": 0.1,
            "bern_prior_mean": 0.7,
            "anchored_prior_mix": 0.25,
            "virtual_evidence": {"w_success": 0.7, "w_failure": 0.3},
            "decision": {"threshold": 0.62, "hysteresis": 0.04, "min_ci_width": 0.45},
            "dissonance": {"window_size": 10, "threshold": -0.5},
            "norm_dev_threshold": 2.0,
            "crisis_weight_multiplier": 0.8,
            "benefit_weight_multiplier": 1.2,
            "propaganda_weight_multiplier": 1.5,
            "influencer_weight_threshold": 0.8,
            "conflict_threshold": 0.5,
            "economic_sma_period": 5,
            "economic_volatility_threshold": 0.1,
            "economic_trigger_threshold": 0.4,
            "manipulation_threshold": 3.0,
            "emotional_manipulation_threshold": 0.8,
            "disinformation_campaign_threshold": 3.0
        },
        "event_trigger": {"type": "economic_boom", "impact": 0.3},
        "context": {"src": "meta", "event_type": "economic_boom"}
    })
    print(lf.get_state()["explain_binary"])
    print(decide_binary(lf, context={"event_type": "economic_boom"}))

    forecasters = {
        "youth": LocalForecaster(mode="psyops", bern_half_life_sec=3600.0, cont_half_life_sec=3600.0),
        "elders": LocalForecaster(mode="psyops", bern_half_life_sec=3600.0, cont_half_life_sec=3600.0)
    }
    for post, price in zip(posts, prices[:len(posts)]):
        for _, _lf in forecasters.items():
            data = parse_x_post(post); data["economic"] = price
            _lf.update_from_metaprogram({**data, "mode": _lf.mode})
    print(LocalForecaster.compare_groups(forecasters))
