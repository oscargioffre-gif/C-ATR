"""
V + ATR — Real-Time Volume & ATR Volatility Monitor
Streamlit Cloud-ready · Mobile-first (540 px) · Nasdaq + Borsa Italiana
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import json, os, time, hashlib, random, datetime as dt
from datetime import datetime, timedelta
from pathlib import Path
import requests
from io import StringIO

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="V + ATR",
    page_icon="📊",
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

# ─── CSS (OPENINSIDER STYLE) ─────────────────────────────────────────────────
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
    --accent-violet:#a78bfa;
    --font-sans:    'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    --font-mono:    'JetBrains Mono', 'Fira Code', monospace;
}

/* ── Global ── */
html, body, .stApp, [data-testid="stAppViewContainer"],
[data-testid="stApp"], section[data-testid="stMain"] {
    background: var(--bg-primary) !important;
    color: var(--text-primary) !important;
    font-family: var(--font-sans) !important;
}
header[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stSidebar"] { background: var(--bg-card) !important; }
.block-container { max-width: 540px !important; padding: 1rem 0.75rem !important; }

/* ── Cards ── */
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
    margin-bottom: .55rem; display: flex; align-items: center; gap: .4rem;
}
.card-value {
    font-family: var(--font-mono); font-size: 1.45rem;
    font-weight: 600; color: var(--text-primary); line-height: 1.15;
}
.card-sub {
    font-size: .78rem; color: var(--text-secondary); margin-top: .25rem;
}

/* ── Metric row ── */
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

/* ── Table ── */
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

/* ── Badge ── */
.badge-up   { color: var(--accent-green); }
.badge-down { color: var(--accent-red);   }
.badge-flat { color: var(--text-secondary); }

/* ── Inputs ── */
input[type="text"], .stTextInput input {
    background: var(--bg-card-alt) !important; color: var(--text-primary) !important;
    border: 1px solid var(--border) !important; border-radius: 8px !important;
    font-family: var(--font-mono) !important;
}
.stTextInput input:focus {
    border-color: var(--accent-cyan) !important;
    box-shadow: 0 0 8px rgba(0,212,255,.15) !important;
}

/* Button */
.stButton > button {
    background: linear-gradient(135deg, #00d4ff 0%, #00ff88 100%) !important;
    color: #080c10 !important; font-weight: 700 !important;
    border: none !important; border-radius: 8px !important;
    width: 100% !important; padding: .6rem !important;
    font-family: var(--font-sans) !important; letter-spacing: .03em;
    transition: opacity .2s;
}
.stButton > button:hover { opacity: .88 !important; }

/* Toggle */
.stCheckbox label span { color: var(--text-secondary) !important; font-size: .82rem !important; }

/* Header */
.app-header {
    text-align: center; padding: .6rem 0 .4rem;
}
.app-header h1 {
    font-family: var(--font-mono); font-size: 1.5rem; font-weight: 700;
    background: linear-gradient(90deg, var(--accent-cyan), var(--accent-green));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin: 0;
}
.app-header p {
    color: var(--text-secondary); font-size: .72rem; margin: .15rem 0 0;
    letter-spacing: .04em;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: var(--bg-primary); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }

/* ── Spinner override ── */
.stSpinner > div { border-top-color: var(--accent-cyan) !important; }

/* Hide Streamlit furniture */
#MainMenu, footer, [data-testid="stToolbar"] { display: none !important; }
</style>
""", unsafe_allow_html=True)


