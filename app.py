"""
V + ATR - Real-Time Volume & ATR Volatility Monitor
Streamlit Cloud · Mobile-first (540px) · Nasdaq + Borsa Italiana
Supports: Ticker (AAPL, ENI.MI) and ISIN codes (IT0003132476)
Buy/Sell volume pressure estimated via price-direction method.
"""

import streamlit as st
import json
import time
import hashlib
import random
import re
from datetime import datetime
from pathlib import Path
import requests

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="V + ATR",
    page_icon="\U0001f4c8",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─── CONSTANTS ────────────────────────────────────────────────────────────────
CACHE_DIR = Path("disk_cache")
CACHE_DIR.mkdir(exist_ok=True)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
]

YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
YAHOO_SEARCH = "https://query1.finance.yahoo.com/v1/finance/search"
ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")

# Icon path: static/icon.png served via enableStaticServing=true
ICON_PATH = "app/static/icon.png"

# ─── CSS + ICON INJECTION ─────────────────────────────────────────────────────
st.markdown(f"""
<script>
(function() {{
    var iconUrl = window.location.origin + "/" + "{ICON_PATH}";
    function setIcons() {{
        document.querySelectorAll('link[rel*="icon"]').forEach(function(el) {{ el.remove(); }});
        var f = document.createElement('link');
        f.rel = 'icon'; f.type = 'image/png'; f.sizes = '512x512'; f.href = iconUrl;
        document.head.appendChild(f);
        var a = document.createElement('link');
        a.rel = 'apple-touch-icon'; a.sizes = '512x512'; a.href = iconUrl;
        document.head.appendChild(a);
        document.title = 'V+ATR';
    }}
    setIcons();
    new MutationObserver(setIcons).observe(document.head, {{childList: true}});
}})();
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {{
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
}}

html, body, .stApp, [data-testid="stAppViewContainer"],
[data-testid="stApp"], section[data-testid="stMain"] {{
    background: var(--bg-primary) !important;
    color: var(--text-primary) !important;
    font-family: var(--font-sans) !important;
}}
header[data-testid="stHeader"] {{ background: transparent !important; }}
.block-container {{ max-width: 540px !important; padding: 1rem 0.75rem !important; }}

.card {{
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: 12px; padding: 1rem 1.1rem; margin-bottom: 0.8rem;
    position: relative; overflow: hidden;
    transition: border-color .25s, box-shadow .25s;
}}
.card:hover {{ border-color: var(--accent-cyan); box-shadow: 0 0 20px rgba(0,212,255,.08); }}
.card::before {{
    content: ''; position: absolute; top: 0; left: 0; width: 3px; height: 100%;
    background: linear-gradient(180deg, var(--accent-cyan), var(--accent-green));
    animation: gradient-slide 3s ease infinite alternate;
}}
@keyframes gradient-slide {{
    0%   {{ background: linear-gradient(180deg, var(--accent-cyan), var(--accent-green)); }}
    50%  {{ background: linear-gradient(180deg, var(--accent-green), var(--accent-amber)); }}
    100% {{ background: linear-gradient(180deg, var(--accent-amber), var(--accent-cyan)); }}
}}

.card-title {{ font-size:.7rem; font-weight:600; letter-spacing:.08em; text-transform:uppercase; color:var(--text-secondary); margin-bottom:.55rem; }}
.card-value {{ font-family:var(--font-mono); font-size:1.45rem; font-weight:600; color:var(--text-primary); line-height:1.15; }}
.card-sub {{ font-size:.78rem; color:var(--text-secondary); margin-top:.25rem; }}
.card-note {{ font-size:.62rem; color:var(--text-secondary); margin-top:.4rem; font-style:italic; }}

.metric-row {{ display:flex; gap:.6rem; margin-bottom:.8rem; flex-wrap:wrap; }}
.metric-box {{ flex:1; min-width:0; background:var(--bg-card-alt); border:1px solid var(--border); border-radius:10px; padding:.7rem .8rem; text-align:center; }}
.metric-label {{ font-size:.6rem; font-weight:600; letter-spacing:.07em; text-transform:uppercase; color:var(--text-secondary); margin-bottom:.3rem; }}
.metric-val {{ font-family:var(--font-mono); font-size:1.05rem; font-weight:600; color:var(--text-primary); }}

.atr-table {{ width:100%; border-collapse:separate; border-spacing:0; font-size:.75rem; margin-top:.5rem; }}
.atr-table th {{ background:var(--bg-card-alt); color:var(--text-secondary); font-weight:600; text-transform:uppercase; font-size:.6rem; letter-spacing:.06em; padding:.5rem .35rem; text-align:center; border-bottom:1px solid var(--border); }}
.atr-table td {{ padding:.45rem .35rem; text-align:center; border-bottom:1px solid var(--border); font-family:var(--font-mono); color:var(--text-primary); font-size:.73rem; }}
.atr-table tr:last-child td {{ border-bottom:none; }}
.atr-table tr:hover td {{ background:rgba(0,212,255,.04); }}

.badge-up   {{ color: var(--accent-green); }}
.badge-down {{ color: var(--accent-red);   }}
.badge-flat {{ color: var(--text-secondary); }}

/* Volume pressure bar */
.vol-pressure {{
    display:flex; height:8px; border-radius:4px; overflow:hidden; margin-top:.4rem;
}}
.vol-pressure-buy {{ background:var(--accent-green); height:100%; }}
.vol-pressure-sell {{ background:var(--accent-red); height:100%; }}

.vol-bar-bg {{ width:100%; height:6px; background:var(--border); border-radius:3px; margin-top:.3rem; overflow:hidden; }}
.vol-bar-fill {{ height:100%; border-radius:3px; }}

.legend {{
    background:var(--bg-card); border:1px solid var(--border); border-radius:12px;
    padding:1rem 1.1rem; margin-bottom:.8rem; font-size:.78rem; line-height:1.65; color:var(--text-secondary);
}}
.legend h3 {{ font-size:.82rem; color:var(--accent-cyan); margin:.8rem 0 .3rem; font-weight:600; }}
.legend h3:first-child {{ margin-top:0; }}
.legend b {{ color:var(--text-primary); }}
.legend .signal-buy {{ color:var(--accent-green); font-weight:600; }}
.legend .signal-warn {{ color:var(--accent-amber); font-weight:600; }}
.legend .signal-sell {{ color:var(--accent-red); font-weight:600; }}
.legend code {{ background:var(--bg-card-alt); padding:.1rem .35rem; border-radius:4px; font-family:var(--font-mono); font-size:.72rem; color:var(--accent-cyan); }}

input[type="text"], .stTextInput input {{ background:var(--bg-card-alt) !important; color:var(--text-primary) !important; border:1px solid var(--border) !important; border-radius:8px !important; font-family:var(--font-mono) !important; }}
.stTextInput input:focus {{ border-color:var(--accent-cyan) !important; box-shadow:0 0 8px rgba(0,212,255,.15) !important; }}
.stButton > button {{ background:linear-gradient(135deg,#00d4ff 0%,#00ff88 100%) !important; color:#080c10 !important; font-weight:700 !important; border:none !important; border-radius:8px !important; width:100% !important; padding:.6rem !important; font-family:var(--font-sans) !important; }}
.stButton > button:hover {{ opacity:.88 !important; }}

.app-header {{ text-align:center; padding:.6rem 0 .4rem; }}
.app-header h1 {{ font-family:var(--font-mono); font-size:1.5rem; font-weight:700; background:linear-gradient(90deg,var(--accent-cyan),var(--accent-green)); -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin:0; }}
.app-header p {{ color:var(--text-secondary); font-size:.72rem; margin:.15rem 0 0; }}

::-webkit-scrollbar {{ width:4px; }}
::-webkit-scrollbar-track {{ background:var(--bg-primary); }}
::-webkit-scrollbar-thumb {{ background:var(--border); border-radius:4px; }}
#MainMenu, footer, [data-testid="stToolbar"] {{ display:none !important; }}

[data-testid="stExpander"] {{ background:transparent !important; border:none !important; }}
[data-testid="stExpander"] details {{ background:var(--bg-card) !important; border:1px solid var(--border) !important; border-radius:12px !important; }}
[data-testid="stExpander"] summary {{ color:var(--text-secondary) !important; font-size:.8rem !important; }}
</style>
""", unsafe_allow_html=True)


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def safe_fetch(url, retries=3, timeout=12):
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers={
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "application/json, text/html, */*",
                "Accept-Language": "en-US,en;q=0.9",
            }, timeout=timeout)
            if resp.status_code == 200:
                return resp
        except Exception:
            pass
        time.sleep(1.5 * (attempt + 1))
    return None


