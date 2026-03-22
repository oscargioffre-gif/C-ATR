"""
V + ATR - Real-Time Volume & ATR Volatility Monitor
Streamlit Cloud · Mobile-first (540px) · Nasdaq + Borsa Italiana
Supports: Ticker (AAPL, ENI.MI) and ISIN codes (IT0003132476)
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

# App icon base64 (green chart on black)
ICON_B64 = "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"

# ─── CSS + PWA META ───────────────────────────────────────────────────────────
st.markdown(f"""
<head>
<link rel="icon" type="image/png" href="data:image/png;base64,{ICON_B64}">
<link rel="apple-touch-icon" href="data:image/png;base64,{ICON_B64}">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="V+ATR">
<meta name="mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#080c10">
</head>

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
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1rem 1.1rem;
    margin-bottom: 0.8rem;
    position: relative;
    overflow: hidden;
    transition: border-color .25s, box-shadow .25s;
}}
.card:hover {{
    border-color: var(--accent-cyan);
    box-shadow: 0 0 20px rgba(0,212,255,.08);
}}
.card::before {{
    content: '';
    position: absolute; top: 0; left: 0; width: 3px; height: 100%;
    background: linear-gradient(180deg, var(--accent-cyan), var(--accent-green));
    animation: gradient-slide 3s ease infinite alternate;
}}
@keyframes gradient-slide {{
    0%   {{ background: linear-gradient(180deg, var(--accent-cyan), var(--accent-green)); }}
    50%  {{ background: linear-gradient(180deg, var(--accent-green), var(--accent-amber)); }}
    100% {{ background: linear-gradient(180deg, var(--accent-amber), var(--accent-cyan)); }}
}}

.card-title {{
    font-size: .7rem; font-weight: 600; letter-spacing: .08em;
    text-transform: uppercase; color: var(--text-secondary);
    margin-bottom: .55rem;
}}
.card-value {{
    font-family: var(--font-mono); font-size: 1.45rem;
    font-weight: 600; color: var(--text-primary); line-height: 1.15;
}}
.card-sub {{
    font-size: .78rem; color: var(--text-secondary); margin-top: .25rem;
}}

.metric-row {{ display: flex; gap: .6rem; margin-bottom: .8rem; flex-wrap: wrap; }}
.metric-box {{
    flex: 1; min-width: 0; background: var(--bg-card-alt); border: 1px solid var(--border);
    border-radius: 10px; padding: .7rem .8rem; text-align: center;
}}
.metric-label {{
    font-size: .6rem; font-weight: 600; letter-spacing: .07em;
    text-transform: uppercase; color: var(--text-secondary); margin-bottom: .3rem;
}}
.metric-val {{
    font-family: var(--font-mono); font-size: 1.05rem;
    font-weight: 600; color: var(--text-primary);
}}

.atr-table {{
    width: 100%; border-collapse: separate; border-spacing: 0;
    font-size: .75rem; margin-top: .5rem;
}}
.atr-table th {{
    background: var(--bg-card-alt); color: var(--text-secondary);
    font-weight: 600; text-transform: uppercase; font-size: .6rem;
    letter-spacing: .06em; padding: .5rem .35rem; text-align: center;
    border-bottom: 1px solid var(--border);
}}
.atr-table td {{
    padding: .45rem .35rem; text-align: center; border-bottom: 1px solid var(--border);
    font-family: var(--font-mono); color: var(--text-primary); font-size: .73rem;
}}
.atr-table tr:last-child td {{ border-bottom: none; }}
.atr-table tr:hover td {{ background: rgba(0,212,255,.04); }}

.badge-up   {{ color: var(--accent-green); }}
.badge-down {{ color: var(--accent-red);   }}
.badge-flat {{ color: var(--text-secondary); }}

.vol-bar-bg {{
    width: 100%; height: 6px; background: var(--border); border-radius: 3px;
    margin-top: .3rem; overflow: hidden;
}}
.vol-bar-fill {{ height: 100%; border-radius: 3px; transition: width .3s; }}

