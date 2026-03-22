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

# ─── CSS + ICON INJECTION ─────────────────────────────────────────────────────
st.markdown(f"""
<script>
(function() {{
    const iconUrl = "data:image/png;base64,{ICON_B64}";
    function setIcons() {{
        // Remove all existing favicons
        document.querySelectorAll('link[rel="icon"], link[rel="shortcut icon"], link[rel="apple-touch-icon"]')
            .forEach(el => el.remove());
        // Add our favicon
        const fav = document.createElement('link');
        fav.rel = 'icon'; fav.type = 'image/png'; fav.href = iconUrl;
        document.head.appendChild(fav);
        // Add apple-touch-icon (for iOS "Add to Home Screen")
        const apple = document.createElement('link');
        apple.rel = 'apple-touch-icon'; apple.href = iconUrl;
        document.head.appendChild(apple);
        // PWA meta
        const meta = (name, content) => {{
            let m = document.querySelector(`meta[name="${{name}}"]`);
            if (!m) {{ m = document.createElement('meta'); m.name = name; document.head.appendChild(m); }}
            m.content = content;
        }};
        meta('apple-mobile-web-app-capable', 'yes');
        meta('apple-mobile-web-app-status-bar-style', 'black-translucent');
        meta('apple-mobile-web-app-title', 'V+ATR');
        meta('mobile-web-app-capable', 'yes');
        meta('theme-color', '#080c10');
        // Title
        document.title = 'V + ATR';
    }}
    // Run immediately + on mutations (Streamlit re-renders)
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
