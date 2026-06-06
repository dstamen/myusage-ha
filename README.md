# OUC MyUsage — Home Assistant Integration

Pull electric, water, and reclaimed water usage from OUC's MyUsage portal directly into Home Assistant as sensors with built-in statistics, month-to-date totals, and 30-day charts.

> **Proper HACS integration** — Install one click, enter credentials in UI, no SSH or manual setup required.

---

## Features

✅ **7 sensors** — electric (kWh + kW demand), water, reclaimed water, and MTD totals for each  
✅ **Hourly updates** — checks for new readings every hour (OUC posts ~9–10 AM)  
✅ **Daily statistics** — auto-injected into HA's SQLite database, shows exact readings not averages  
✅ **30-day charts** — statistics-graph cards ready to drop into your dashboard  
✅ **Zero config** — auto-detects your meters, works for any OUC account  
✅ **stdlib only** — no `pip install` required, works on HAOS  

---

## Installation via HACS

1. Go to **Settings → Devices & Services → Integrations**
2. Click **+ Create Automation** → search for **OUC MyUsage**
3. Click **Install**
4. Restart Home Assistant
5. Go to **Integrations**, search **OUC MyUsage**, click **Create Entry**
6. Enter your OUC email and password
7. Sensors appear in 1–2 minutes

---

## Sensors Created

| Sensor | Value | Unit |
|--------|-------|------|
| `sensor.ouc_myusage_electric` | Last daily kWh | kWh |
| `sensor.ouc_myusage_electric_peak_demand` | Peak kW | kW |
| `sensor.ouc_myusage_water` | Last daily water usage | gal |
| `sensor.ouc_myusage_reclaimed_water` | Last daily reclaimed usage | gal |
| `sensor.ouc_myusage_electric_month_to_date` | Month total (kWh) | kWh |
| `sensor.ouc_myusage_water_month_to_date` | Month total (gal) | gal |
| `sensor.ouc_myusage_reclaimed_month_to_date` | Month total (gal) | gal |

All sensors have meter numbers, reading types, and timestamps in their attributes.

---

## Dashboard Example

```yaml
type: sections
title: Utilities
cards:
  - type: statistics-graph
    title: "⚡ Electric (30 days)"
    entities:
      - sensor.ouc_myusage_electric
    period: day
    stat_types:
      - mean
  - type: statistics-graph
    title: "💧 Water (30 days)"
    entities:
      - sensor.ouc_myusage_water
      - sensor.ouc_myusage_reclaimed_water
    period: day
    stat_types:
      - mean
```

---

## How It Works

1. **Hourly fetch** — coordinator logs into OUC's MyUsage portal via HTTPS
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

- OUC posts readings ~9–10 AM; sensors update hourly but values only change when OUC posts
- Uses Python stdlib only — works on any HAOS installation
- Stats are external (not entity recorder) — stored with statistic_id `ouc_myusage:electric_kwh` etc.
- Safe to run multiple times; statistics only update if values changed
- Works for any utility using Exceleron's MyUsage platform

---

## Troubleshooting

**Sensors showing "unavailable":**
- Integration may still be fetching on first run (1–2 min)
- Check Settings → Devices & Services → Integrations for "OUC MyUsage" errors
- Verify email/password are correct

**Charts show old data:**
- Statistics populate hourly after first fetch; wait 1–2 hours for backfill
- Restart HA if charts still blank after waiting

**Login errors:**
- Double-check OUC email and password (case-sensitive)
- If you changed your OUC password, re-enter it in the integration settings

---

## License

MIT
