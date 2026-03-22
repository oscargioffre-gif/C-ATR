"""
V + ATR - Real-Time Volume & ATR Volatility Monitor
Streamlit Cloud · Mobile-first (540px) · Nasdaq + Borsa Italiana
ZERO heavy deps: only streamlit + requests. Pure Python math.
"""

import streamlit as st
import json
import time
import hashlib
import random
from datetime import datetime
from pathlib import Path
import requests

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="V + ATR",
    page_icon="\U0001f4ca",
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
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1",
]

YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
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
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1rem 1.1rem;
    margin-bottom: 0.8rem;
    position: relative;
    overflow: hidden;
    transition: border-color .25s, box-shadow .25s;
}
.card:hover {
    border-color: var(--accent-cyan);
    box-shadow: 0 0 20px rgba(0,212,255,.08);
}
.card::before {
    content: '';
    position: absolute; top: 0; left: 0; width: 3px; height: 100%;
    background: linear-gradient(180deg, var(--accent-cyan), var(--accent-green));
    animation: gradient-slide 3s ease infinite alternate;
}
@keyframes gradient-slide {
    0%   { background: linear-gradient(180deg, var(--accent-cyan), var(--accent-green)); }
    50%  { background: linear-gradient(180deg, var(--accent-green), var(--accent-amber)); }
    100% { background: linear-gradient(180deg, var(--accent-amber), var(--accent-cyan)); }
}

.card-title {
    font-size: .7rem; font-weight: 600; letter-spacing: .08em;
    text-transform: uppercase; color: var(--text-secondary);
    margin-bottom: .55rem;
}
.card-value {
    font-family: var(--font-mono); font-size: 1.45rem;
    font-weight: 600; color: var(--text-primary); line-height: 1.15;
}
.card-sub {
    font-size: .78rem; color: var(--text-secondary); margin-top: .25rem;
}

.metric-row { display: flex; gap: .6rem; margin-bottom: .8rem; }
.metric-box {
    flex: 1; background: var(--bg-card-alt); border: 1px solid var(--border);
    border-radius: 10px; padding: .7rem .8rem; text-align: center;
}
.metric-label {
    font-size: .62rem; font-weight: 600; letter-spacing: .07em;
    text-transform: uppercase; color: var(--text-secondary); margin-bottom: .3rem;
}
.metric-val {
    font-family: var(--font-mono); font-size: 1.05rem;
    font-weight: 600; color: var(--text-primary);
}

.atr-table {
    width: 100%; border-collapse: separate; border-spacing: 0;
    font-size: .78rem; margin-top: .5rem;
}
.atr-table th {
    background: var(--bg-card-alt); color: var(--text-secondary);
    font-weight: 600; text-transform: uppercase; font-size: .62rem;
    letter-spacing: .06em; padding: .55rem .5rem; text-align: center;
    border-bottom: 1px solid var(--border);
}
.atr-table td {
    padding: .5rem; text-align: center; border-bottom: 1px solid var(--border);
    font-family: var(--font-mono); color: var(--text-primary);
}
.atr-table tr:last-child td { border-bottom: none; }
.atr-table tr:hover td { background: rgba(0,212,255,.04); }

.badge-up   { color: var(--accent-green); }
.badge-down { color: var(--accent-red);   }
.badge-flat { color: var(--text-secondary); }