def _cache_key(name):
    return CACHE_DIR / f"{hashlib.md5(name.encode()).hexdigest()[:12]}.json"


def save_disk(name, data):
    try:
        with open(_cache_key(name), "w") as f:
            json.dump({"ts": time.time(), "data": data}, f)
    except Exception:
        pass


def load_disk(name, max_age=86400):
    p = _cache_key(name)
    if not p.exists():
        return None
    try:
        with open(p) as f:
            obj = json.load(f)
        return obj["data"] if time.time() - obj["ts"] <= max_age else None
    except Exception:
        return None


def is_italian(ticker):
    return ticker.upper().endswith(".MI")


def cur_sym(ticker):
    return "\u20ac" if is_italian(ticker) else "$"


def fmt_num(val, decimals=2, prefix=""):
    if val is None:
        return "\u2014"
    v = abs(val)
    if v >= 1e9: return f"{prefix}{val/1e9:,.{decimals}f}B"
    if v >= 1e6: return f"{prefix}{val/1e6:,.{decimals}f}M"
    if v >= 1e3: return f"{prefix}{val/1e3:,.{decimals}f}K"
    return f"{prefix}{val:,.{decimals}f}"


def pct_badge(val):
    if val is None:
        return '<span class="badge-flat">\u2014</span>'
    cls = "badge-up" if val > 0 else ("badge-down" if val < 0 else "badge-flat")
    sign = "+" if val > 0 else ""
    return f'<span class="{cls}">{sign}{val:.2f}%</span>'


