"""Regenerate reference.json from PyEphem (dev only: pip install ephem).

PyEphem is used only to produce fixed reference values; the integration
itself has no dependencies.
"""
import json
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import ephem

PLACES = {
    "greenwich": (51.4779, 0.0),
    "new_york": (40.7128, -74.006),
    "sydney": (-33.8688, 151.2093),
    "quito": (-0.1807, -78.4678),
    "fairbanks": (64.8378, -147.7164),
    "ushuaia": (-54.8019, -68.303),
}


def _event(func):
    try:
        return func(ephem.Moon(), use_center=False).datetime().replace(tzinfo=timezone.utc).isoformat()
    except (ephem.NeverUpError, ephem.AlwaysUpError):
        return None


def main() -> None:
    rng = random.Random(20261113)
    rows = []
    names = list(PLACES)
    for n in range(60):
        place = names[n % len(names)]
        lat, lon = PLACES[place]
        when = datetime(2020, 1, 1, tzinfo=timezone.utc) + timedelta(
            seconds=int(rng.uniform(0, 12 * 365.25 * 86400))
        )
        obs = ephem.Observer()
        obs.lat, obs.lon, obs.elevation = str(lat), str(lon), 0
        obs.date = when.replace(tzinfo=None)
        obs.pressure = 0  # geometric positions; rise/set use the 34' horizon below
        obs.horizon = "-0:34"
        moon = ephem.Moon(obs)
        rows.append({
            "place": place,
            "lat": lat,
            "lon": lon,
            "when": when.isoformat(),
            "azimuth": round(math.degrees(moon.az), 4),
            "elevation": round(math.degrees(moon.alt), 4),
            "illumination": round(moon.moon_phase * 100, 3),
            "angular_size": round(moon.size / 3600, 5),
            "next_rising": _event(obs.next_rising),
            "next_setting": _event(obs.next_setting),
            "next_full_moon": ephem.next_full_moon(obs.date).datetime().replace(tzinfo=timezone.utc).isoformat(),
            "next_new_moon": ephem.next_new_moon(obs.date).datetime().replace(tzinfo=timezone.utc).isoformat(),
        })
    out = Path(__file__).with_name("reference.json")
    out.write_text(json.dumps({"source": f"PyEphem {ephem.__version__}", "rows": rows}, indent=1) + "\n")
    print(f"wrote {len(rows)} rows to {out}")


if __name__ == "__main__":
    main()
