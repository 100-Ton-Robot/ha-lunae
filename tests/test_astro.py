"""Check the astronomy module against PyEphem reference values (reference.json).

Tolerances are about 1.5x the worst error seen over 300 random samples
(2020-2032, six latitudes from -55 to +65) when the module was written.
"""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "custom_components" / "lunae"))
import astro  # noqa: E402

ROWS = json.loads(Path(__file__).with_name("reference.json").read_text())["rows"]

TOL_ANGLE = 0.15          # degrees, azimuth (scaled by cos elevation) and elevation
TOL_ILLUMINATION = 0.5    # percent
TOL_SIZE = 0.003          # degrees
TOL_RISE_SET = 3          # minutes
TOL_FULL_NEW = 15         # minutes


def _ids(row):
    return f"{row['place']}-{row['when'][:16]}"


@pytest.fixture(params=ROWS, ids=_ids)
def case(request):
    row = request.param
    when = datetime.fromisoformat(row["when"])
    return row, when, astro.compute(row["lat"], row["lon"], when)


def _minutes(a: datetime, b_iso: str) -> float:
    return abs((a - datetime.fromisoformat(b_iso)).total_seconds()) / 60


def test_position(case):
    row, _, state = case
    import math
    daz = abs((state.azimuth - row["azimuth"] + 180) % 360 - 180) * math.cos(math.radians(row["elevation"]))
    assert daz < TOL_ANGLE
    assert abs(state.elevation - row["elevation"]) < TOL_ANGLE


def test_illumination_and_size(case):
    row, _, state = case
    assert abs(state.illumination - row["illumination"]) < TOL_ILLUMINATION
    assert abs(state.angular_size - row["angular_size"]) < TOL_SIZE
    assert astro.ANGULAR_SIZE_MIN <= state.angular_size <= astro.ANGULAR_SIZE_MAX


def test_full_and_new(case):
    row, when, state = case
    assert state.next_full_moon > when and state.next_new_moon > when
    assert _minutes(state.next_full_moon, row["next_full_moon"]) < TOL_FULL_NEW
    assert _minutes(state.next_new_moon, row["next_new_moon"]) < TOL_FULL_NEW


@pytest.mark.parametrize("key", ["next_rising", "next_setting"])
def test_rise_set(case, key):
    row, when, state = case
    ours, ref = getattr(state, key), row[key]
    if ref is None or datetime.fromisoformat(ref) - when > timedelta(hours=26):
        assert ours is None or ours - when <= timedelta(hours=26)
        return
    assert ours is not None
    assert _minutes(ours, ref) < TOL_RISE_SET


def test_above_horizon_matches_events(case):
    """Above horizon exactly when the next setting comes before the next rising."""
    _, _, state = case
    if state.next_rising and state.next_setting:
        assert state.above_horizon == (state.next_setting < state.next_rising)


@pytest.mark.parametrize(
    ("elong", "phase"),
    [(0, "new_moon"), (5, "new_moon"), (355, "new_moon"), (45, "waxing_crescent"),
     (90, "first_quarter"), (135, "waxing_gibbous"), (180, "full_moon"),
     (225, "waning_gibbous"), (270, "last_quarter"), (315, "waning_crescent")],
)
def test_phase_names(elong, phase):
    assert astro._phase_name(elong) == phase


def test_geocentric(case):
    row, when, state = case
    geo = astro.compute_geocentric(when)
    assert abs(geo.angular_size - row["geo_angular_size"]) < TOL_SIZE
    assert astro.GEO_ANGULAR_SIZE_MIN <= geo.angular_size <= astro.GEO_ANGULAR_SIZE_MAX
    assert abs(geo.illumination - row["illumination"]) < TOL_ILLUMINATION
    assert geo.next_full_moon == state.next_full_moon and geo.next_new_moon == state.next_new_moon
    for key in ("azimuth", "elevation", "above_horizon", "next_rising", "next_setting"):
        assert getattr(geo, key) is None