input[type="text"], .stTextInput input {
    background: var(--bg-card-alt) !important; color: var(--text-primary) !important;
    border: 1px solid var(--border) !important; border-radius: 8px !important;
    font-family: var(--font-mono) !important;
}
.stTextInput input:focus {
    border-color: var(--accent-cyan) !important;
    box-shadow: 0 0 8px rgba(0,212,255,.15) !important;
}
.stButton > button {
    background: linear-gradient(135deg, #00d4ff 0%, #00ff88 100%) !important;
    color: #080c10 !important; font-weight: 700 !important;
    border: none !important; border-radius: 8px !important;
    width: 100% !important; padding: .6rem !important;
    font-family: var(--font-sans) !important;
    transition: opacity .2s;
}
.stButton > button:hover { opacity: .88 !important; }
.stCheckbox label span { color: var(--text-secondary) !important; }

.app-header { text-align: center; padding: .6rem 0 .4rem; }
.app-header h1 {
    font-family: var(--font-mono); font-size: 1.5rem; font-weight: 700;
    background: linear-gradient(90deg, var(--accent-cyan), var(--accent-green));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin: 0;
}
.app-header p {
    color: var(--text-secondary); font-size: .72rem; margin: .15rem 0 0;
}

::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: var(--bg-primary); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
#MainMenu, footer, [data-testid="stToolbar"] { display: none !important; }
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
    h = hashlib.md5(name.encode()).hexdigest()[:12]
    return CACHE_DIR / f"{h}.json"


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


# ─── YAHOO FINANCE API (pure requests) ───────────────────────────────────────

def yahoo_chart(ticker, interval="1d", range_="1mo", prepost=False):
    params = {
        "interval": interval,
        "range": range_,
        "includePrePost": "true" if prepost else "false",
    }
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{YAHOO_CHART.format(ticker=ticker)}?{qs}"
    resp = safe_fetch(url)
    if resp is None:
        return None
    try:
        data = resp.json()
        result = data.get("chart", {}).get("result")
        if not result:
            return None
        return result[0]
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
        ext_vol = 0
        for i, ts in enumerate(timestamps):
            if i < len(volumes) and volumes[i] is not None:
                if ts < reg_start or ts >= reg_end:
                    ext_vol += volumes[i]

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
        opens = q.get("open", [])
        highs = q.get("high", [])
        lows = q.get("low", [])
        closes = q.get("close", [])

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
            rows.append({
                "date": datetime.utcfromtimestamp(ts_list[i]).strftime("%Y-%m-%d"),
                "open": round(o, 4),
                "high": round(h, 4),
                "low": round(lo, 4),
                "close": round(c, 4),
            })

        if len(rows) < 15:
            return None

        # True Range
        for i, r in enumerate(rows):
            if i == 0:
                r["tr"] = round(r["high"] - r["low"], 4)
            else:
                pc = rows[i - 1]["close"]
                r["tr"] = round(max(r["high"] - r["low"], abs(r["high"] - pc), abs(r["low"] - pc)), 4)

        # ATR-14 Wilder
        atr_p = 14
        for i, r in enumerate(rows):
            if i < atr_p - 1:
                r["atr"] = None
            elif i == atr_p - 1:
                r["atr"] = round(sum(rows[j]["tr"] for j in range(atr_p)) / atr_p, 4)
            else:
                r["atr"] = round((rows[i - 1]["atr"] * (atr_p - 1) + r["tr"]) / atr_p, 4)

        # Pct change
        for i, r in enumerate(rows):
            if i == 0:
                r["pct_change"] = 0.0
            else:
                pc = rows[i - 1]["close"]
                r["pct_change"] = round((r["close"] - pc) / pc * 100, 2) if pc else 0.0

        # Intraday 30-min
        ic = yahoo_chart(ticker, interval="30m", range_="5d")
        intraday = []
        last_td = None
        if ic:
            its = ic.get("timestamp", [])
            iq = ic.get("indicators", {}).get("quote", [{}])[0]
            if its:
                dates_seen = sorted(set(datetime.utcfromtimestamp(t).strftime("%Y-%m-%d") for t in its))
                last_td = dates_seen[-1] if dates_seen else None
                if last_td:
                    ih = iq.get("high", [])
                    il = iq.get("low", [])
                    iv = iq.get("volume", [])
                    for i, t in enumerate(its):
                        d = datetime.utcfromtimestamp(t)
                        if d.strftime("%Y-%m-%d") != last_td:
                            continue
                        hv = ih[i] if i < len(ih) and ih[i] is not None else None
                        lv = il[i] if i < len(il) and il[i] is not None else None
                        vv = iv[i] if i < len(iv) and iv[i] is not None else 0
                        if hv is None or lv is None:
                            continue
                        intraday.append({
                            "time": d.strftime("%H:%M"),
                            "high": round(hv, 4),
                            "low": round(lv, 4),
                            "range": round(hv - lv, 4),
                            "volume": int(vv),
                        })

        rows = rows[-25:]
        ca = rows[-1].get("atr")
        lc = rows[-1]["close"]
        ap = round(ca / lc * 100, 2) if ca and lc else None

        result = {
            "daily": rows,
            "intraday_30min": intraday,
            "current_atr": ca,
            "atr_pct": ap,
            "last_close": lc,
            "last_trading_day": last_td,
        }
        save_disk(cache_name, result)
        return result
    except Exception:
        return None


# ─── HEADER ───────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="app-header">'
    '<h1>\U0001f4ca V + ATR</h1>'
    '<p>Real-Time Volume &amp; Volatility Monitor \u00b7 Nasdaq &amp; Milano</p>'
    '</div>', unsafe_allow_html=True)

# ─── INPUT ────────────────────────────────────────────────────────────────────
c1, c2 = st.columns([3, 1.2])
with c1:
    ticker_input = st.text_input("Ticker", value="", placeholder="es. AAPL, TSLA, ENI.MI",
                                  label_visibility="collapsed")
with c2:
    st.markdown("<div style='height:1px'></div>", unsafe_allow_html=True)
    run = st.button("Genera \u25b6", use_container_width=True)

show_atr = st.toggle("\U0001f52c Modulo ATR (Volatilit\u00e0)", value=False)

