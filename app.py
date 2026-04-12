"""
V + ATR — Real-Time Volume & ATR% Volatility Monitor
Only Regular Session · All values in % · Clickable daily detail
"""

import streamlit as st
import json, time, hashlib, random, re
from datetime import datetime, timezone
from pathlib import Path
import requests

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
_page_icon = "\U0001f7e2"
try:
    _icon_path = Path("static/icon.png")
    if _icon_path.exists():
        from PIL import Image as _PILImage
        _page_icon = _PILImage.open(_icon_path)
except Exception:
    pass

st.set_page_config(page_title="V + ATR", page_icon=_page_icon, layout="centered",
                   initial_sidebar_state="collapsed")

# ─── CONSTANTS ────────────────────────────────────────────────────────────────
CACHE_DIR = Path("disk_cache")
CACHE_DIR.mkdir(exist_ok=True)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
]

YAHOO_URLS = [
    "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
    "https://query2.finance.yahoo.com/v8/finance/chart/{ticker}",
]
ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown(
    '<link rel="icon" type="image/png" sizes="512x512" href="/app/static/icon.png">'
    '<link rel="apple-touch-icon" sizes="512x512" href="/app/static/icon.png">',
    unsafe_allow_html=True)

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
    --bg-primary:   #080c10;
    --bg-card:      #0d1117;
    --bg-card-alt:  #111820;
    --border:       #1b2432;
    --text-primary: #e6edf3;
    --text-secondary:#8b949e;
    --accent-cyan:  #00d4ff;
    --accent-green: #00ff88;
    --accent-red:   #ff4757;
    --accent-amber: #ffb340;
    --font-sans:    'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    --font-mono:    'JetBrains Mono', 'Fira Code', monospace;
}

html, body, .stApp, [data-testid="stAppViewContainer"],
[data-testid="stApp"], section[data-testid="stMain"] {
    background: var(--bg-primary) !important;
    color: var(--text-primary) !important;
    font-family: var(--font-sans) !important;
}
header[data-testid="stHeader"] { background: transparent !important; }
.block-container { max-width: 540px !important; padding: 1rem 0.75rem !important; }

.card {
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: 12px; padding: 1rem 1.1rem; margin-bottom: 0.8rem;
    position: relative; overflow: hidden;
}
.card:hover { border-color: var(--accent-cyan); box-shadow: 0 0 20px rgba(0,212,255,.08); }
.card::before {
    content: ''; position: absolute; top: 0; left: 0; width: 3px; height: 100%;
    background: linear-gradient(180deg, var(--accent-cyan), var(--accent-green));
    animation: gslide 3s ease infinite alternate;
}
@keyframes gslide {
    0%   { background: linear-gradient(180deg, var(--accent-cyan), var(--accent-green)); }
    50%  { background: linear-gradient(180deg, var(--accent-green), var(--accent-amber)); }
    100% { background: linear-gradient(180deg, var(--accent-amber), var(--accent-cyan)); }
}

.card-title { font-size:.7rem; font-weight:600; letter-spacing:.08em; text-transform:uppercase; color:var(--text-secondary); margin-bottom:.55rem; }
.card-value { font-family:var(--font-mono); font-size:1.45rem; font-weight:600; color:var(--text-primary); line-height:1.15; }
.card-sub { font-size:.78rem; color:var(--text-secondary); margin-top:.25rem; }
.card-note { font-size:.62rem; color:var(--text-secondary); margin-top:.4rem; font-style:italic; }

.metric-row { display:flex; gap:.6rem; margin-bottom:.8rem; flex-wrap:wrap; }
.metric-box { flex:1; min-width:0; background:var(--bg-card-alt); border:1px solid var(--border); border-radius:10px; padding:.7rem .8rem; text-align:center; }
.metric-label { font-size:.6rem; font-weight:600; letter-spacing:.07em; text-transform:uppercase; color:var(--text-secondary); margin-bottom:.3rem; }
.metric-val { font-family:var(--font-mono); font-size:1.05rem; font-weight:600; color:var(--text-primary); }

.atr-table { width:100%; border-collapse:separate; border-spacing:0; font-size:.75rem; margin-top:.5rem; }
.atr-table th { background:var(--bg-card-alt); color:var(--text-secondary); font-weight:600; text-transform:uppercase; font-size:.6rem; letter-spacing:.06em; padding:.5rem .35rem; text-align:center; border-bottom:1px solid var(--border); }
.atr-table td { padding:.45rem .35rem; text-align:center; border-bottom:1px solid var(--border); font-family:var(--font-mono); color:var(--text-primary); font-size:.73rem; }
.atr-table tr:last-child td { border-bottom:none; }
.atr-table tr:hover td { background:rgba(0,212,255,.04); }

.badge-up   { color: var(--accent-green); }
.badge-down { color: var(--accent-red);   }
.badge-flat { color: var(--text-secondary); }

.vol-pressure { display:flex; height:8px; border-radius:4px; overflow:hidden; margin-top:.4rem; }
.vol-pressure-buy { background:var(--accent-green); height:100%; }
.vol-pressure-sell { background:var(--accent-red); height:100%; }

.vol-bar-bg { width:100%; height:6px; background:var(--border); border-radius:3px; margin-top:.3rem; overflow:hidden; }
.vol-bar-fill { height:100%; border-radius:3px; }