# ─── HELPER: safe_fetch with retries ─────────────────────────────────────────
def safe_fetch(url: str, retries: int = 3, timeout: int = 10) -> requests.Response | None:
    """HTTP GET with rotating User-Agent and exponential back-off."""
    for attempt in range(retries):
        try:
            headers = {"User-Agent": random.choice(USER_AGENTS),
                       "Accept": "application/json, text/html, */*",
                       "Accept-Language": "en-US,en;q=0.9"}
            resp = requests.get(url, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                return resp
        except Exception:
            pass
        time.sleep(1.2 * (attempt + 1))
    return None


# ─── DISK CACHE ───────────────────────────────────────────────────────────────
def _cache_key(name: str) -> Path:
    h = hashlib.md5(name.encode()).hexdigest()[:12]
    return CACHE_DIR / f"{h}.json"


def save_disk(name: str, data: dict | list):
    try:
        with open(_cache_key(name), "w") as f:
            json.dump({"ts": time.time(), "data": data}, f)
    except Exception:
        pass


def load_disk(name: str, max_age: int = 86400):
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


# ─── MARKET HELPERS ───────────────────────────────────────────────────────────
def is_italian(ticker: str) -> bool:
    return ticker.upper().endswith(".MI")


def currency_symbol(ticker: str) -> str:
    return "€" if is_italian(ticker) else "$"


def fmt_num(val, decimals=2, prefix=""):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "—"
    if abs(val) >= 1_000_000_000:
        return f"{prefix}{val/1e9:,.{decimals}f}B"
    if abs(val) >= 1_000_000:
        return f"{prefix}{val/1e6:,.{decimals}f}M"
    if abs(val) >= 1_000:
        return f"{prefix}{val/1e3:,.{decimals}f}K"
    return f"{prefix}{val:,.{decimals}f}"


def pct_badge(val):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return '<span class="badge-flat">—</span>'
    cls = "badge-up" if val > 0 else ("badge-down" if val < 0 else "badge-flat")
    sign = "+" if val > 0 else ""
    return f'<span class="{cls}">{sign}{val:.2f}%</span>'


# ─── DATA: Real-Time Quote (yfinance fast_info + extended hours) ──────────────
@st.cache_data(ttl=60, show_spinner=False)
def fetch_realtime(ticker: str) -> dict | None:
    """Fetch current price, extended-hours data, previous close via yfinance."""
    try:
        tk = yf.Ticker(ticker)
        info = tk.fast_info
        hist_2d = tk.history(period="5d", interval="1m", prepost=True)

        if hist_2d.empty:
            return None

        last_price = float(info.last_price) if hasattr(info, "last_price") and info.last_price else float(hist_2d["Close"].dropna().iloc[-1])
        prev_close = float(info.previous_close) if hasattr(info, "previous_close") and info.previous_close else None

        # Extended-hours volume: volume from bars outside regular session
        today = datetime.now().date()
        today_data = hist_2d[hist_2d.index.date == today] if not hist_2d.empty else pd.DataFrame()

        regular_start, regular_end = ("09:30", "16:00")
        if is_italian(ticker):
            regular_start, regular_end = ("09:00", "17:30")

        ext_vol = 0
        total_vol = 0
        if not today_data.empty:
            total_vol = int(today_data["Volume"].sum())
            regular_mask = (today_data.index.strftime("%H:%M") >= regular_start) & \
                           (today_data.index.strftime("%H:%M") < regular_end)
            reg_vol = int(today_data.loc[regular_mask, "Volume"].sum()) if regular_mask.any() else 0
            ext_vol = max(total_vol - reg_vol, 0)

        change_pct = ((last_price - prev_close) / prev_close * 100) if prev_close else None

        # Day range from today
        day_high = float(today_data["High"].max()) if not today_data.empty else None
        day_low = float(today_data["Low"].min()) if not today_data.empty else None

        return {
            "price": last_price,
            "prev_close": prev_close,
            "change_pct": change_pct,
            "ext_volume": ext_vol,
            "total_volume": total_vol,
            "day_high": day_high,
            "day_low": day_low,
            "name": tk.info.get("shortName", ticker.upper()) if tk.info else ticker.upper(),
        }
    except Exception as e:
        return None


# ─── DATA: ATR Calculations ──────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def fetch_atr_data(ticker: str, period: int = 30) -> dict | None:
    """
    Returns daily OHLC (1 month) + ATR-14 + intraday 30-min bars for yesterday.
    Uses disk cache for historical daily data.
    """
    cache_name = f"atr_{ticker}_{period}"
    cached = load_disk(cache_name, max_age=3600)
    if cached:
        return cached

    try:
        tk = yf.Ticker(ticker)

        # Daily data — last ~45 calendar days to ensure 30 trading days
        daily = tk.history(period=f"{period + 15}d", interval="1d")
        if daily.empty or len(daily) < 14:
            return None

        daily = daily.tail(period + 1)  # keep exactly what we need + 1 for TR calc

        # True Range
        highs = daily["High"].values
        lows = daily["Low"].values
        closes = daily["Close"].values

        tr_list = [highs[0] - lows[0]]
        for i in range(1, len(highs)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            tr_list.append(tr)

        daily = daily.iloc[:]  # copy
        daily["TR"] = tr_list

        # ATR-14 (Wilder smoothing)
        atr_period = 14
        atr_vals = [np.nan] * (atr_period - 1)
        first_atr = np.mean(tr_list[:atr_period])
        atr_vals.append(first_atr)
        for i in range(atr_period, len(tr_list)):
            atr_vals.append((atr_vals[-1] * (atr_period - 1) + tr_list[i]) / atr_period)
        daily["ATR"] = atr_vals

        # Build daily summary
        daily_records = []
        for idx, row in daily.iterrows():
            prev_close_val = closes[list(daily.index).index(idx) - 1] if list(daily.index).index(idx) > 0 else row["Open"]
            pct_chg = (row["Close"] - prev_close_val) / prev_close_val * 100 if prev_close_val else 0
            daily_records.append({
                "date": idx.strftime("%Y-%m-%d"),
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "tr": round(float(row["TR"]), 2),
                "atr": round(float(row["ATR"]), 2) if not np.isnan(row["ATR"]) else None,
                "pct_change": round(pct_chg, 2),
            })

        # Intraday 30-min for last trading day
        intraday_30 = tk.history(period="5d", interval="30m")
        intraday_records = []
        if not intraday_30.empty:
            last_trading_day = intraday_30.index.date[-1]
            yesterday_data = intraday_30[intraday_30.index.date == last_trading_day]
            for idx, row in yesterday_data.iterrows():
                slot_range = row["High"] - row["Low"]
                intraday_records.append({
                    "time": idx.strftime("%H:%M"),
                    "high": round(float(row["High"]), 2),
                    "low": round(float(row["Low"]), 2),
                    "range": round(float(slot_range), 2),
                    "volume": int(row["Volume"]),
                })

        current_atr = atr_vals[-1] if atr_vals and not np.isnan(atr_vals[-1]) else None
        last_close = float(closes[-1])
        atr_pct = (current_atr / last_close * 100) if current_atr and last_close else None

        result = {
            "daily": daily_records,
            "intraday_30min": intraday_records,
            "current_atr": round(current_atr, 4) if current_atr else None,
            "atr_pct": round(atr_pct, 2) if atr_pct else None,
            "last_close": round(last_close, 2),
            "last_trading_day": str(last_trading_day) if intraday_records else None,
        }

        save_disk(cache_name, result)
        return result
    except Exception:
        return None


# ─── RENDER: Header ──────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <h1>📊 V + ATR</h1>
    <p>Real-Time Volume &amp; Volatility Monitor · Nasdaq &amp; Milano</p>
</div>
""", unsafe_allow_html=True)

# ─── INPUT ────────────────────────────────────────────────────────────────────
col_input, col_btn = st.columns([3, 1.2])
with col_input:
    ticker_input = st.text_input(
        "Ticker", value="", placeholder="es. AAPL, TSLA, ENI.MI",
        label_visibility="collapsed",
    )
with col_btn:
    st.markdown("<div style='height:1px'></div>", unsafe_allow_html=True)  # vertical align
    run = st.button("Genera ▶", use_container_width=True)

show_atr = st.toggle("🔬 Modulo ATR (Volatilità)", value=False)

# ─── MAIN LOGIC ──────────────────────────────────────────────────────────────
if run and ticker_input.strip():
    ticker = ticker_input.strip().upper()
    cur = currency_symbol(ticker)
    market_label = "Borsa Italiana" if is_italian(ticker) else "Nasdaq / NYSE"

    # ── Real-Time ─────────────────────────────────────────────────────────
    with st.spinner("Recupero dati in tempo reale…"):
        rt = fetch_realtime(ticker)

    if rt is None:
        st.markdown("""
        <div class="card" style="border-color:var(--accent-red);">
            <div class="card-title">⚠️ ERRORE</div>
            <div class="card-sub">Impossibile recuperare i dati per <b>{}</b>. Verifica il ticker e riprova.</div>
        </div>
        """.format(ticker), unsafe_allow_html=True)
    else:
        # Company name
        st.markdown(f"""
        <div class="card">
            <div class="card-title">🏢 {market_label}</div>
            <div class="card-value">{rt['name']}</div>
            <div class="card-sub" style="font-family:var(--font-mono);color:var(--accent-cyan);">{ticker}</div>
        </div>
        """, unsafe_allow_html=True)

        # Price + Change
        st.markdown(f"""
        <div class="card">
            <div class="card-title">💰 Prezzo Attuale</div>
            <div class="card-value">{cur}{rt['price']:,.2f}  &nbsp;{pct_badge(rt['change_pct'])}</div>
            <div class="card-sub">Chiusura precedente: {cur}{rt['prev_close']:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

        # Volume row
        st.markdown(f"""
        <div class="metric-row">
            <div class="metric-box">
                <div class="metric-label">Volume Totale</div>
                <div class="metric-val">{fmt_num(rt['total_volume'], 1)}</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">Vol. Esteso (Pre/After)</div>
                <div class="metric-val">{fmt_num(rt['ext_volume'], 1)}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Day range
        if rt["day_high"] and rt["day_low"]:
            spread = rt["day_high"] - rt["day_low"]
            st.markdown(f"""
            <div class="metric-row">
                <div class="metric-box">
                    <div class="metric-label">Min Giorno</div>
                    <div class="metric-val" style="color:var(--accent-red)">{cur}{rt['day_low']:,.2f}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Max Giorno</div>
                    <div class="metric-val" style="color:var(--accent-green)">{cur}{rt['day_high']:,.2f}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Spread</div>
                    <div class="metric-val">{cur}{spread:,.2f}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # ── ATR MODULE ────────────────────────────────────────────────────
        if show_atr:
            with st.spinner("Calcolo ATR e volatilità…"):
                atr = fetch_atr_data(ticker)

            if atr is None:
                st.markdown("""
                <div class="card" style="border-color:var(--accent-amber);">
                    <div class="card-title">⚠️ ATR NON DISPONIBILE</div>
                    <div class="card-sub">Dati storici insufficienti per calcolare l'ATR.</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                # ATR summary
                st.markdown(f"""
                <div class="card">
                    <div class="card-title">📐 ATR-14 (Average True Range)</div>
                    <div class="card-value">{cur}{atr['current_atr']:,.4f}</div>
                    <div class="card-sub">
                        {atr['atr_pct']}% della chiusura ({cur}{atr['last_close']:,.2f})
                        &nbsp;·&nbsp; Estensione media del movimento giornaliero
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Intraday 30-min volatility
                if atr["intraday_30min"]:
                    st.markdown(f"""
                    <div class="card">
                        <div class="card-title">⏱ Volatilità Intraday 30min · {atr['last_trading_day']}</div>
                        <table class="atr-table">
                            <thead><tr>
                                <th>Ora</th><th>Min</th><th>Max</th><th>Range</th><th>Volume</th>
                            </tr></thead>
                            <tbody>
                    """, unsafe_allow_html=True)

                    rows_html = ""
                    for slot in atr["intraday_30min"]:
                        rows_html += f"""
                        <tr>
                            <td>{slot['time']}</td>
                            <td style="color:var(--accent-red)">{cur}{slot['low']:,.2f}</td>
                            <td style="color:var(--accent-green)">{cur}{slot['high']:,.2f}</td>
                            <td>{cur}{slot['range']:,.2f}</td>
                            <td>{fmt_num(slot['volume'], 0)}</td>
                        </tr>"""

                    st.markdown(rows_html + "</tbody></table></div>", unsafe_allow_html=True)

                # Daily History — Min/Max + % change
                if atr["daily"]:
                    daily_list = [d for d in atr["daily"] if d["atr"] is not None]
                    # Take last 22 trading days (roughly 1 month)
                    daily_list = daily_list[-22:]

                    st.markdown(f"""
                    <div class="card">
                        <div class="card-title">📅 Storico Ultimo Mese · Min / Max / ATR</div>
                        <table class="atr-table">
                            <thead><tr>
                                <th>Data</th><th>Min</th><th>Max</th><th>ATR</th><th>Var%</th>
                            </tr></thead>
                            <tbody>
                    """, unsafe_allow_html=True)

                    hist_rows = ""
                    for d in reversed(daily_list):
                        hist_rows += f"""
                        <tr>
                            <td style="font-size:.7rem">{d['date']}</td>
                            <td style="color:var(--accent-red)">{cur}{d['low']:,.2f}</td>
                            <td style="color:var(--accent-green)">{cur}{d['high']:,.2f}</td>
                            <td style="color:var(--accent-amber)">{cur}{d['atr']:,.2f}</td>
                            <td>{pct_badge(d['pct_change'])}</td>
                        </tr>"""

                    st.markdown(hist_rows + "</tbody></table></div>", unsafe_allow_html=True)

                    # ATR Trend mini-chart (sparkline with Streamlit)
                    atr_series = [d["atr"] for d in daily_list if d["atr"]]
                    dates = [d["date"] for d in daily_list if d["atr"]]
                    if len(atr_series) > 2:
                        chart_df = pd.DataFrame({"ATR": atr_series}, index=pd.to_datetime(dates))
                        st.markdown("""
                        <div class="card">
                            <div class="card-title">📈 Trend ATR-14</div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.line_chart(chart_df, color="#00d4ff", height=180)

    # ── Timestamp ─────────────────────────────────────────────────────────
    now_str = datetime.now().strftime("%H:%M:%S · %d/%m/%Y")
    st.markdown(f"""
    <div style="text-align:center;margin-top:.8rem;">
        <span style="font-size:.65rem;color:var(--text-secondary);font-family:var(--font-mono);">
            Ultimo aggiornamento: {now_str} · Cache TTL 60s
        </span>
    </div>
    """, unsafe_allow_html=True)

elif not ticker_input.strip() and run:
    st.markdown("""
    <div class="card" style="border-color:var(--accent-amber);">
        <div class="card-title">⚠️ INSERISCI UN TICKER</div>
        <div class="card-sub">Digita un simbolo valido (es. AAPL, TSLA, ENI.MI) e premi Genera.</div>
    </div>
    """, unsafe_allow_html=True)