def pressure_bar_html(buy_vol, sell_vol, label=""):
    total = buy_vol + sell_vol
    if total == 0:
        return ""
    buy_pct = buy_vol / total * 100
    sell_pct = 100 - buy_pct
    return (
        f'<div style="display:flex;justify-content:space-between;font-size:.62rem;color:var(--text-secondary);margin-top:.2rem;">'
        f'<span style="color:var(--accent-green)">\u25b2 Buy {buy_pct:.0f}% ({fmt_num(buy_vol,1)})</span>'
        f'<span style="color:var(--accent-red)">\u25bc Sell {sell_pct:.0f}% ({fmt_num(sell_vol,1)})</span></div>'
        f'<div class="vol-pressure">'
        f'<div class="vol-pressure-buy" style="width:{buy_pct:.1f}%"></div>'
        f'<div class="vol-pressure-sell" style="width:{sell_pct:.1f}%"></div></div>'
    )


def vol_ratio_bar(ratio):
    if ratio is None:
        return ""
    pct = min(ratio * 100, 200)
    color = "var(--accent-green)" if ratio >= 1.5 else ("var(--accent-amber)" if ratio >= 0.8 else "var(--accent-red)")
    label = "Alto" if ratio >= 1.5 else ("Nella media" if ratio >= 0.8 else "Basso")
    return (
        f'<div style="display:flex;justify-content:space-between;font-size:.65rem;color:var(--text-secondary);margin-top:.15rem;">'
        f'<span>{label}</span><span>{ratio:.1f}x media 3M</span></div>'
        f'<div class="vol-bar-bg"><div class="vol-bar-fill" style="width:{pct:.0f}%;background:{color};"></div></div>'
    )


# ─── ISIN RESOLVER ────────────────────────────────────────────────────────────

def is_isin(text):
    return bool(ISIN_RE.match(text.upper()))


@st.cache_data(ttl=3600, show_spinner=False)
def resolve_isin(isin):
    isin = isin.upper()
    resp = safe_fetch(f"{YAHOO_SEARCH}?q={isin}&quotesCount=5&newsCount=0")
    if resp is None:
        return None
    try:
        quotes = resp.json().get("quotes", [])
        for q in quotes:
            if q.get("quoteType") == "EQUITY":
                return q.get("symbol")
        return quotes[0].get("symbol") if quotes else None
    except Exception:
        return None


def resolve_input(user_input):
    text = user_input.strip().upper()
    if not text:
        return None, "Inserisci un ticker o codice ISIN."
    if is_isin(text):
        ticker = resolve_isin(text)
        return (ticker, f"ISIN {text} \u2192 {ticker}") if ticker else (None, f"ISIN {text} non trovato.")
    return text, None


# ─── YAHOO API ────────────────────────────────────────────────────────────────

def yahoo_chart(ticker, interval="1d", range_="1mo", prepost=False):
    params = {"interval": interval, "range": range_, "includePrePost": "true" if prepost else "false"}
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    resp = safe_fetch(f"{YAHOO_CHART.format(ticker=ticker)}?{qs}")
    if resp is None:
        return None
    try:
        result = resp.json().get("chart", {}).get("result")
        return result[0] if result else None
    except Exception:
        return None


# ─── FETCH REAL-TIME WITH BUY/SELL PRESSURE ───────────────────────────────────

