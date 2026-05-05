import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json, os, re
from datetime import datetime
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

st.set_page_config(
    page_title="Yad2 Market | Ra'anana",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@400;500;600;700;800&display=swap');
*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] {
    font-family: "Inter", "Heebo", -apple-system, BlinkMacSystemFont, "SF Pro Display", "Helvetica Neue", sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
.stApp { background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%); }
.block-container { max-width: 1700px !important; padding-top: 0.5rem !important; padding-left: 2rem !important; padding-right: 2rem !important; direction: rtl; }
[data-testid="stVerticalBlock"] { gap: 0.3rem !important; }
.element-container { margin-bottom: 0 !important; }

/* ── Top filter bar widgets ─────────────────────────────── */
[data-testid="stSlider"] label,
[data-testid="stSelectbox"] label,
.stSlider label, .stSelectbox label {
    color: #475569 !important;
    font-size: 0.68rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    padding: 0 0 2px 0 !important;
    margin: 0 !important;
    line-height: 1.2 !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] > div {
    background: #f8fafc !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    min-height: 34px !important;
    font-size: 0.82rem !important;
    color: #0f172a !important;
}
[data-testid="stSlider"] [data-baseweb="slider"] { padding-top: 4px !important; }
[data-testid="stSlider"] > div { padding-top: 0 !important; }
[data-testid="stSidebar"] { direction: rtl; }
[data-testid="stSidebar"] * { text-align: right; }

/* Keep numerics/charts LTR-friendly inside RTL container */
.kpi-value, .d-value, .stPlotlyChart, .ag-root-wrapper, .stDataFrame { direction: ltr; }
.kpi-value, .d-value { text-align: right; }