/* Legend */
.legend {{
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: 12px; padding: 1rem 1.1rem; margin-bottom: .8rem;
    font-size: .78rem; line-height: 1.65; color: var(--text-secondary);
}}
.legend h3 {{
    font-size: .82rem; color: var(--accent-cyan); margin: .8rem 0 .3rem;
    font-weight: 600;
}}
.legend h3:first-child {{ margin-top: 0; }}
.legend b {{ color: var(--text-primary); }}
.legend .signal-buy {{ color: var(--accent-green); font-weight: 600; }}
.legend .signal-warn {{ color: var(--accent-amber); font-weight: 600; }}
.legend .signal-sell {{ color: var(--accent-red); font-weight: 600; }}
.legend code {{
    background: var(--bg-card-alt); padding: .1rem .35rem; border-radius: 4px;
    font-family: var(--font-mono); font-size: .72rem; color: var(--accent-cyan);
}}

input[type="text"], .stTextInput input {{
    background: var(--bg-card-alt) !important; color: var(--text-primary) !important;
    border: 1px solid var(--border) !important; border-radius: 8px !important;
    font-family: var(--font-mono) !important;
}}
.stTextInput input:focus {{
    border-color: var(--accent-cyan) !important;
    box-shadow: 0 0 8px rgba(0,212,255,.15) !important;
}}
.stButton > button {{
    background: linear-gradient(135deg, #00d4ff 0%, #00ff88 100%) !important;
    color: #080c10 !important; font-weight: 700 !important;
    border: none !important; border-radius: 8px !important;
    width: 100% !important; padding: .6rem !important;
    font-family: var(--font-sans) !important;
    transition: opacity .2s;
}}
.stButton > button:hover {{ opacity: .88 !important; }}
.stCheckbox label span {{ color: var(--text-secondary) !important; }}

.app-header {{ text-align: center; padding: .6rem 0 .4rem; }}
.app-header h1 {{
    font-family: var(--font-mono); font-size: 1.5rem; font-weight: 700;
    background: linear-gradient(90deg, var(--accent-cyan), var(--accent-green));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin: 0;
}}
.app-header p {{
    color: var(--text-secondary); font-size: .72rem; margin: .15rem 0 0;
}}

::-webkit-scrollbar {{ width: 4px; }}
::-webkit-scrollbar-track {{ background: var(--bg-primary); }}
::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 4px; }}
#MainMenu, footer, [data-testid="stToolbar"] {{ display: none !important; }}