@st.cache_data(ttl=60, show_spinner=False)
def fetch_realtime(ticker):
    chart = yahoo_chart(ticker, interval="1m", range_="1d", prepost=True)
    if chart is None:
        return None
    try:
        meta = chart.get("meta", {})
        quotes = chart.get("indicators", {}).get("quote", [{}])[0]
        timestamps = chart.get("timestamp", [])
        if not timestamps:
            return None

        last_price = meta.get("regularMarketPrice", 0)
        prev_close = meta.get("previousClose") or meta.get("chartPreviousClose", 0)
        name = meta.get("shortName") or meta.get("symbol", ticker.upper())
        change_pct = ((last_price - prev_close) / prev_close * 100) if prev_close else None

        volumes = quotes.get("volume", [])
        highs = quotes.get("high", [])
        lows = quotes.get("low", [])
        opens = quotes.get("open", [])
        closes = quotes.get("close", [])

        reg_start = meta.get("currentTradingPeriod", {}).get("regular", {}).get("start", 0)
        reg_end = meta.get("currentTradingPeriod", {}).get("regular", {}).get("end", 0)

        # Classify each 1-min bar as buy or sell pressure based on price direction
        # IMPORTANT: reset prev_mid at session boundaries to avoid contamination
        total_vol = 0; buy_vol = 0; sell_vol = 0
        pre_total = 0; pre_buy = 0; pre_sell = 0
        ah_total = 0; ah_buy = 0; ah_sell = 0
        reg_total = 0; reg_buy = 0; reg_sell = 0

        prev_mid = None
        prev_session = None  # track session changes

        for i in range(len(timestamps)):
            v = volumes[i] if i < len(volumes) and volumes[i] is not None else 0
            h = highs[i] if i < len(highs) and highs[i] is not None else None
            lo = lows[i] if i < len(lows) and lows[i] is not None else None
            if v == 0 or h is None or lo is None:
                continue

            mid = (h + lo) / 2
            ts = timestamps[i]

            # Determine session
            if ts < reg_start:
                session = "pre"
            elif ts >= reg_end:
                session = "ah"
            else:
                session = "reg"

            # Reset midpoint at session boundaries to avoid cross-contamination
            if prev_session is not None and session != prev_session:
                prev_mid = None

            # Determine direction
            is_buy = True  # default for first bar in session
            if prev_mid is not None:
                is_buy = (mid >= prev_mid)
            else:
                o_val = opens[i] if i < len(opens) and opens[i] is not None else None
                c_val = closes[i] if i < len(closes) and closes[i] is not None else None
                if o_val is not None and c_val is not None:
                    is_buy = (c_val >= o_val)

            # Accumulate
            total_vol += v
            if is_buy:
                buy_vol += v
            else:
                sell_vol += v

            if session == "pre":
                pre_total += v
                if is_buy: pre_buy += v
                else: pre_sell += v
            elif session == "ah":
                ah_total += v
                if is_buy: ah_buy += v
                else: ah_sell += v
            else:
                reg_total += v
                if is_buy: reg_buy += v
                else: reg_sell += v

            prev_mid = mid
            prev_session = session

        valid_h = [h for h in highs if h is not None]
        valid_l = [lo for lo in lows if lo is not None]

        return {
            "price": round(last_price, 4),
            "prev_close": round(prev_close, 4) if prev_close else None,
            "change_pct": round(change_pct, 2) if change_pct is not None else None,
            "total_volume": total_vol,
            "buy_volume": buy_vol,
            "sell_volume": sell_vol,
            "reg_total": reg_total, "reg_buy": reg_buy, "reg_sell": reg_sell,
            "pre_total": pre_total, "pre_buy": pre_buy, "pre_sell": pre_sell,
            "ah_total": ah_total, "ah_buy": ah_buy, "ah_sell": ah_sell,
            "day_high": round(max(valid_h), 4) if valid_h else None,
            "day_low": round(min(valid_l), 4) if valid_l else None,
            "name": name,
        }
    except Exception:
        return None


# ─── FETCH VOLUME STATS ──────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def fetch_volume_stats(ticker):
    chart = yahoo_chart(ticker, interval="1d", range_="3mo")
    if chart is None:
        return None
    try:
        q = chart.get("indicators", {}).get("quote", [{}])[0]
        vols = q.get("volume", [])
        daily_vols = [v for v in vols if v is not None and v > 0]
        if len(daily_vols) < 5:
            return None
        today_vol = daily_vols[-1]
        hist = daily_vols[:-1]
        avg = sum(hist) / len(hist)
        return {
            "today_vol": today_vol, "avg_vol_3m": round(avg),
            "max_vol_3m": max(hist), "min_vol_3m": min(hist),
            "ratio": round(today_vol / avg, 2) if avg > 0 else None,
            "trading_days": len(hist),
        }
    except Exception:
        return None