input[type="text"], .stTextInput input { background:var(--bg-card-alt) !important; color:var(--text-primary) !important; border:1px solid var(--border) !important; border-radius:8px !important; font-family:var(--font-mono) !important; }
.stTextInput input:focus { border-color:var(--accent-cyan) !important; box-shadow:0 0 8px rgba(0,212,255,.15) !important; }
.stButton > button { background:linear-gradient(135deg,#00d4ff 0%,#00ff88 100%) !important; color:#080c10 !important; font-weight:700 !important; border:none !important; border-radius:8px !important; width:100% !important; padding:.6rem !important; }
.stButton > button:hover { opacity:.88 !important; }

.app-header { text-align:center; padding:.6rem 0 .4rem; }
.app-header h1 { font-family:var(--font-mono); font-size:1.5rem; font-weight:700; background:linear-gradient(90deg,var(--accent-cyan),var(--accent-green)); -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin:0; }
.app-header p { color:var(--text-secondary); font-size:.72rem; margin:.15rem 0 0; }

::-webkit-scrollbar { width:4px; }
::-webkit-scrollbar-track { background:var(--bg-primary); }
::-webkit-scrollbar-thumb { background:var(--border); border-radius:4px; }
#MainMenu, footer, [data-testid="stToolbar"] { display:none !important; }

[data-testid="stExpander"] { background:transparent !important; border:none !important; }
[data-testid="stExpander"] details { background:var(--bg-card) !important; border:1px solid var(--border) !important; border-radius:12px !important; }
[data-testid="stExpander"] summary { color:var(--text-secondary) !important; font-size:.8rem !important; }

.stSelectbox > div > div { background:var(--bg-card-alt) !important; color:var(--text-primary) !important; border:1px solid var(--border) !important; border-radius:8px !important; }
</style>
""", unsafe_allow_html=True)


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def safe_fetch(url, retries=2, timeout=8):
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers={
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "application/json, */*",
                "Accept-Language": "en-US,en;q=0.9",
            }, timeout=timeout)
            if resp.status_code == 200:
                return resp
        except Exception:
            pass
        time.sleep(1 * (attempt + 1))
    return None

def _ck(name):
    return CACHE_DIR / f"{hashlib.md5(name.encode()).hexdigest()[:12]}.json"

def save_disk(name, data):
    try:
        with open(_ck(name), "w") as f:
            json.dump({"ts": time.time(), "data": data}, f)
    except Exception:
        pass

def load_disk(name, max_age=86400):
    p = _ck(name)
    if not p.exists(): return None
    try:
        with open(p) as f:
            obj = json.load(f)
        return obj["data"] if time.time() - obj["ts"] <= max_age else None
    except Exception:
        return None

def is_italian(t): return t.upper().endswith(".MI")
def cur_sym(t): return "\u20ac" if is_italian(t) else "$"

def fmt_num(val, d=2, p=""):
    if val is None: return "\u2014"
    v = abs(val)
    if v >= 1e9: return f"{p}{val/1e9:,.{d}f}B"
    if v >= 1e6: return f"{p}{val/1e6:,.{d}f}M"
    if v >= 1e3: return f"{p}{val/1e3:,.{d}f}K"
    return f"{p}{val:,.{d}f}"

def pct_badge(val):
    if val is None: return '<span class="badge-flat">\u2014</span>'
    cls = "badge-up" if val > 0 else ("badge-down" if val < 0 else "badge-flat")
    sign = "+" if val > 0 else ""
    return f'<span class="{cls}">{sign}{val:.2f}%</span>'

def pressure_bar(buy, sell):
    total = buy + sell
    if total == 0: return ""
    bp = buy / total * 100
    sp = 100 - bp
    return (
        f'<div style="display:flex;justify-content:space-between;font-size:.62rem;color:var(--text-secondary);margin-top:.2rem;">'
        f'<span style="color:var(--accent-green)">\u25b2 Buy {bp:.0f}% ({fmt_num(buy,1)})</span>'
        f'<span style="color:var(--accent-red)">\u25bc Sell {sp:.0f}% ({fmt_num(sell,1)})</span></div>'
        f'<div class="vol-pressure"><div class="vol-pressure-buy" style="width:{bp:.1f}%"></div>'
        f'<div class="vol-pressure-sell" style="width:{sp:.1f}%"></div></div>'
    )

def vol_ratio_bar(ratio):
    if ratio is None: return ""
    pct = min(ratio * 100, 200)
    color = "var(--accent-green)" if ratio >= 1.5 else ("var(--accent-amber)" if ratio >= 0.8 else "var(--accent-red)")
    label = "Alto" if ratio >= 1.5 else ("Nella media" if ratio >= 0.8 else "Basso")
    return (
        f'<div style="display:flex;justify-content:space-between;font-size:.65rem;color:var(--text-secondary);margin-top:.15rem;">'
        f'<span>{label}</span><span>{ratio:.1f}x media 3M</span></div>'
        f'<div class="vol-bar-bg"><div class="vol-bar-fill" style="width:{pct:.0f}%;background:{color};"></div></div>'
    )


# ─── ISIN / TICKER RESOLVER (bulletproof) ─────────────────────────────────────

def is_isin(t): return bool(ISIN_RE.match(t.strip().upper()))

YAHOO_SEARCH_URLS = [
    "https://query1.finance.yahoo.com/v1/finance/search",
    "https://query2.finance.yahoo.com/v1/finance/search",
]

@st.cache_data(ttl=3600, show_spinner=False)
def resolve_ticker(text):
    """Resolve any input: ISIN, ticker, company name. Returns (ticker, display_msg) or (None, error)."""
    t = text.strip()
    if not t:
        return None, "Inserisci un ticker o ISIN."

    tu = t.upper()

    # 1. Try direct as ticker (e.g. AAPL, ENI.MI)
    #    Quick check: if chart returns data, it's a valid ticker
    if not is_isin(tu) and len(tu) <= 12:
        chart = yahoo_chart(tu, interval="1d", range_="5d")
        if chart and chart.get("timestamp"):
            return tu, None

    # 2. Search Yahoo Finance (works for ISIN, company names, partial tickers)
    for search_url in YAHOO_SEARCH_URLS:
        resp = safe_fetch(f"{search_url}?q={tu}&quotesCount=10&newsCount=0")
        if not resp:
            continue
        try:
            quotes = resp.json().get("quotes", [])
            # Priority: exact ISIN match, then EQUITY, then first result
            for q in quotes:
                if q.get("quoteType") == "EQUITY":
                    sym = q.get("symbol")
                    if sym:
                        name = q.get("shortname") or q.get("longname") or sym
                        return sym, f"{t} \u2192 {name} ({sym})"
            # Fallback: first result of any type
            if quotes:
                sym = quotes[0].get("symbol")
                if sym:
                    name = quotes[0].get("shortname") or quotes[0].get("longname") or sym
                    return sym, f"{t} \u2192 {name} ({sym})"
        except Exception:
            continue

    # 3. Try with .MI suffix (Italian market)
    if "." not in tu and not is_isin(tu):
        chart = yahoo_chart(tu + ".MI", interval="1d", range_="5d")
        if chart and chart.get("timestamp"):
            return tu + ".MI", f"{t} \u2192 {tu}.MI (Borsa Italiana)"

    return None, f"Ticker/ISIN \"{t}\" non trovato. Prova con il nome completo o un altro formato."


# ─── YAHOO API ────────────────────────────────────────────────────────────────

def yahoo_chart(ticker, interval="1d", range_="1mo", prepost=False):
    params = {"interval": interval, "range": range_, "includePrePost": "true" if prepost else "false"}
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    for base in YAHOO_URLS:
        resp = safe_fetch(f"{base.format(ticker=ticker)}?{qs}")
        if not resp: continue
        try:
            data = resp.json()
            if data.get("chart", {}).get("error"): continue
            result = data.get("chart", {}).get("result")
            if result and result[0].get("timestamp"): return result[0]
        except Exception:
            continue
    return None


def get_reg_bounds(meta, timestamps):
    """Get regular session start/end, adjusting for timezone offset."""
    rs = meta.get("currentTradingPeriod", {}).get("regular", {}).get("start", 0)
    re_ = meta.get("currentTradingPeriod", {}).get("regular", {}).get("end", 0)
    if timestamps and rs > 0 and timestamps[-1] < rs:
        rd = datetime.fromtimestamp(rs, tz=timezone.utc).date()
        bd = datetime.fromtimestamp(timestamps[-1], tz=timezone.utc).date()
        dd = (rd - bd).days
        if dd > 0:
            rs -= dd * 86400
            re_ -= dd * 86400
    return rs, re_


# ─── RSI CALCULATION ──────────────────────────────────────────────────────────

def compute_rsi(closes, period=14):
    """Compute RSI from a list of close prices. Returns RSI value or None."""
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    if len(gains) < period:
        return None
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)


# ─── FETCH ANALYST + EARNINGS DATA (multi-source, never gives up) ─────────────

SUMMARY_URLS = [
    "https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}",
    "https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}",
    "https://query1.finance.yahoo.com/v6/finance/quoteSummary/{ticker}",
    "https://query2.finance.yahoo.com/v6/finance/quoteSummary/{ticker}",
    "https://query1.finance.yahoo.com/v11/finance/quoteSummary/{ticker}",
]

def _try_summary(ticker, modules_str):
    """Try fetching quoteSummary from multiple endpoints."""
    for base in SUMMARY_URLS:
        resp = safe_fetch(f"{base.format(ticker=ticker)}?modules={modules_str}")
        if not resp:
            continue
        try:
            data = resp.json()
            result = data.get("quoteSummary", {}).get("result")
            if result:
                return result[0]
        except Exception:
            continue
    return None

def _parse_summary(r):
    """Parse quoteSummary result into standard format."""
    out = {
        "target_mean": None, "target_high": None, "target_low": None,
        "current": None, "rec_key": "", "rec_mean": None,
        "num_analysts": 0, "rec_detail": {},
        "next_earnings": None, "past_earnings": [],
        "earnings_sentiment": None,
    }
    fd = r.get("financialData", {})
    if fd:
        out["target_mean"] = fd.get("targetMeanPrice", {}).get("raw")
        out["target_high"] = fd.get("targetHighPrice", {}).get("raw")
        out["target_low"] = fd.get("targetLowPrice", {}).get("raw")
        out["current"] = fd.get("currentPrice", {}).get("raw")
        out["rec_key"] = fd.get("recommendationKey", "")
        out["rec_mean"] = fd.get("recommendationMean", {}).get("raw")
        out["num_analysts"] = fd.get("numberOfAnalystOpinions", {}).get("raw", 0)
    rt_ = r.get("recommendationTrend", {}).get("trend", [])
    if rt_:
        c = rt_[0]
        out["rec_detail"] = {"strongBuy": c.get("strongBuy",0), "buy": c.get("buy",0),
            "hold": c.get("hold",0), "sell": c.get("sell",0), "strongSell": c.get("strongSell",0)}
    ce = r.get("calendarEvents", {}).get("earnings", {})
    ed = ce.get("earningsDate", [])
    if ed:
        ts = ed[0].get("raw") if isinstance(ed[0], dict) else (ed[0] if ed else None)
        if ts:
            out["next_earnings"] = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
    for h in r.get("earningsHistory", {}).get("history", []):
        ed_raw = h.get("quarter", {}).get("raw")
        if ed_raw:
            out["past_earnings"].append({
                "date": datetime.utcfromtimestamp(ed_raw).strftime("%Y-%m-%d"),
                "quarter": h.get("quarter", {}).get("fmt", ""),
                "actual": h.get("epsActual", {}).get("raw"),
                "estimate": h.get("epsEstimate", {}).get("raw"),
                "surprise_pct": round(h.get("surprisePercent", {}).get("raw", 0) * 100, 1) if h.get("surprisePercent", {}).get("raw") is not None else None,
            })
    for trend in r.get("earningsTrend", {}).get("trend", []):
        if trend.get("period") == "+1":
            g = trend.get("growth", {}).get("raw")
            if g is not None:
                out["earnings_sentiment"] = round(g * 100, 1)
            break
    # price module fallback
    pm = r.get("price", {})
    if pm:
        if not out["rec_key"]:
            out["rec_key"] = pm.get("recommendationKey", "")
        if not out["current"]:
            out["current"] = pm.get("regularMarketPrice", {}).get("raw")
    return out

def _fill(base, patch):
    """Merge: patch fills in what base is missing."""
    for k, v in patch.items():
        if k in ("past_earnings", "rec_detail"):
            if v and not base.get(k):
                base[k] = v
        elif v and not base.get(k):
            base[k] = v
    return base

@st.cache_data(ttl=600, show_spinner=False)
def fetch_analyst_data(ticker):
    """Fetch analyst data with aggressive multi-strategy fallbacks."""
    result = {
        "target_mean": None, "target_high": None, "target_low": None,
        "current": None, "rec_key": "", "rec_mean": None,
        "num_analysts": 0, "rec_detail": {},
        "next_earnings": None, "past_earnings": [],
        "earnings_sentiment": None,
    }

    # Strategy 1: all modules at once
    r = _try_summary(ticker, "financialData,recommendationTrend,calendarEvents,earningsHistory,earningsTrend")
    if r:
        result = _fill(result, _parse_summary(r))

    # Strategy 2: modules one by one (partial failures)
    missing_target = not result["target_mean"]
    missing_earnings = not result["past_earnings"] and not result["next_earnings"]
    if missing_target or missing_earnings:
        for mod in ["financialData", "recommendationTrend", "calendarEvents,earningsHistory", "earningsTrend", "price"]:
            r2 = _try_summary(ticker, mod)
            if r2:
                result = _fill(result, _parse_summary(r2))

    # Strategy 3: defaultKeyStatistics + price
    if not result["target_mean"] or not result["rec_key"]:
        r3 = _try_summary(ticker, "defaultKeyStatistics,price")
        if r3:
            result = _fill(result, _parse_summary(r3))

    # Strategy 4: upgradeDowngradeHistory for sentiment
    if not result["rec_key"]:
        r4 = _try_summary(ticker, "upgradeDowngradeHistory")
        if r4:
            hist = r4.get("upgradeDowngradeHistory", {}).get("history", [])
            if hist:
                latest = hist[0]
                action = latest.get("action", "").lower()
                grade = latest.get("toGrade", "")
                if "up" in action:
                    result["rec_key"] = result["rec_key"] or "buy"
                elif "down" in action:
                    result["rec_key"] = result["rec_key"] or "sell"
                elif grade:
                    g = grade.lower()
                    if "buy" in g or "outperform" in g or "overweight" in g:
                        result["rec_key"] = result["rec_key"] or "buy"
                    elif "sell" in g or "underperform" in g or "underweight" in g:
                        result["rec_key"] = result["rec_key"] or "sell"
                    else:
                        result["rec_key"] = result["rec_key"] or "hold"

    has_data = (result["target_mean"] or result["past_earnings"] or
                result["next_earnings"] or result["rec_key"])
    return result if has_data else None


def get_earnings_price_impact(daily_rows, earnings_date):
    """Get price movement around an earnings date: 3 days before, day of, 3 days after."""
    dates = [r["date"] for r in daily_rows]
    if earnings_date not in dates:
        # Find closest date
        closest = None
        for d in dates:
            if abs((datetime.strptime(d, "%Y-%m-%d") - datetime.strptime(earnings_date, "%Y-%m-%d")).days) <= 3:
                closest = d
                break
        if not closest:
            return None
        earnings_date = closest

    idx = dates.index(earnings_date)
    result = []
    for offset in range(-3, 4):
        i = idx + offset
        if 0 <= i < len(daily_rows) and i > 0:
            r = daily_rows[i]
            prev = daily_rows[i-1]
            chg = round((r["close"] - prev["close"]) / prev["close"] * 100, 2)
            label = "Earnings" if offset == 0 else (f"G{offset:+d}" if offset != 0 else "")
            result.append({"date": r["date"], "label": label, "var_pct": chg,
                           "close": r["close"], "volume": r.get("volume", 0)})
    return result if result else None


# ─── FETCH REAL-TIME (regular session only) ───────────────────────────────────

@st.cache_data(ttl=60, show_spinner=False)
def fetch_realtime(ticker):
    chart = None
    for intv, rng in [("1m","1d"),("2m","1d"),("5m","1d"),("1m","5d")]:
        chart = yahoo_chart(ticker, interval=intv, range_=rng, prepost=True)
        if chart and chart.get("timestamp"): break
        chart = None
    if not chart: return None

    try:
        meta = chart["meta"]
        quotes = chart["indicators"]["quote"][0]
        timestamps = chart["timestamp"]
        if not timestamps: return None

        last_price = meta.get("regularMarketPrice", 0)
        prev_close = meta.get("previousClose") or meta.get("chartPreviousClose", 0)
        name = meta.get("shortName") or meta.get("symbol", ticker.upper())
        change_pct = ((last_price - prev_close) / prev_close * 100) if prev_close else None

        rs, re_ = get_reg_bounds(meta, timestamps)
        volumes = quotes.get("volume", [])
        highs = quotes.get("high", [])
        lows = quotes.get("low", [])

        # Regular session only
        reg_vol = 0; reg_buy = 0; reg_sell = 0
        reg_highs = []; reg_lows = []
        prev_mid = None
        for i in range(len(timestamps)):
            if timestamps[i] < rs or timestamps[i] >= re_: continue
            v = volumes[i] if i < len(volumes) and volumes[i] else 0
            h = highs[i] if i < len(highs) and highs[i] is not None else None
            lo = lows[i] if i < len(lows) and lows[i] is not None else None
            if h is None or lo is None: continue

            if h is not None: reg_highs.append(h)
            if lo is not None: reg_lows.append(lo)

            mid = (h + lo) / 2
            if v > 0:
                reg_vol += v
                if prev_mid is not None:
                    if mid >= prev_mid: reg_buy += v
                    else: reg_sell += v
                else:
                    reg_buy += v  # first bar defaults to buy
            prev_mid = mid

        reg_high = round(max(reg_highs), 4) if reg_highs else None
        reg_low = round(min(reg_lows), 4) if reg_lows else None
        range_pct = round((reg_high - reg_low) / reg_low * 100, 2) if reg_high and reg_low and reg_low > 0 else None

        return {
            "price": round(last_price, 4),
            "prev_close": round(prev_close, 4) if prev_close else None,
            "change_pct": round(change_pct, 2) if change_pct is not None else None,
            "reg_vol": reg_vol, "reg_buy": reg_buy, "reg_sell": reg_sell,
            "reg_high": reg_high, "reg_low": reg_low,
            "range_pct": range_pct,
            "name": name,
        }
    except Exception:
        return None


# ─── FETCH VOLUME STATS ──────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def fetch_volume_stats(ticker):
    chart = None
    for rng in ["3mo","6mo","1y","1mo"]:
        chart = yahoo_chart(ticker, interval="1d", range_=rng)
        if chart and chart.get("timestamp"): break
        chart = None
    if not chart: return None
    try:
        vols = chart["indicators"]["quote"][0].get("volume", [])
        dv = [v for v in vols if v is not None and v > 0]
        if len(dv) < 5: return None
        hist = dv[:-1]; avg = sum(hist) / len(hist)
        return {"today": dv[-1], "avg": round(avg), "max": max(hist), "min": min(hist),
                "ratio": round(dv[-1] / avg, 2) if avg > 0 else None, "days": len(hist)}
    except Exception:
        return None


# ─── FETCH ATR% + DAILY HISTORY + INTRADAY PER DAY ───────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def fetch_history(ticker):
    ck = f"hist_v2_{ticker}"
    cached = load_disk(ck, max_age=3600)
    if cached: return cached

    dc = None
    for rng in ["1y","6mo","3mo","1mo"]:
        dc = yahoo_chart(ticker, interval="1d", range_=rng)
        if dc and dc.get("timestamp") and len(dc["timestamp"]) >= 3: break
        dc = None
    if not dc: return None

    try:
        ts = dc["timestamp"]; q = dc["indicators"]["quote"][0]
        opens, highs, lows, closes = q.get("open",[]), q.get("high",[]), q.get("low",[]), q.get("close",[])
        vols = q.get("volume", [])

        rows = []
        for i in range(len(ts)):
            c = closes[i] if i < len(closes) else None
            if c is None: continue
            o = opens[i] if i < len(opens) and opens[i] is not None else c
            h = highs[i] if i < len(highs) and highs[i] is not None else c
            lo = lows[i] if i < len(lows) and lows[i] is not None else c
            v = vols[i] if i < len(vols) and vols[i] is not None else 0
            mid = (h + lo) / 2
            range_pct = round((h - lo) / lo * 100, 2) if lo > 0 else 0
            rows.append({
                "date": datetime.utcfromtimestamp(ts[i]).strftime("%Y-%m-%d"),
                "open": round(o,4), "high": round(h,4), "low": round(lo,4),
                "close": round(c,4), "volume": int(v), "range_pct": range_pct,
            })

        if len(rows) < 3: return None

        # True Range %
        for i, r in enumerate(rows):
            if i == 0:
                r["tr_pct"] = r["range_pct"]
            else:
                pc = rows[i-1]["close"]
                if pc > 0:
                    tr = max(r["high"]-r["low"], abs(r["high"]-pc), abs(r["low"]-pc))
                    r["tr_pct"] = round(tr / pc * 100, 2)
                else:
                    r["tr_pct"] = r["range_pct"]

        # ATR% (Beta) — adaptive period
        atr_p = min(14, len(rows)-1)
        atr_p = max(atr_p, 1)
        for i, r in enumerate(rows):
            if i < atr_p - 1:
                r["atr_pct"] = None
            elif i == atr_p - 1:
                r["atr_pct"] = round(sum(rows[j]["tr_pct"] for j in range(atr_p)) / atr_p, 2)
            else:
                r["atr_pct"] = round((rows[i-1]["atr_pct"] * (atr_p-1) + r["tr_pct"]) / atr_p, 2)

        # Var% day-over-day
        for i, r in enumerate(rows):
            r["var_pct"] = 0.0 if i == 0 else round((r["close"]-rows[i-1]["close"])/rows[i-1]["close"]*100, 2)

        rows = rows[-260:]
        ca = None
        for r in reversed(rows):
            if r.get("atr_pct") is not None:
                ca = r["atr_pct"]; break

        result = {"daily": rows, "current_atr_pct": ca, "atr_period": atr_p,
                  "last_close": rows[-1]["close"]}
        save_disk(ck, result)
        return result
    except Exception:
        return None


# ─── FETCH ALL INTRADAY 30-MIN (single API call) ─────────────────────────────

@st.cache_data(ttl=600, show_spinner=False)
def fetch_all_intraday(ticker):
    """Fetch 30-min bars for ALL available days in one call, return dict of date->bars."""
    ic = None
    for rng in ["1mo", "3mo"]:
        ic = yahoo_chart(ticker, interval="30m", range_=rng)
        if ic and ic.get("timestamp"): break
        ic = None
    if not ic: return {}

    try:
        its = ic["timestamp"]
        iq = ic["indicators"]["quote"][0]
        ih, il, iv = iq.get("high",[]), iq.get("low",[]), iq.get("volume",[])
        io, icl = iq.get("open",[]), iq.get("close",[])

        # Group bars by date
        all_bars = {}
        for i, t in enumerate(its):
            d = datetime.utcfromtimestamp(t)
            date_str = d.strftime("%Y-%m-%d")
            hv = ih[i] if i < len(ih) and ih[i] is not None else None
            lv = il[i] if i < len(il) and il[i] is not None else None
            vv = iv[i] if i < len(iv) and iv[i] is not None else 0
            ov = io[i] if i < len(io) and io[i] is not None else None
            cv = icl[i] if i < len(icl) and icl[i] is not None else None
            if hv is None or lv is None: continue
            mid = (hv + lv) / 2
            range_pct = round((hv - lv) / lv * 100, 2) if lv > 0 else 0
            # Direction: close vs open of this candle
            if ov is not None and cv is not None:
                direction = "up" if cv >= ov else "down"
            else:
                direction = "flat"
            if date_str not in all_bars:
                all_bars[date_str] = []
            all_bars[date_str].append({
                "time": d.strftime("%H:%M"), "high": round(hv,4), "low": round(lv,4),
                "range_pct": range_pct, "mid": round(mid,4), "volume": int(vv),
                "direction": direction,
            })

        # Compute Var% within each day + fix direction
        for date_str, bars in all_bars.items():
            for i, b in enumerate(bars):
                if i == 0:
                    b["var_pct"] = None
                else:
                    pm = bars[i-1]["mid"]
                    b["var_pct"] = round((b["mid"]-pm)/pm*100, 2) if pm else None
                # Fix direction: if open/close were null, use var_pct
                if b["direction"] == "flat" and b.get("var_pct") is not None:
                    b["direction"] = "up" if b["var_pct"] >= 0 else "down"
                # First bar of day: if still flat, use high vs low proximity
                if i == 0 and b["direction"] == "flat":
                    b["direction"] = "up"  # default first bar

        return all_bars
    except Exception:
        return {}


# ─── HEADER ───────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="app-header"><h1>\U0001f7e2 V + ATR</h1>'
    '<p>Volume &amp; ATR% (Beta) \u00b7 Solo Sessione Regolare</p></div>',
    unsafe_allow_html=True)

# ─── INPUT ────────────────────────────────────────────────────────────────────
c1, c2 = st.columns([3, 1.2])
with c1:
    ticker_input = st.text_input("Ticker/ISIN", value="", placeholder="AAPL, ENI.MI, IT0003132476...",
                                  label_visibility="collapsed")
with c2:
    st.markdown("<div style='height:1px'></div>", unsafe_allow_html=True)
    run = st.button("Genera \u25b6", use_container_width=True)

# ─── LEGEND ───────────────────────────────────────────────────────────────────
with st.expander("\U0001f4d6 Guida ai Dati"):
    st.markdown("""
<div style="font-size:.78rem;line-height:1.65;color:#8b949e;">

<b style="color:#00d4ff;">ATR% (Beta)</b> \u2014 Average True Range in percentuale.
Misura quanto oscilla il titolo in media rispetto al prezzo. Tutto \u00e8 in %, cos\u00ec puoi confrontare titoli da $2 e da $200.<br>
\u2022 <span style="color:#00ff88">ATR% &lt; 2%</span> = calmo \u2022 <span style="color:#ffb340">2-5%</span> = moderato \u2022 <span style="color:#ff4757">&gt; 5%</span> = molto volatile.

<b style="color:#00d4ff;">Range% (Storico)</b> \u2014 (Max-Min)/Min \u00d7 100 del giorno. L\u2019oscillazione reale di quella giornata.

<b style="color:#00d4ff;">Range% (Intraday 30min)</b> \u2014 Differenza % tra il prezzo minimo e massimo raggiunto in ciascun intervallo di 30 minuti (es. 13:30-13:59, 14:00-14:29, ecc.).<br>
\u2022 Barra <span style="color:#00ff88">verde</span> = oscillazione contenuta (&lt;1%).<br>
\u2022 Barra <span style="color:#ffb340">ambra</span> = oscillazione moderata (1-2%).<br>
\u2022 Barra <span style="color:#ff4757">rossa</span> = forte oscillazione (&gt;2%).

<b style="color:#00d4ff;">$1K / \u20ac1K</b> \u2014 Guadagno potenziale se avessi comprato al Min e venduto al Max di quella mezz\u2019ora, con 1.000 investiti. \u00c8 il massimo teorico, non il risultato reale.

<b style="color:#00d4ff;">Tabella cliccabile</b> \u2014 Tocca una data per espandere il dettaglio ogni 30 minuti di quella seduta.

<b style="color:#00d4ff;">Solo sessione regolare</b> \u2014 Pre-market e after-hours sono esclusi da tutti i calcoli.

</div>
""", unsafe_allow_html=True)

# ─── MAIN ─────────────────────────────────────────────────────────────────────

# Initialize session state
if "active_ticker" not in st.session_state:
    st.session_state.active_ticker = None
    st.session_state.active_cur = "$"
    st.session_state.active_mkt = ""
    st.session_state.show_trim = False

# When Genera is clicked, resolve and store ticker
if run and ticker_input.strip():
    raw = ticker_input.strip()
    with st.spinner("Risoluzione ticker..."):
        ticker, msg = resolve_ticker(raw)
    if ticker is None:
        st.markdown(f'<div class="card" style="border-color:var(--accent-red);"><div class="card-title">\u26a0\ufe0f ERRORE</div><div class="card-sub">{msg}</div></div>', unsafe_allow_html=True)
        st.stop()
    if msg:
        st.markdown(f'<div class="card"><div class="card-title">\U0001f50d Risoluzione</div><div class="card-sub" style="font-family:var(--font-mono);color:var(--accent-cyan);">{msg}</div></div>', unsafe_allow_html=True)
    st.session_state.active_ticker = ticker
    st.session_state.active_cur = cur_sym(ticker)
    st.session_state.active_mkt = "Borsa Italiana" if is_italian(ticker) else "Nasdaq / NYSE"
    st.session_state.show_trim = False  # reset on new ticker

# Render if we have an active ticker
if st.session_state.active_ticker:
    ticker = st.session_state.active_ticker
    cur = st.session_state.active_cur
    mkt = st.session_state.active_mkt

    with st.spinner("Recupero dati..."):
        rt = fetch_realtime(ticker)

    if rt is None:
        st.markdown(f'<div class="card" style="border-color:var(--accent-red);"><div class="card-title">\u26a0\ufe0f ERRORE</div><div class="card-sub">Impossibile recuperare dati.</div></div>', unsafe_allow_html=True)
        st.stop()

    # ── Name + TRIM button ──
    col_name, col_trim = st.columns([4, 1])
    with col_name:
        st.markdown(f'<div class="card"><div class="card-title">\U0001f3e2 {mkt}</div><div class="card-value">{rt["name"]}</div><div class="card-sub" style="font-family:var(--font-mono);color:var(--accent-cyan);">{ticker}</div></div>', unsafe_allow_html=True)
    with col_trim:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("\U0001f4c5 TRIM", use_container_width=True, help="Trimestrali"):
            st.session_state.show_trim = not st.session_state.show_trim
            st.rerun()

    # ── Price ──
    pc = f'{cur}{rt["prev_close"]:,.2f}' if rt["prev_close"] else "\u2014"
    st.markdown(f'<div class="card"><div class="card-title">\U0001f4b0 Prezzo Attuale</div><div class="card-value">{cur}{rt["price"]:,.2f} &nbsp;{pct_badge(rt["change_pct"])}</div><div class="card-sub">Chiusura precedente: {pc}</div></div>', unsafe_allow_html=True)

    # ── RSI + ANALYST CONSENSUS ──
    # Fetch analyst data (single API call)
    with st.spinner("Analisi analisti..."):
        analyst = fetch_analyst_data(ticker)

    # Compute RSI from history (fetched later, but we need closes now)
    # Quick fetch for RSI
    rsi_chart = yahoo_chart(ticker, interval="1d", range_="3mo")
    rsi_val = None
    if rsi_chart:
        rsi_closes = [c for c in rsi_chart.get("indicators",{}).get("quote",[{}])[0].get("close",[]) if c is not None]
        rsi_val = compute_rsi(rsi_closes)

    # Display RSI + Analyst in one row
    if rsi_val is not None or analyst:
        html_parts = []

        # RSI block
        if rsi_val is not None:
            if rsi_val >= 70:
                rsi_label = "IPERCOMPRATO"
                rsi_color = "#ff4757"
                rsi_bg = "rgba(255,71,87,.12)"
                rsi_border = "#ff4757"
            elif rsi_val <= 30:
                rsi_label = "IPERVENDUTO"
                rsi_color = "#00ff88"
                rsi_bg = "rgba(0,255,136,.12)"
                rsi_border = "#00ff88"
            else:
                rsi_label = "NEUTRO"
                rsi_color = "#ffb340"
                rsi_bg = "rgba(255,179,64,.08)"
                rsi_border = "#1b2432"

            st.markdown(
                f'<div style="background:{rsi_bg};border:2px solid {rsi_border};border-radius:12px;padding:.8rem 1rem;margin-bottom:.8rem;text-align:center;">'
                f'<div style="font-size:.65rem;color:var(--text-secondary);letter-spacing:.08em;text-transform:uppercase;">RSI-14</div>'
                f'<div style="font-family:var(--font-mono);font-size:2rem;font-weight:700;color:{rsi_color};line-height:1.2;">{rsi_val}</div>'
                f'<div style="font-size:1rem;font-weight:700;color:{rsi_color};letter-spacing:.1em;">{rsi_label}</div>'
                f'</div>', unsafe_allow_html=True)

        # Analyst consensus
        if analyst and analyst.get("target_mean"):
            a = analyst
            price = rt["price"]
            target = a["target_mean"]
            upside = round((target - price) / price * 100, 1) if price > 0 else 0
            upside_color = "#00ff88" if upside > 0 else "#ff4757"
            upside_sign = "+" if upside > 0 else ""

            # Recommendation label
            rec = a.get("rec_key", "").lower()
            if rec in ("strong_buy", "strongbuy"):
                rec_lbl, rec_color = "STRONG BUY", "#00ff88"
            elif rec in ("buy",):
                rec_lbl, rec_color = "BUY", "#00ff88"
            elif rec in ("hold",):
                rec_lbl, rec_color = "HOLD", "#ffb340"
            elif rec in ("sell",):
                rec_lbl, rec_color = "SELL", "#ff4757"
            elif rec in ("strong_sell", "strongsell"):
                rec_lbl, rec_color = "STRONG SELL", "#ff4757"
            elif rec == "underperform":
                rec_lbl, rec_color = "UNDERPERFORM", "#ff4757"
            elif rec == "outperform":
                rec_lbl, rec_color = "OUTPERFORM", "#00ff88"
            else:
                rec_lbl, rec_color = rec.upper() or "N/A", "#8b949e"

            st.markdown(
                f'<div class="card">'
                f'<div class="card-title">\U0001f3af Target Analisti ({a.get("num_analysts",0)} analisti)</div>'
                f'<div style="text-align:center;margin-bottom:.5rem;">'
                f'<span style="font-size:1.4rem;font-weight:700;color:{rec_color};letter-spacing:.05em;">{rec_lbl}</span></div>'
                f'<div class="metric-row" style="margin-bottom:.3rem">'
                f'<div class="metric-box"><div class="metric-label">Target</div><div class="metric-val" style="color:var(--accent-cyan)">{cur}{target:,.2f}</div></div>'
                f'<div class="metric-box"><div class="metric-label">Potenziale</div><div class="metric-val" style="color:{upside_color}">{upside_sign}{upside:.1f}%</div></div></div>'
                f'<div class="metric-row" style="margin-bottom:.2rem">'
                f'<div class="metric-box"><div class="metric-label">Min Target</div><div class="metric-val" style="color:var(--accent-red)">{cur}{a["target_low"]:,.2f}</div></div>'
                f'<div class="metric-box"><div class="metric-label">Max Target</div><div class="metric-val" style="color:var(--accent-green)">{cur}{a["target_high"]:,.2f}</div></div></div>',
                unsafe_allow_html=True)

            # Recommendation breakdown bar
            rd = a.get("rec_detail", {})
            total_r = sum(rd.values()) or 1
            st.markdown(
                f'<div style="display:flex;height:10px;border-radius:5px;overflow:hidden;margin-top:.4rem;">'
                f'<div style="width:{rd.get("strongBuy",0)/total_r*100:.0f}%;background:#00cc66;"></div>'
                f'<div style="width:{rd.get("buy",0)/total_r*100:.0f}%;background:#00ff88;"></div>'
                f'<div style="width:{rd.get("hold",0)/total_r*100:.0f}%;background:#ffb340;"></div>'
                f'<div style="width:{rd.get("sell",0)/total_r*100:.0f}%;background:#ff6b6b;"></div>'
                f'<div style="width:{rd.get("strongSell",0)/total_r*100:.0f}%;background:#ff4757;"></div></div>'
                f'<div style="display:flex;justify-content:space-between;font-size:.55rem;color:var(--text-secondary);margin-top:.2rem;">'
                f'<span>Strong Buy {rd.get("strongBuy",0)}</span>'
                f'<span>Buy {rd.get("buy",0)}</span>'
                f'<span>Hold {rd.get("hold",0)}</span>'
                f'<span>Sell {rd.get("sell",0)}</span>'
                f'<span>Strong Sell {rd.get("strongSell",0)}</span></div>'
                f'</div>', unsafe_allow_html=True)

    # ── TRIM: Trimestrali ──
    if st.session_state.show_trim:
        with st.spinner("Caricamento dati trimestrali..."):
            analyst_trim = fetch_analyst_data(ticker)

        if analyst_trim:
            a = analyst_trim
            st.markdown(
                '<div class="card" style="border-color:var(--accent-cyan);">'
                '<div class="card-title">\U0001f4c5 TRIMESTRALI</div>',
                unsafe_allow_html=True)

            # Next earnings
            if a.get("next_earnings"):
                st.markdown(
                    f'<div style="text-align:center;margin-bottom:.8rem;">'
                    f'<div style="font-size:.65rem;color:var(--text-secondary);text-transform:uppercase;letter-spacing:.08em;">Prossima trimestrale</div>'
                    f'<div style="font-family:var(--font-mono);font-size:1.5rem;font-weight:700;color:var(--accent-cyan);">{a["next_earnings"]}</div>'
                    f'</div>', unsafe_allow_html=True)
            else:
                st.markdown(
                    '<div style="text-align:center;margin-bottom:.6rem;font-size:.8rem;color:var(--text-secondary);">'
                    'Data prossima trimestrale non ancora confermata.</div>',
                    unsafe_allow_html=True)

            # Earnings sentiment
            if a.get("earnings_sentiment") is not None:
                es = a["earnings_sentiment"]
                if es > 5:
                    es_lbl, es_color, es_icon = "POSITIVO", "#00ff88", "\u25b2"
                elif es < -5:
                    es_lbl, es_color, es_icon = "NEGATIVO", "#ff4757", "\u25bc"
                else:
                    es_lbl, es_color, es_icon = "NEUTRO", "#ffb340", "\u25c6"
                st.markdown(
                    f'<div style="text-align:center;margin-bottom:.8rem;padding:.5rem;background:var(--bg-card-alt);border-radius:8px;">'
                    f'<div style="font-size:.6rem;color:var(--text-secondary);text-transform:uppercase;">Sentiment EPS prossimo trimestre</div>'
                    f'<div style="font-size:1.1rem;font-weight:700;color:{es_color};">'
                    f'{es_icon} {es_lbl} ({es:+.1f}% crescita attesa)</div></div>',
                    unsafe_allow_html=True)

            # Past earnings history + price impact
            if a.get("past_earnings"):
                with st.spinner("Analisi impatto trimestrali..."):
                    hist_for_impact = fetch_history(ticker)

                pe = a["past_earnings"]
                html = '<div style="font-size:.65rem;color:var(--text-secondary);margin-bottom:.3rem;">Ultimi risultati trimestrali:</div>'
                html += '<table class="atr-table"><thead><tr><th>Trimestre</th><th>EPS</th><th>Stima</th><th>Sorpresa</th></tr></thead><tbody>'
                for e in pe:
                    surp = e.get("surprise_pct")
                    surp_str = f'{surp:+.1f}%' if surp is not None else "\u2014"
                    surp_color = "#00ff88" if surp and surp > 0 else ("#ff4757" if surp and surp < 0 else "var(--text-primary)")
                    actual_str = f'{e["actual"]:.2f}' if e.get("actual") is not None else "\u2014"
                    est_str = f'{e["estimate"]:.2f}' if e.get("estimate") is not None else "\u2014"
                    html += (
                        f'<tr><td>{e["quarter"]}</td>'
                        f'<td>{actual_str}</td><td>{est_str}</td>'
                        f'<td style="color:{surp_color}">{surp_str}</td></tr>')
                html += '</tbody></table>'
                st.markdown(html, unsafe_allow_html=True)

                # Price impact around earnings dates
                if hist_for_impact and hist_for_impact.get("daily"):
                    all_daily = hist_for_impact["daily"]
                    for e in pe[:4]:
                        impact = get_earnings_price_impact(all_daily, e["date"])
                        if impact:
                            surp = e.get("surprise_pct")
                            surp_str = f' (EPS sorpresa: {surp:+.1f}%)' if surp is not None else ''
                            st.markdown(
                                f'<div style="font-size:.65rem;color:var(--accent-cyan);margin-top:.6rem;margin-bottom:.2rem;font-weight:600;">'
                                f'\U0001f4ca Impatto {e["quarter"]}{surp_str}</div>',
                                unsafe_allow_html=True)
                            ihtml = '<table class="atr-table"><thead><tr><th></th><th>Data</th><th>Var%</th><th>Vol</th></tr></thead><tbody>'
                            for day in impact:
                                lbl = day["label"]
                                if lbl == "Earnings":
                                    row_style = 'style="background:rgba(0,212,255,.08);"'
                                    lbl_html = f'<b style="color:var(--accent-cyan)">\u2b50 EARNINGS</b>'
                                else:
                                    row_style = ''
                                    lbl_html = f'<span style="color:var(--text-secondary)">{lbl}</span>'
                                ihtml += (
                                    f'<tr {row_style}><td>{lbl_html}</td><td style="font-size:.7rem">{day["date"]}</td>'
                                    f'<td>{pct_badge(day["var_pct"])}</td>'
                                    f'<td>{fmt_num(day["volume"],0)}</td></tr>')
                            ihtml += '</tbody></table>'
                            st.markdown(ihtml, unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

        else:
            st.markdown(
                '<div class="card" style="border-color:var(--accent-amber);">'
                '<div class="card-title">\U0001f4c5 TRIMESTRALI</div>'
                '<div class="card-sub">Dati sulle trimestrali non disponibili per questo ticker.</div></div>',
                unsafe_allow_html=True)

    # ── Range % sessione regolare ──
    if rt["reg_high"] and rt["reg_low"]:
        sp = rt["reg_high"] - rt["reg_low"]
        st.markdown(
            f'<div class="card"><div class="card-title">\U0001f4ca Range Sessione Regolare</div>'
            f'<div class="metric-row" style="margin-bottom:.3rem">'
            f'<div class="metric-box"><div class="metric-label">Min</div><div class="metric-val" style="color:var(--accent-red)">{cur}{rt["reg_low"]:,.2f}</div></div>'
            f'<div class="metric-box"><div class="metric-label">Max</div><div class="metric-val" style="color:var(--accent-green)">{cur}{rt["reg_high"]:,.2f}</div></div>'
            f'<div class="metric-box"><div class="metric-label">Range%</div><div class="metric-val" style="color:var(--accent-amber)">{rt["range_pct"]:.2f}%</div></div>'
            f'</div></div>', unsafe_allow_html=True)

    # ── Volume + pressure ──
    if rt["reg_vol"] > 0:
        st.markdown(
            f'<div class="card"><div class="card-title">\U0001f4ca Volume Sessione Regolare &nbsp;&nbsp;<span style="font-family:var(--font-mono);color:var(--text-primary);font-size:.85rem;">{fmt_num(rt["reg_vol"],1)}</span></div>'
            f'{pressure_bar(rt["reg_buy"], rt["reg_sell"])}'
            f'<div class="card-note">\u26a0\ufe0f Stima basata sulla direzione del prezzo. Non \u00e8 un dato certo.</div>'
            f'</div>', unsafe_allow_html=True)

    # ── Volume vs 3M ──
    with st.spinner("Analisi volumi..."):
        vs = fetch_volume_stats(ticker)
    if vs:
        rc = "var(--accent-green)" if vs["ratio"] and vs["ratio"] >= 1 else "var(--accent-red)"
        st.markdown(
            f'<div class="card"><div class="card-title">\U0001f4ca Volume vs Media ({vs["days"]} sedute)</div>'
            f'<div class="metric-row" style="margin-bottom:.4rem">'
            f'<div class="metric-box"><div class="metric-label">Media</div><div class="metric-val">{fmt_num(vs["avg"],1)}</div></div>'
            f'<div class="metric-box"><div class="metric-label">Max</div><div class="metric-val">{fmt_num(vs["max"],1)}</div></div>'
            f'<div class="metric-box"><div class="metric-label">Min</div><div class="metric-val">{fmt_num(vs["min"],1)}</div></div></div>'
            f'<div class="metric-row" style="margin-bottom:.2rem"><div class="metric-box" style="flex:1"><div class="metric-label">Rapporto Oggi / Media</div>'
            f'<div class="metric-val" style="font-size:1.3rem;color:{rc}">{vs["ratio"]}x</div>'
            f'{vol_ratio_bar(vs["ratio"])}</div></div></div>', unsafe_allow_html=True)

    # ── ATR% + History ──
    with st.spinner("Calcolo ATR%..."):
        hist = fetch_history(ticker)

    if hist is None:
        st.markdown('<div class="card" style="border-color:var(--accent-amber);"><div class="card-title">\u26a0\ufe0f DATI STORICI NON DISPONIBILI</div><div class="card-sub">Impossibile calcolare ATR%.</div></div>', unsafe_allow_html=True)
    else:
        # ATR% summary
        atr_label = f'ATR%-{hist["atr_period"]}'
        ca = hist["current_atr_pct"]
        if ca is not None:
            if ca < 2: vol_color = "var(--accent-green)"; vol_lbl = "Calmo"
            elif ca < 5: vol_color = "var(--accent-amber)"; vol_lbl = "Moderato"
            else: vol_color = "var(--accent-red)"; vol_lbl = "Molto volatile"
            st.markdown(
                f'<div class="card"><div class="card-title">\U0001f4d0 {atr_label} (Beta)</div>'
                f'<div class="card-value" style="color:{vol_color}">{ca:.2f}%</div>'
                f'<div class="card-sub">{vol_lbl} \u00b7 Chiusura {cur}{hist["last_close"]:,.2f}</div></div>',
                unsafe_allow_html=True)

        # Daily history — each day is clickable
        dl = [d for d in hist["daily"] if d.get("atr_pct") is not None]
        if dl:
            # Pre-fetch all intraday data in ONE API call
            with st.spinner("Caricamento dati intraday..."):
                all_intraday = fetch_all_intraday(ticker)

            # Table header
            st.markdown(
                '<div class="card"><div class="card-title">\U0001f4c5 Storico \u00b7 Tocca una data per il dettaglio 30min</div>'
                '<table class="atr-table"><thead><tr>'
                '<th>Data</th><th>Range%</th><th>ATR%</th><th>Var%</th><th>Vol</th>'
                '</tr></thead><tbody>'
                + ''.join(
                    f'<tr><td style="font-size:.7rem">{d["date"]}</td>'
                    f'<td style="color:var(--accent-amber)">{d["range_pct"]:.2f}%</td>'
                    f'<td>{d["atr_pct"]:.2f}%</td>'
                    f'<td>{pct_badge(d["var_pct"])}</td>'
                    f'<td>{fmt_num(d.get("volume",0),0)}</td></tr>'
                    for d in reversed(dl))
                + '</tbody></table></div>',
                unsafe_allow_html=True)

            # Each day as an expander — only last 30 trading days (intraday data available)
            dl_intraday = dl[-30:] if len(dl) > 30 else dl
            for d in reversed(dl_intraday):
                var_sign = "+" if d["var_pct"] > 0 else ""
                exp_label = f'{d["date"]}  \u2502  Range {d["range_pct"]:.1f}%  \u2502  {var_sign}{d["var_pct"]:.1f}%'
                with st.expander(exp_label):
                    bars = all_intraday.get(d["date"])
                    if bars:
                        # Table: Range% = (Max-Min)/Min of each 30-min candle
                        # $1K = potential gain if you caught the full swing
                        html = (
                            f'<table class="atr-table"><thead><tr>'
                            f'<th></th><th>Ora</th><th>Min</th><th>Max</th><th>Range%</th><th style="min-width:60px"></th><th>{cur}1K</th><th>Vol</th>'
                            f'</tr></thead><tbody>')
                        for b in bars:
                            rp = b.get("range_pct", 0)
                            dire = b.get("direction", "flat")

                            # Direction arrow + var%
                            vp = b.get("var_pct")
                            if dire == "up":
                                vp_str = f'+{vp:.1f}%' if vp is not None else ''
                                arrow = f'<span style="color:#00ff88;font-size:.75rem;white-space:nowrap;">\u25b2 {vp_str}</span>'
                            elif dire == "down":
                                vp_str = f'{vp:.1f}%' if vp is not None else ''
                                arrow = f'<span style="color:#ff4757;font-size:.75rem;white-space:nowrap;">\u25bc {vp_str}</span>'
                            else:
                                arrow = '<span style="color:#8b949e;font-size:.7rem;">\u2014</span>'

                            # Visual bar proportional to range
                            if rp > 0:
                                if rp >= 2:
                                    bar_color = "#ff4757"
                                elif rp >= 1:
                                    bar_color = "#ffb340"
                                else:
                                    bar_color = "#00ff88"
                                bar_w = min(rp * 12, 100)
                                bar_html = f'<div style="width:{bar_w:.0f}%;height:6px;background:{bar_color};border-radius:3px;"></div>'
                                gl = rp / 100 * 1000
                                # $1K color follows direction: green if up, red if down
                                if dire == "down":
                                    gl_html = f'<span style="color:#ff4757">-{gl:.1f}</span>'
                                else:
                                    gl_html = f'<span style="color:#00ff88">+{gl:.1f}</span>'
                            else:
                                bar_html = '<div style="height:6px;"></div>'
                                gl_html = '\u2014'

                            html += (
                                f'<tr><td style="padding:0 .15rem">{arrow}</td>'
                                f'<td>{b["time"]}</td>'
                                f'<td style="color:var(--accent-red)">{cur}{b["low"]:,.2f}</td>'
                                f'<td style="color:var(--accent-green)">{cur}{b["high"]:,.2f}</td>'
                                f'<td style="color:var(--accent-amber)">{rp:.2f}%</td>'
                                f'<td style="padding:0 .2rem">{bar_html}</td>'
                                f'<td>{gl_html}</td>'
                                f'<td>{fmt_num(b["volume"],0)}</td></tr>')
                        html += '</tbody></table>'

                        # Day summary: max range in a single 30min candle
                        ranges = [b.get("range_pct", 0) for b in bars]
                        if ranges:
                            max_range = max(ranges)
                            max_r_idx = ranges.index(max_range)
                            avg_range = sum(ranges) / len(ranges)
                            max_gl = max_range / 100 * 1000
                            avg_gl = avg_range / 100 * 1000

                            html += (
                                f'<div style="text-align:center;margin-top:.6rem;padding:.5rem;'
                                f'background:var(--bg-card-alt);border-radius:8px;border:1px solid var(--border);">'
                                f'<div style="font-size:.6rem;color:var(--text-secondary);text-transform:uppercase;letter-spacing:.06em;">'
                                f'Oscillazione max in 30min su {cur}1.000 investiti</div>'
                                f'<div style="font-family:var(--font-mono);font-size:1.2rem;font-weight:600;color:#00ff88;margin-top:.2rem;">'
                                f'+{cur}{max_gl:.2f} ({max_range:.2f}%) ore {bars[max_r_idx]["time"]}</div>'
                                f'<div style="font-size:.65rem;color:var(--text-secondary);margin-top:.25rem;">'
                                f'Media per barra: +{cur}{avg_gl:.2f} ({avg_range:.2f}%)</div></div>')

                        st.markdown(html, unsafe_allow_html=True)

                        # Session summary using direction (open vs close)
                        up = sum(1 for b in bars if b.get("direction") == "up")
                        down = sum(1 for b in bars if b.get("direction") == "down")
                        ranges = [b.get("range_pct", 0) for b in bars]
                        avg_range = sum(ranges) / len(ranges) if ranges else 0
                        strong = sum(1 for r in ranges if r >= 1.0)

                        if up > down * 1.5: d_lbl = '\u25b2 Rialzista'
                        elif down > up * 1.5: d_lbl = '\u25bc Ribassista'
                        else: d_lbl = '\u25c6 Laterale'
                        if avg_range >= 1.5: s_lbl = 'Molto agitata'
                        elif avg_range >= 0.5: s_lbl = 'Moderata'
                        else: s_lbl = 'Calma'

                        st.markdown(
                            f'<div style="font-size:.72rem;color:var(--text-secondary);margin-top:.5rem;line-height:1.6;">'
                            f'\u25b2<span style="color:var(--accent-green)"> {up}</span> / '
                            f'\u25bc<span style="color:var(--accent-red)"> {down}</span> barre &nbsp;\u00b7&nbsp; '
                            f'Range medio: <b style="color:var(--text-primary)">{avg_range:.2f}%</b> &nbsp;\u00b7&nbsp; '
                            f'Barre &gt;1%: <b style="color:var(--text-primary)">{strong}/{len(ranges)}</b><br>'
                            f'{d_lbl} &nbsp;\u00b7&nbsp; {s_lbl}</div>',
                            unsafe_allow_html=True)
                    else:
                        st.markdown(
                            f'<div style="font-size:.75rem;color:var(--text-secondary);">'
                            f'Dati intraday non disponibili per {d["date"]}.</div>',
                            unsafe_allow_html=True)

    # Timestamp
    now = datetime.now().strftime("%H:%M:%S \u00b7 %d/%m/%Y")
    st.markdown(f'<div style="text-align:center;margin-top:.8rem;"><span style="font-size:.65rem;color:var(--text-secondary);font-family:var(--font-mono);">Aggiornamento: {now} \u00b7 Cache 60s</span></div>', unsafe_allow_html=True)

elif not ticker_input.strip() and run:
    st.markdown('<div class="card" style="border-color:var(--accent-amber);"><div class="card-title">\u26a0\ufe0f INSERISCI UN TICKER</div><div class="card-sub">Digita un simbolo (AAPL, ENI.MI) o ISIN.</div></div>', unsafe_allow_html=True)
