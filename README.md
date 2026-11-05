# MyUsage

[![Version](https://img.shields.io/github/v/release/dstamen/myusage-ha?label=version)](https://github.com/dstamen/myusage-ha/releases/latest)
[![Validate with hassfest and HACS](https://github.com/dstamen/myusage-ha/actions/workflows/validate.yml/badge.svg?branch=main)](https://github.com/dstamen/myusage-ha/actions/workflows/validate.yml)

Pull electric, water, and reclaimed water usage from your utility's MyUsage portal (Exceleron-powered) into Home Assistant as sensors, month-to-date totals, and hourly long-term statistics.

Works with utilities on Exceleron's MyUsage platform, such as Orlando Utilities Commission (OUC).

---

## Features

- **13 sensors**: electric (daily kWh, peak kW demand, meter reading, month to date), water (daily usage, meter reading, month to date), reclaimed water (daily usage, meter reading, month to date), and the last posted time for each service
- **Hourly updates**: checks the portal for new readings every hour
- **Hourly statistics**: imports the portal's per-hour electric and water readings (the last 7 days) as external statistics, usable in statistics-graph cards and the Energy dashboard
- **Auto-detected meters**: no meter numbers to enter
- **No extra dependencies**: Python standard library only

---

## Installation

### HACS

1. In Home Assistant, open **HACS** and search for **MyUsage**.
   If it does not show up, open the ⋮ menu → **Custom repositories**, add `https://github.com/dstamen/myusage-ha` with type **Integration**, then search again.
2. Open **MyUsage** and select **Download**.
3. Restart Home Assistant.
4. Go to **Settings → Devices & services**, select **+ Add integration**, and search for **MyUsage**.
5. Enter the email and password you use on your utility's MyUsage portal.

### Manual

Copy `custom_components/myusage` into your Home Assistant `config/custom_components/` folder, restart Home Assistant, then follow step 4 above.

---

## Sensors

| Sensor | Value | Unit |
|--------|-------|------|
| `sensor.myusage_electric` | Latest daily usage | kWh |
| `sensor.myusage_electric_peak_demand` | Latest peak demand | kW |
| `sensor.myusage_electric_meter_reading` | Cumulative meter reading | kWh |
| `sensor.myusage_electric_month_to_date` | Usage posted so far this month | kWh |
| `sensor.myusage_water` | Latest daily usage | gal |
| `sensor.myusage_water_meter_reading` | Cumulative meter reading | gal |
| `sensor.myusage_water_month_to_date` | Usage posted so far this month | gal |
| `sensor.myusage_reclaimed_water` | Latest daily usage | gal |
| `sensor.myusage_reclaimed_water_meter_reading` | Cumulative meter reading | gal |
| `sensor.myusage_reclaimed_water_month_to_date` | Usage posted so far this month | gal |
| `sensor.myusage_electric_last_posted` | When the latest electric reading was posted | text |
| `sensor.myusage_water_last_posted` | When the latest water reading was posted | text |
| `sensor.myusage_reclaimed_water_last_posted` | When the latest reclaimed reading was posted | text |

The `*_meter_reading` sensors use `state_class: total_increasing`, so they work with the **Energy dashboard** (Settings → Dashboards → Energy).

The daily usage sensors carry the meter number, reading type, posted time and meter reading as attributes. Month-to-date totals add up the daily readings posted in the current calendar month.

### Statistics

The integration also writes external statistics that hold the portal's hourly readings:

| Statistic ID | Resolution |
|--------------|-----------|
| `myusage:electric_kwh` | Hourly |
| `myusage:water_gal` | Hourly |
| `myusage:reclaimed_gal` | Daily (the portal has no hourly reclaimed data) |

The portal labels hours in the utility's local time. The integration reads them in your Home Assistant time zone, so set that to the utility's time zone (Settings → System → General).

---

## Dashboard example

```yaml
type: statistics-graph
title: Electric (last 7 days)
entities:
  - myusage:electric_kwh
period: hour
days_to_show: 7
stat_types:
  - change
chart_type: bar
```

---

## Notes

- Utilities usually post readings around 9–10 AM. Sensors poll hourly, but values only change once a new reading is posted.
- Your MyUsage email and password are stored in the Home Assistant config entry. Like other integrations' credentials, they are kept as plain text in `config/.storage`, so protect that folder and your backups.
- Re-importing statistics is safe: each run overwrites the same hours.

---

## Troubleshooting

**Sensors show "unavailable":**

- The first fetch can take a minute or two.
- Check **Settings → Devices & services → MyUsage** for errors.

**Login errors:**

- If your password changed, Home Assistant shows a **Re-authenticate** prompt for MyUsage under **Settings → Devices & services**. Enter the new password there.

---

## License

MIT