# ─── FETCH ATR ────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def fetch_atr_data(ticker):
    cache_name = f"atr_v3_{ticker}"
    cached = load_disk(cache_name, max_age=3600)
    if cached:
        return cached
    try:
        dc = yahoo_chart(ticker, interval="1d", range_="3mo")
        if dc is None:
            return None
        ts_list = dc.get("timestamp", [])
        q = dc.get("indicators", {}).get("quote", [{}])[0]
        opens, highs, lows, closes = q.get("open",[]), q.get("high",[]), q.get("low",[]), q.get("close",[])
        vols_d = q.get("volume", [])
        if len(ts_list) < 15:
            return None

        rows = []
        for i in range(len(ts_list)):
            o,h,lo,c = (x[i] if i < len(x) else None for x in [opens,highs,lows,closes])
            vd = vols_d[i] if i < len(vols_d) and vols_d[i] is not None else 0
            if None in (o,h,lo,c):
                continue
            rows.append({"date": datetime.utcfromtimestamp(ts_list[i]).strftime("%Y-%m-%d"),
                         "open":round(o,4),"high":round(h,4),"low":round(lo,4),"close":round(c,4),"volume":int(vd)})
        if len(rows) < 15:
            return None

        for i,r in enumerate(rows):
            r["tr"] = round(r["high"]-r["low"],4) if i==0 else round(max(r["high"]-r["low"],abs(r["high"]-rows[i-1]["close"]),abs(r["low"]-rows[i-1]["close"])),4)

        atr_p = 14
        for i,r in enumerate(rows):
            if i < atr_p-1: r["atr"] = None
            elif i == atr_p-1: r["atr"] = round(sum(rows[j]["tr"] for j in range(atr_p))/atr_p,4)
            else: r["atr"] = round((rows[i-1]["atr"]*(atr_p-1)+r["tr"])/atr_p,4)

        for i,r in enumerate(rows):
            r["pct_change"] = 0.0 if i==0 else round((r["close"]-rows[i-1]["close"])/rows[i-1]["close"]*100,2)

        ic = yahoo_chart(ticker, interval="30m", range_="5d")
        intraday, last_td = [], None
        if ic:
            its = ic.get("timestamp",[])
            iq = ic.get("indicators",{}).get("quote",[{}])[0]
            if its:
                dates_seen = sorted(set(datetime.utcfromtimestamp(t).strftime("%Y-%m-%d") for t in its))
                last_td = dates_seen[-1] if dates_seen else None
                if last_td:
                    ih,il,iv = iq.get("high",[]),iq.get("low",[]),iq.get("volume",[])
                    for i,t in enumerate(its):
                        d = datetime.utcfromtimestamp(t)
                        if d.strftime("%Y-%m-%d") != last_td: continue
                        hv = ih[i] if i<len(ih) and ih[i] is not None else None
                        lv = il[i] if i<len(il) and il[i] is not None else None
                        vv = iv[i] if i<len(iv) and iv[i] is not None else 0
                        if hv is None or lv is None: continue
                        mid = (hv+lv)/2
                        intraday.append({"time":d.strftime("%H:%M"),"high":round(hv,4),"low":round(lv,4),
                                         "range":round(hv-lv,4),"mid":round(mid,4),"volume":int(vv)})
                    for idx,bar in enumerate(intraday):
                        if idx == 0: bar["pct_change"] = None
                        else:
                            pm = intraday[idx-1]["mid"]
                            bar["pct_change"] = round((bar["mid"]-pm)/pm*100,2) if pm else None
                    # Compute True Range and ATR-5 for intraday bars
                    for idx,bar in enumerate(intraday):
                        if idx == 0:
                            bar["tr"] = bar["range"]
                        else:
                            prev_mid = intraday[idx-1]["mid"]
                            bar["tr"] = round(max(bar["range"], abs(bar["high"]-prev_mid), abs(bar["low"]-prev_mid)),4)
                    atr_intra = 5
                    for idx,bar in enumerate(intraday):
                        if idx < atr_intra-1:
                            bar["atr"] = None
                        elif idx == atr_intra-1:
                            bar["atr"] = round(sum(intraday[j]["tr"] for j in range(atr_intra))/atr_intra,4)
                        else:
                            bar["atr"] = round((intraday[idx-1]["atr"]*(atr_intra-1)+bar["tr"])/atr_intra,4)

        rows = rows[-25:]
        ca = rows[-1].get("atr")
        lc = rows[-1]["close"]
        result = {"daily":rows,"intraday_30min":intraday,"current_atr":ca,
                  "atr_pct":round(ca/lc*100,2) if ca and lc else None,
                  "last_close":lc,"last_trading_day":last_td}
        save_disk(cache_name, result)
        return result
    except Exception:
        return None


