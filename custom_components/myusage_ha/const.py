"""Constants for MyUsage HA integration."""

DOMAIN = "myusage_ha"
SCAN_INTERVAL_HOURS = 1

BASE_URL    = "https://www.myusage.com"
LOGIN_URL   = f"{BASE_URL}/login"
DATA_URL    = f"{BASE_URL}/data.cfm"

CONF_EMAIL    = "email"
CONF_PASSWORD = "password"

# Statistic IDs (external, not tied to entity recorder)
STAT_ELECTRIC = f"{DOMAIN}:electric_kwh"
STAT_WATER    = f"{DOMAIN}:water_gal"
STAT_RECLAIMED= f"{DOMAIN}:reclaimed_gal"
