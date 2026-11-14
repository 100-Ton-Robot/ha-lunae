# Lunae

Moon position, phase, apparent size and events for Home Assistant — calculated
locally for one or more locations, with no cloud service and no dependencies.

Home Assistant's built-in Moon integration gives only the phase. Lunae adds where
the Moon is in your sky, how much of it is lit, how big it looks, and when it
next rises, sets, is full and is new.

## Install

Settings → Marketplace → ⋮ → Add from link → `https://github.com/100-Ton-Robot/ha-lunae`
(category: Integration), install, restart Home Assistant.

Then Settings → Devices & services → Add integration → **Lunae**, and choose:

- **Map location** — values as seen from a place. The form opens on your home
  location; pick another point on the map for a different place. Add the
  integration again for each extra location — each gets its own device and
  entities. Change a location later with **Reconfigure** on the entry.
- **Centre of the Earth** — values as seen from the Earth's centre, the viewpoint
  almanacs use (one entry only). There is no horizon there, so azimuth,
  elevation, above horizon, moonrise and moonset are created **disabled**; if
  enabled they stay `unknown`. Angular size uses the geocentric limits
  `min` 0.490 ° / `max` 0.559 °.

## Versions

Install and update from [releases](https://github.com/100-Ton-Robot/ha-lunae/releases);
the Marketplace offers releases only. The `dev` branch is work in progress and
may change at any time — the version in `manifest.json` matches the release tag.

## Entities

Shown for an entry named "Lunae" (the default for the first entry). Example values
are real output for Greenwich at 2026-11-14 18:00 UTC; times are UTC.

| Entity | Example | Notes |
|---|---|---|
| `binary_sensor.lunae_above_horizon` | on | Upper limb above the horizon, with standard refraction — flips exactly at moonrise/moonset |
| `sensor.lunae_azimuth` | 206.8 ° | 0 = north, clockwise (same as `sun.sun`) |
| `sensor.lunae_elevation` | 9.2 ° | Geometric, as seen from the location; negative below the horizon |
| `sensor.lunae_illumination` | 25.2 % | Lit fraction of the disk |
| `sensor.lunae_phase` | waxing_crescent | `new_moon`, `waxing_crescent`, `first_quarter`, `waxing_gibbous`, `full_moon`, `waning_gibbous`, `last_quarter`, `waning_crescent`. The four principal phases are reported for half a day either side of the exact instant |
| `sensor.lunae_angular_size` | 0.493 ° | Apparent diameter seen from the location. Attributes `min` (0.482 °) and `max` (0.569 °) are the fixed all-time limits |
| `sensor.lunae_next_moonrise` | 2026-11-15 12:40 | Timestamp; unknown if the Moon doesn't rise in the next 26 hours (polar regions) |
| `sensor.lunae_next_moonset` | 2026-11-14 19:50 | Timestamp; as above |
| `sensor.lunae_next_full_moon` | 2026-11-24 15:02 | Timestamp |
| `sensor.lunae_next_new_moon` | 2026-12-09 00:51 | Timestamp |

Everything updates once a minute. Timestamps are rounded to the minute.

## Recorder (optional)

Every Lunae entity is recorded by default. The non-numeric ones — the four
timestamps, the phase and above horizon — change rarely (rise/set about once a
day, full/new about once a month, phase eight times a month), so they add very
little to the database. To leave them out anyway, add globs to your
[recorder](https://www.home-assistant.io/integrations/recorder/) exclude:

```yaml
recorder:
  exclude:
    entity_globs:
      - sensor.*lunae*_next_*              # next moonrise, moonset, full moon, new moon
      - sensor.*lunae*_phase
      - binary_sensor.*lunae*_above_horizon
```

The globs match any entity ID containing "lunae", so they still match when Home
Assistant adds an area or device name in front (e.g. `sensor.lunae_next_moonrise`,
`sensor.outside_lunae_home_next_moonrise`, `sensor.lunae_geocentric_phase`). For
an entry whose name doesn't contain "Lunae", use its entity IDs instead. Excluded entities have no history
or logbook; already recorded rows stay until the recorder purges them. Recorder
settings take effect after a Home Assistant restart. The constant `min`/`max`
attributes of angular size are never recorded.

## InfluxDB (optional)

The [InfluxDB](https://www.home-assistant.io/integrations/influxdb/) integration
sends every state change, and every attribute as a field. The connection is set
up in the UI, but its filters still come from the `influxdb:` section of
`configuration.yaml`. To leave out the same non-numeric entities:

```yaml
influxdb:
  exclude:
    entity_globs:
      - sensor.*lunae*_next_*              # next moonrise, moonset, full moon, new moon
      - sensor.*lunae*_phase
      - binary_sensor.*lunae*_above_horizon
```

The angular size `min`/`max` attributes do reach InfluxDB (Lunae keeps them out
of the recorder only). They are worth keeping there: a graph can use them as
fixed axis bounds, showing where the current size sits in the full possible
range rather than auto-scaling to the span of the data. If your `influxdb:`
section has an `include:` filter, Lunae entities are only sent when they match
it, and the exclude still applies on top. Restart Home Assistant after changing
these settings.

## Accuracy

Lunae uses Paul Schlyter's low-precision analytic theory
([How to compute planetary positions](https://stjarnhimlen.se/comp/ppcomp.html))
with the lunar perturbation terms, made topocentric (seen from the location, not
the Earth's centre). Checked against PyEphem over 300 random instants from 2020 to
2032 at latitudes from 55° S to 65° N, the worst errors were:

| Value | Worst error |
|---|---|
| Azimuth, elevation | 0.08 ° |
| Illumination | 0.3 % |
| Angular size | 0.002 ° |
| Moonrise, moonset | 1.3 min |
| Full moon, new moon | 9 min |

`tests/test_astro.py` repeats the check against stored reference values
(`tests/reference.json`, regenerated by `tests/generate_reference.py`).

## Development

```sh
pip install pytest
pytest -q tests
```

## Credits

- **Icon:** the brand icon (`custom_components/lunae/brand/`) is the
  [Material Design Icons](https://pictogrammers.com/library/mdi/) glyph
  [`weather-moonset`](https://pictogrammers.com/library/mdi/icon/weather-moonset/)
  by [Pictogrammers](https://pictogrammers.com/), redrawn on a dark background by
  `tools/make_brand.py`. Material Design Icons are licensed under the
  [Apache License 2.0](https://github.com/Templarian/MaterialDesign/blob/master/LICENSE).
- **Astronomy:** Paul Schlyter,
  [How to compute planetary positions](https://stjarnhimlen.se/comp/ppcomp.html).
- **Test reference values:** [PyEphem](https://rhodesmill.org/pyephem/) (development only, not a runtime dependency).

## License

MIT for the code in this repository — see [LICENSE](LICENSE). The brand icon is a
derivative of an Apache-2.0 Material Design Icons glyph — see [NOTICE](NOTICE).