/* Streamlit expander override */
[data-testid="stExpander"] {{
    background: transparent !important;
    border: none !important;
}}
[data-testid="stExpander"] details {{
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
}}
[data-testid="stExpander"] summary {{
    color: var(--text-secondary) !important;
    font-size: .8rem !important;
}}
</style>
""", unsafe_allow_html=True)


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def safe_fetch(url, retries=3, timeout=12):
    for attempt in range(retries):
        try:
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "application/json, text/html, */*",
                "Accept-Language": "en-US,en;q=0.9",
            }
            resp = requests.get(url, headers=headers, timeout=timeout)
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
        if time.time() - obj["ts"] > max_age:
            return None
        return obj["data"]
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
    if v >= 1e9:
        return f"{prefix}{val / 1e9:,.{decimals}f}B"
    if v >= 1e6:
        return f"{prefix}{val / 1e6:,.{decimals}f}M"
    if v >= 1e3:
        return f"{prefix}{val / 1e3:,.{decimals}f}K"
    return f"{prefix}{val:,.{decimals}f}"


def pct_badge(val):
    if val is None:
        return '<span class="badge-flat">\u2014</span>'
    cls = "badge-up" if val > 0 else ("badge-down" if val < 0 else "badge-flat")
    sign = "+" if val > 0 else ""
    return f'<span class="{cls}">{sign}{val:.2f}%</span>'


def vol_ratio_bar(ratio):
    if ratio is None:
        return ""
    pct = min(ratio * 100, 200)
    if ratio >= 1.5:
        color = "var(--accent-green)"
        label = "Alto"
    elif ratio >= 0.8:
        color = "var(--accent-amber)"
        label = "Nella media"
    else:
        color = "var(--accent-red)"
        label = "Basso"
    return (
        f'<div style="display:flex;justify-content:space-between;font-size:.65rem;'
        f'color:var(--text-secondary);margin-top:.15rem;">'
        f'<span>{label}</span><span>{ratio:.1f}x media 3M</span></div>'
        f'<div class="vol-bar-bg"><div class="vol-bar-fill" '
        f'style="width:{pct:.0f}%;background:{color};"></div></div>'
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
        if ticker:
            return ticker, f"ISIN {text} \u2192 {ticker}"
        return None, f"ISIN {text} non trovato."
    if "." in text:
        return text, None
    return text, None


# ─── YAHOO API ────────────────────────────────────────────────────────────────

def yahoo_chart(ticker, interval="1d", range_="1mo", prepost=False):
    params = {"interval": interval, "range": range_,
              "includePrePost": "true" if prepost else "false"}
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    resp = safe_fetch(f"{YAHOO_CHART.format(ticker=ticker)}?{qs}")
    if resp is None:
        return None
    try:
        result = resp.json().get("chart", {}).get("result")
        return result[0] if result else None
    except Exception:
        return None


# ─── FETCH REAL-TIME ──────────────────────────────────────────────────────────

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
        total_vol = sum(v for v in volumes if v is not None)

        reg_start = meta.get("currentTradingPeriod", {}).get("regular", {}).get("start", 0)
        reg_end = meta.get("currentTradingPeriod", {}).get("regular", {}).get("end", 0)
        ext_vol = sum(volumes[i] for i, ts in enumerate(timestamps)
                      if i < len(volumes) and volumes[i] and (ts < reg_start or ts >= reg_end))

        valid_h = [h for h in highs if h is not None]
        valid_l = [lo for lo in lows if lo is not None]

        return {
            "price": round(last_price, 4),
            "prev_close": round(prev_close, 4) if prev_close else None,
            "change_pct": round(change_pct, 2) if change_pct is not None else None,
            "ext_volume": ext_vol,
            "total_volume": total_vol,
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
            "today_vol": today_vol,
            "avg_vol_3m": round(avg),
            "max_vol_3m": max(hist),
            "min_vol_3m": min(hist),
            "ratio": round(today_vol / avg, 2) if avg > 0 else None,
            "trading_days": len(hist),
        }
    except Exception:
        return None


# ─── FETCH ATR ────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def fetch_atr_data(ticker):
    cache_name = f"atr_{ticker}"
    cached = load_disk(cache_name, max_age=3600)
    if cached:
        return cached
    try:
        dc = yahoo_chart(ticker, interval="1d", range_="3mo")
        if dc is None:
            return None

        ts_list = dc.get("timestamp", [])
        q = dc.get("indicators", {}).get("quote", [{}])[0]
        opens, highs, lows, closes = q.get("open", []), q.get("high", []), q.get("low", []), q.get("close", [])

        if len(ts_list) < 15:
            return None

        rows = []
        for i in range(len(ts_list)):
            o = opens[i] if i < len(opens) else None
            h = highs[i] if i < len(highs) else None
            lo = lows[i] if i < len(lows) else None
            c = closes[i] if i < len(closes) else None
            if None in (o, h, lo, c):
                continue
            rows.append({"date": datetime.utcfromtimestamp(ts_list[i]).strftime("%Y-%m-%d"),
                         "open": round(o, 4), "high": round(h, 4),
                         "low": round(lo, 4), "close": round(c, 4)})

        if len(rows) < 15:
            return None

        for i, r in enumerate(rows):
            if i == 0:
                r["tr"] = round(r["high"] - r["low"], 4)
            else:
                pc = rows[i - 1]["close"]
                r["tr"] = round(max(r["high"] - r["low"], abs(r["high"] - pc), abs(r["low"] - pc)), 4)

        atr_p = 14
        for i, r in enumerate(rows):
            if i < atr_p - 1:
                r["atr"] = None
            elif i == atr_p - 1:
                r["atr"] = round(sum(rows[j]["tr"] for j in range(atr_p)) / atr_p, 4)
            else:
                r["atr"] = round((rows[i - 1]["atr"] * (atr_p - 1) + r["tr"]) / atr_p, 4)

        for i, r in enumerate(rows):
            r["pct_change"] = 0.0 if i == 0 else round((r["close"] - rows[i-1]["close"]) / rows[i-1]["close"] * 100, 2)

        # Intraday 30-min
        ic = yahoo_chart(ticker, interval="30m", range_="5d")
        intraday, last_td = [], None
        if ic:
            its = ic.get("timestamp", [])
            iq = ic.get("indicators", {}).get("quote", [{}])[0]
            if its:
                dates_seen = sorted(set(datetime.utcfromtimestamp(t).strftime("%Y-%m-%d") for t in its))
                last_td = dates_seen[-1] if dates_seen else None
                if last_td:
                    ih, il, iv = iq.get("high", []), iq.get("low", []), iq.get("volume", [])
                    for i, t in enumerate(its):
                        d = datetime.utcfromtimestamp(t)
                        if d.strftime("%Y-%m-%d") != last_td:
                            continue
                        hv = ih[i] if i < len(ih) and ih[i] is not None else None
                        lv = il[i] if i < len(il) and il[i] is not None else None
                        vv = iv[i] if i < len(iv) and iv[i] is not None else 0
                        if hv is None or lv is None:
                            continue
                        mid = (hv + lv) / 2
                        intraday.append({"time": d.strftime("%H:%M"), "high": round(hv, 4),
                                         "low": round(lv, 4), "range": round(hv - lv, 4),
                                         "mid": round(mid, 4), "volume": int(vv)})
                    for idx, bar in enumerate(intraday):
                        if idx == 0:
                            bar["pct_change"] = None
                        else:
                            pm = intraday[idx - 1]["mid"]
                            bar["pct_change"] = round((bar["mid"] - pm) / pm * 100, 2) if pm else None

        rows = rows[-25:]
        ca = rows[-1].get("atr")
        lc = rows[-1]["close"]
        result = {"daily": rows, "intraday_30min": intraday, "current_atr": ca,
                  "atr_pct": round(ca / lc * 100, 2) if ca and lc else None,
                  "last_close": lc, "last_trading_day": last_td}
        save_disk(cache_name, result)
        return result
    except Exception:
        return None


# ─── LEGEND ───────────────────────────────────────────────────────────────────
LEGEND_HTML = """
<div class="legend">