# ─── MAIN ─────────────────────────────────────────────────────────────────────
if run and ticker_input.strip():
    ticker = ticker_input.strip().upper()
    cur = cur_sym(ticker)
    mkt = "Borsa Italiana" if is_italian(ticker) else "Nasdaq / NYSE"

    with st.spinner("Recupero dati in tempo reale..."):
        rt = fetch_realtime(ticker)

    if rt is None:
        st.markdown(
            '<div class="card" style="border-color:var(--accent-red);">'
            '<div class="card-title">\u26a0\ufe0f ERRORE</div>'
            f'<div class="card-sub">Impossibile recuperare dati per <b>{ticker}</b>. Verifica il ticker.</div>'
            '</div>', unsafe_allow_html=True)
    else:
        # Name card
        st.markdown(
            f'<div class="card">'
            f'<div class="card-title">\U0001f3e2 {mkt}</div>'
            f'<div class="card-value">{rt["name"]}</div>'
            f'<div class="card-sub" style="font-family:var(--font-mono);color:var(--accent-cyan);">{ticker}</div>'
            f'</div>', unsafe_allow_html=True)

        # Price
        pc_str = f'{cur}{rt["prev_close"]:,.2f}' if rt["prev_close"] else "\u2014"
        st.markdown(
            f'<div class="card">'
            f'<div class="card-title">\U0001f4b0 Prezzo Attuale</div>'
            f'<div class="card-value">{cur}{rt["price"]:,.2f} &nbsp;{pct_badge(rt["change_pct"])}</div>'
            f'<div class="card-sub">Chiusura precedente: {pc_str}</div>'
            f'</div>', unsafe_allow_html=True)

        # Volume
        st.markdown(
            f'<div class="metric-row">'
            f'<div class="metric-box"><div class="metric-label">Volume Totale</div>'
            f'<div class="metric-val">{fmt_num(rt["total_volume"], 1)}</div></div>'
            f'<div class="metric-box"><div class="metric-label">Vol. Esteso (Pre/After)</div>'
            f'<div class="metric-val">{fmt_num(rt["ext_volume"], 1)}</div></div>'
            f'</div>', unsafe_allow_html=True)

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
                f'<div class="metric-val">{cur}{sp:,.2f}</div></div>'
                f'</div>', unsafe_allow_html=True)

        # ── ATR ───────────────────────────────────────────────────────────
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
                # ATR summary
                st.markdown(
                    f'<div class="card">'
                    f'<div class="card-title">\U0001f4d0 ATR-14 (Average True Range)</div>'
                    f'<div class="card-value">{cur}{atr["current_atr"]:,.4f}</div>'
                    f'<div class="card-sub">{atr["atr_pct"]}% della chiusura ({cur}{atr["last_close"]:,.2f})'
                    f' &middot; Estensione media movimento</div>'
                    f'</div>', unsafe_allow_html=True)

                # Intraday 30-min table
                if atr["intraday_30min"]:
                    html = (
                        f'<div class="card">'
                        f'<div class="card-title">\u23f1 Volatilit\u00e0 Intraday 30min \u00b7 {atr["last_trading_day"] or ""}</div>'
                        f'<table class="atr-table"><thead><tr>'
                        f'<th>Ora</th><th>Min</th><th>Max</th><th>Range</th><th>Vol</th>'
                        f'</tr></thead><tbody>'
                    )
                    for s in atr["intraday_30min"]:
                        html += (
                            f'<tr><td>{s["time"]}</td>'
                            f'<td style="color:var(--accent-red)">{cur}{s["low"]:,.2f}</td>'
                            f'<td style="color:var(--accent-green)">{cur}{s["high"]:,.2f}</td>'
                            f'<td>{cur}{s["range"]:,.2f}</td>'
                            f'<td>{fmt_num(s["volume"], 0)}</td></tr>'
                        )
                    html += '</tbody></table></div>'
                    st.markdown(html, unsafe_allow_html=True)

                # Monthly history table
                if atr["daily"]:
                    dl = [d for d in atr["daily"] if d.get("atr") is not None][-22:]
                    html = (
                        '<div class="card">'
                        '<div class="card-title">\U0001f4c5 Storico Mese \u00b7 Min / Max / ATR</div>'
                        '<table class="atr-table"><thead><tr>'
                        '<th>Data</th><th>Min</th><th>Max</th><th>ATR</th><th>Var%</th>'
                        '</tr></thead><tbody>'
                    )
                    for d in reversed(dl):
                        html += (
                            f'<tr><td style="font-size:.7rem">{d["date"]}</td>'
                            f'<td style="color:var(--accent-red)">{cur}{d["low"]:,.2f}</td>'
                            f'<td style="color:var(--accent-green)">{cur}{d["high"]:,.2f}</td>'
                            f'<td style="color:var(--accent-amber)">{cur}{d["atr"]:,.2f}</td>'
                            f'<td>{pct_badge(d["pct_change"])}</td></tr>'
                        )
                    html += '</tbody></table></div>'
                    st.markdown(html, unsafe_allow_html=True)

    # Timestamp
    now_str = datetime.now().strftime("%H:%M:%S \u00b7 %d/%m/%Y")
    st.markdown(
        f'<div style="text-align:center;margin-top:.8rem;">'
        f'<span style="font-size:.65rem;color:var(--text-secondary);font-family:var(--font-mono);">'
        f'Aggiornamento: {now_str} \u00b7 Cache 60s</span></div>',
        unsafe_allow_html=True)

elif not ticker_input.strip() and run:
    st.markdown(
        '<div class="card" style="border-color:var(--accent-amber);">'
        '<div class="card-title">\u26a0\ufe0f INSERISCI UN TICKER</div>'
        '<div class="card-sub">Digita un simbolo (es. AAPL, TSLA, ENI.MI) e premi Genera.</div>'
        '</div>', unsafe_allow_html=True)
