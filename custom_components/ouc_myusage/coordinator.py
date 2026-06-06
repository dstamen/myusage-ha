"""DataUpdateCoordinator for OUC MyUsage — fetches usage from myusage.com."""
from __future__ import annotations

import logging
import re
import urllib.parse
import urllib.request
import http.cookiejar
import json
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import DOMAIN, BASE_URL, LOGIN_URL, DATA_URL

_LOGGER = logging.getLogger(__name__)

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
)


# ── HTML table parser ─────────────────────────────────────────────────────────

class _TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self._in_table = self._in_thead = self._in_cell = False
        self._raw_value = None
        self._cell_text: list[str] = []
        self._current_row: list[dict] = []
        self.rows: list[list[dict]] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "table" and attrs.get("id") == "gridUsageHistory":
            self._in_table = True
        if not self._in_table:
            return
        if tag == "thead":
            self._in_thead = True
        if tag == "tr" and not self._in_thead:
            self._current_row = []
        if tag == "td" and not self._in_thead:
            self._in_cell = True
            self._raw_value = attrs.get("data-raw-value")
            self._cell_text = []

    def handle_endtag(self, tag):
        if not self._in_table:
            return
        if tag == "thead":
            self._in_thead = False
        if tag == "td" and self._in_cell:
            self._in_cell = False
            self._current_row.append({
                "text": "".join(self._cell_text).strip(),
                "raw": self._raw_value,
            })
            self._raw_value = None
            self._cell_text = []
        if tag == "tr" and self._current_row:
            self.rows.append(self._current_row)
            self._current_row = []
        if tag == "table" and self._in_table:
            self._in_table = False

    def handle_data(self, data):
        if self._in_cell:
            self._cell_text.append(data)


def _parse_table(html: str) -> list[list[dict]]:
    p = _TableParser()
    p.feed(html)
    return p.rows


def _row_to_electric(c: list[dict]) -> dict:
    return {
        "meter":   c[0]["text"],
        "posted":  c[3]["text"],
        "from":    c[4]["text"],
        "to":      c[5]["text"],
        "kwh":     int(c[6]["raw"] or 0),
        "kw":      float(c[7]["text"].strip()) if c[7]["text"].strip() else 0.0,
        "reading": int(c[8]["text"].strip()) if c[8]["text"].strip() else 0,
        "type":    c[9]["text"],
    }


def _row_to_water(c: list[dict]) -> dict:
    return {
        "meter":   c[0]["text"],
        "posted":  c[3]["text"],
        "from":    c[4]["text"],
        "to":      c[5]["text"],
        "gal":     int(c[6]["raw"] or 0),
        "reading": int(c[7]["text"].strip()) if c[7]["text"].strip() else 0,
        "type":    c[8]["text"],
    }


# ── HTTP helpers (synchronous — run in executor) ──────────────────────────────