<h3>\U0001f4b0 Prezzo e Variazione</h3>
<b>Prezzo Attuale</b> \u2014 Ultimo prezzo scambiato (incluso pre/after market).<br>
<b>Var%</b> \u2014 Scostamento % dal prezzo di chiusura del giorno prima.<br>
\u2022 <span class="signal-buy">Verde (+)</span> = il titolo sta salendo.<br>
\u2022 <span class="signal-sell">Rosso (-)</span> = il titolo sta scendendo.

<h3>\U0001f4ca Volume</h3>
<b>Volume Oggi</b> \u2014 Numero totale di azioni scambiate nella giornata.<br>
<b>Vol. Esteso</b> \u2014 Azioni scambiate fuori orario (pre-market + after-hours).<br>
<b>Rapporto Oggi/Media 3M</b> \u2014 Confronta il volume odierno con la media degli ultimi 3 mesi.<br>
\u2022 <span class="signal-buy">&gt; 1.5x</span> = volume anomalo alto \u2192 forte interesse, possibile catalizzatore.<br>
\u2022 <span class="signal-warn">0.8x \u2013 1.5x</span> = nella norma.<br>
\u2022 <span class="signal-sell">&lt; 0.8x</span> = volume basso \u2192 scarso interesse, movimento meno affidabile.

