"""
Модуль: analytics_predictor.py (Lastivka)

Поєднує три компоненти: Аналіз → Прогноз → Аналітика (рекомендації).
Без зовнішніх залежностей. Готовий до вбудовування у lastivka_core.

Пропоноване розміщення:
  C:\Lastivka\lastivka_core\core\analytics\analytics_predictor.py

Публічний інтерфейс:
  - run_pipeline(records, horizon, options) → AnalyticsResult
  - Analyzer.analyze(records) → AnalysisReport
  - Forecaster.forecast(records, horizon, method) → ForecastReport
  - Strategist.recommend(analysis, forecast, policy) → StrategyReport

Дані вхідних записів: EventRecord(ts: datetime, value: float, tags: list[str], ctx: dict)

Автор: Софія Ластівка
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable, Tuple
import math
import statistics
from collections import defaultdict, deque

# =============================
# Схеми даних результатів
# =============================

@dataclass
class EventRecord:
    ts: datetime
    value: float
    tags: List[str] = field(default_factory=list)
    ctx: Dict[str, float | int | str] = field(default_factory=dict)

@dataclass
class Pattern:
    name: str
    score: float
    details: Dict[str, float] = field(default_factory=dict)

@dataclass
class AnalysisReport:
    count: int
    time_span_h: float
    mean: float
    stdev: float
    slope_per_h: float
    volatility: float
    last_value: Optional[float]
    z_anomalies_idx: List[int]
    patterns: List[Pattern]

@dataclass
class Scenario:
    name: str
    expected: float
    low: float
    high: float
    probability: float

@dataclass
class ForecastReport:
    horizon_h: int
    method: str
    baseline: float
    scenarios: List[Scenario]

@dataclass
class StrategyAction:
    title: str
    reason: str
    priority: int  # 1..5 (5 — найвищий)

@dataclass
class StrategyReport:
    risk_level: str  # "low" | "medium" | "high"
    actions: List[StrategyAction]
    notes: List[str] = field(default_factory=list)

@dataclass
class AnalyticsResult:
    analysis: AnalysisReport
    forecast: ForecastReport
    strategy: StrategyReport

# =============================
# Утиліти
# =============================

def _safe_stdev(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    try:
        return statistics.stdev(values)
    except statistics.StatisticsError:
        return 0.0


def _linear_regression_slope(xs: List[float], ys: List[float]) -> float:
    """Повертає нахил (slope) простої лінійної регресії y = a + b*x."""
    n = len(xs)
    if n < 2:
        return 0.0
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den = sum((x - mean_x) ** 2 for x in xs)
    return (num / den) if den != 0 else 0.0


def _z_scores(values: List[float]) -> List[float]:
    m = statistics.mean(values) if values else 0.0
    s = _safe_stdev(values)
    if s == 0:
        return [0.0 for _ in values]
    return [(v - m) / s for v in values]


# =============================
# 1) Аналіз
# =============================

class Analyzer:
    """Розбирає минулі дані: тренд, волатильність, аномалії, прості патерни."""

    def analyze(self, records: List[EventRecord]) -> AnalysisReport:
        if not records:
            now = datetime.utcnow()
            return AnalysisReport(
                count=0,
                time_span_h=0.0,
                mean=0.0,
                stdev=0.0,
                slope_per_h=0.0,
                volatility=0.0,
                last_value=None,
                z_anomalies_idx=[],
                patterns=[],
            )

        records_sorted = sorted(records, key=lambda r: r.ts)
        values = [r.value for r in records_sorted]
        t0, tN = records_sorted[0].ts, records_sorted[-1].ts
        span_h = max((tN - t0).total_seconds() / 3600.0, 1e-9)

        # Побудуємо часову вісь у годинах від t0
        xs = [max((r.ts - t0).total_seconds() / 3600.0, 0.0) for r in records_sorted]
        slope = _linear_regression_slope(xs, values)  # зміна value на годину
        stdev = _safe_stdev(values)
        mean = statistics.mean(values)
        volatility = stdev / mean if mean != 0 else 0.0

        # Z-аномалії (|z| > 2)
        z = _z_scores(values)
        anomalies_idx = [i for i, z_i in enumerate(z) if abs(z_i) > 2.0]

        patterns = self._extract_patterns(records_sorted, values, xs, mean, stdev)

        return AnalysisReport(
            count=len(records_sorted),
            time_span_h=span_h,
            mean=mean,
            stdev=stdev,
            slope_per_h=slope,
            volatility=volatility,
            last_value=values[-1] if values else None,
            z_anomalies_idx=anomalies_idx,
            patterns=patterns,
        )

    def _extract_patterns(
        self,
        recs: List[EventRecord],
        values: List[float],
        xs: List[float],
        mean: float,
        stdev: float,
    ) -> List[Pattern]:
        pats: List[Pattern] = []

        # Патерн 1: стійкий тренд (нахил суттєвий щодо шуму)
        slope = _linear_regression_slope(xs, values)
        noise = stdev if stdev > 0 else 1e-9
        trend_score = abs(slope) / (noise + 1e-9)
        pats.append(Pattern(name="trend_strength", score=trend_score, details={"slope": slope, "noise": noise}))

        # Патерн 2: кластер по тегам (які теги найчастіші)
        tag_counts: Dict[str, int] = defaultdict(int)
        for r in recs:
            for t in r.tags:
                tag_counts[t] += 1
        if tag_counts:
            top_tag, top_cnt = max(tag_counts.items(), key=lambda kv: kv[1])
            tag_score = top_cnt / max(len(recs), 1)
            pats.append(Pattern(name="top_tag", score=tag_score, details={"tag": top_tag, "count": float(top_cnt)}))

        # Патерн 3: імпульс (останні 3 точки зростають/падають)
        if len(values) >= 3:
            last3 = values[-3:]
            up = last3[0] < last3[1] < last3[2]
            down = last3[0] > last3[1] > last3[2]
            if up or down:
                pats.append(Pattern(name="momentum", score=1.0, details={"direction": 1.0 if up else -1.0}))

        return pats


# =============================
# 2) Прогноз
# =============================

class Forecaster:
    """Створює кілька сценаріїв на горизонті: базовий, оптимістичний, песимістичний."""

    def forecast(
        self,
        records: List[EventRecord],
        horizon_h: int = 24,
        method: str = "auto",
    ) -> ForecastReport:
        if not records:
            return ForecastReport(
                horizon_h=horizon_h,
                method=method,
                baseline=0.0,
                scenarios=[
                    Scenario("base", 0.0, 0.0, 0.0, 1.0),
                ],
            )

        records_sorted = sorted(records, key=lambda r: r.ts)
        values = [r.value for r in records_sorted]
        t0 = records_sorted[0].ts
        xs = [max((r.ts - t0).total_seconds() / 3600.0, 0.0) for r in records_sorted]

        # Автовибір: якщо сильно шумно — використовуємо EWMA, інакше лінійний тренд
        stdev = _safe_stdev(values)
        mean = statistics.mean(values)
        volatility = (stdev / mean) if mean else 0.0
        use_ewma = volatility > 0.5

        if method == "auto":
            method = "ewma" if use_ewma else "linear"

        if method == "linear":
            slope = _linear_regression_slope(xs, values)
            baseline = values[-1] + slope * horizon_h
            sigma = stdev
        else:  # "ewma"
            alpha = 2 / (min(len(values), 20) + 1)  # класична формула EWMA
            ema = values[0]
            for v in values[1:]:
                ema = alpha * v + (1 - alpha) * ema
            baseline = ema
            sigma = _safe_stdev(values[-min(len(values), 10):])

        # Сценарії: базовий, оптимістичний, песимістичний
        # Розкид залежить від волатильності (sigma)
        delta = 1.0 * sigma if sigma > 0 else max(0.05 * abs(baseline), 0.1)
        scenarios = [
            Scenario("base", baseline, baseline - 0.5 * delta, baseline + 0.5 * delta, 0.6),
            Scenario("optimistic", baseline + 1.0 * delta, baseline, baseline + 2.0 * delta, 0.2),
            Scenario("pessimistic", baseline - 1.0 * delta, baseline - 2.0 * delta, baseline, 0.2),
        ]

        return ForecastReport(
            horizon_h=horizon_h,
            method=method,
            baseline=baseline,
            scenarios=scenarios,
        )


# =============================
# 3) Аналітика (рішення/рекомендації)
# =============================

class Strategist:
    """Перетворює аналіз+прогноз у практичні дії відповідно до простої політики."""

    def recommend(
        self,
        analysis: AnalysisReport,
        forecast: ForecastReport,
        policy: Optional[Dict[str, float]] = None,
    ) -> StrategyReport:
        policy = policy or {
            "high_volatility": 0.8,    # відносна волатильність
            "trend_slope_abs": 0.05,   # мінімальний |slope|/год для активної дії
            "anomaly_frac": 0.1,       # частка аномалій для підвищеного ризику
        }

        actions: List[StrategyAction] = []
        notes: List[str] = []

        # Оцінка ризику
        anom_frac = (len(analysis.z_anomalies_idx) / max(analysis.count, 1)) if analysis.count else 0.0
        risk_score = 0.0
        risk_score += min(1.0, analysis.volatility / max(policy["high_volatility"], 1e-9)) * 0.5
        risk_score += min(1.0, anom_frac / max(policy["anomaly_frac"], 1e-9)) * 0.5
        risk_level = "low" if risk_score < 0.33 else ("medium" if risk_score < 0.66 else "high")

        # Дії залежно від тренду
        slope = analysis.slope_per_h
        slope_abs = abs(slope)
        if slope_abs >= policy["trend_slope_abs"]:
            if slope > 0:
                actions.append(StrategyAction(
                    title="Підсилити напрямок зростання",
                    reason=f"Позитивний тренд {slope:.4f}/год",
                    priority=4,
                ))
            else:
                actions.append(StrategyAction(
                    title="Гасити спад",
                    reason=f"Негативний тренд {slope:.4f}/год",
                    priority=4,
                ))
        else:
            actions.append(StrategyAction(
                title="Тримати курс",
                reason="Тренд слабкий/нейтральний",
                priority=2,
            ))

        # Дії залежно від прогнозу (сценарії)
        base = next((s for s in forecast.scenarios if s.name == "base"), None)
        if base:
            width = base.high - base.low
            if width > max(0.2 * abs(base.expected), 0.1):
                actions.append(StrategyAction(
                    title="Зменшити невизначеність",
                    reason=f"Широкий коридор прогнозу ±{width/2:.3f}",
                    priority=3,
                ))

        # Високий ризик — завжди мати план Б
        if risk_level == "high":
            actions.append(StrategyAction(
                title="Активувати план Б",
                reason="Високий ризик (волатильність/аномалії)",
                priority=5,
            ))

        # Нотатки/пояснення
        notes.append(f"volatility={analysis.volatility:.3f}, anomalies={len(analysis.z_anomalies_idx)}")
        notes.append(f"forecast_method={forecast.method}, baseline={forecast.baseline:.3f}")

        # Сортування за пріоритетом (вищий перший)
        actions.sort(key=lambda a: a.priority, reverse=True)

        return StrategyReport(
            risk_level=risk_level,
            actions=actions,
            notes=notes,
        )


# =============================
# 4) Суцільний конвеєр
# =============================

class LastivkaAnalytics:
    def __init__(self,
                 analyzer: Optional[Analyzer] = None,
                 forecaster: Optional[Forecaster] = None,
                 strategist: Optional[Strategist] = None):
        self.analyzer = analyzer or Analyzer()
        self.forecaster = forecaster or Forecaster()
        self.strategist = strategist or Strategist()

    def run(self,
            records: List[EventRecord],
            horizon_h: int = 24,
            method: str = "auto",
            policy: Optional[Dict[str, float]] = None) -> AnalyticsResult:
        analysis = self.analyzer.analyze(records)
        forecast = self.forecaster.forecast(records, horizon_h=horizon_h, method=method)
        strategy = self.strategist.recommend(analysis, forecast, policy)
        return AnalyticsResult(analysis=analysis, forecast=forecast, strategy=strategy)


# =============================
# 5) Зручна точка входу
# =============================

def run_pipeline(records: List[EventRecord],
                 horizon_h: int = 24,
                 method: str = "auto",
                 policy: Optional[Dict[str, float]] = None) -> AnalyticsResult:
    return LastivkaAnalytics().run(records, horizon_h=horizon_h, method=method, policy=policy)


# =============================
# 6) Приклад використання (локальний тест)
# =============================
if __name__ == "__main__":
    # Невеликий синтетичний приклад
    now = datetime.utcnow()
    data = [
        EventRecord(ts=now + timedelta(hours=i), value=10 + 0.2 * i + (1 if i % 5 == 0 else 0), tags=["alpha"]) for i in range(24)
    ]
    res = run_pipeline(data, horizon_h=12)

    # Короткий вивід
    print("Analysis:", res.analysis)
    print("Forecast:", res.forecast)
    print("Strategy:")
    for a in res.strategy.actions:
        print("  -", a)
    print("Notes:", res.strategy.notes)
