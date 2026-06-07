# MyUsage

[![Version](https://img.shields.io/github/v/release/dstamen/myusage-ha?label=version)](https://github.com/dstamen/myusage-ha/releases/latest)
[![Validate for HACS](https://github.com/dstamen/myusage-ha/workflows/Validate%20with%20hassfest%20and%20HACS/badge.svg)](https://github.com/dstamen/myusage-ha/actions/workflows/validate.yml)

Pull electric, water, and reclaimed water usage from your utility's MyUsage portal (Exceleron-powered) directly into Home Assistant as sensors with built-in statistics, month-to-date totals, and 30-day charts.

Works with any utility using Exceleron's MyUsage platform — Orlando Utilities Commission (OUC), Tampa Electric, and many others.

> **Proper HACS integration** — Install one click, enter credentials in UI, no SSH or manual setup required.

---

## Features

✅ **4 sensors** — electric (kWh + kW demand), water, reclaimed water
✅ **Hourly updates** — checks for new readings every hour
✅ **Daily statistics** — auto-injected into HA's SQLite database, shows exact readings not averages
✅ **30-day charts** — statistics-graph cards ready to drop into your dashboard
✅ **Zero config** — auto-detects your meters, works for any supported utility
✅ **stdlib only** — no `pip install` required, works on HAOS

---

## Installation via HACS

1. Go to **Settings → Devices & Services → Integrations**
2. Click **+ Create Automation** → search for **MyUsage**
3. Click **Install**
4. Restart Home Assistant
5. Go to **Integrations**, search **MyUsage**, click **Create Entry**
6. Enter your utility email and password
7. Sensors appear in 1–2 minutes

---

## Sensors Created

| Sensor | Value | Unit |
|--------|-------|------|
| `sensor.myusage_electric` | Last daily kWh | kWh |
| `sensor.myusage_electric_peak_demand` | Peak kW | kW |
| `sensor.myusage_water` | Last daily water usage | gal |
| `sensor.myusage_reclaimed_water` | Last daily reclaimed usage | gal |

All sensors include meter numbers, reading types, and posted timestamps in their attributes. The `history` attribute contains the last 30 days of readings (used for month-to-date calculations).

### Optional: Month-to-Date Totals**

Add template sensors to calculate MTD totals from history:

```yaml
template:
  - sensor:
      - name: "Electric MTD"
        unique_id: myusage_electric_mtd
        unit_of_measurement: "kWh"
        state: >
          {% set hist = state_attr('sensor.myusage_electric', 'electric')['history'] %}
          {% set m = now().month %}{% set y = now().year %}
          {% set ns = namespace(t=0) %}
          {% for h in hist %}{% set p = h.d.split('/') %}
            {% if p[0]|int == m and p[2]|int == y %}{% set ns.t = ns.t + h.kwh %}{% endif %}
          {% endfor %}{{ ns.t }}
```

---

## Dashboard Example

```yaml
type: sections
title: Utilities
cards:
  - type: statistics-graph
    title: "⚡ Electric (30 days)"
    entities:
      - sensor.myusage_electric
    period: day
    stat_types:
      - mean
  - type: statistics-graph
    title: "💧 Water (30 days)"
    entities:
      - sensor.myusage_water
      - sensor.myusage_reclaimed_water
    period: day
    stat_types:
      - mean
```

---

## How It Works

1. **Hourly fetch** — coordinator logs into your utility's MyUsage portal via HTTPS
2. **Parse history** — extracts last 30 days of electric & water readings from portal
3. **Create sensors** — displays latest reading + peak demand + MTD totals
4. **Daily backfill** — automatically injects daily readings into HA's statistics database
5. **Chart display** — statistics-graph cards show exact daily values, not averages

The key difference from command-line approach:

- ✅ Stored in HA's native integration registry
- ✅ Automatic stats injection (no manual backfill)
- ✅ Credentials encrypted in config entry (not exposed in YAML)
- ✅ One-click HACS install
- ✅ Proper error handling and retry logic

---

## Notes

- Your utility posts readings ~9–10 AM; sensors update hourly but values only change when readings are posted
- Uses Python stdlib only — works on any HAOS installation
- Stats are external (not entity recorder) — stored with statistic_id `myusage:electric_kwh` etc.
- Safe to run multiple times; statistics only update if values changed
- Works for any utility using Exceleron's MyUsage platform

---

## Troubleshooting

**Sensors showing "unavailable":**

- Integration may still be fetching on first run (1–2 min)
- Check Settings → Devices & Services → Integrations for "MyUsage" errors
- Verify email/password are correct

**Charts show old data:**

- Statistics populate hourly after first fetch; wait 1–2 hours for backfill
- Restart HA if charts still blank after waiting

**Login errors:**

- Double-check your utility email and password (case-sensitive)
- If you changed your password, re-enter it in the integration settings

---

## License

MIT