<h3>\U0001f4d0 ATR-14 (Average True Range)</h3>
Misura la <b>volatilit\u00e0 media</b> degli ultimi 14 giorni. Non indica direzione, ma <b>quanto si muove</b> il titolo.<br>
<b>ATR%</b> = ATR / Prezzo \u00d7 100. Pi\u00f9 \u00e8 alto, pi\u00f9 il titolo \u00e8 volatile.<br>
\u2022 <code>ATR% &lt; 2%</code> = bassa volatilit\u00e0 \u2192 movimenti contenuti.<br>
\u2022 <code>ATR% 2-5%</code> = volatilit\u00e0 moderata \u2192 buona per swing trading.<br>
\u2022 <code>ATR% &gt; 5%</code> = alta volatilit\u00e0 \u2192 rischio elevato, possibili grandi gain o perdite.

<h3>\u23f1 Tabella Intraday 30min</h3>
Ogni riga = una candela di 30 minuti dell\u2019ultima seduta.<br>
<b>Min/Max</b> = range della candela. <b>Var%</b> = scostamento dal prezzo medio della candela precedente.<br>
\u2022 Candele con <b>Range alto + Volume alto</b> = momento di forte attivit\u00e0.

<h3>\U0001f4c5 Storico Mensile</h3>
Ultimi ~22 giorni di borsa con Min, Max, ATR e variazione giornaliera.<br>
Utile per capire se la volatilit\u00e0 sta <b>aumentando</b> (trend in formazione) o <b>diminuendo</b> (consolidamento).

<h3>\u2705 Segnali Favorevoli all\u2019Acquisto</h3>
\u2022 Volume odierno <span class="signal-buy">&gt; 1.5x</span> la media + prezzo in salita = conferma di forza.<br>
\u2022 ATR in aumento + prezzo sopra la chiusura precedente = trend emergente.<br>
\u2022 Volume esteso alto in pre-market = anticipazione di un movimento importante.

<h3>\u26a0\ufe0f Segnali di Cautela</h3>
\u2022 Prezzo in salita ma volume <span class="signal-sell">&lt; 0.8x</span> = movimento debole, potrebbe rientrare.<br>
\u2022 ATR% molto alto (<code>&gt;8%</code>) = rischio elevato di inversioni improvvise.<br>
\u2022 Spread giornaliero molto ampio con volume basso = scarsa liquidit\u00e0.