# ─── LEGEND ───────────────────────────────────────────────────────────────────
LEGEND_HTML = """
<div class="legend">

<h3>\U0001f4b0 Prezzo e Variazione</h3>
<b>Prezzo Attuale</b> \u2014 Ultimo prezzo scambiato (incluso pre/after market).<br>
<b>Var%</b> \u2014 Scostamento dal prezzo di chiusura del giorno prima.<br>
\u2022 <span class="signal-buy">Verde (+)</span> = il titolo sta salendo \u2022 <span class="signal-sell">Rosso (-)</span> = sta scendendo.

<h3>\U0001f4ca Volume e Pressione Buy/Sell</h3>
<b>Volume Oggi</b> \u2014 Totale azioni scambiate nella giornata.<br>
<b>Barra Buy/Sell</b> \u2014 Stima della pressione in acquisto vs vendita.<br>
\u26a0\ufe0f <b>Importante:</b> i dati di mercato NON distinguono compratori da venditori. Ogni scambio ha entrambi.
La stima usa il <b>metodo della direzione del prezzo</b>: se il prezzo sale in una barra da 1 minuto, quel volume \u00e8 classificato come "buy pressure"; se scende, come "sell pressure". \u00c8 un'approssimazione usata nell'analisi tecnica, non un dato certo.<br>
\u2022 <span class="signal-buy">Buy &gt; 60%</span> = forte pressione in acquisto.<br>
\u2022 <span class="signal-sell">Sell &gt; 60%</span> = forte pressione in vendita.<br>
\u2022 Circa 50/50 = equilibrio tra compratori e venditori.

<h3>\U0001f4ca Volume vs Media Trimestrale</h3>
\u2022 <span class="signal-buy">&gt; 1.5x</span> = volume anomalo alto \u2192 forte interesse.<br>
\u2022 <span class="signal-warn">0.8x \u2013 1.5x</span> = nella norma.<br>
\u2022 <span class="signal-sell">&lt; 0.8x</span> = volume basso \u2192 movimento meno affidabile.

<h3>\U0001f4d0 ATR-14</h3>
Misura la volatilit\u00e0 media degli ultimi 14 giorni. Non indica direzione, ma quanto si muove il titolo.<br>
\u2022 <code>ATR% &lt; 2%</code> bassa \u2022 <code>2-5%</code> moderata \u2022 <code>&gt; 5%</code> alta volatilit\u00e0.

<h3>\u2705 Segnali Favorevoli all'Acquisto</h3>
\u2022 Buy pressure <span class="signal-buy">&gt; 60%</span> + volume <span class="signal-buy">&gt; 1.5x</span> media + prezzo in salita.<br>
\u2022 ATR in aumento + prezzo sopra la chiusura precedente.<br>
\u2022 Volume esteso alto con buy pressure dominante in pre-market.

<h3>\u26a0\ufe0f Segnali di Cautela</h3>
\u2022 Prezzo sale ma sell pressure <span class="signal-sell">&gt; 60%</span> = salita debole.<br>
\u2022 Volume <span class="signal-sell">&lt; 0.8x</span> media = scarso interesse.<br>
\u2022 ATR% molto alto (<code>&gt;8%</code>) = rischio di inversioni improvvise.

</div>
"""

# ─── HEADER ───────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="app-header"><h1>\U0001f4ca V + ATR</h1>'
    '<p>Real-Time Volume &amp; Volatility \u00b7 Nasdaq &amp; Borsa Italiana</p></div>',
    unsafe_allow_html=True)

c1, c2 = st.columns([3, 1.2])
with c1:
    ticker_input = st.text_input("Ticker / ISIN", value="", placeholder="AAPL, ENI.MI, IT0003132476...", label_visibility="collapsed")
with c2:
    st.markdown("<div style='height:1px'></div>", unsafe_allow_html=True)
    run = st.button("Genera \u25b6", use_container_width=True)

show_atr = st.toggle("\U0001f52c Modulo ATR (Volatilit\u00e0)", value=False)

with st.expander("\U0001f4d6 Guida ai Dati \u2014 Come leggere i risultati"):
    st.markdown(LEGEND_HTML, unsafe_allow_html=True)

