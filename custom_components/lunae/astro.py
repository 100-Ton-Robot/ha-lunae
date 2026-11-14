"""Moon position, phase and events — pure Python, no dependencies.

Low-precision analytic theory after Paul Schlyter, "How to compute planetary
positions" (https://stjarnhimlen.se/comp/ppcomp.html), with the lunar
longitude, latitude and distance perturbation terms. Positions are made
topocentric (seen from the observer, not the Earth's centre) before being
converted to azimuth/elevation, so elevation and angular size are what an
observer at the given location actually sees.

This module must not import Home Assistant: the tests load it on its own.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

EARTH_RADIUS_KM = 6378.14
MOON_RADIUS_KM = 1737.4
AU_IN_EARTH_RADII = 23454.8
SYNODIC_RATE = 360.0 / 29.530588853  # mean elongation change, degrees per day

# Fixed all-time limits of the topocentric apparent diameter, in degrees. They
# bracket every value the sensor can report, including while the Moon is down:
#   min: farthest apogee (~406,720 km) seen from the far side of the Earth (nadir).
#   max: closest perigee (~356,370 km) seen from directly beneath it (zenith).
ANGULAR_SIZE_MIN = round(
    math.degrees(2 * math.asin(MOON_RADIUS_KM / (406720.0 + EARTH_RADIUS_KM))), 3
)
ANGULAR_SIZE_MAX = round(
    math.degrees(2 * math.asin(MOON_RADIUS_KM / (356370.0 - EARTH_RADIUS_KM))), 3
)
# The same limits seen from the Earth's centre (geocentric mode).
GEO_ANGULAR_SIZE_MIN = round(math.degrees(2 * math.asin(MOON_RADIUS_KM / 406720.0)), 3)
GEO_ANGULAR_SIZE_MAX = round(math.degrees(2 * math.asin(MOON_RADIUS_KM / 356370.0)), 3)

# Altitude of the Moon's centre at rise/set for an observer: upper limb on the
# horizon with standard refraction (34'). The semi-diameter is added per instant.
REFRACTION_AT_HORIZON = 34.0 / 60.0

# Principal phases (new, quarters, full) are reported for half a day either side
# of the exact instant — the same ~1-day window HA's built-in Moon integration uses.
PRINCIPAL_PHASE_HALF_WIDTH = SYNODIC_RATE / 2

PHASES = [
    "new_moon",
    "waxing_crescent",
    "first_quarter",
    "waxing_gibbous",
    "full_moon",
    "waning_gibbous",
    "last_quarter",
    "waning_crescent",
]


@dataclass(frozen=True)
class MoonState:
    """Everything the integration exposes, for one instant and one viewpoint.

    In geocentric mode there is no horizon, so azimuth, elevation,
    above_horizon, next_rising and next_setting are None.
    """

    azimuth: float | None       # degrees, N=0 clockwise
    elevation: float | None     # degrees, topocentric, geometric (no refraction)
    illumination: float         # percent of the disk lit
    phase: str                  # one of PHASES
    angular_size: float         # degrees, apparent diameter from the viewpoint
    above_horizon: bool | None  # upper limb above the horizon, with refraction
    next_rising: datetime | None
    next_setting: datetime | None
    next_full_moon: datetime
    next_new_moon: datetime


def _rev(x: float) -> float:
    return x % 360.0


def _sind(x: float) -> float:
    return math.sin(math.radians(x))


def _cosd(x: float) -> float:
    return math.cos(math.radians(x))


def _day_number(when: datetime) -> float:
    """Days since 2000 Jan 0.0 UT (Schlyter's d)."""
    return when.timestamp() / 86400.0 + 2440587.5 - 2451543.5


def _kepler(m_deg: float, e: float) -> float:
    m = math.radians(m_deg)
    ecc = m + e * math.sin(m) * (1.0 + e * math.cos(m))
    for _ in range(10):
        ecc -= (ecc - e * math.sin(ecc) - m) / (1.0 - e * math.cos(ecc))
    return math.degrees(ecc)


def _sun(d: float) -> tuple[float, float, float]:
    """Sun ecliptic longitude (deg), distance (AU), mean longitude (deg)."""
    w = 282.9404 + 4.70935e-5 * d
    e = 0.016709 - 1.151e-9 * d
    m = _rev(356.0470 + 0.9856002585 * d)
    ecc = _kepler(m, e)
    xv = _cosd(ecc) - e
    yv = math.sqrt(1.0 - e * e) * _sind(ecc)
    v = math.degrees(math.atan2(yv, xv))
    r = math.hypot(xv, yv)
    return _rev(v + w), r, _rev(m + w)


def _moon_ecliptic(d: float) -> tuple[float, float, float]:
    """Moon geocentric ecliptic longitude, latitude (deg) and distance (Earth radii)."""
    n = _rev(125.1228 - 0.0529538083 * d)
    i = 5.1454
    w = _rev(318.0634 + 0.1643573223 * d)
    a = 60.2666
    e = 0.054900
    m = _rev(115.3654 + 13.0649929509 * d)

    ecc = _kepler(m, e)
    xv = a * (_cosd(ecc) - e)
    yv = a * math.sqrt(1.0 - e * e) * _sind(ecc)
    v = math.degrees(math.atan2(yv, xv))
    r = math.hypot(xv, yv)

    xh = r * (_cosd(n) * _cosd(v + w) - _sind(n) * _sind(v + w) * _cosd(i))
    yh = r * (_sind(n) * _cosd(v + w) + _cosd(n) * _sind(v + w) * _cosd(i))
    zh = r * _sind(v + w) * _sind(i)
    lon = math.degrees(math.atan2(yh, xh))
    lat = math.degrees(math.atan2(zh, math.hypot(xh, yh)))

    ms = _rev(356.0470 + 0.9856002585 * d)            # Sun mean anomaly
    ls = _rev(ms + 282.9404 + 4.70935e-5 * d)          # Sun mean longitude
    lm = _rev(n + w + m)                               # Moon mean longitude
    dd = _rev(lm - ls)                                 # mean elongation
    f = _rev(lm - n)                                   # argument of latitude

    lon += (
        -1.274 * _sind(m - 2 * dd)
        + 0.658 * _sind(2 * dd)
        - 0.186 * _sind(ms)
        - 0.059 * _sind(2 * m - 2 * dd)
        - 0.057 * _sind(m - 2 * dd + ms)
        + 0.053 * _sind(m + 2 * dd)
        + 0.046 * _sind(2 * dd - ms)
        + 0.041 * _sind(m - ms)
        - 0.035 * _sind(dd)
        - 0.031 * _sind(m + ms)
        - 0.015 * _sind(2 * f - 2 * dd)
        + 0.011 * _sind(m - 4 * dd)
    )
    lat += (
        -0.173 * _sind(f - 2 * dd)
        - 0.055 * _sind(m - f - 2 * dd)
        - 0.046 * _sind(m + f - 2 * dd)
        + 0.033 * _sind(f + 2 * dd)
        + 0.017 * _sind(2 * m + f)
    )
    r += -0.58 * _cosd(m - 2 * dd) - 0.46 * _cosd(2 * dd)
    return _rev(lon), lat, r


def _elongation(d: float) -> float:
    """Moon minus Sun ecliptic longitude, 0..360 (0 = new, 180 = full)."""
    moon_lon, _, _ = _moon_ecliptic(d)
    sun_lon, _, _ = _sun(d)
    return _rev(moon_lon - sun_lon)


def _illumination(d: float) -> float:
    """Illuminated fraction of the disk, 0..1."""
    moon_lon, moon_lat, moon_r = _moon_ecliptic(d)
    sun_lon, sun_r, _ = _sun(d)
    cos_elong = _cosd(moon_lat) * _cosd(moon_lon - sun_lon)
    elong = math.acos(max(-1.0, min(1.0, cos_elong)))
    sun_er = sun_r * AU_IN_EARTH_RADII
    phase_angle = math.atan2(sun_er * math.sin(elong), moon_r - sun_er * math.cos(elong))
    return (1.0 + math.cos(phase_angle)) / 2.0


def _topocentric(d: float, lat: float, lon: float) -> tuple[float, float, float]:
    """Topocentric azimuth (deg), elevation (deg) and distance (km)."""
    moon_lon, moon_lat, r = _moon_ecliptic(d)

    # Geocentric ecliptic → equatorial rectangular (Earth radii)
    obliquity = 23.4393 - 3.563e-7 * d
    x = r * _cosd(moon_lon) * _cosd(moon_lat)
    y = r * _sind(moon_lon) * _cosd(moon_lat)
    z = r * _sind(moon_lat)
    ye = y * _cosd(obliquity) - z * _sind(obliquity)
    ze = y * _sind(obliquity) + z * _cosd(obliquity)

    # Local sidereal time (deg) from the IAU 1982 GMST expression
    jd = d + 2451543.5
    lst = _rev(280.46061837 + 360.98564736629 * (jd - 2451545.0) + lon)

    # Observer on the reference ellipsoid (geocentric latitude and radius)
    gclat = lat - 0.1924 * _sind(2 * lat)
    rho = 0.99833 + 0.00167 * _cosd(2 * lat)
    x -= rho * _cosd(gclat) * _cosd(lst)
    ye -= rho * _cosd(gclat) * _sind(lst)
    ze -= rho * _sind(gclat)

    dist = math.sqrt(x * x + ye * ye + ze * ze)
    ra = math.degrees(math.atan2(ye, x))
    dec = math.degrees(math.asin(ze / dist))
    ha = lst - ra

    # Equatorial → horizontal, horizon defined by geodetic latitude
    xh = _cosd(ha) * _cosd(dec) * _sind(lat) - _sind(dec) * _cosd(lat)
    yh = _sind(ha) * _cosd(dec)
    zh = _cosd(ha) * _cosd(dec) * _cosd(lat) + _sind(dec) * _sind(lat)
    az = _rev(math.degrees(math.atan2(yh, xh)) + 180.0)
    alt = math.degrees(math.asin(max(-1.0, min(1.0, zh))))
    return az, alt, dist * EARTH_RADIUS_KM


def _angular_size(dist_km: float) -> float:
    return math.degrees(2 * math.asin(MOON_RADIUS_KM / dist_km))


def _horizon_margin(d: float, lat: float, lon: float) -> float:
    """Degrees by which the upper limb (with refraction) is above the horizon."""
    _, alt, dist = _topocentric(d, lat, lon)
    return alt + REFRACTION_AT_HORIZON + _angular_size(dist) / 2


def _phase_name(elong: float) -> str:
    half = PRINCIPAL_PHASE_HALF_WIDTH
    if elong < half or elong >= 360 - half:
        return "new_moon"
    for idx, centre in ((2, 90.0), (4, 180.0), (6, 270.0)):
        if abs(elong - centre) < half:
            return PHASES[idx]
    if elong < 90:
        return "waxing_crescent"
    if elong < 180:
        return "waxing_gibbous"
    if elong < 270:
        return "waning_gibbous"
    return "waning_crescent"


def _from_day_number(d: float) -> datetime:
    return datetime.fromtimestamp((d + 2451543.5 - 2440587.5) * 86400.0, tz=timezone.utc)


def _next_elongation(d0: float, target: float) -> float:
    """First day number after d0 at which the elongation equals target."""
    ahead = _rev(target - _elongation(d0))
    if ahead < 1e-6:
        ahead += 360.0
    d = d0 + ahead / SYNODIC_RATE
    for _ in range(20):
        err = (target - _elongation(d) + 180.0) % 360.0 - 180.0
        d += err / SYNODIC_RATE
        if abs(err) < 1e-6:
            break
    return d


def _rise_set(d0: float, lat: float, lon: float) -> tuple[float | None, float | None]:
    """Next rising and setting after d0 (day numbers), searching 26 hours ahead."""
    step = 10.0 / 1440.0
    rising = setting = None
    d = d0
    prev = _horizon_margin(d, lat, lon)
    for _ in range(int(26 * 6)):
        d_next = d + step
        cur = _horizon_margin(d_next, lat, lon)
        if (prev < 0 <= cur and rising is None) or (prev >= 0 > cur and setting is None):
            going_up = prev < 0
            lo, hi = d, d_next
            for _ in range(12):  # 10 min / 2^12 ≈ 0.15 s
                mid = (lo + hi) / 2
                up = _horizon_margin(mid, lat, lon) >= 0
                if up == going_up:
                    hi = mid
                else:
                    lo = mid
            if going_up:
                rising = hi
            else:
                setting = hi
            if rising is not None and setting is not None:
                break
        d, prev = d_next, cur
    return rising, setting


def _to_minute(when: datetime) -> datetime:
    """Round to the nearest minute — the model is good to a minute or two, and
    whole minutes stop the timestamp sensors writing a new state every update."""
    return (when + timedelta(seconds=30)).replace(second=0, microsecond=0)


def compute_geocentric(when: datetime) -> MoonState:
    """Moon state seen from the Earth's centre: no horizon-dependent values."""
    d = _day_number(when)
    _, _, r = _moon_ecliptic(d)
    return MoonState(
        azimuth=None,
        elevation=None,
        illumination=round(_illumination(d) * 100.0, 1),
        phase=_phase_name(_elongation(d)),
        angular_size=round(_angular_size(r * EARTH_RADIUS_KM), 4),
        above_horizon=None,
        next_rising=None,
        next_setting=None,
        next_full_moon=_to_minute(_from_day_number(_next_elongation(d, 180.0))),
        next_new_moon=_to_minute(_from_day_number(_next_elongation(d, 0.0))),
    )


def compute(lat: float, lon: float, when: datetime) -> MoonState:
    """Moon state for an observer at (lat, lon) degrees at an aware datetime."""
    d = _day_number(when)
    az, alt, dist = _topocentric(d, lat, lon)
    size = _angular_size(dist)
    rising, setting = _rise_set(d, lat, lon)
    return MoonState(
        azimuth=round(az, 2),
        elevation=round(alt, 2),
        illumination=round(_illumination(d) * 100.0, 1),
        phase=_phase_name(_elongation(d)),
        angular_size=round(size, 4),
        above_horizon=alt + REFRACTION_AT_HORIZON + size / 2 > 0,
        next_rising=_to_minute(_from_day_number(rising)) if rising is not None else None,
        next_setting=_to_minute(_from_day_number(setting)) if setting is not None else None,
        next_full_moon=_to_minute(_from_day_number(_next_elongation(d, 180.0))),
        next_new_moon=_to_minute(_from_day_number(_next_elongation(d, 0.0))),
    )