</div>
"""

# ─── HEADER ───────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="app-header">'
    '<h1>\U0001f4ca V + ATR</h1>'
    '<p>Real-Time Volume &amp; Volatility \u00b7 Nasdaq &amp; Borsa Italiana</p>'
    '</div>', unsafe_allow_html=True)

# ─── INPUT ────────────────────────────────────────────────────────────────────
c1, c2 = st.columns([3, 1.2])
with c1:
    ticker_input = st.text_input("Ticker / ISIN", value="",
                                  placeholder="AAPL, ENI.MI, IT0003132476...",
                                  label_visibility="collapsed")
with c2:
    st.markdown("<div style='height:1px'></div>", unsafe_allow_html=True)
    run = st.button("Genera \u25b6", use_container_width=True)

show_atr = st.toggle("\U0001f52c Modulo ATR (Volatilit\u00e0)", value=False)

# Legend toggle
with st.expander("\U0001f4d6 Guida ai Dati \u2014 Come leggere i risultati"):
    st.markdown(LEGEND_HTML, unsafe_allow_html=True)

# ─── MAIN ─────────────────────────────────────────────────────────────────────
if run and ticker_input.strip():
    raw_input = ticker_input.strip().upper()

    with st.spinner("Risoluzione ticker..."):
        ticker, resolve_msg = resolve_input(raw_input)

    if ticker is None:
        st.markdown(
            '<div class="card" style="border-color:var(--accent-red);">'
            '<div class="card-title">\u26a0\ufe0f ERRORE</div>'
            f'<div class="card-sub">{resolve_msg}</div></div>', unsafe_allow_html=True)
        st.stop()

    if resolve_msg:
        st.markdown(
            f'<div class="card"><div class="card-title">\U0001f50d Risoluzione</div>'
            f'<div class="card-sub" style="font-family:var(--font-mono);color:var(--accent-cyan);">'
            f'{resolve_msg}</div></div>', unsafe_allow_html=True)

    cur = cur_sym(ticker)
    mkt = "Borsa Italiana" if is_italian(ticker) else "Nasdaq / NYSE"

    with st.spinner("Recupero dati..."):
        rt = fetch_realtime(ticker)

    if rt is None and "." not in ticker:
        ticker_mi = ticker + ".MI"
        rt = fetch_realtime(ticker_mi)
        if rt is not None:
            ticker, cur, mkt = ticker_mi, "\u20ac", "Borsa Italiana"

    if rt is None:
        st.markdown(
            '<div class="card" style="border-color:var(--accent-red);">'
            '<div class="card-title">\u26a0\ufe0f ERRORE</div>'
            f'<div class="card-sub">Impossibile recuperare dati per <b>{raw_input}</b>.<br>'
            f'Prova con .MI (es. ENI.MI) o il codice ISIN.</div></div>', unsafe_allow_html=True)
        st.stop()

    # Name
    st.markdown(
        f'<div class="card"><div class="card-title">\U0001f3e2 {mkt}</div>'
        f'<div class="card-value">{rt["name"]}</div>'
        f'<div class="card-sub" style="font-family:var(--font-mono);color:var(--accent-cyan);">'
        f'{ticker}</div></div>', unsafe_allow_html=True)

    # Price
    pc_str = f'{cur}{rt["prev_close"]:,.2f}' if rt["prev_close"] else "\u2014"
    st.markdown(
        f'<div class="card"><div class="card-title">\U0001f4b0 Prezzo Attuale</div>'
        f'<div class="card-value">{cur}{rt["price"]:,.2f} &nbsp;{pct_badge(rt["change_pct"])}</div>'
        f'<div class="card-sub">Chiusura precedente: {pc_str}</div></div>', unsafe_allow_html=True)

    # Volume + 3M stats
    with st.spinner("Analisi volumi..."):
        vs = fetch_volume_stats(ticker)

    st.markdown(
        f'<div class="metric-row">'
        f'<div class="metric-box"><div class="metric-label">Volume Oggi</div>'
        f'<div class="metric-val">{fmt_num(rt["total_volume"], 1)}</div></div>'
        f'<div class="metric-box"><div class="metric-label">Vol. Esteso</div>'
        f'<div class="metric-val">{fmt_num(rt["ext_volume"], 1)}</div></div>'
        f'</div>', unsafe_allow_html=True)

    if vs:
        rc = "var(--accent-green)" if vs["ratio"] and vs["ratio"] >= 1 else "var(--accent-red)"
        st.markdown(
            f'<div class="card">'
            f'<div class="card-title">\U0001f4ca Volume vs Media Trimestrale ({vs["trading_days"]} sedute)</div>'
            f'<div class="metric-row" style="margin-bottom:.4rem">'
            f'<div class="metric-box"><div class="metric-label">Media 3M</div>'
            f'<div class="metric-val">{fmt_num(vs["avg_vol_3m"], 1)}</div></div>'
            f'<div class="metric-box"><div class="metric-label">Max 3M</div>'
            f'<div class="metric-val">{fmt_num(vs["max_vol_3m"], 1)}</div></div>'
            f'<div class="metric-box"><div class="metric-label">Min 3M</div>'
            f'<div class="metric-val">{fmt_num(vs["min_vol_3m"], 1)}</div></div></div>'
            f'<div class="metric-row" style="margin-bottom:.2rem">'
            f'<div class="metric-box" style="flex:1"><div class="metric-label">Rapporto Oggi / Media</div>'
            f'<div class="metric-val" style="font-size:1.3rem;color:{rc}">{vs["ratio"]}x</div>'
            f'{vol_ratio_bar(vs["ratio"])}</div></div></div>', unsafe_allow_html=True)

    # Day range
    if rt["day_high"] and rt["day_low"]:
        sp = rt["day_high"] - rt["day_low"]
        st.markdown(
            f'<div class="metric-row">'
            f'<div class="metric-box"><div class="metric-label">Min Giorno</div>'
            f'<div class="metric-val" style="color:var(--accent-red)">{cur}{rt["day_low"]:,.2f}</div></div>'
            f'<div class="metric-box"><div class="metric-label">Max Giorno</div>'
            f'<div class="metric-val" style="color:var(--accent-green)">{cur}{rt["day_high"]:,.2f}</div></div>'
            f'<div class="metric-box"><div class="metric-label">Spread</div>'
            f'<div class="metric-val">{cur}{sp:,.2f}</div></div></div>', unsafe_allow_html=True)

    # ── ATR ────────────────────────────────────────────────────────────────
    if show_atr:
        with st.spinner("Calcolo ATR..."):
            atr = fetch_atr_data(ticker)
        if atr is None:
            st.markdown(
                '<div class="card" style="border-color:var(--accent-amber);">'
                '<div class="card-title">\u26a0\ufe0f ATR NON DISPONIBILE</div>'
                '<div class="card-sub">Dati storici insufficienti.</div></div>',
                unsafe_allow_html=True)
        else:
            st.markdown(
                f'<div class="card"><div class="card-title">\U0001f4d0 ATR-14</div>'
                f'<div class="card-value">{cur}{atr["current_atr"]:,.4f}</div>'
                f'<div class="card-sub">{atr["atr_pct"]}% della chiusura ({cur}{atr["last_close"]:,.2f})'
                f' &middot; Estensione media movimento</div></div>', unsafe_allow_html=True)

            if atr["intraday_30min"]:
                html = (
                    f'<div class="card">'
                    f'<div class="card-title">\u23f1 Intraday 30min \u00b7 {atr["last_trading_day"] or ""}</div>'
                    f'<table class="atr-table"><thead><tr>'
                    f'<th>Ora</th><th>Min</th><th>Max</th><th>Range</th><th>Var%</th><th>Vol</th>'
                    f'</tr></thead><tbody>')
                for s in atr["intraday_30min"]:
                    html += (
                        f'<tr><td>{s["time"]}</td>'
                        f'<td style="color:var(--accent-red)">{cur}{s["low"]:,.2f}</td>'
                        f'<td style="color:var(--accent-green)">{cur}{s["high"]:,.2f}</td>'
                        f'<td>{cur}{s["range"]:,.2f}</td>'
                        f'<td>{pct_badge(s.get("pct_change"))}</td>'
                        f'<td>{fmt_num(s["volume"], 0)}</td></tr>')
                html += '</tbody></table></div>'
                st.markdown(html, unsafe_allow_html=True)

            if atr["daily"]:
                dl = [d for d in atr["daily"] if d.get("atr") is not None][-22:]
                html = (
                    '<div class="card">'
                    '<div class="card-title">\U0001f4c5 Storico Mese</div>'
                    '<table class="atr-table"><thead><tr>'
                    '<th>Data</th><th>Min</th><th>Max</th><th>ATR</th><th>Var%</th>'
                    '</tr></thead><tbody>')
                for d in reversed(dl):
                    html += (
                        f'<tr><td style="font-size:.7rem">{d["date"]}</td>'
                        f'<td style="color:var(--accent-red)">{cur}{d["low"]:,.2f}</td>'
                        f'<td style="color:var(--accent-green)">{cur}{d["high"]:,.2f}</td>'
                        f'<td style="color:var(--accent-amber)">{cur}{d["atr"]:,.2f}</td>'
                        f'<td>{pct_badge(d["pct_change"])}</td></tr>')
                html += '</tbody></table></div>'
                st.markdown(html, unsafe_allow_html=True)

    now_str = datetime.now().strftime("%H:%M:%S \u00b7 %d/%m/%Y")
    st.markdown(
        f'<div style="text-align:center;margin-top:.8rem;">'
        f'<span style="font-size:.65rem;color:var(--text-secondary);font-family:var(--font-mono);">'
        f'Aggiornamento: {now_str} \u00b7 Cache 60s</span></div>', unsafe_allow_html=True)

elif not ticker_input.strip() and run:
    st.markdown(
        '<div class="card" style="border-color:var(--accent-amber);">'
        '<div class="card-title">\u26a0\ufe0f INSERISCI UN TICKER O ISIN</div>'
        '<div class="card-sub">Digita un simbolo (AAPL, ENI.MI) o ISIN (IT0003132476).</div>'
        '</div>', unsafe_allow_html=True)
