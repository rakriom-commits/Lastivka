# test_predictor_v2e.py
import pytest
from models import predictor_v2e_merged as pv2

def test_basic_flow():
    lf = pv2.LocalForecaster(mode="psyops", bern_half_life_sec=1800, cont_half_life_sec=1800)
    ctx = {"source_id": "u1", "followers": 100, "retweets": 5, "sentiment": 0.6}
    lf.observe_continuous(0.6, context=ctx)
    lf.observe_binary(1, context=ctx)
    lf.observe_economic(101.0, context=ctx)

    assert lf.forecast_binary()["p"] >= 0.0
    assert "explain_binary" in lf.get_state()
    assert lf.forecast_economic()["ready"]

def test_invalid_inputs():
    lf = pv2.LocalForecaster()
    res_nan = lf.observe_continuous(float("nan"))
    res_inf = lf.observe_continuous(float("inf"))
    assert res_nan.get("skipped")
    assert res_inf.get("skipped")

def test_manipulation_detect():
    lf = pv2.LocalForecaster()
    ctx = {"source_id": "spam", "followers": 10, "retweets": 200, "sentiment": 0.9}
    for _ in range(int(lf.manipulation_threshold)):
        lf.observe_binary(1, context=ctx)
    assert any(e["type"] == "manipulation" for e in lf.events)