/* ── Sidebar ──────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid #e2e8f0 !important;
    box-shadow: 1px 0 3px rgba(15,23,42,0.03);
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stSlider label {
    color: #475569 !important; font-size: 0.7rem !important; font-weight: 700 !important;
    text-transform: uppercase !important; letter-spacing: 0.1em !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: #f8fafc !important; border: 1px solid #e2e8f0 !important; border-radius: 10px !important;
    color: #0f172a !important; font-size: 0.88rem !important; transition: all 0.15s;
}
[data-testid="stSidebar"] [data-baseweb="select"] > div:hover {
    border-color: #cbd5e1 !important; background: #ffffff !important;
}

.sidebar-brand { padding: 18px 0 24px; border-bottom: 1px solid #e2e8f0; margin-bottom: 22px; }
.sidebar-brand .brand-mark {
    width: 50px; height: 50px;
    background: linear-gradient(135deg, #2563eb 0%, #06b6d4 100%);
    border-radius: 14px;
    display: flex; align-items: center; justify-content: center;
    margin: 0 auto 14px; box-shadow: 0 8px 20px rgba(37,99,235,0.25), 0 2px 4px rgba(37,99,235,0.15);
}
.sidebar-brand .brand-mark svg { width: 24px; height: 24px; stroke: #fff; fill: none; stroke-width: 2.2; stroke-linecap: round; stroke-linejoin: round; }
.sidebar-brand h3 { color: #0f172a; font-size: 1rem; font-weight: 700; text-align: center; margin: 0; letter-spacing: -0.01em; }
.sidebar-brand p  { color: #475569; font-size: 0.72rem; text-align: center; margin: 4px 0 0; font-weight: 500; }

.sidebar-status {
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
    border: 1px solid #e2e8f0; border-radius: 14px;
    padding: 14px 16px; margin-top: 14px;
}
.sidebar-status .status-live { display: flex; align-items: center; gap: 8px; color: #0f172a; font-size: 0.8rem; font-weight: 600; margin-bottom: 8px; }
.sidebar-status .live-dot { width: 8px; height: 8px; border-radius: 50%; background: #10b981; box-shadow: 0 0 0 3px rgba(16,185,129,0.18); animation: blink 2s infinite; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.5} }
.sidebar-status .stat-row { color: #334155; font-size: 0.77rem; margin-top: 4px; font-weight: 500; }
.sidebar-status .delta-pills { display: flex; gap: 6px; margin-top: 12px; flex-wrap: wrap; }
.sidebar-status .dpill { padding: 4px 10px; border-radius: 999px; font-size: 0.72rem; font-weight: 600; display:inline-flex; align-items:center; gap:4px; }
.sidebar-status .dpill.green { background: #ecfdf5; color: #059669; border: 1px solid #d1fae5; }
.sidebar-status .dpill.red   { background: #fef2f2; color: #dc2626; border: 1px solid #fee2e2; }
.sidebar-status .dpill.yel   { background: #fffbeb; color: #d97706; border: 1px solid #fef3c7; }

/* ── Page header ─────────────────────────────────────── */
.page-header {
    padding: 2px 0 6px; margin-bottom: 6px;
    border-bottom: 1px solid #e2e8f0;
    text-align: right; direction: rtl;
}
.page-header .eyebrow {
    display: inline-flex; align-items: center; gap: 6px;
    color: #2563eb; font-size: 0.7rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 2px;
    background: #eff6ff; padding: 5px 11px; border-radius: 999px; border: 1px solid #dbeafe;
}
.page-header h1 {
    color: #0f172a; font-size: 1.6rem; font-weight: 800;
    letter-spacing: -0.035em; margin: 0 0 2px; line-height: 1.1;
    background: linear-gradient(135deg, #0f172a 0%, #1e40af 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}
.page-header .sub { color: #334155; font-size: 0.82rem; font-weight: 500; }
.page-header .sub b { color: #0f172a; font-weight: 700; }

/* ── KPI strip ───────────────────────────────────────── */
.kpi-strip { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 14px; }
.kpi {
    background: #ffffff; border-radius: 18px;
    padding: 16px 18px 14px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 1px 3px rgba(15,23,42,0.04);
    transition: box-shadow 0.2s, transform 0.2s, border-color 0.2s;
    display: flex; flex-direction: column;
    min-height: 148px;
}
.kpi:hover { box-shadow: 0 10px 24px rgba(15,23,42,0.07); transform: translateY(-2px); border-color: #cbd5e1; }
.kpi-head {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 10px;
}
.kpi-label {
    color: #475569; font-size: 0.86rem; font-weight: 700;
    letter-spacing: 0;
}
.kpi-icon {
    width: 34px; height: 34px; border-radius: 10px;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 1rem;
}
.kpi.blue   .kpi-icon { background: #dbeafe; }
.kpi.green  .kpi-icon { background: #d1fae5; }
.kpi.gray   .kpi-icon { background: #f1f5f9; }
.kpi.orange .kpi-icon { background: #ffedd5; }
.kpi.purple .kpi-icon { background: #ede9fe; }
.kpi-value {
    font-size: 1.7rem; font-weight: 800;
    color: #0f172a; letter-spacing: -0.025em;
    line-height: 1.1;
}
.kpi-sub {
    color: #94a3b8; font-size: 0.74rem; font-weight: 500;
    margin-top: 4px;
}
.kpi-delta {
    display: inline-flex; align-items: center; gap: 4px;
    padding: 3px 10px; border-radius: 999px;
    font-size: 0.72rem; font-weight: 700;
    margin-top: auto; width: fit-content;
    padding-top: 3px;
}
.kpi-delta.up   { background: #fef2f2; color: #dc2626; border: 1px solid #fee2e2; }
.kpi-delta.down { background: #ecfdf5; color: #059669; border: 1px solid #d1fae5; }
.kpi-delta.flat { background: #f8fafc; color: #64748b; border: 1px solid #e2e8f0; }
.kpi-spacer { margin-top: auto; }

/* ── Section labels ──────────────────────────────────── */
.section-label {
    color: #1e293b; font-size: 0.76rem; font-weight: 800;
    text-transform: uppercase; letter-spacing: 0.14em;
    margin: 12px 0 4px; display: flex; align-items: center; gap: 14px;
    direction: rtl;
}
.section-title, .section-desc { direction: rtl; text-align: right; }
.run-status, .filter-hint, .info-notice { direction: rtl; text-align: right; }
.kpi, .delta-tile, .card { direction: rtl; text-align: right; }
.section-label::before {
    content: ''; width: 4px; height: 14px; background: linear-gradient(180deg, #2563eb, #06b6d4);
    border-radius: 4px;
}
.section-label::after { content: ''; flex: 1; height: 1px; background: linear-gradient(90deg, #e2e8f0, transparent); }
.section-title { color: #0f172a; font-size: 1.15rem; font-weight: 800; letter-spacing: -0.025em; margin: 0 0 2px; }
.section-desc { color: #334155; font-size: 0.85rem; margin: 0 0 6px; font-weight: 500; }

/* ── Cards ───────────────────────────────────────────── */
.card {
    background: #ffffff; border-radius: 18px;
    padding: 12px 6px 8px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 1px 3px rgba(15,23,42,0.04);
    height: 100%; transition: box-shadow 0.2s, border-color 0.2s;
}
.card:hover { box-shadow: 0 8px 20px rgba(15,23,42,0.06); border-color: #cbd5e1; }
.card-title {
    color: #0f172a; font-size: 0.95rem; font-weight: 700;
    letter-spacing: -0.015em;
    display: inline; margin: 0 12px 0 0;
}
.card-desc {
    color: #64748b; font-size: 0.78rem; font-weight: 500;
    display: inline; margin: 0;
}
.card-desc::before { content: "·\00a0"; margin: 0 6px; color: #cbd5e1; }
.card > .card-desc + * { display: block; margin-top: 8px; }

/* ── Delta tiles ─────────────────────────────────────── */
.delta-row { display: grid; grid-template-columns: repeat(4,1fr); gap: 14px; margin-bottom: 12px; }
.delta-tile {
    background: #ffffff; border-radius: 16px; padding: 12px 16px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 1px 3px rgba(15,23,42,0.04);
    transition: transform 0.2s, box-shadow 0.2s;
}
.delta-tile:hover { transform: translateY(-2px); box-shadow: 0 12px 24px rgba(15,23,42,0.06); }
.delta-tile .d-label { color: #1e293b; font-size: 0.7rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 4px; }
.delta-tile .d-value { font-size: 1.5rem; font-weight: 800; letter-spacing: -0.025em; line-height: 1; }
.delta-tile .d-value.green  { background: linear-gradient(135deg, #059669, #10b981); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.delta-tile .d-value.red    { background: linear-gradient(135deg, #dc2626, #ef4444); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.delta-tile .d-value.orange { background: linear-gradient(135deg, #d97706, #f59e0b); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.delta-tile .d-value.blue   { background: linear-gradient(135deg, #2563eb, #06b6d4); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.delta-tile .d-sub { color: #475569; font-size: 0.74rem; margin-top: 3px; font-weight: 500; }

/* ── Notices ─────────────────────────────────────────── */
.info-notice {
    background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 12px;
    padding: 12px 16px; color: #1d4ed8; font-size: 0.84rem; font-weight: 500;
    margin-bottom: 16px;
}

/* ── Run status banner ───────────────────────────────── */
.run-status {
    display: flex; align-items: center; gap: 14px;
    padding: 8px 14px; border-radius: 14px;
    margin-bottom: 8px; font-size: 0.88rem; font-weight: 500;
    box-shadow: 0 1px 3px rgba(15,23,42,0.04);
}
.run-status .icon { font-size: 1.4rem; line-height: 1; }
.run-status b { font-weight: 700; }
.run-status .meta { margin-right: auto; opacity: 0.7; font-size: 0.8rem; }
.run-status.ok   { background: linear-gradient(135deg, #ecfdf5, #d1fae5); border: 1px solid #a7f3d0; color: #065f46; }
.run-status.err  { background: linear-gradient(135deg, #fef2f2, #fee2e2); border: 1px solid #fecaca; color: #991b1b; }
.run-status.warn { background: linear-gradient(135deg, #fffbeb, #fef3c7); border: 1px solid #fde68a; color: #92400e; }
.filter-hint  {
    background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px;
    padding: 6px 12px; color: #334155; font-size: 0.76rem; margin-top: 4px; font-weight: 500;
}

/* ── Change tables ───────────────────────────────────── */
.chg-tbl { width:100%; border-collapse:collapse; font-size:0.85rem; direction:rtl; }
.chg-tbl th { background:#f8fafc; color:#64748b; font-weight:700; font-size:0.65rem; text-transform:uppercase; letter-spacing:0.12em; padding:13px 16px; text-align:right; border-bottom:1px solid #e2e8f0; }
.chg-tbl td { padding:12px 16px; color:#0f172a; border-bottom:1px solid #f1f5f9; vertical-align:middle; }
.chg-tbl tr:hover td { background:#f8fafc; }
.chg-tbl tr:last-child td { border-bottom:none; }
.up   { color:#dc2626; font-weight:700; }
.down { color:#059669; font-weight:700; }
.open-btn {
    display:inline-block; padding:6px 14px;
    background:linear-gradient(135deg, #eff6ff, #dbeafe);
    border:1px solid #bfdbfe; border-radius:8px;
    color:#1d4ed8; text-decoration:none;
    font-size:0.75rem; font-weight:700; white-space:nowrap; transition: all 0.15s;
}
.open-btn:hover { background:linear-gradient(135deg, #dbeafe, #bfdbfe); transform: translateY(-1px); }

/* ── Sticky filter bar ───────────────────────────────── */
.filter-bar-wrap {
    position: sticky; top: 0; z-index: 99;
    background: rgba(248,250,252,0.92);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 12px 14px 10px;
    margin: 18px -4px 14px;
    box-shadow: 0 2px 8px rgba(15,23,42,0.04);
}
div[data-testid="stButton"] > button[kind="secondary"] {
    background: linear-gradient(135deg, #f8fafc, #f1f5f9) !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 10px !important;
    color: #475569 !important;
    font-size: 0.78rem !important;
    font-weight: 700 !important;
    padding: 6px 14px !important;
    height: 38px !important;
    margin-top: 22px !important;
    transition: all 0.15s !important;
}
div[data-testid="stButton"] > button[kind="secondary"]:hover {
    background: linear-gradient(135deg, #eff6ff, #dbeafe) !important;
    border-color: #bfdbfe !important;
    color: #1d4ed8 !important;
    transform: translateY(-1px);
}

/* ── Help tooltip (ⓘ) ────────────────────────────────────── */
.tip {
    position: relative;
    display: inline-flex; align-items: center; justify-content: center;
    width: 18px; height: 18px;
    margin-right: 6px;
    border-radius: 50%;
    background: #f1f5f9; color: #64748b;
    font-size: 0.7rem; font-weight: 800;
    cursor: help; user-select: none;
    border: 1px solid #e2e8f0;
    transition: all 0.15s;
    vertical-align: middle;
}
.tip:hover { background: #eff6ff; color: #1d4ed8; border-color: #bfdbfe; }
.tip::after {
    content: attr(data-tip);
    position: absolute; top: 130%; right: 50%;
    transform: translateX(50%);
    background: #0f172a; color: #f1f5f9;
    padding: 8px 12px; border-radius: 8px;
    font-size: 0.78rem; font-weight: 500;
    white-space: normal; width: max-content; max-width: 280px;
    text-align: right; direction: rtl;
    line-height: 1.45;
    box-shadow: 0 8px 20px rgba(15,23,42,0.18);
    opacity: 0; pointer-events: none;
    transition: opacity 0.15s;
    z-index: 1000;
}
.tip:hover::after { opacity: 1; }

/* ── Streamlit widgets ───────────────────────────────── */
[data-testid="stHorizontalBlock"] { gap: 16px; }
div[data-testid="column"] { padding: 0 !important; }
.stTabs [data-baseweb="tab-list"] { background: #ffffff !important; border: 1px solid #e2e8f0 !important; border-radius: 12px !important; padding: 4px !important; gap: 2px !important; }
.stTabs [data-baseweb="tab"] { background: transparent !important; border-radius: 9px !important; color: #334155 !important; font-size: 0.84rem !important; font-weight: 600 !important; padding: 7px 16px !important; border: none !important; transition: all 0.15s !important; }
.stTabs [data-baseweb="tab"]:hover { color: #0f172a !important; background: #f8fafc !important; }
.stTabs [aria-selected="true"] { background: linear-gradient(135deg, #2563eb, #06b6d4) !important; color: #ffffff !important; font-weight: 700 !important; box-shadow: 0 4px 10px rgba(37,99,235,0.25) !important; }
.stTabs [data-baseweb="tab-panel"] { padding: 22px 0 0 !important; }

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #94a3b8; }
</style>
""", unsafe_allow_html=True)

# ── Theme colours ────────────────────────────────────────────────────────────────
CYAN   = "#2563eb"
GREEN  = "#10b981"
RED    = "#ef4444"
YELLOW = "#f59e0b"
PURPLE = "#7c3aed"

def _chart(fig, height=280):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Heebo, -apple-system, sans-serif", color="#64748b", size=11),
        height=height,
        margin=dict(t=8, b=12, l=4, r=4),
        dragmode=False,
        xaxis=dict(gridcolor="#f1f5f9", zerolinecolor="#f1f5f9",
                   tickfont=dict(color="#94a3b8", size=11), showline=False,
                   fixedrange=True),
        yaxis=dict(gridcolor="#f1f5f9", zerolinecolor="#f1f5f9",
                   tickfont=dict(color="#94a3b8", size=11), showline=False, fixedrange=True),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)", font=dict(color="#475569", size=11)),
        hoverlabel=dict(bgcolor="#0f172a", bordercolor="#0f172a", font=dict(color="#f1f5f9", size=12, family="Inter, Heebo, sans-serif")),
        showlegend=False,
    )
    return fig

def _daily(x, y, agg="last"):
    """Collapse multiple same-day points into one string-labeled day (no duplicate ticks)."""
    tmp = pd.DataFrame({"x": pd.to_datetime(x).dt.normalize(), "y": pd.to_numeric(y, errors="coerce")}).dropna()
    if tmp.empty:
        return x, y
    res = tmp.groupby("x")["y"].last() if agg == "last" else tmp.groupby("x")["y"].mean().round()
    return res.index.strftime("%d/%m/%y"), res.values

def _yrange(values, pad_frac=0.08):
    """Return [min,max] for y-axis with `pad_frac` of the spread on each side.
    Used to keep small variations visible without forcing y to start at zero."""
    import numpy as np
    arr = np.asarray([v for v in values if v is not None and not pd.isna(v)], dtype=float)
    if arr.size == 0:
        return None
    lo, hi = float(arr.min()), float(arr.max())
    spread = max(hi - lo, abs(hi) * 0.02, 1e-9)
    return [lo - spread * pad_frac, hi + spread * pad_frac]

# ── Data loaders ─────────────────────────────────────────────────────────────────
DATA_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(DATA_DIR, "yad2_raanana_4rooms.json")

def parse_price_num(p):
    p = str(p).replace(",", "").replace("₪", "").strip()
    m = re.search(r"(\d+)", p)
    return int(m.group(1)) if m else None

@st.cache_data
def load_current(_mtime):
    with open(DATA_FILE, encoding="utf-8") as f:
        raw = json.load(f)
    df = pd.DataFrame(raw)
    df["price_num"] = df["price"].apply(parse_price_num)
    for col in ["rooms", "floor", "size_sqm"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    def exf(info, idx):
        parts = str(info).split(",")
        return parts[idx].strip() if len(parts) > idx else ""
    df["apt_type"]     = df["info"].apply(lambda x: exf(x, 0) or "דירה")
    df["neighborhood"] = df["info"].apply(lambda x: exf(x, 1))

    fs_path = os.path.join(DATA_DIR, "yad2_first_seen.json")
    try:
        with open(fs_path, encoding="utf-8") as f:
            first_seen = json.load(f)
    except Exception:
        first_seen = {}

    today_str = datetime.now().strftime("%Y-%m-%d")

    def _lid(url):
        return url.split("?")[0].rstrip("/").split("/")[-1] if url else ""

    # Both first_seen.json and date_posted.json are keyed by listing-ID
    # (path segment after /realestate/item/...), stable across runs.
    def _resolve_date(row):
        dp  = row.get("date_posted") or ""
        return dp or first_seen.get(_lid(row.get("url") or ""), "")

    def _first_seen_earliest(row):
        return first_seen.get(_lid(row.get("url") or ""), "")

    def _calc_dom(row):
        ds = _resolve_date(row)
        if not ds:
            return None
        try:
            return (datetime.strptime(today_str, "%Y-%m-%d") - datetime.strptime(ds, "%Y-%m-%d")).days
        except Exception:
            return None

    df["תאריך_הופעה"] = df.apply(_resolve_date, axis=1)
    df["מעקב_ראשון"]  = df.apply(_first_seen_earliest, axis=1)
    df["ימים_בשוק"]   = df.apply(_calc_dom, axis=1)
    return df

@st.cache_data(ttl=300)
def load_history():
    path = os.path.join(DATA_DIR, "yad2_history.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["date"] = pd.to_datetime(df["timestamp"])
    df = df.rename(columns={"count": "כמות"})
    return df.sort_values("date").reset_index(drop=True)

@st.cache_data(ttl=300)
def load_nb_history():
    path = os.path.join(DATA_DIR, "yad2_neighborhood_history.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["date"] = pd.to_datetime(df["timestamp"])
    return df.sort_values("date").reset_index(drop=True)

@st.cache_data(ttl=300)
def load_type_history():
    path = os.path.join(DATA_DIR, "yad2_type_history.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["date"] = pd.to_datetime(df["timestamp"])
    return df.sort_values("date").reset_index(drop=True)

@st.cache_data(ttl=300)
def detect_changes():
    prev_file = os.path.join(DATA_DIR, "yad2_prev_run.json")
    if not os.path.exists(prev_file):
        return None, None, None, None, None
    with open(prev_file, encoding="utf-8") as f:
        prev_list = json.load(f)
    with open(DATA_FILE, encoding="utf-8") as f:
        curr_list = json.load(f)
    prev_time = datetime.fromtimestamp(os.path.getmtime(prev_file)).strftime("%d/%m/%Y %H:%M")
    curr_time = datetime.fromtimestamp(os.path.getmtime(DATA_FILE)).strftime("%d/%m/%Y %H:%M")
    # Compare by listing-ID — yad2 randomizes URL query strings between runs,
    # so URL-keyed comparison would mark ~all listings as both new and removed.
    def _id(u): return (u or "").split("?")[0].rstrip("/").split("/")[-1]
    prev_map  = {_id(r.get("url", "")): r for r in prev_list if r.get("url")}
    curr_map  = {_id(r.get("url", "")): r for r in curr_list if r.get("url")}
    new_rows, rem_rows, price_rows = [], [], []
    for k in set(curr_map) - set(prev_map): new_rows.append(curr_map[k])
    for k in set(prev_map) - set(curr_map): rem_rows.append(prev_map[k])
    for k in set(prev_map) & set(curr_map):
        pp = parse_price_num(prev_map[k].get("price", ""))
        cp = parse_price_num(curr_map[k].get("price", ""))
        if pp and cp and pp != cp:
            row = dict(curr_map[k])
            row.update({"price_num": cp, "prev_price_num": pp,
                        "prev_price": prev_map[k].get("price", ""),
                        "delta": cp - pp, "delta_pct": round((cp - pp) / pp * 100, 1)})
            price_rows.append(row)
    return (pd.DataFrame(new_rows) if new_rows else pd.DataFrame(),
            pd.DataFrame(rem_rows) if rem_rows else pd.DataFrame(),
            pd.DataFrame(price_rows) if price_rows else pd.DataFrame(),
            prev_time, curr_time)

@st.cache_data(ttl=300)
def load_run_log():
    path = os.path.join(DATA_DIR, "yad2_run_log.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.sort_values("timestamp", ascending=False).reset_index(drop=True)

@st.cache_data(ttl=300)
def load_first_seen_map():
    path = os.path.join(DATA_DIR, "yad2_first_seen.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)

@st.cache_data(ttl=300)
def load_dom_log():
    path = os.path.join(DATA_DIR, "yad2_dom_log.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig")

# ── Load data ────────────────────────────────────────────────────────────────────
_mtime    = os.path.getmtime(DATA_FILE)
df        = load_current(_mtime)
history   = load_history()
nb_hist   = load_nb_history()
type_hist = load_type_history()
run_log   = load_run_log()
chg      = detect_changes()
new_df, rem_df, price_df, prev_time, curr_time = (
    chg if chg[0] is not None
    else (pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), "—", "—")
)
mod_time = datetime.fromtimestamp(os.path.getmtime(DATA_FILE)).strftime("%d/%m/%Y %H:%M")

def _hebrew_age(dt):
    """Return a Hebrew 'X ago' string."""
    secs = (datetime.now() - dt).total_seconds()
    if secs < 60:        return "עכשיו"
    mins = int(secs // 60)
    if mins < 60:        return f"לפני {mins} דקות" if mins > 1 else "לפני דקה"
    hrs = int(mins // 60)
    if hrs < 24:         return f"לפני {hrs} שעות" if hrs > 1 else "לפני שעה"
    days = int(hrs // 24)
    if days < 30:        return f"לפני {days} ימים" if days > 1 else "אתמול"
    return dt.strftime("%d/%m/%Y")

mod_age = _hebrew_age(datetime.fromtimestamp(os.path.getmtime(DATA_FILE)))

# ── Page header (placeholder — filled below once fdf is known) ───────────────────
header_slot = st.empty()

# ── Top filter bar ───────────────────────────────────────────────────────────────
# Sort dropdown values by frequency — rarest first, so unusual options surface easily
def _by_rarity(series, as_int=False):
    s = series.dropna()
    if as_int:
        s = s.astype(int)
    counts = s.value_counts(ascending=True)
    return counts.index.tolist()

apt_types   = [t for t in _by_rarity(df["apt_type"]) if t]
rooms_opts  = _by_rarity(df["rooms"], as_int=True)
floors_opts = _by_rarity(df["floor"], as_int=True)
nbs         = [n for n in _by_rarity(df["neighborhood"]) if n]

price_min, price_max = int(df["price_num"].min()), int(df["price_num"].max())
size_min, size_max   = int(df["size_sqm"].dropna().min()), int(df["size_sqm"].dropna().max())

# Defaults for reset
_defaults = {
    "flt_price":  (price_min, price_max),
    "flt_size":   (size_min, size_max),
    "flt_type":   "הכל",
    "flt_rooms":  "הכל",
    "flt_floor":  "הכל",
    "flt_nb":     "הכל",
    "quick_range": "הכל",
}
for k, v in _defaults.items():
    st.session_state.setdefault(k, v)

if st.session_state.get("_reset_filters"):
    for k, v in _defaults.items():
        st.session_state[k] = v
    st.session_state["_reset_filters"] = False

st.markdown('<div class="filter-bar-wrap"><div class="filter-bar-anchor"></div>', unsafe_allow_html=True)
fb1, fb2, fb3, fb4, fb5, fb6, fb_reset, _spacer = st.columns([1.4, 1.4, 0.9, 0.7, 0.7, 1, 0.7, 2.3])
with fb1:
    price_range = st.slider("טווח מחיר (₪)", price_min, price_max, step=50000, format="%d", key="flt_price")
with fb2:
    size_range = st.slider("גודל (מ״ר)", size_min, size_max, key="flt_size")
with fb3:
    sel_type = st.selectbox("סוג נכס", ["הכל"] + apt_types, key="flt_type")
with fb4:
    sel_rooms = st.selectbox("חדרים", ["הכל"] + [str(r) for r in rooms_opts], key="flt_rooms")
with fb5:
    sel_floor = st.selectbox("קומה", ["הכל"] + [str(f) for f in floors_opts], key="flt_floor")
with fb6:
    sel_nb = st.selectbox("שכונה", ["הכל"] + nbs, key="flt_nb")
with fb_reset:
    if st.button("♺ אפס", help="איפוס כל הפילטרים", use_container_width=True):
        st.session_state["_reset_filters"] = True
        st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# ── Apply filters ────────────────────────────────────────────────────────────────
size_filled = df["size_sqm"].fillna(size_range[0])
mask = (
    (df["price_num"] >= price_range[0]) & (df["price_num"] <= price_range[1]) &
    (size_filled >= size_range[0])      & (size_filled <= size_range[1])
)
if sel_type  != "הכל": mask &= df["apt_type"]     == sel_type
if sel_nb    != "הכל": mask &= df["neighborhood"] == sel_nb
if sel_rooms != "הכל": mask &= df["rooms"]        == int(sel_rooms)
if sel_floor != "הכל": mask &= df["floor"]        == int(sel_floor)
fdf_raw = df[mask].copy()

# Yad2 boosts paid ads to appear on multiple search pages — same listing recorded N
# times under different URL query strings. Dedupe by listing ID (path segment).
def _listing_id(u):
    return (u or "").split("?")[0].rstrip("/").split("/")[-1]
fdf_raw["_lid"] = fdf_raw["url"].apply(_listing_id)
fdf = (fdf_raw[fdf_raw["_lid"] != ""]
            .drop_duplicates(subset="_lid", keep="first")
            .copy())
# Capture the duplicates so we can show them in a separate panel
dup_mask = fdf_raw.duplicated(subset="_lid", keep="first") & (fdf_raw["_lid"] != "")
fdf_dups = fdf_raw[dup_mask].copy()
fdf_raw.drop(columns="_lid", inplace=True, errors="ignore")
fdf.drop(columns="_lid", inplace=True, errors="ignore")
fdf_dups.drop(columns="_lid", inplace=True, errors="ignore")

# ── Page header ──────────────────────────────────────────────────────────────────
avg_p   = int(fdf["price_num"].mean())    if len(fdf) else 0
med_p   = int(fdf["price_num"].median())  if len(fdf) else 0
min_p   = int(fdf["price_num"].min())     if len(fdf) else 0
avg_sqm = fdf["size_sqm"].dropna().mean() if len(fdf) else 0
ppsqm   = int(avg_p / avg_sqm)            if avg_sqm else 0

header_slot.markdown(f"""
<div class="page-header">
    <h1>סקירת שוק רעננה · 4 חדרים</h1>
    <div class="sub">
        <b>{len(fdf):,}</b> מודעות &nbsp;·&nbsp; עודכן <b>{mod_age}</b> &nbsp;<span style="opacity:0.55">({mod_time})</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Run status banner ────────────────────────────────────────────────────────────
if len(run_log) > 0:
    last_run     = run_log.iloc[0]
    last_status  = str(last_run.get("status", "")).lower()
    last_ts      = last_run["timestamp"]
    last_ts_fmt  = last_ts.strftime("%d/%m/%Y %H:%M")
    hours_ago    = (datetime.now() - last_ts.to_pydatetime()).total_seconds() / 3600

    if last_status == "error":
        err_msg = str(last_run.get("error", "") or "שגיאה לא מזוהה")
        if len(err_msg) > 160: err_msg = err_msg[:160] + "…"
        st.markdown(f"""
        <div class="run-status err">
            <span class="icon">❌</span>
            <div><b>הריצה האחרונה נכשלה</b> · {last_ts_fmt}<br>
                 <span style="opacity:0.85;font-size:0.82rem;">{err_msg}</span></div>
        </div>
        """, unsafe_allow_html=True)
    elif hours_ago > 14:
        st.markdown(f"""
        <div class="run-status warn">
            <span class="icon">⚠️</span>
            <div><b>הריצה האחרונה הייתה לפני {int(hours_ago)} שעות</b> · {last_ts_fmt}<br>
                 <span style="opacity:0.85;font-size:0.82rem;">ייתכן שה-Scraper לא רץ כמתוכנן</span></div>
        </div>
        """, unsafe_allow_html=True)
    else:
        n_listings = int(last_run.get("total_listings") or 0)
        st.markdown(f"""
        <div class="run-status ok">
            <span class="icon">✅</span>
            <div><b>הריצה האחרונה הצליחה</b> · {last_ts_fmt}</div>
            <span class="meta">{n_listings:,} מודעות נסרקו</span>
        </div>
        """, unsafe_allow_html=True)

# ── KPI strip ────────────────────────────────────────────────────────────────────
def fmt(n): return f"₪{n:,}" if n else "—"

# Compute deltas vs ~7 days ago from market-wide history (best signal we have)
def _kpi_delta(curr, ref):
    """Return (html_pill, sub_text). For lower-is-better KPIs flip with `invert`."""
    if curr is None or ref is None or ref == 0:
        return ""
    diff = curr - ref
    pct  = (diff / ref) * 100 if ref else 0
    if abs(pct) < 0.05:
        cls, arrow = "flat", "—"
    elif diff > 0:
        cls, arrow = "up", "▲"
    else:
        cls, arrow = "down", "▼"
    return f'<div class="kpi-delta {cls}">{arrow} {abs(pct):.1f}% מול שבוע</div>'

ref_count = ref_avg = ref_med = ref_pps = None
if len(history) > 0:
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=7)
    past = history[history["date"] <= cutoff]
    ref_row = past.iloc[-1] if len(past) else history.iloc[0]
    ref_count = int(ref_row["כמות"]) if pd.notna(ref_row.get("כמות")) else None
    ref_avg   = float(ref_row["avg_price"])         if "avg_price"         in ref_row and pd.notna(ref_row["avg_price"])         else None
    ref_med   = float(ref_row["median_price"])      if "median_price"      in ref_row and pd.notna(ref_row["median_price"])      else None
    ref_pps   = float(ref_row["avg_price_per_sqm"]) if "avg_price_per_sqm" in ref_row and pd.notna(ref_row["avg_price_per_sqm"]) else None

d_count = _kpi_delta(len(fdf), ref_count)
d_avg   = _kpi_delta(avg_p,    ref_avg)
d_med   = _kpi_delta(med_p,    ref_med)
d_pps   = _kpi_delta(ppsqm,    ref_pps)

st.markdown(f"""
<div class="kpi-strip">
    <div class="kpi blue">
        <div class="kpi-head">
            <div class="kpi-label">מודעות פעילות</div>
            <div class="kpi-icon">🏠</div>
        </div>
        <div class="kpi-value">{len(fdf):,}</div>
        <div class="kpi-sub">תוצאות מסוננות</div>
        {d_count}
    </div>
    <div class="kpi green">
        <div class="kpi-head">
            <div class="kpi-label">מחיר ממוצע</div>
            <div class="kpi-icon">💰</div>
        </div>
        <div class="kpi-value">{fmt(avg_p)}</div>
        <div class="kpi-sub">ממוצע מחירי מכירה</div>
        {d_avg}
    </div>
    <div class="kpi gray">
        <div class="kpi-head">
            <div class="kpi-label">מחיר חציוני</div>
            <div class="kpi-icon">📊</div>
        </div>
        <div class="kpi-value">{fmt(med_p)}</div>
        <div class="kpi-sub">אמצע השוק</div>
        {d_med}
    </div>
    <div class="kpi orange">
        <div class="kpi-head">
            <div class="kpi-label">מחיר מינימום</div>
            <div class="kpi-icon">⬇️</div>
        </div>
        <div class="kpi-value">{fmt(min_p)}</div>
        <div class="kpi-sub">המחיר הנמוך ביותר</div>
        <div class="kpi-spacer"></div>
    </div>
    <div class="kpi purple">
        <div class="kpi-head">
            <div class="kpi-label">מחיר למ״ר</div>
            <div class="kpi-icon">📐</div>
        </div>
        <div class="kpi-value">{fmt(ppsqm)}</div>
        <div class="kpi-sub">ממוצע למטר רבוע</div>
        {d_pps}
    </div>
</div>
""", unsafe_allow_html=True)

# ── Section: Charts ──────────────────────────────────────────────────────────────
quick_range = "הכל"

chart_nb   = sel_nb
chart_type = sel_type

if len(history) == 0:
    st.markdown('<div class="info-notice">גרפים יופיעו לאחר מספר ריצות של ה-Scraper.</div>', unsafe_allow_html=True)
else:
    # Apply time-range filter to all history sources
    def _within_range(df_in, days):
        if df_in is None or len(df_in) == 0 or days is None:
            return df_in
        cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)
        return df_in[df_in["date"] >= cutoff]

    range_days = {"30 ימים": 30, "7 ימים": 7}.get(quick_range)
    history_f = _within_range(history,   range_days)
    nb_hist_f = _within_range(nb_hist,   range_days)
    type_hist_f = _within_range(type_hist, range_days)

    using_nb   = chart_nb   != "הכל" and len(nb_hist_f)   > 0
    using_type = chart_type != "הכל" and len(type_hist_f) > 0

    if using_nb and using_type:
        # Both filters active: type drives both qty and price
        # (no per-(nb × type) history file is tracked, so we pick one — type is what most users compare)
        src = type_hist_f[type_hist_f["apt_type"] == chart_type].sort_values("date")
        qty_x,   qty_y   = src["date"], src["count"]
        price_x, price_y = src["date"], src["avg_price_per_sqm"]
        scope_label = f"{chart_nb} · {chart_type}"
    elif using_nb:
        src = nb_hist_f[nb_hist_f["neighborhood"] == chart_nb].sort_values("date")
        qty_x, qty_y     = src["date"], src["count"]
        price_x, price_y = src["date"], src["avg_price_per_sqm"]
        scope_label = chart_nb
    elif using_type:
        src = type_hist_f[type_hist_f["apt_type"] == chart_type].sort_values("date")
        qty_x, qty_y     = src["date"], src["count"]
        price_x, price_y = src["date"], src["avg_price_per_sqm"]
        scope_label = chart_type
    else:
        qty_x, qty_y     = history["date"], history["כמות"]
        price_x, price_y = history["date"], history["avg_price_per_sqm"]
        scope_label = "כל השוק"

    # Narrowing filters that the pre-aggregated history files can't slice by
    any_narrow_filter = (
        sel_rooms != "הכל" or sel_floor != "הכל" or
        price_range != (price_min, price_max) or
        size_range != (size_min, size_max)
    )

    active_filters = [f for f in [chart_nb if using_nb else "", chart_type if using_type else "", quick_range if quick_range != "הכל" else ""] if f]
    if active_filters:
        st.markdown(f'<div class="filter-hint">מסונן לפי: <b>{" · ".join(active_filters)}</b></div>', unsafe_allow_html=True)

    gc1, gc2 = st.columns(2, gap="medium")

    # ── Chart 1: Listing quantity over time ──────────────────────────────────────
    with gc1:
        qty_label = scope_label if not any_narrow_filter else f"{scope_label} · פילוח חי"
        st.markdown(f'<div class="card"><div class="card-title"><span class="tip" data-tip="כמה מודעות 4-חדרים פעילות היו בכל יום. עלייה = יותר היצע, ירידה = פחות היצע (יותר נסגרו ממה שנפתחו).">ⓘ</span>כמות מודעות לאורך זמן</div><div class="card-desc">{qty_label}</div>', unsafe_allow_html=True)
        if any_narrow_filter:
            # Pre-aggregated history can't be sliced by price/size/rooms/floor — show today's filtered count only
            st.markdown(
                f'<p style="color:#0f172a;font-size:2rem;font-weight:800;padding:18px 0 4px;">{len(fdf):,} מודעות</p>'
                f'<p style="color:#475569;font-size:0.84rem;">תואמות את הפילטרים · היסטוריה לפי מחיר/גודל/חדרים/קומה אינה נשמרת</p>',
                unsafe_allow_html=True)
        else:
            qty_color = CYAN
            fig_qty = go.Figure()
            _qx, _qy = _daily(qty_x, qty_y)
            fig_qty.add_trace(go.Scatter(
                x=_qx, y=_qy,
                mode="lines+markers+text",
                line=dict(color=qty_color, width=2.8, shape="spline", smoothing=0.3),
                marker=dict(size=7, color=qty_color, line=dict(color="#ffffff", width=2)),
                text=[f"{int(v):,}" for v in _qy],
                textposition="top center",
                textfont=dict(size=11, color="#0f172a", family="Inter, Heebo, sans-serif"),
                cliponaxis=False,
                hovertemplate="<b>%{x}</b><br>%{y} מודעות<extra></extra>"
            ))
            _chart(fig_qty, 280)
            qty_rng = _yrange(_qy)
            fig_qty.update_layout(yaxis_title="מודעות",
                                  yaxis=dict(range=qty_rng, fixedrange=True,
                                             gridcolor="#f1f5f9", tickfont=dict(color="#475569", size=11)))
            st.plotly_chart(fig_qty, use_container_width=True, config=dict(displayModeBar=False, scrollZoom=False))
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Chart 2: Avg price per sqm over time ─────────────────────────────────────
    with gc2:
        st.markdown(f'<div class="card"><div class="card-title"><span class="tip" data-tip="מחיר ממוצע לכל מ״ר על פני כל המודעות הפעילות. זה האינדיקטור הכי טוב למחיר נטו של השוק (מנטרל הבדלי גודל).">ⓘ</span>מחיר ממוצע למ״ר לאורך זמן</div><div class="card-desc">{scope_label} — עולה/יורד = התייקרות/הוזלה</div>', unsafe_allow_html=True)
        if len(price_y.dropna()) >= 2:
            trend_up = float(price_y.dropna().iloc[-1]) >= float(price_y.dropna().iloc[0])
            p_color = RED if trend_up else GREEN
            fill_col = "rgba(239,68,68,0.08)" if trend_up else "rgba(16,185,129,0.08)"
        else:
            p_color, fill_col = CYAN, "rgba(37,99,235,0.08)"
        fig_price = go.Figure()
        _px, _py = _daily(price_x, price_y, agg="mean")
        fig_price.add_trace(go.Scatter(
            x=_px, y=_py,
            mode="lines+markers+text",
            line=dict(color=p_color, width=2.8, shape="spline", smoothing=0.3),
            marker=dict(size=7, color=p_color, line=dict(color="#ffffff", width=2)),
            text=[f"₪{int(v):,}" for v in _py],
            textposition="top center",
            textfont=dict(size=11, color="#0f172a", family="Inter, Heebo, sans-serif"),
            cliponaxis=False,
            hovertemplate="<b>%{x}</b><br>₪%{y:,.0f}/מ״ר<extra></extra>"
        ))
        _chart(fig_price, 280)
        p_rng = _yrange(_py)
        fig_price.update_layout(yaxis_title="₪/מ״ר",
                                yaxis=dict(range=p_rng, tickformat=",d", fixedrange=True,
                                           gridcolor="#f1f5f9", tickfont=dict(color="#475569", size=11)))
        st.plotly_chart(fig_price, use_container_width=True, config=dict(displayModeBar=False, scrollZoom=False))
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Chart 5: Avg days on market over time ────────────────────────────────
    st.markdown('<div style="margin-top:14px"></div>', unsafe_allow_html=True)
    gc5, gc6 = st.columns(2, gap="medium")
    with gc5:
        st.markdown(f'<div class="card"><div class="card-title"><span class="tip" data-tip="DOM = Days On Market. כמה ימים בממוצע מודעה כבר באוויר. עלייה = מודעות נתקעות (השוק מאט), ירידה = מתחלפות מהר (השוק חם).">ⓘ</span>ממוצע ימים בשוק לאורך זמן</div><div class="card-desc">DOM ממוצע של כל המודעות הפעילות · {scope_label}</div>', unsafe_allow_html=True)

        # ONLY use avg_active_dom (avg DOM of currently active listings).
        # Skip the old avg_dom column entirely — it's a different metric (DOM of removed only).
        # Source priority: per-neighborhood → per-type → market-wide. Hide the line entirely
        # if a narrow filter (price/size/rooms/floor) is active, since none of the histories slice by those.
        xs, ys = [], []
        dom_src = None
        if not any_narrow_filter:
            if sel_nb != "הכל" and "avg_active_dom" in nb_hist_f.columns:
                dom_src = nb_hist_f[nb_hist_f["neighborhood"] == sel_nb]
            elif sel_type != "הכל" and "avg_active_dom" in type_hist_f.columns:
                dom_src = type_hist_f[type_hist_f["apt_type"] == sel_type]
            elif sel_nb == "הכל" and sel_type == "הכל" and "avg_active_dom" in history_f.columns:
                dom_src = history_f
        if dom_src is not None and len(dom_src):
            hd = dom_src.dropna(subset=["avg_active_dom"]).copy()
            hd["avg_active_dom"] = pd.to_numeric(hd["avg_active_dom"], errors="coerce")
            hd = hd[hd["avg_active_dom"] > 0]
            if len(hd):
                _ddx, _ddy = _daily(hd["date"], hd["avg_active_dom"], agg="mean")
                xs, ys = list(_ddx), list(_ddy)

        # Live point reflects the active filters via fdf
        live_dom = fdf["ימים_בשוק"].dropna()
        live_dom = live_dom[live_dom >= 0]
        live_avg = float(live_dom.mean()) if len(live_dom) else None

        today_str = datetime.now().strftime("%d/%m/%y")
        if live_avg is not None and (not xs or xs[-1] != today_str):
            xs.append(today_str); ys.append(round(live_avg, 1))

        if len(xs) >= 2:
            fig_dom = go.Figure(go.Scatter(
                x=xs, y=ys,
                mode="lines+markers+text",
                line=dict(color=PURPLE, width=2.8, shape="spline", smoothing=0.3),
                marker=dict(size=7, color=PURPLE, line=dict(color="#ffffff", width=2)),
                text=[f"{v:.0f}" for v in ys],
                textposition="top center",
                textfont=dict(size=11, color="#0f172a", family="Inter, Heebo, sans-serif"),
                cliponaxis=False,
                hovertemplate="<b>%{x}</b><br>%{y:.1f} ימים<extra></extra>"
            ))
            _chart(fig_dom, 300)
            dom_rng = _yrange(ys)
            fig_dom.update_layout(yaxis_title="ימים",
                                  yaxis=dict(range=dom_rng, fixedrange=True,
                                             gridcolor="#f1f5f9", tickfont=dict(color="#475569", size=11)))
            st.plotly_chart(fig_dom, use_container_width=True, config=dict(displayModeBar=False, scrollZoom=False))
        elif len(xs) == 1:
            st.markdown(f'<p style="color:#0f172a;font-size:1.4rem;font-weight:800;padding:16px 0 4px;">{ys[0]:.1f} ימים בממוצע</p><p style="color:#475569;font-size:0.84rem;">המגמה תיווצר עם ריצות נוספות של ה-Scraper</p>', unsafe_allow_html=True)
        else:
            st.markdown('<p style="color:#475569;padding:24px 0;">זמין לאחר ריצת ה-Scraper.</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with gc6:
        # Avg DOM per neighborhood (mean days on market by area)
        st.markdown('<div class="card"><div class="card-title"><span class="tip" data-tip="ממוצע ימים בשוק לכל שכונה. עמודה גוהה = השכונה איטית למכור, נמוכה = מודעות מתחלפות מהר.">ⓘ</span>ממוצע ימים בשוק לפי שכונה</div><div class="card-desc">DOM ממוצע פר שכונה (מסונן)</div>', unsafe_allow_html=True)
        nb_dom = (fdf[fdf["ימים_בשוק"] >= 0]
                    .groupby("neighborhood")
                    .agg(avg_dom=("ימים_בשוק", "mean"),
                         n=("ימים_בשוק", "size"))
                    .reset_index())
        nb_dom = nb_dom[(nb_dom["neighborhood"] != "") & (nb_dom["n"] >= 2)]
        nb_dom = nb_dom.sort_values("avg_dom", ascending=True)
        if len(nb_dom):
            # Color: low DOM (fast) = green, high DOM (slow) = red
            max_d = nb_dom["avg_dom"].max() or 1
            def _col(d):
                t = d / max_d
                if t < 0.33:  return GREEN
                if t < 0.66:  return YELLOW
                return RED
            colors = [_col(d) for d in nb_dom["avg_dom"]]
            fig_nbdom = go.Figure(go.Bar(
                x=nb_dom["avg_dom"].round(1),
                y=nb_dom["neighborhood"],
                orientation="h",
                marker=dict(color=colors, line=dict(width=0)),
                text=[f"{d:.0f} ימים · {int(n)} דירות" for d, n in zip(nb_dom["avg_dom"], nb_dom["n"])],
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(size=12, color="white", family="Heebo, Inter, sans-serif"),
                customdata=nb_dom["n"],
                hovertemplate="<b>%{y}</b><br>%{x:.1f} ימים בממוצע<br>%{customdata} דירות למכירה<extra></extra>",
            ))
            _chart(fig_nbdom, max(300, len(nb_dom) * 26))
            fig_nbdom.update_layout(
                xaxis_title="ימים", yaxis_title="",
                xaxis=dict(fixedrange=True, gridcolor="#f1f5f9",
                           tickfont=dict(color="#475569", size=11)),
                yaxis=dict(fixedrange=True, gridcolor="rgba(0,0,0,0)",
                           tickfont=dict(color="#0f172a", size=11), automargin=True),
                bargap=0.25,
            )
            st.plotly_chart(fig_nbdom, use_container_width=True, config=dict(displayModeBar=False, scrollZoom=False))
        else:
            st.markdown('<p style="color:#475569;padding:24px 0;">אין מספיק נתונים לפילוח לפי שכונה.</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── New / Removed listings per DAY (deduped by listing ID) ─────────────
    # Uses first_seen.json + dom_log.csv (canonical sources, not run_log which double-counts)
    st.markdown('<div style="margin-top:14px"></div>', unsafe_allow_html=True)
    gc7, gc8 = st.columns(2, gap="medium")

    def _lid(u):
        return (u or "").split("?")[0].rstrip("/").split("/")[-1]

    fs_map = load_first_seen_map()
    # Aggregate first_seen by listing-ID → earliest date per ID, then count by date.
    # After the listing-ID migration, fs_map keys are already listing-IDs but we
    # still apply _lid() defensively (no-op) so the legacy URL-keyed format also
    # works if someone restores an old backup.
    by_lid = {}
    for k, dt in fs_map.items():
        lid = _lid(k)
        if not lid or not dt: continue
        if lid not in by_lid or dt < by_lid[lid]:
            by_lid[lid] = dt
    new_by_date = pd.Series(list(by_lid.values())).value_counts().sort_index() if by_lid else pd.Series(dtype=int)
    # Hide the baseline scrape date — every listing alive at first scrape gets
    # marked first_seen=that-date, which is not "new listings" in the sales sense.
    # Use the earliest date in run_log as the baseline, and drop it from the chart.
    if len(run_log) > 0 and len(new_by_date) > 1:
        baseline_date = pd.to_datetime(run_log["timestamp"]).min().strftime("%Y-%m-%d")
        if baseline_date in new_by_date.index:
            new_by_date = new_by_date.drop(baseline_date)

    dom_df_full = load_dom_log()
    if not dom_df_full.empty and "removed_date" in dom_df_full.columns:
        dom_dedup = dom_df_full.copy()
        dom_dedup["_lid"] = dom_dedup["url"].apply(_lid)
        # one removal event per unique listing per date
        dom_dedup = dom_dedup[dom_dedup["_lid"] != ""].drop_duplicates(subset=["_lid", "removed_date"])
        rem_by_date = dom_dedup.groupby("removed_date").size().sort_index()
    else:
        rem_by_date = pd.Series(dtype=int)

    with gc7:
        st.markdown('<div class="card"><div class="card-title"><span class="tip" data-tip="כמה מודעות ייחודיות נראו לראשונה ביום נתון. מקור: yad2_first_seen.json. ספירה לפי מזהה מודעה (לא URL מלא), כך שכפילויות booster לא נספרות.">ⓘ</span>מודעות חדשות שנוספו</div><div class="card-desc">לפי יום · ייחודיות בלבד</div>', unsafe_allow_html=True)
        if len(new_by_date):
            fig_new = go.Figure(go.Bar(
                x=new_by_date.index, y=new_by_date.values,
                marker=dict(color=GREEN, line=dict(width=0)),
                text=[f"+{int(v)}" for v in new_by_date.values],
                textposition="outside",
                textfont=dict(size=11, color="#0f172a", family="Inter, Heebo, sans-serif"),
                cliponaxis=False,
                hovertemplate="<b>%{x}</b><br>+%{y} מודעות חדשות<extra></extra>",
            ))
            _chart(fig_new, 280)
            fig_new.update_layout(yaxis_title="מודעות", bargap=0.3,
                                  xaxis=dict(type="category", fixedrange=True))
            st.plotly_chart(fig_new, use_container_width=True, config=dict(displayModeBar=False, scrollZoom=False))
        else:
            st.markdown('<p style="color:#475569;padding:24px 0;">אין נתוני first_seen.</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with gc8:
        st.markdown('<div class="card"><div class="card-title"><span class="tip" data-tip="כמה מודעות ייחודיות הוסרו מהשוק ביום נתון (נמכרו או הוסרו). מקור: yad2_dom_log.csv, מנוקה מכפילויות booster.">ⓘ</span>מודעות שהוסרו</div><div class="card-desc">לפי יום · ייחודיות בלבד</div>', unsafe_allow_html=True)
        if len(rem_by_date):
            fig_rem = go.Figure(go.Bar(
                x=rem_by_date.index, y=rem_by_date.values,
                marker=dict(color=RED, line=dict(width=0)),
                text=[f"-{int(v)}" for v in rem_by_date.values],
                textposition="outside",
                textfont=dict(size=11, color="#0f172a", family="Inter, Heebo, sans-serif"),
                cliponaxis=False,
                hovertemplate="<b>%{x}</b><br>-%{y} מודעות הוסרו<extra></extra>",
            ))
            _chart(fig_rem, 280)
            fig_rem.update_layout(yaxis_title="מודעות", bargap=0.3,
                                  xaxis=dict(type="category", fixedrange=True))
            st.plotly_chart(fig_rem, use_container_width=True, config=dict(displayModeBar=False, scrollZoom=False))
        else:
            st.markdown('<p style="color:#475569;padding:24px 0;">אין נתוני dom_log.</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ── Section: Changes ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-title" style="margin-top:18px">מה השתנה מאז העדכון הקודם</div>', unsafe_allow_html=True)

if chg[0] is None:
    st.markdown('<div class="info-notice">נדרשות לפחות 2 ריצות לזיהוי שינויים.</div>', unsafe_allow_html=True)
else:
    # Apply the active filter bar to the change tables/tiles so this section honors filters too
    def _apply_filters(d):
        if d is None or len(d) == 0:
            return d
        d = d.copy()
        if "price" in d.columns:
            d["_pn"] = d["price"].apply(parse_price_num)
        else:
            d["_pn"] = None
        d["_sz"] = pd.to_numeric(d.get("size_sqm"), errors="coerce")
        d["_rm"] = pd.to_numeric(d.get("rooms"),    errors="coerce")
        d["_fl"] = pd.to_numeric(d.get("floor"),    errors="coerce")
        d["_nb"] = d.get("info", "").apply(lambda x: (str(x).split(",")[1].strip() if len(str(x).split(",")) > 1 else "")) if "info" in d.columns else ""
        d["_tp"] = d.get("info", "").apply(lambda x: (str(x).split(",")[0].strip() if str(x) else ""))           if "info" in d.columns else ""
        m = pd.Series(True, index=d.index)
        if d["_pn"].notna().any():
            m &= d["_pn"].between(price_range[0], price_range[1]) | d["_pn"].isna()
        m &= d["_sz"].fillna(size_range[0]).between(size_range[0], size_range[1])
        if sel_type  != "הכל" and "_tp" in d.columns: m &= d["_tp"] == sel_type
        if sel_nb    != "הכל" and "_nb" in d.columns: m &= d["_nb"] == sel_nb
        if sel_rooms != "הכל": m &= d["_rm"] == int(sel_rooms)
        if sel_floor != "הכל": m &= d["_fl"] == int(sel_floor)
        return d[m].drop(columns=["_pn","_sz","_rm","_fl","_nb","_tp"], errors="ignore")

    new_df   = _apply_filters(new_df)
    rem_df   = _apply_filters(rem_df)
    price_df = _apply_filters(price_df)

    cuts_n  = len(price_df[price_df["delta"] < 0]) if len(price_df) else 0
    rises_n = len(price_df[price_df["delta"] > 0]) if len(price_df) else 0

    # Count "uniquely new" — listings whose first_seen date matches the current run date
    fs_path = os.path.join(DATA_DIR, "yad2_first_seen.json")
    try:
        with open(fs_path, encoding="utf-8") as _f:
            _first_seen = json.load(_f)
    except Exception:
        _first_seen = {}
    curr_date = datetime.fromtimestamp(os.path.getmtime(DATA_FILE)).strftime("%Y-%m-%d")
    if len(new_df) > 0:
        unique_new = sum(1 for u in new_df.get("url", []) if _first_seen.get(u or "", "") == curr_date)
    else:
        unique_new = 0
    total_ever = len(_first_seen)

    st.markdown(f"""
    <div class="delta-row">
        <div class="delta-tile"><div class="d-label">מודעות חדשות</div><div class="d-value green">+{len(new_df)}</div><div class="d-sub">מתוכן <b>{unique_new}</b> חדשות לחלוטין · מאז {prev_time}</div></div>
        <div class="delta-tile"><div class="d-label">הוסרו / נמכרו</div><div class="d-value red">-{len(rem_df)}</div><div class="d-sub">יצאו מהשוק</div></div>
        <div class="delta-tile"><div class="d-label">הורדות מחיר</div><div class="d-value green">{cuts_n}</div><div class="d-sub">מחיר הופחת</div></div>
        <div class="delta-tile"><div class="d-label">עליות מחיר</div><div class="d-value red">{rises_n}</div><div class="d-sub">מחיר עלה</div></div>
    </div>
    <div class="filter-hint" style="margin-bottom:18px">סך-כל המודעות הייחודיות שראינו אי-פעם: <b>{total_ever:,}</b></div>
    """, unsafe_allow_html=True)

    def chg_table(data, mode="normal"):
        if data is None or len(data) == 0:
            st.markdown('<p style="color:#aeaeb2;font-size:0.84rem;padding:8px 0;">אין נתונים.</p>', unsafe_allow_html=True)
            return
        rows = ""
        for _, r in data.iterrows():
            url  = r.get("url", "#") or "#"
            pr   = r.get("price", "—")
            st_v = r.get("street", "—") or "—"
            nb   = r.get("neighborhood", "—") or "—"
            sz   = f"{int(r['size_sqm'])} m²" if pd.notna(r.get("size_sqm")) else "—"
            lnk  = f'<a class="open-btn" href="{url}" target="_blank">פתח</a>'
            if mode == "delta":
                d = r["delta"]; pct = r["delta_pct"]; pp = r.get("prev_price", "—")
                cls = "down" if d < 0 else "up"
                arrow = "▼" if d < 0 else "▲"
                ds = f'<span class="{cls}">{arrow} ₪{abs(int(d)):,} ({abs(pct)}%)</span>'
                rows += f"<tr><td class='muted'>{pp}</td><td>{pr}</td><td>{ds}</td><td>{st_v}</td><td>{nb}</td><td class='muted'>{sz}</td><td>{lnk}</td></tr>"
            else:
                rows += f"<tr><td>{pr}</td><td>{st_v}</td><td>{nb}</td><td class='muted'>{sz}</td><td>{lnk}</td></tr>"
        hdr = ("<tr><th>מחיר קודם</th><th>מחיר חדש</th><th>שינוי</th><th>רחוב</th><th>שכונה</th><th>שטח</th><th></th></tr>"
               if mode == "delta" else
               "<tr><th>מחיר</th><th>רחוב</th><th>שכונה</th><th>שטח</th><th></th></tr>")
        st.markdown(f'<div style="overflow-x:auto"><table class="chg-tbl"><thead>{hdr}</thead><tbody>{rows}</tbody></table></div>',
                    unsafe_allow_html=True)

    t1, t2, t3 = st.tabs([f"חדשות ({len(new_df)})", f"הוסרו ({len(rem_df)})", f"שינויי מחיר ({len(price_df)})"])
    with t1: chg_table(new_df)
    with t2: chg_table(rem_df)
    with t3: chg_table(price_df, "delta")

# ── Section: Duplicates panel ────────────────────────────────────────────────────
if len(fdf_dups):
    with st.expander(f"🔁 כפילויות שזוהו והוסרו ({len(fdf_dups)} מודעות) — לחצי לפתיחה", expanded=False):
        st.markdown(
            f'<div class="filter-hint" style="margin-bottom:10px">'
            f'יד2 מקדם מודעות תשלום (booster/platinum) ומציג אותן במספר עמודי חיפוש. '
            f'הסקרייפר רושם כל הופעה כשורה נפרדת — אז אותה דירה נספרת מספר פעמים. '
            f'מתוך <b>{len(fdf_raw):,}</b> שורות סוננו <b>{len(fdf_dups):,}</b> כפילויות, '
            f'נשארו <b>{len(fdf):,}</b> מודעות ייחודיות.</div>',
            unsafe_allow_html=True
        )
        dup_tbl = fdf_dups[["price_num", "street", "neighborhood", "size_sqm", "url"]].copy()
        dup_tbl.columns = ["מחיר (₪)", "רחוב", "שכונה", "שטח (מ״ר)", "קישור"]
        st.dataframe(
            dup_tbl, use_container_width=True, hide_index=True,
            height=min(400, 40 + len(dup_tbl) * 36),
            column_config={"קישור": st.column_config.LinkColumn("קישור", display_text="פתח")},
        )

# ── Section: Full Table with Excel-style multi-select filters ────────────────────
st.markdown('<div class="section-title" style="margin-top:18px">כל המודעות</div>', unsafe_allow_html=True)

# fdf is already deduped by listing ID (see top of file)
tbl_df = fdf[[
    "price_num", "street", "neighborhood", "apt_type", "rooms", "floor", "size_sqm",
    "תאריך_הופעה", "מעקב_ראשון", "ימים_בשוק", "url"
]].copy()
tbl_df.columns = [
    "מחיר (₪)", "רחוב", "שכונה", "סוג", "חדרים", "קומה", "שטח (מ״ר)",
    "תאריך יד2", "מעקב ראשון", "ימים בשוק", "קישור"
]
for c in ["חדרים", "קומה", "שטח (מ״ר)", "ימים בשוק"]:
    tbl_df[c] = pd.to_numeric(tbl_df[c], errors="coerce")

# Filtering is handled by the top filter bar + AgGrid's per-column filter (▼ on header)
st.markdown(f'<div class="section-desc">{len(tbl_df):,} מודעות &nbsp;·&nbsp; לחצי על ▼ בכותרת כל עמודה לסינון</div>', unsafe_allow_html=True)

# Configure AgGrid — Excel-style: filter ▼ button on each column header
gb = GridOptionsBuilder.from_dataframe(tbl_df)
gb.configure_default_column(
    filter=True,
    sortable=True,
    resizable=True,
    floatingFilter=False,
    suppressMenu=False,
    menuTabs=["filterMenuTab"],
    minWidth=90,
    flex=1,
)
# Per-column minimum widths so nothing gets cut off
col_widths = {
    "מחיר (₪)":     {"minWidth": 130, "flex": 1.1},
    "רחוב":         {"minWidth": 150, "flex": 1.3},
    "שכונה":        {"minWidth": 160, "flex": 1.3},
    "סוג":          {"minWidth": 130, "flex": 1.1},
    "חדרים":        {"minWidth":  80, "flex": 0.6},
    "קומה":         {"minWidth":  80, "flex": 0.6},
    "שטח (מ״ר)":   {"minWidth": 100, "flex": 0.8},
    "תאריך יד2":   {"minWidth": 120, "flex": 0.9},
    "מעקב ראשון":  {"minWidth": 120, "flex": 0.9},
    "ימים בשוק":   {"minWidth": 110, "flex": 0.8},
}
for col, opts in col_widths.items():
    gb.configure_column(col, **opts)

# Numeric columns → range/comparison filter
for col in ["מחיר (₪)", "שטח (מ״ר)", "חדרים", "קומה", "ימים בשוק"]:
    gb.configure_column(col, type=["numericColumn"], filter="agNumberColumnFilter",
                        menuTabs=["filterMenuTab"], minWidth=col_widths[col]["minWidth"], flex=col_widths[col]["flex"])
gb.configure_column("מחיר (₪)", valueFormatter="value ? '₪' + value.toLocaleString() : ''",
                    minWidth=130, flex=1.1)
# Categorical columns → text contains/equals filter (community AgGrid).
# Multi-value Excel-style filtering is handled by the multiselect widgets above the table.
gb.configure_column("שכונה", filter="agTextColumnFilter", menuTabs=["filterMenuTab"], minWidth=160, flex=1.3)
gb.configure_column("סוג",   filter="agTextColumnFilter", menuTabs=["filterMenuTab"], minWidth=130, flex=1.1)
# Text columns
gb.configure_column("רחוב",        filter="agTextColumnFilter", minWidth=150, flex=1.3)
gb.configure_column("תאריך יד2",  filter="agTextColumnFilter", minWidth=120, flex=0.9)
gb.configure_column("מעקב ראשון", filter="agTextColumnFilter", minWidth=120, flex=0.9)
# Link column
gb.configure_column("קישור",
    cellRenderer=JsCode("""
        class UrlRenderer {
            init(p) {
                this.gui = document.createElement('a');
                this.gui.href = p.value || '#';
                this.gui.target = '_blank';
                this.gui.innerText = 'פתח';
                this.gui.style.cssText = 'display:inline-block;padding:5px 12px;background:linear-gradient(135deg,#eff6ff,#dbeafe);border:1px solid #bfdbfe;border-radius:8px;color:#1d4ed8;font-weight:700;text-decoration:none;font-size:0.78rem;';
            }
            getGui() { return this.gui; }
        }
    """),
    filter=False, sortable=False, minWidth=90, maxWidth=110, flex=0,
)
gb.configure_grid_options(
    enableRtl=True,
    rowHeight=42,
    headerHeight=46,
    suppressRowClickSelection=True,
    domLayout="normal",
    suppressMenuHide=True,
    suppressHorizontalScroll=False,
    enableCellTextSelection=True,
    ensureDomOrder=True,
)
grid_options = gb.build()

AgGrid(
    tbl_df,
    gridOptions=grid_options,
    update_mode=GridUpdateMode.NO_UPDATE,
    allow_unsafe_jscode=True,
    enable_enterprise_modules=False,
    height=620,
    theme="alpine",
    fit_columns_on_grid_load=True,
    custom_css={
        ".ag-root-wrapper": {
            "border": "1px solid #e2e8f0 !important",
            "border-radius": "14px !important",
            "overflow": "hidden",
            "box-shadow": "0 1px 3px rgba(15,23,42,0.04) !important",
        },
        ".ag-header": {
            "background": "#f8fafc !important",
            "border-bottom": "1px solid #e2e8f0 !important",
        },
        ".ag-header-cell": {"font-family": "Inter, Heebo, sans-serif !important"},
        ".ag-header-cell-menu-button": {
            "opacity": "1 !important",
            "color": "#94a3b8",
            "transition": "color 0.15s",
        },
        ".ag-header-cell-menu-button:hover": {
            "color": "#2563eb !important",
        },
        ".ag-header-cell-label": {
            "font-weight": "700 !important",
            "font-size": "0.95rem !important",
            "color": "#0f172a !important",
            "letter-spacing": "0.01em",
            "white-space": "normal !important",
            "line-height": "1.15 !important",
            "text-align": "center !important",
            "justify-content": "center !important",
        },
        ".ag-header-cell-text": {
            "white-space": "normal !important",
            "overflow": "visible !important",
            "text-overflow": "clip !important",
        },
        ".ag-row": {
            "font-size": "0.86rem",
            "font-family": "Inter, Heebo, sans-serif !important",
            "color": "#0f172a !important",
            "border-bottom": "1px solid #f1f5f9 !important",
        },
        ".ag-row:hover": {"background": "#f8fafc !important"},
        ".ag-row-odd": {"background": "#fafbfc !important"},
        ".ag-cell": {"display": "flex !important", "align-items": "center !important"},
        ".ag-set-filter-list": {"direction": "rtl"},
    }
)

# ── Section: Run Log ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-title" style="margin-top:18px">יומן ריצות</div>', unsafe_allow_html=True)

if len(run_log) == 0:
    st.markdown('<div class="info-notice">יומן ריצות יופיע לאחר הריצה הראשונה.</div>', unsafe_allow_html=True)
else:
    cols_to_show = ["timestamp", "status", "pages_scraped", "total_listings", "new_listings",
                    "removed_listings", "price_cuts", "price_rises", "avg_cut_pct",
                    "avg_price", "avg_price_per_sqm", "absorption_rate", "survival_30d", "avg_dom", "error"]
    cols_present = [c for c in cols_to_show if c in run_log.columns]
    display_log  = run_log[cols_present].copy()
    display_log["run_date"]  = display_log["timestamp"].dt.strftime("%Y-%m-%d")
    display_log["timestamp"] = display_log["timestamp"].dt.strftime("%d/%m/%Y %H:%M")
    _heb_log_cols = {
        "timestamp":         "תאריך ושעה",
        "status":            "סטטוס",
        "pages_scraped":     "עמודים שנסרקו",
        "total_listings":    'סה"כ מודעות',
        "new_listings":      "מודעות חדשות",
        "removed_listings":  "מודעות שהוסרו",
        "price_cuts":        "הורדות מחיר",
        "price_rises":       "עליות מחיר",
        "avg_cut_pct":       "% הורדה ממוצעת",
        "avg_price":         "מחיר ממוצע",
        "avg_price_per_sqm": 'מחיר ממוצע למ"ר',
        "absorption_rate":   "קצב ספיגה",
        "survival_30d":      "שורדות 30 יום",
        "avg_dom":           "ימים בשוק (ממוצע)",
        "error":             "שגיאה",
    }
    display_log = display_log.rename(columns=_heb_log_cols)

    rl_gb = GridOptionsBuilder.from_dataframe(display_log)
    rl_gb.configure_default_column(filter=False, sortable=True, resizable=True,
                                   minWidth=130, flex=1,
                                   wrapHeaderText=True, autoHeaderHeight=True)
    rl_gb.configure_column("run_date", hide=True)
    rl_gb.configure_selection(selection_mode="single", use_checkbox=False)
    rl_gb.configure_grid_options(enableRtl=True, rowHeight=36, headerHeight=64,
                                 suppressMenuHide=True, rowSelection="single")
    rl_grid_options = rl_gb.build()

    rl_resp = AgGrid(
        display_log,
        gridOptions=rl_grid_options,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        allow_unsafe_jscode=True,
        enable_enterprise_modules=False,
        height=min(420, 60 + len(display_log) * 36),
        theme="alpine",
        fit_columns_on_grid_load=True,
    )

    # ── New / Removed listings for selected run ──────────────────────────────
    sel = rl_resp.get("selected_rows")
    sel_date = None
    if isinstance(sel, pd.DataFrame) and not sel.empty:
        sel_date = str(sel.iloc[0].get("run_date", "")) or None
    elif isinstance(sel, list) and len(sel) > 0:
        sel_date = sel[0].get("run_date") or None

    if not sel_date:
        st.markdown('<div class="info-notice">בחר/י שורה ביומן כדי לראות אילו מודעות חדשות ואילו הוסרו באותו יום.</div>',
                    unsafe_allow_html=True)
    else:
        first_seen_map = load_first_seen_map()
        dom_log_df     = load_dom_log()

        def _nb_from_info(info):
            parts = str(info).split(",")
            return parts[1].strip() if len(parts) > 1 else ""
        def _type_from_info(info):
            parts = str(info).split(",")
            return parts[0].strip() if parts else ""

        # Build a URL → details map (active listings + historical removed listings)
        details = {}
        for _, r in df.iterrows():
            u = r.get("url") or ""
            if u:
                details[u] = {
                    "price":        r.get("price", ""),
                    "neighborhood": r.get("neighborhood", "") or _nb_from_info(r.get("info", "")),
                    "size_sqm":     r.get("size_sqm", ""),
                    "apt_type":     r.get("apt_type", "") or _type_from_info(r.get("info", "")),
                    "rooms":        r.get("rooms", ""),
                    "floor":        r.get("floor", ""),
                }
        if not dom_log_df.empty:
            for _, r in dom_log_df.iterrows():
                u = r.get("url") or ""
                if u and u not in details:
                    details[u] = {
                        "price":        r.get("price", ""),
                        "neighborhood": r.get("neighborhood", ""),
                        "size_sqm":     r.get("size_sqm", ""),
                        "apt_type":     r.get("apt_type", ""),
                        "rooms":        "",
                        "floor":        "",
                    }

        new_urls_for_date = [u for u, d in first_seen_map.items() if d == sel_date]
        new_rows = []
        for u in new_urls_for_date:
            d = details.get(u, {})
            new_rows.append({
                "מחיר":   d.get("price", ""),
                "שכונה":  d.get("neighborhood", ""),
                "סוג":    d.get("apt_type", ""),
                "חדרים":  d.get("rooms", ""),
                "קומה":   d.get("floor", ""),
                "מ״ר":    d.get("size_sqm", ""),
                "קישור":  u,
            })
        new_tbl = pd.DataFrame(new_rows)

        if not dom_log_df.empty:
            rem_for_date = dom_log_df[dom_log_df["removed_date"] == sel_date].copy()
        else:
            rem_for_date = pd.DataFrame()
        rem_rows = []
        for _, r in rem_for_date.iterrows():
            rem_rows.append({
                "מחיר":         r.get("price", ""),
                "שכונה":        r.get("neighborhood", ""),
                "סוג":          r.get("apt_type", ""),
                "מ״ר":          r.get("size_sqm", ""),
                "ימים בשוק":    r.get("dom_days", ""),
                "מעקב ראשון":   r.get("first_seen", ""),
                "קישור":        r.get("url", ""),
            })
        rem_tbl = pd.DataFrame(rem_rows)

        st.markdown(
            f'<div class="info-notice">מציג מודעות חדשות והוסרו לתאריך <b>{sel_date}</b> '
            f'(נתונים ברזולוציית יום — אם היו מספר ריצות באותו יום, הרשימה משותפת).</div>',
            unsafe_allow_html=True
        )

        col_new, col_rem = st.columns(2)
        with col_new:
            st.markdown(f'<div class="section-title">🟢 חדשות ({len(new_tbl)})</div>', unsafe_allow_html=True)
            if new_tbl.empty:
                st.markdown('<div class="info-notice">אין מודעות חדשות לתאריך זה.</div>', unsafe_allow_html=True)
            else:
                st.dataframe(new_tbl, use_container_width=True, hide_index=True,
                             height=min(420, 40 + len(new_tbl) * 32),
                             column_config={"קישור": st.column_config.LinkColumn("קישור", display_text="פתח")})
        with col_rem:
            st.markdown(f'<div class="section-title">🔴 הוסרו ({len(rem_tbl)})</div>', unsafe_allow_html=True)
            if rem_tbl.empty:
                st.markdown('<div class="info-notice">אין מודעות שהוסרו לתאריך זה.</div>', unsafe_allow_html=True)
            else:
                st.dataframe(rem_tbl, use_container_width=True, hide_index=True,
                             height=min(420, 40 + len(rem_tbl) * 32),
                             column_config={"קישור": st.column_config.LinkColumn("קישור", display_text="פתח")})

st.markdown("""
<div style="text-align:center;padding:28px 0 18px;margin-top:24px;border-top:1px solid #e2e8f0;color:#94a3b8;font-size:0.74rem;font-weight:500;">
    מעקב שוק יד2 · רעננה · מתעדכן 08:00 ו-20:00
</div>
""", unsafe_allow_html=True)