def _make_opener():
    cj = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def _get(opener, url: str, extra_headers: dict | None = None) -> tuple[str, str]:
    req = urllib.request.Request(url)
    req.add_header("User-Agent", UA)
    req.add_header("Accept", "text/html,application/xhtml+xml,*/*")
    req.add_header("Accept-Language", "en-US,en;q=0.9")
    for k, v in (extra_headers or {}).items():
        req.add_header(k, v)
    with opener.open(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace"), r.geturl()


def _post(opener, url: str, data_dict: dict, extra_headers: dict | None = None) -> tuple[str, str]:
    data = urllib.parse.urlencode(data_dict).encode()
    req = urllib.request.Request(url, data=data)
    req.add_header("User-Agent", UA)
    req.add_header("Accept", "text/html,application/xhtml+xml,*/*")
    req.add_header("Accept-Language", "en-US,en;q=0.9")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    for k, v in (extra_headers or {}).items():
        req.add_header(k, v)
    with opener.open(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace"), r.geturl()


def _fetch_ouc_data(email: str, password: str) -> dict:
    """Fetch 30-day usage history from OUC MyUsage (blocking — run in executor)."""
    today = datetime.now()
    from_date = (today - timedelta(days=30)).strftime("%m/%d/%Y")
    to_date   = (today + timedelta(days=1)).strftime("%m/%d/%Y")

    opener = _make_opener()

    # Login
    login_data = urllib.parse.urlencode({"email": email, "password": password}).encode()
    req = urllib.request.Request(LOGIN_URL, data=login_data)
    req.add_header("User-Agent", UA)
    req.add_header("Accept", "application/json, text/javascript, */*; q=0.01")
    req.add_header("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8")
    req.add_header("X-Requested-With", "XMLHttpRequest")
    req.add_header("Referer", BASE_URL + "/")
    with opener.open(req, timeout=30) as r:
        login_json = json.loads(r.read().decode())

    redirect_url = login_json.get("redirect_url")
    if not redirect_url:
        raise ConfigEntryAuthFailed("Login failed — check credentials")

    # Follow SSO redirect
    _, final_url = _get(opener, redirect_url, {"Referer": BASE_URL + "/"})
    m = re.search(r"appFlow=(\w+)", final_url)
    if not m:
        raise UpdateFailed("Could not extract session token after login")
    app_flow = m.group(1)

    history_base = (
        f"{DATA_URL}?appPage=Postpaid&appPageScreen=History"
        f"&appPageScreenSub=Usage%20History&appFlow={app_flow}&"
    )

    # Electric history (default GET)
    elec_html, _ = _get(opener, history_base)
    csrf     = re.search(r'name="cf_CSRFToken"\s+value="([^"]+)"', elec_html).group(1)
    csrf_web = re.search(r'name="cf_CSRFToken_web"\s+value="([^"]+)"', elec_html).group(1)

    # Water history (POST)
    water_html, _ = _post(opener, history_base, {
        "selectedTimePeriod": "4",
        "FromDate": from_date,
        "ToDate": to_date,
        "ServiceType": "Water",
        "action": "Load",
        "SubmitButtonValidateTimePeriod": (
            "[['FromDate','isRequired','','From:','0'],"
            "['FromDate','isDate','','From:','0'],"
            "['ToDate','isRequired','','To:','0'],"
            "['ToDate','isDate','','To:','0'],"
            "['ServiceType','isRequired','','Service:','0']]"
        ),
        "cf_CSRFToken": csrf,
        "cf_CSRFToken_web": csrf_web,
    }, {"Referer": history_base})

    # Parse electric rows — auto-detect electric meter (first meter found)
    elec_rows_raw = [r for r in _parse_table(elec_html) if len(r) >= 10]
    elec_meters   = list(dict.fromkeys(r[0]["text"] for r in elec_rows_raw))
    electric_meter = elec_meters[0] if elec_meters else None

    elec_rows = [_row_to_electric(r) for r in elec_rows_raw
                 if r[0]["text"] == electric_meter]

    # Parse water rows — R-prefixed meters = reclaimed
    water_rows_raw = [r for r in _parse_table(water_html) if len(r) >= 9]
    water_meters   = list(dict.fromkeys(r[0]["text"] for r in water_rows_raw))
    water_meter    = next((m for m in water_meters if not m.upper().startswith("R")), None)
    reclaimed_meter= next((m for m in water_meters if m.upper().startswith("R")), None)

    water_rows    = [_row_to_water(r) for r in water_rows_raw
                     if water_meter and r[0]["text"] == water_meter]
    reclaimed_rows= [_row_to_water(r) for r in water_rows_raw
                     if reclaimed_meter and r[0]["text"] == reclaimed_meter]

    def latest_nonzero(rows, key):
        return next((r for r in rows if r.get(key, 0) > 0), rows[0] if rows else {})

    def latest(rows):
        return rows[0] if rows else {}

    le = latest_nonzero(elec_rows, "kwh")
    lw = latest(water_rows)
    lr = latest(reclaimed_rows)

    # Build trimmed history for attributes and MTD calcs
    elec_hist    = [{"d": r["posted"].split(" ")[0], "kwh": r["kwh"], "kw": r["kw"], "t": r["type"]} for r in elec_rows]
    water_hist   = [{"d": r["posted"].split(" ")[0], "gal": r["gal"]} for r in water_rows]
    reclaim_hist = [{"d": r["posted"].split(" ")[0], "gal": r["gal"]} for r in reclaimed_rows]

    # MTD totals
    m_now = today.month
    y_now = today.year

    def mtd(hist, key):
        total = 0
        for h in hist:
            p = h["d"].split("/")
            if int(p[0]) == m_now and int(p[2]) == y_now:
                total += h.get(key, 0)
        return total

    return {
        "electric": {
            "last_kwh":  le.get("kwh", 0),
            "last_kw":   le.get("kw", 0.0),
            "reading":   le.get("reading", 0),
            "posted":    le.get("posted", ""),
            "from":      le.get("from", ""),
            "to":        le.get("to", ""),
            "type":      le.get("type", ""),
            "mtd_kwh":   mtd(elec_hist, "kwh"),
            "history":   elec_hist,
        },
        "water": {
            "last_gal":  lw.get("gal", 0),
            "reading":   lw.get("reading", 0),
            "posted":    lw.get("posted", ""),
            "type":      lw.get("type", ""),
            "mtd_gal":   mtd(water_hist, "gal"),
            "history":   water_hist,
        },
        "reclaimed": {
            "last_gal":  lr.get("gal", 0),
            "reading":   lr.get("reading", 0),
            "posted":    lr.get("posted", ""),
            "type":      lr.get("type", ""),
            "mtd_gal":   mtd(reclaim_hist, "gal"),
            "history":   reclaim_hist,
        },
        "meters": {
            "electric":  electric_meter,
            "water":     water_meter,
            "reclaimed": reclaimed_meter,
        },
    }


# ── Coordinator ───────────────────────────────────────────────────────────────

class OUCCoordinator(DataUpdateCoordinator):
    """Fetches OUC data and injects daily statistics."""

    def __init__(self, hass: HomeAssistant, email: str, password: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=1),
        )
        self._email    = email
        self._password = password

    async def _async_update_data(self) -> dict:
        try:
            data = await self.hass.async_add_executor_job(
                _fetch_ouc_data, self._email, self._password
            )
        except ConfigEntryAuthFailed:
            raise
        except Exception as exc:
            raise UpdateFailed(f"Error fetching OUC data: {exc}") from exc

        # Inject statistics after fetching
        await self.hass.async_add_executor_job(self._inject_statistics, data)
        return data

    def _inject_statistics(self, data: dict) -> None:
        """Write daily readings to HA's SQLite statistics database."""
        import sqlite3

        db_path = self.hass.config.path("home-assistant_v2.db")

        def parse_ts(date_str: str) -> float:
            p = date_str.split("/")
            return datetime(int(p[2]), int(p[0]), int(p[1]), 0, 0, 0, tzinfo=timezone.utc).timestamp()

        datasets = [
            ("ouc_myusage:electric_kwh", "OUC Electric",        "kWh", data["electric"]["history"], "kwh"),
            ("ouc_myusage:water_gal",    "OUC Water",           "gal", data["water"]["history"],    "gal"),
            ("ouc_myusage:reclaimed_gal","OUC Reclaimed Water", "gal", data["reclaimed"]["history"],"gal"),
        ]

        now_ts = datetime.now(timezone.utc).timestamp()

        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()

            for statistic_id, name, unit, history, value_key in datasets:
                c.execute("SELECT id FROM statistics_meta WHERE statistic_id=?", (statistic_id,))
                row = c.fetchone()
                if row:
                    meta_id = row[0]
                    c.execute(
                        "UPDATE statistics_meta SET has_mean=1, has_sum=1 WHERE id=?",
                        (meta_id,)
                    )
                else:
                    c.execute(
                        "INSERT INTO statistics_meta "
                        "(statistic_id, source, unit_of_measurement, has_mean, has_sum, name) "
                        "VALUES (?,?,?,?,?,?)",
                        (statistic_id, DOMAIN, unit, 1, 1, name)
                    )
                    meta_id = c.lastrowid

                running_sum = 0.0
                for h in sorted(history, key=lambda x: x["d"]):
                    val = float(h.get(value_key, 0))
                    ts  = parse_ts(h["d"])
                    running_sum += val
                    c.execute(
                        "SELECT id, mean FROM statistics WHERE metadata_id=? AND start_ts=?",
                        (meta_id, ts)
                    )
                    existing = c.fetchone()
                    if existing:
                        if existing[1] != val:
                            c.execute(
                                "UPDATE statistics SET mean=?, min=?, max=?, state=?, sum=?, created_ts=? WHERE id=?",
                                (val, val, val, val, running_sum, now_ts, existing[0])
                            )
                    else:
                        c.execute(
                            "INSERT INTO statistics "
                            "(metadata_id, created_ts, start_ts, mean, min, max, state, sum) "
                            "VALUES (?,?,?,?,?,?,?,?)",
                            (meta_id, now_ts, ts, val, val, val, val, running_sum)
                        )

            conn.commit()
            conn.close()
            _LOGGER.debug("OUC statistics updated successfully")
        except Exception as exc:
            _LOGGER.error("Failed to update OUC statistics: %s", exc)