# ─── MAIN ─────────────────────────────────────────────────────────────────────
if run and ticker_input.strip():
    raw_input = ticker_input.strip().upper()

    with st.spinner("Risoluzione ticker..."):
        ticker, resolve_msg = resolve_input(raw_input)

    if ticker is None:
        st.markdown(f'<div class="card" style="border-color:var(--accent-red);"><div class="card-title">\u26a0\ufe0f ERRORE</div><div class="card-sub">{resolve_msg}</div></div>', unsafe_allow_html=True)
        st.stop()

    if resolve_msg:
        st.markdown(f'<div class="card"><div class="card-title">\U0001f50d Risoluzione</div><div class="card-sub" style="font-family:var(--font-mono);color:var(--accent-cyan);">{resolve_msg}</div></div>', unsafe_allow_html=True)

    cur = cur_sym(ticker)
    mkt = "Borsa Italiana" if is_italian(ticker) else "Nasdaq / NYSE"

    with st.spinner("Recupero dati..."):
        rt = fetch_realtime(ticker)

    if rt is None and "." not in ticker:
        rt = fetch_realtime(ticker + ".MI")
        if rt is not None:
            ticker, cur, mkt = ticker + ".MI", "\u20ac", "Borsa Italiana"

    if rt is None:
        st.markdown(f'<div class="card" style="border-color:var(--accent-red);"><div class="card-title">\u26a0\ufe0f ERRORE</div><div class="card-sub">Impossibile recuperare dati per <b>{raw_input}</b>. Prova con .MI o il codice ISIN.</div></div>', unsafe_allow_html=True)
        st.stop()

    # Name
    st.markdown(f'<div class="card"><div class="card-title">\U0001f3e2 {mkt}</div><div class="card-value">{rt["name"]}</div><div class="card-sub" style="font-family:var(--font-mono);color:var(--accent-cyan);">{ticker}</div></div>', unsafe_allow_html=True)

    # Price
    pc_str = f'{cur}{rt["prev_close"]:,.2f}' if rt["prev_close"] else "\u2014"
    st.markdown(f'<div class="card"><div class="card-title">\U0001f4b0 Prezzo Attuale</div><div class="card-value">{cur}{rt["price"]:,.2f} &nbsp;{pct_badge(rt["change_pct"])}</div><div class="card-sub">Chiusura precedente: {pc_str}</div></div>', unsafe_allow_html=True)

    # Volume overview — 3 boxes
    st.markdown(
        f'<div class="metric-row">'
        f'<div class="metric-box"><div class="metric-label">Vol. Regolare</div>'
        f'<div class="metric-val">{fmt_num(rt["reg_total"],1)}</div></div>'
        f'<div class="metric-box"><div class="metric-label">\U0001f305 Pre-Market</div>'
        f'<div class="metric-val">{fmt_num(rt["pre_total"],1)}</div></div>'
        f'<div class="metric-box"><div class="metric-label">\U0001f319 After-Hours</div>'
        f'<div class="metric-val">{fmt_num(rt["ah_total"],1)}</div></div>'
        f'</div>', unsafe_allow_html=True)

    # Regular session pressure
    if rt["reg_total"] > 0:
        st.markdown(
            f'<div class="card">'
            f'<div class="card-title">\U0001f4ca Sessione Regolare &nbsp;&nbsp;<span style="font-family:var(--font-mono);color:var(--text-primary);font-size:.85rem;">{fmt_num(rt["reg_total"],1)}</span></div>'
            f'{pressure_bar_html(rt["reg_buy"], rt["reg_sell"])}'
            f'<div class="card-note">\u26a0\ufe0f Stima basata sulla direzione del prezzo (metodo midpoint). Non \u00e8 un dato certo.</div>'
            f'</div>', unsafe_allow_html=True)

    # Pre-Market pressure
    if rt["pre_total"] > 0:
        st.markdown(
            f'<div class="card">'
            f'<div class="card-title">\U0001f305 Pre-Market &nbsp;&nbsp;<span style="font-family:var(--font-mono);color:var(--text-primary);font-size:.85rem;">{fmt_num(rt["pre_total"],1)}</span></div>'
            f'{pressure_bar_html(rt["pre_buy"], rt["pre_sell"])}'
            f'</div>', unsafe_allow_html=True)

    # After-Hours pressure
    if rt["ah_total"] > 0:
        st.markdown(
            f'<div class="card">'
            f'<div class="card-title">\U0001f319 After-Hours &nbsp;&nbsp;<span style="font-family:var(--font-mono);color:var(--text-primary);font-size:.85rem;">{fmt_num(rt["ah_total"],1)}</span></div>'
            f'{pressure_bar_html(rt["ah_buy"], rt["ah_sell"])}'
            f'</div>', unsafe_allow_html=True)

    # Volume vs 3M average
    with st.spinner("Analisi volumi..."):
        vs = fetch_volume_stats(ticker)

    if vs:
        rc = "var(--accent-green)" if vs["ratio"] and vs["ratio"] >= 1 else "var(--accent-red)"
        st.markdown(
            f'<div class="card"><div class="card-title">\U0001f4ca Volume vs Media Trimestrale ({vs["trading_days"]} sedute)</div>'
            f'<div class="metric-row" style="margin-bottom:.4rem">'
            f'<div class="metric-box"><div class="metric-label">Media 3M</div><div class="metric-val">{fmt_num(vs["avg_vol_3m"],1)}</div></div>'
            f'<div class="metric-box"><div class="metric-label">Max 3M</div><div class="metric-val">{fmt_num(vs["max_vol_3m"],1)}</div></div>'
            f'<div class="metric-box"><div class="metric-label">Min 3M</div><div class="metric-val">{fmt_num(vs["min_vol_3m"],1)}</div></div></div>'
            f'<div class="metric-row" style="margin-bottom:.2rem"><div class="metric-box" style="flex:1"><div class="metric-label">Rapporto Oggi / Media</div>'
            f'<div class="metric-val" style="font-size:1.3rem;color:{rc}">{vs["ratio"]}x</div>'
            f'{vol_ratio_bar(vs["ratio"])}</div></div></div>', unsafe_allow_html=True)

    # Day range
    if rt["day_high"] and rt["day_low"]:
        sp = rt["day_high"] - rt["day_low"]
        st.markdown(
            f'<div class="metric-row">'
            f'<div class="metric-box"><div class="metric-label">Min Giorno</div><div class="metric-val" style="color:var(--accent-red)">{cur}{rt["day_low"]:,.2f}</div></div>'
            f'<div class="metric-box"><div class="metric-label">Max Giorno</div><div class="metric-val" style="color:var(--accent-green)">{cur}{rt["day_high"]:,.2f}</div></div>'
            f'<div class="metric-box"><div class="metric-label">Spread</div><div class="metric-val">{cur}{sp:,.2f}</div></div></div>', unsafe_allow_html=True)

    # ATR
    if show_atr:
        with st.spinner("Calcolo ATR..."):
            atr = fetch_atr_data(ticker)
        if atr is None:
            st.markdown('<div class="card" style="border-color:var(--accent-amber);"><div class="card-title">\u26a0\ufe0f ATR NON DISPONIBILE</div><div class="card-sub">Dati storici insufficienti.</div></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="card"><div class="card-title">\U0001f4d0 ATR-14</div><div class="card-value">{cur}{atr["current_atr"]:,.4f}</div><div class="card-sub">{atr["atr_pct"]}% della chiusura ({cur}{atr["last_close"]:,.2f}) &middot; Estensione media movimento</div></div>', unsafe_allow_html=True)

            if atr["intraday_30min"]:
                html = f'<div class="card"><div class="card-title">\u23f1 Intraday 30min \u00b7 {atr["last_trading_day"] or ""}</div><table class="atr-table"><thead><tr><th>Ora</th><th>Min</th><th>Max</th><th>Range</th><th>ATR5</th><th>Var%</th><th>Vol</th></tr></thead><tbody>'
                for s in atr["intraday_30min"]:
                    atr_cell = f'{cur}{s["atr"]:,.2f}' if s.get("atr") is not None else '\u2014'
                    html += f'<tr><td>{s["time"]}</td><td style="color:var(--accent-red)">{cur}{s["low"]:,.2f}</td><td style="color:var(--accent-green)">{cur}{s["high"]:,.2f}</td><td>{cur}{s["range"]:,.2f}</td><td style="color:var(--accent-amber)">{atr_cell}</td><td>{pct_badge(s.get("pct_change"))}</td><td>{fmt_num(s["volume"],0)}</td></tr>'
                html += '</tbody></table></div>'
                st.markdown(html, unsafe_allow_html=True)

            if atr["daily"]:
                dl = [d for d in atr["daily"] if d.get("atr") is not None][-22:]
                html = '<div class="card"><div class="card-title">\U0001f4c5 Storico Mese</div><table class="atr-table"><thead><tr><th>Data</th><th>Min</th><th>Max</th><th>ATR</th><th>Var%</th><th>Vol</th></tr></thead><tbody>'
                for d in reversed(dl):
                    html += f'<tr><td style="font-size:.7rem">{d["date"]}</td><td style="color:var(--accent-red)">{cur}{d["low"]:,.2f}</td><td style="color:var(--accent-green)">{cur}{d["high"]:,.2f}</td><td style="color:var(--accent-amber)">{cur}{d["atr"]:,.2f}</td><td>{pct_badge(d["pct_change"])}</td><td>{fmt_num(d.get("volume",0),0)}</td></tr>'
                html += '</tbody></table></div>'
                st.markdown(html, unsafe_allow_html=True)

    now_str = datetime.now().strftime("%H:%M:%S \u00b7 %d/%m/%Y")
    st.markdown(f'<div style="text-align:center;margin-top:.8rem;"><span style="font-size:.65rem;color:var(--text-secondary);font-family:var(--font-mono);">Aggiornamento: {now_str} \u00b7 Cache 60s</span></div>', unsafe_allow_html=True)

elif not ticker_input.strip() and run:
    st.markdown('<div class="card" style="border-color:var(--accent-amber);"><div class="card-title">\u26a0\ufe0f INSERISCI UN TICKER O ISIN</div><div class="card-sub">Digita un simbolo (AAPL, ENI.MI) o ISIN (IT0003132476).</div></div>', unsafe_allow_html=True)
