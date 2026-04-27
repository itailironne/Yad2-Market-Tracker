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
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Inter", "Helvetica Neue", sans-serif;
    -webkit-font-smoothing: antialiased;
}
#MainMenu, footer, header { visibility: hidden; }
.stApp { background: #f5f5f7; }

[data-testid="stSidebar"] { background: #fbfbfd !important; border-right: 1px solid rgba(0,0,0,0.06) !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stSlider label {
    color: #aeaeb2 !important; font-size: 0.7rem !important; font-weight: 600 !important;
    text-transform: uppercase !important; letter-spacing: 0.09em !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: #f2f2f7 !important; border: none !important; border-radius: 10px !important;
    color: #1d1d1f !important; font-size: 0.88rem !important;
}

.sidebar-brand { padding: 24px 0 28px; border-bottom: 1px solid rgba(0,0,0,0.06); margin-bottom: 24px; }
.sidebar-brand .brand-mark {
    width: 44px; height: 44px; background: #0071e3; border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    margin: 0 auto 12px; box-shadow: 0 4px 12px rgba(0,113,227,0.3);
}
.sidebar-brand .brand-mark svg { width: 22px; height: 22px; fill: #fff; }
.sidebar-brand h3 { color: #1d1d1f; font-size: 0.92rem; font-weight: 600; text-align: center; margin: 0; }
.sidebar-brand p  { color: #aeaeb2; font-size: 0.72rem; text-align: center; margin: 3px 0 0; }

.sidebar-status { background: #f2f2f7; border-radius: 12px; padding: 14px 16px; margin-top: 8px; }
.sidebar-status .status-live { display: flex; align-items: center; gap: 7px; color: #1d1d1f; font-size: 0.8rem; font-weight: 500; margin-bottom: 8px; }
.sidebar-status .live-dot { width: 7px; height: 7px; border-radius: 50%; background: #34c759; box-shadow: 0 0 0 2px rgba(52,199,89,0.25); animation: blink 2s infinite; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.4} }
.sidebar-status .stat-row { color: #6e6e73; font-size: 0.77rem; margin-top: 3px; }
.sidebar-status .delta-pills { display: flex; gap: 6px; margin-top: 10px; flex-wrap: wrap; }
.sidebar-status .dpill { padding: 3px 9px; border-radius: 20px; font-size: 0.72rem; font-weight: 600; }
.sidebar-status .dpill.green { background: #d1f5db; color: #1a7f3c; }
.sidebar-status .dpill.red   { background: #ffd6d6; color: #c0392b; }
.sidebar-status .dpill.yel   { background: #fff3cc; color: #976800; }

.page-header { padding: 36px 0 28px; border-bottom: 1px solid rgba(0,0,0,0.06); margin-bottom: 32px; }
.page-header .eyebrow { color: #0071e3; font-size: 0.72rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 8px; }
.page-header h1 { color: #1d1d1f; font-size: 2.4rem; font-weight: 700; letter-spacing: -0.03em; margin: 0 0 8px; line-height: 1.15; }
.page-header .sub { color: #6e6e73; font-size: 0.95rem; }
.page-header .sub b { color: #1d1d1f; font-weight: 600; }

.kpi-strip { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 40px; }
.kpi { background: #fff; border-radius: 18px; padding: 22px 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06), 0 0 1px rgba(0,0,0,0.04); transition: box-shadow 0.2s, transform 0.2s; }
.kpi:hover { box-shadow: 0 8px 24px rgba(0,0,0,0.1), 0 0 1px rgba(0,0,0,0.04); transform: translateY(-2px); }
.kpi .kpi-label { color: #aeaeb2; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 10px; }
.kpi .kpi-value { font-size: 1.8rem; font-weight: 700; letter-spacing: -0.02em; color: #1d1d1f; line-height: 1; }
.kpi .kpi-value.blue   { color: #0071e3; }
.kpi .kpi-value.green  { color: #34c759; }
.kpi .kpi-value.orange { color: #ff9500; }
.kpi .kpi-value.red    { color: #ff3b30; }
.kpi .kpi-value.purple { color: #af52de; }
.kpi .kpi-sub { color: #aeaeb2; font-size: 0.78rem; margin-top: 6px; }

.section-label { color: #aeaeb2; font-size: 0.76rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.12em; margin: 44px 0 16px; display: flex; align-items: center; gap: 12px; }
.section-label::after { content: ''; flex: 1; height: 1px; background: rgba(0,0,0,0.06); }
.section-title { color: #1d1d1f; font-size: 1.6rem; font-weight: 700; letter-spacing: -0.02em; margin: 0 0 4px; }
.section-desc { color: #6e6e73; font-size: 0.82rem; margin: 0 0 20px; }

.card { background: #fff; border-radius: 20px; padding: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.06), 0 0 1px rgba(0,0,0,0.04); height: 100%; }
.card-title { color: #1d1d1f; font-size: 1rem; font-weight: 600; letter-spacing: -0.01em; margin: 0 0 3px; }
.card-desc { color: #aeaeb2; font-size: 0.82rem; margin: 0 0 16px; }

.delta-row { display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; margin-bottom: 24px; }
.delta-tile { background: #fff; border-radius: 18px; padding: 20px 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.06), 0 0 1px rgba(0,0,0,0.04); }
.delta-tile .d-label { color: #aeaeb2; font-size: 0.68rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 10px; }
.delta-tile .d-value { font-size: 2rem; font-weight: 700; letter-spacing: -0.02em; line-height: 1; }
.delta-tile .d-value.green  { color: #34c759; }
.delta-tile .d-value.red    { color: #ff3b30; }
.delta-tile .d-value.orange { color: #ff9500; }
.delta-tile .d-value.blue   { color: #0071e3; }
.delta-tile .d-sub { color: #aeaeb2; font-size: 0.73rem; margin-top: 6px; }

.info-notice { background: #f0f7ff; border: 1px solid rgba(0,113,227,0.2); border-radius: 12px; padding: 12px 16px; color: #0071e3; font-size: 0.82rem; margin-bottom: 16px; }
.filter-hint  { background: #f9f9fb; border: 1px solid rgba(0,0,0,0.06); border-radius: 10px; padding: 9px 14px; color: #8e8e93; font-size: 0.76rem; margin-top: 8px; }

.chg-tbl { width:100%; border-collapse:collapse; font-size:0.83rem; direction:rtl; }
.chg-tbl th { background:#fbfbfd; color:#aeaeb2; font-weight:600; font-size:0.67rem; text-transform:uppercase; letter-spacing:0.1em; padding:12px 16px; text-align:right; border-bottom:1px solid rgba(0,0,0,0.06); }
.chg-tbl td { padding:11px 16px; color:#1d1d1f; border-bottom:1px solid rgba(0,0,0,0.04); vertical-align:middle; }
.chg-tbl tr:hover td { background:#f5f5f7; }
.chg-tbl tr:last-child td { border-bottom:none; }
.up   { color:#ff3b30; font-weight:600; }
.down { color:#34c759; font-weight:600; }
.open-btn { display:inline-block; padding:5px 13px; background:#f2f2f7; border-radius:8px; color:#0071e3; text-decoration:none; font-size:0.76rem; font-weight:600; white-space:nowrap; }

[data-testid="stHorizontalBlock"] { gap: 14px; }
div[data-testid="column"] { padding: 0 !important; }
.stTabs [data-baseweb="tab-list"] { background: #f2f2f7 !important; border-radius: 10px !important; padding: 3px !important; gap: 2px !important; border: none !important; }
.stTabs [data-baseweb="tab"] { background: transparent !important; border-radius: 8px !important; color: #6e6e73 !important; font-size: 0.82rem !important; font-weight: 500 !important; padding: 6px 14px !important; border: none !important; }
.stTabs [aria-selected="true"] { background: #fff !important; color: #1d1d1f !important; font-weight: 600 !important; box-shadow: 0 1px 4px rgba(0,0,0,0.1) !important; }
.stTabs [data-baseweb="tab-panel"] { padding: 20px 0 0 !important; }
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #d1d1d6; border-radius: 2px; }
</style>
""", unsafe_allow_html=True)

# ── Theme colours ────────────────────────────────────────────────────────────────
CYAN   = "#0071e3"
GREEN  = "#34c759"
RED    = "#ff3b30"
YELLOW = "#ff9500"
PURPLE = "#af52de"

def _chart(fig, height=280):
    fig.update_layout(
        paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
        font=dict(family="-apple-system, BlinkMacSystemFont, 'Inter', sans-serif", color="#aeaeb2", size=11),
        height=height,
        margin=dict(t=10, b=10, l=8, r=8),
        dragmode=False,
        xaxis=dict(gridcolor="rgba(0,0,0,0.04)", zerolinecolor="rgba(0,0,0,0.04)",
                   tickfont=dict(color="#aeaeb2", size=11), showline=False,
                   tickformat="%d/%m", dtick=86400000, fixedrange=True),
        yaxis=dict(gridcolor="rgba(0,0,0,0.04)", zerolinecolor="rgba(0,0,0,0.04)",
                   tickfont=dict(color="#aeaeb2", size=11), showline=False, fixedrange=True),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)", font=dict(color="#6e6e73", size=11)),
        hoverlabel=dict(bgcolor="#1d1d1f", bordercolor="#1d1d1f", font=dict(color="#f5f5f7", size=12)),
        showlegend=False,
    )
    return fig

def _daily(x, y, agg="last"):
    """Collapse multiple same-day points into one (takes last value by default)."""
    tmp = pd.DataFrame({"x": pd.to_datetime(x).dt.normalize(), "y": pd.to_numeric(y, errors="coerce")}).dropna()
    if tmp.empty:
        return x, y
    res = tmp.groupby("x")["y"].last() if agg == "last" else tmp.groupby("x")["y"].mean().round()
    return res.index, res.values

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

    def _resolve_date(row):
        dp  = row.get("date_posted") or ""
        url = row.get("url") or ""
        return dp or first_seen.get(url, "") or first_seen.get(url.split("?")[0], "")

    def _first_seen_earliest(row):
        lid = _lid(row.get("url") or "")
        if not lid:
            return ""
        dates = [v for k, v in first_seen.items() if lid in k]
        return min(dates) if dates else ""

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
    prev_map  = {r["url"]: r for r in prev_list if r.get("url")}
    curr_map  = {r["url"]: r for r in curr_list if r.get("url")}
    new_rows, rem_rows, price_rows = [], [], []
    for u in set(curr_map) - set(prev_map): new_rows.append(curr_map[u])
    for u in set(prev_map) - set(curr_map): rem_rows.append(prev_map[u])
    for u in set(prev_map) & set(curr_map):
        pp = parse_price_num(prev_map[u].get("price", ""))
        cp = parse_price_num(curr_map[u].get("price", ""))
        if pp and cp and pp != cp:
            row = dict(curr_map[u])
            row.update({"price_num": cp, "prev_price_num": pp,
                        "prev_price": prev_map[u].get("price", ""),
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

# ── Sidebar ──────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
        <div class="brand-mark">
            <svg viewBox="0 0 24 24"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
        </div>
        <h3>יד2 שוק</h3>
        <p>רעננה · 4 חדרים</p>
    </div>
    """, unsafe_allow_html=True)

    price_min, price_max = int(df["price_num"].min()), int(df["price_num"].max())
    price_range = st.slider("טווח מחיר (₪)", price_min, price_max, (price_min, price_max), step=50000, format="%d")

    size_min, size_max = int(df["size_sqm"].dropna().min()), int(df["size_sqm"].dropna().max())
    size_range = st.slider("גודל (מ״ר)", size_min, size_max, (size_min, size_max))

    apt_types = sorted([t for t in df["apt_type"].dropna().unique() if t])
    sel_type  = st.selectbox("סוג נכס", ["הכל"] + apt_types)

    rooms_opts = sorted(df["rooms"].dropna().unique().astype(int).tolist())
    sel_rooms  = st.selectbox("חדרים", ["הכל"] + [str(r) for r in rooms_opts])

    floors_opts = sorted(df["floor"].dropna().unique().astype(int).tolist())
    sel_floor   = st.selectbox("קומה", ["הכל"] + [str(f) for f in floors_opts])

    nbs    = sorted([n for n in df["neighborhood"].dropna().unique().tolist() if n])
    sel_nb = st.selectbox("שכונה", ["הכל"] + nbs)

    n_new = len(new_df); n_rem = len(rem_df); n_chg = len(price_df)
    st.markdown(f"""
    <div class="sidebar-status">
        <div class="status-live"><div class="live-dot"></div>עודכן {mod_time}</div>
        <div class="stat-row">{len(df):,} מודעות פעילות</div>
        <div class="delta-pills">
            <span class="dpill green">+{n_new} חדשות</span>
            <span class="dpill red">-{n_rem} הוסרו</span>
            <span class="dpill yel">{n_chg} שינויי מחיר</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── Apply sidebar filters ────────────────────────────────────────────────────────
size_filled = df["size_sqm"].fillna(size_range[0])
mask = (
    (df["price_num"] >= price_range[0]) & (df["price_num"] <= price_range[1]) &
    (size_filled >= size_range[0])      & (size_filled <= size_range[1])
)
if sel_type  != "הכל": mask &= df["apt_type"]     == sel_type
if sel_nb    != "הכל": mask &= df["neighborhood"] == sel_nb
if sel_rooms != "הכל": mask &= df["rooms"]        == int(sel_rooms)
if sel_floor != "הכל": mask &= df["floor"]        == int(sel_floor)
fdf = df[mask].copy()

# ── Page header ──────────────────────────────────────────────────────────────────
avg_p   = int(fdf["price_num"].mean())    if len(fdf) else 0
med_p   = int(fdf["price_num"].median())  if len(fdf) else 0
min_p   = int(fdf["price_num"].min())     if len(fdf) else 0
avg_sqm = fdf["size_sqm"].dropna().mean() if len(fdf) else 0
ppsqm   = int(avg_p / avg_sqm)            if avg_sqm else 0

st.markdown(f"""
<div class="page-header">
    <div class="eyebrow">ניתוח נדל"ן</div>
    <h1>סקירת שוק רעננה</h1>
    <div class="sub">
        <b>{len(fdf):,}</b> מודעות מוצגות &nbsp;&middot;&nbsp; עודכן <b>{mod_time}</b>
    </div>
</div>
""", unsafe_allow_html=True)

# ── KPI strip ────────────────────────────────────────────────────────────────────
def fmt(n): return f"₪{n:,}" if n else "—"

st.markdown(f"""
<div class="kpi-strip">
    <div class="kpi">
        <div class="kpi-label">מודעות</div>
        <div class="kpi-value blue">{len(fdf):,}</div>
        <div class="kpi-sub">תוצאות מסוננות</div>
    </div>
    <div class="kpi">
        <div class="kpi-label">מחיר ממוצע</div>
        <div class="kpi-value green">{fmt(avg_p)}</div>
        <div class="kpi-sub">ממוצע מחירי מכירה</div>
    </div>
    <div class="kpi">
        <div class="kpi-label">מחיר חציוני</div>
        <div class="kpi-value">{fmt(med_p)}</div>
        <div class="kpi-sub">אמצע השוק</div>
    </div>
    <div class="kpi">
        <div class="kpi-label">מחיר מינימום</div>
        <div class="kpi-value orange">{fmt(min_p)}</div>
        <div class="kpi-sub">המחיר הנמוך ביותר</div>
    </div>
    <div class="kpi">
        <div class="kpi-label">מחיר למ״ר</div>
        <div class="kpi-value purple">{fmt(ppsqm)}</div>
        <div class="kpi-sub">ממוצע למטר רבוע</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Section: Charts ──────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">גרפים</div>', unsafe_allow_html=True)
st.markdown('<div class="section-title">מגמות שוק לאורך זמן</div>', unsafe_allow_html=True)

if len(history) == 0:
    st.markdown('<div class="info-notice">גרפים יופיעו לאחר מספר ריצות של ה-Scraper.</div>', unsafe_allow_html=True)
else:
    # Decide data source based on active filters
    using_nb   = sel_nb   != "הכל" and len(nb_hist)   > 0
    using_type = sel_type != "הכל" and len(type_hist) > 0

    if using_nb and using_type:
        # Both filters: neighbourhood takes priority for qty; type for price
        src_nb   = nb_hist[nb_hist["neighborhood"] == sel_nb].sort_values("date")
        src_type = type_hist[type_hist["apt_type"]  == sel_type].sort_values("date")
        qty_x,   qty_y   = src_nb["date"],   src_nb["count"]
        price_x, price_y = src_type["date"], src_type["avg_price_per_sqm"]
        scope_label = f"{sel_nb} · {sel_type}"
    elif using_nb:
        src = nb_hist[nb_hist["neighborhood"] == sel_nb].sort_values("date")
        qty_x, qty_y     = src["date"], src["count"]
        price_x, price_y = src["date"], src["avg_price_per_sqm"]
        scope_label = sel_nb
    elif using_type:
        src = type_hist[type_hist["apt_type"] == sel_type].sort_values("date")
        qty_x, qty_y     = src["date"], src["count"]
        price_x, price_y = src["date"], src["avg_price_per_sqm"]
        scope_label = sel_type
    else:
        qty_x, qty_y     = history["date"], history["כמות"]
        price_x, price_y = history["date"], history["avg_price_per_sqm"]
        scope_label = "כל השוק"

    active_filters = [f for f in [sel_nb if using_nb else "", sel_type if using_type else ""] if f]
    if active_filters:
        hint = "הגרפים מסוננים לפי: " + " · ".join(active_filters)
    else:
        hint = "פילטרי שכונה וסוג נכס משפיעים על הגרפים · פילטרים אחרים (מחיר, גודל, קומה) משפיעים על הטבלה בלבד"
    st.markdown(f'<div class="filter-hint">{hint}</div>', unsafe_allow_html=True)

    gc1, gc2 = st.columns(2, gap="medium")

    # ── Chart 1: Listing quantity over time ──────────────────────────────────────
    with gc1:
        st.markdown(f'<div class="card"><div class="card-title">כמות מודעות לאורך זמן</div><div class="card-desc">{scope_label}</div>', unsafe_allow_html=True)
        qty_color = CYAN
        fig_qty = go.Figure()
        _qx, _qy = _daily(qty_x, qty_y)
        fig_qty.add_trace(go.Scatter(
            x=_qx, y=_qy,
            mode="lines+markers",
            line=dict(color=qty_color, width=2.5),
            marker=dict(size=6, color=qty_color, line=dict(color="#fff", width=1.5)),
            fill="tozeroy", fillcolor="rgba(0,113,227,0.05)",
            hovertemplate="<b>%{x|%d/%m/%y}</b><br>%{y} מודעות<extra></extra>"
        ))
        _chart(fig_qty, 260)
        fig_qty.update_layout(yaxis_title="מודעות")
        st.plotly_chart(fig_qty, use_container_width=True, config=dict(displayModeBar=False, scrollZoom=False))
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Chart 2: Avg price per sqm over time ─────────────────────────────────────
    with gc2:
        st.markdown(f'<div class="card"><div class="card-title">מחיר ממוצע למ״ר לאורך זמן</div><div class="card-desc">{scope_label} — עולה/יורד = התייקרות/הוזלה</div>', unsafe_allow_html=True)
        if len(price_y.dropna()) >= 2:
            trend_up = float(price_y.dropna().iloc[-1]) >= float(price_y.dropna().iloc[0])
            p_color = RED if trend_up else GREEN
            fill_col = "rgba(255,59,48,0.05)" if trend_up else "rgba(52,199,89,0.05)"
        else:
            p_color, fill_col = CYAN, "rgba(0,113,227,0.05)"
        fig_price = go.Figure()
        _px, _py = _daily(price_x, price_y, agg="mean")
        fig_price.add_trace(go.Scatter(
            x=_px, y=_py,
            mode="lines+markers",
            line=dict(color=p_color, width=2.5),
            marker=dict(size=6, color=p_color, line=dict(color="#fff", width=1.5)),
            fill="tozeroy", fillcolor=fill_col,
            hovertemplate="<b>%{x|%d/%m/%y}</b><br>₪%{y:,.0f}/מ״ר<extra></extra>"
        ))
        _chart(fig_price, 260)
        fig_price.update_layout(yaxis_title="₪/מ״ר", yaxis_tickformat=",d")
        st.plotly_chart(fig_price, use_container_width=True, config=dict(displayModeBar=False, scrollZoom=False))
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Chart 3: Price cuts per run (market-wide only) ───────────────────────────
    if "price_cuts" in history.columns and "price_rises" in history.columns:
        st.markdown('<div style="margin-top:14px"></div>', unsafe_allow_html=True)
        gc3, gc4 = st.columns(2, gap="medium")
        with gc3:
            st.markdown('<div class="card"><div class="card-title">הורדות / עליות מחיר לאורך זמן</div><div class="card-desc">כל עדכון — כמה מודעות שינו מחיר · כל השוק</div>', unsafe_allow_html=True)
            fig_cuts = go.Figure()
            _cx, _cuts = _daily(history["date"], history["price_cuts"], agg="last")
            _cx2, _rises = _daily(history["date"], history["price_rises"], agg="last")
            fig_cuts.add_trace(go.Bar(
                x=_cx, y=_cuts, name="הורדות",
                marker=dict(color=GREEN, opacity=0.85),
                hovertemplate="%{x|%d/%m/%y}<br>%{y} הורדות<extra></extra>"
            ))
            fig_cuts.add_trace(go.Bar(
                x=_cx2, y=_rises, name="עליות",
                marker=dict(color=RED, opacity=0.85),
                hovertemplate="%{x|%d/%m/%y}<br>%{y} עליות<extra></extra>"
            ))
            _chart(fig_cuts, 240)
            fig_cuts.update_layout(barmode="group", bargap=0.25, bargroupgap=0.05,
                                   yaxis_title="מודעות", showlegend=True,
                                   legend=dict(orientation="h", y=1.08, x=0))
            st.plotly_chart(fig_cuts, use_container_width=True, config=dict(displayModeBar=False, scrollZoom=False))
            st.markdown('</div>', unsafe_allow_html=True)

        with gc4:
            if "avg_cut_pct" in history.columns:
                st.markdown('<div class="card"><div class="card-title">עומק הורדת המחיר הממוצעת</div><div class="card-desc">% ממוצע של ירידת מחיר כשמוכרים מורידים · כל השוק</div>', unsafe_allow_html=True)
                cut_data = history.dropna(subset=["avg_cut_pct"])
                if len(cut_data):
                    _dx, _dy = _daily(cut_data["date"], cut_data["avg_cut_pct"], agg="mean")
                    fig_depth = go.Figure(go.Scatter(
                        x=_dx, y=_dy,
                        mode="lines+markers",
                        line=dict(color=YELLOW, width=2.5),
                        marker=dict(size=6, color=YELLOW, line=dict(color="#fff", width=1.5)),
                        fill="tozeroy", fillcolor="rgba(255,149,0,0.06)",
                        hovertemplate="<b>%{x|%d/%m/%y}</b><br>%{y:.2f}%<extra></extra>"
                    ))
                    _chart(fig_depth, 240)
                    fig_depth.update_layout(yaxis_title="%")
                    st.plotly_chart(fig_depth, use_container_width=True, config=dict(displayModeBar=False, scrollZoom=False))
                else:
                    st.markdown('<p style="color:#aeaeb2;padding:24px 0;">זמין לאחר זיהוי הורדות מחיר.</p>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

# ── Section: Changes ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">פעילות</div>', unsafe_allow_html=True)
st.markdown('<div class="section-title">מה השתנה מאז העדכון הקודם</div>', unsafe_allow_html=True)

if chg[0] is None:
    st.markdown('<div class="info-notice">נדרשות לפחות 2 ריצות לזיהוי שינויים.</div>', unsafe_allow_html=True)
else:
    cuts_n  = len(price_df[price_df["delta"] < 0]) if len(price_df) else 0
    rises_n = len(price_df[price_df["delta"] > 0]) if len(price_df) else 0
    st.markdown(f"""
    <div class="delta-row">
        <div class="delta-tile"><div class="d-label">מודעות חדשות</div><div class="d-value green">+{len(new_df)}</div><div class="d-sub">מאז {prev_time}</div></div>
        <div class="delta-tile"><div class="d-label">הוסרו / נמכרו</div><div class="d-value red">-{len(rem_df)}</div><div class="d-sub">יצאו מהשוק</div></div>
        <div class="delta-tile"><div class="d-label">הורדות מחיר</div><div class="d-value green">{cuts_n}</div><div class="d-sub">מחיר הופחת</div></div>
        <div class="delta-tile"><div class="d-label">עליות מחיר</div><div class="d-value red">{rises_n}</div><div class="d-sub">מחיר עלה</div></div>
    </div>
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

# ── Section: Full Table with Excel column filters (AgGrid) ───────────────────────
st.markdown('<div class="section-label">כל המודעות</div>', unsafe_allow_html=True)
st.markdown(f'<div class="section-title">{len(fdf):,} מודעות</div>', unsafe_allow_html=True)

# Build display dataframe
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

# Configure AgGrid — Excel-style: filter ▼ button on each column header
gb = GridOptionsBuilder.from_dataframe(tbl_df)
gb.configure_default_column(
    filter=True,
    sortable=True,
    resizable=True,
    floatingFilter=False,       # no second row — filter opens from the header button
    suppressMenu=False,
    menuTabs=["filterMenuTab"],  # clicking header icon goes straight to the filter panel
)
# Numeric columns → range/comparison filter
for col in ["מחיר (₪)", "שטח (מ״ר)", "חדרים", "קומה", "ימים בשוק"]:
    gb.configure_column(col, type=["numericColumn"], filter="agNumberColumnFilter",
                        menuTabs=["filterMenuTab"])
gb.configure_column("מחיר (₪)", valueFormatter="value ? '₪' + value.toLocaleString() : ''")
# Categorical columns → checkbox list exactly like Excel, values from FULL dataset
all_neighborhoods = sorted(df["neighborhood"].dropna().unique().tolist())
all_types         = sorted(df["apt_type"].dropna().unique().tolist())
gb.configure_column("שכונה", filter="agSetColumnFilter", menuTabs=["filterMenuTab"],
                    filterParams={"values": all_neighborhoods})
gb.configure_column("סוג",   filter="agSetColumnFilter", menuTabs=["filterMenuTab"],
                    filterParams={"values": all_types})
# Text columns → contains/starts-with
gb.configure_column("רחוב",        filter="agTextColumnFilter")
gb.configure_column("תאריך יד2",  filter="agTextColumnFilter")
gb.configure_column("מעקב ראשון", filter="agTextColumnFilter")
# Link column — no filter, render as clickable link
gb.configure_column("קישור",
    cellRenderer=JsCode("""
        class UrlRenderer {
            init(p) {
                this.gui = document.createElement('a');
                this.gui.href = p.value || '#';
                this.gui.target = '_blank';
                this.gui.innerText = 'פתח';
                this.gui.style.cssText = 'color:#0071e3;font-weight:600;text-decoration:none;';
            }
            getGui() { return this.gui; }
        }
    """),
    filter=False, sortable=False, width=80,
)
gb.configure_grid_options(
    enableRtl=True,
    rowHeight=40,
    headerHeight=46,
    suppressRowClickSelection=True,
    domLayout="normal",
    suppressMenuHide=True,      # always show the ▼ filter button on every column header
)
grid_options = gb.build()

AgGrid(
    tbl_df,
    gridOptions=grid_options,
    update_mode=GridUpdateMode.NO_UPDATE,
    allow_unsafe_jscode=True,
    enable_enterprise_modules=False,
    height=600,
    theme="alpine",
    fit_columns_on_grid_load=False,
    custom_css={
        ".ag-header-cell-menu-button": {
            "opacity": "1 !important",
            "color": "#555",
        },
        ".ag-header-cell-menu-button:hover": {
            "color": "#0071e3 !important",
        },
        ".ag-header-cell-label": {
            "font-weight": "600",
            "font-size": "0.82rem",
        },
        ".ag-row": {"font-size": "0.88rem"},
        ".ag-set-filter-list": {"direction": "rtl"},
    }
)

# ── Section: Run Log ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Run Log</div>', unsafe_allow_html=True)
st.markdown('<div class="section-title">יומן ריצות</div>', unsafe_allow_html=True)

if len(run_log) == 0:
    st.markdown('<div class="info-notice">יומן ריצות יופיע לאחר הריצה הראשונה.</div>', unsafe_allow_html=True)
else:
    cols_to_show = ["timestamp", "status", "pages_scraped", "total_listings", "new_listings",
                    "removed_listings", "price_cuts", "price_rises", "avg_cut_pct",
                    "avg_price", "avg_price_per_sqm", "absorption_rate", "survival_30d", "avg_dom", "error"]
    cols_present = [c for c in cols_to_show if c in run_log.columns]
    display_log  = run_log[cols_present].copy()
    display_log["timestamp"] = display_log["timestamp"].dt.strftime("%d/%m/%Y %H:%M")
    st.dataframe(display_log, use_container_width=True, hide_index=True,
                 height=min(400, 40 + len(display_log) * 35))

st.markdown("""
<div style="text-align:center;padding:40px 0 20px;color:#d1d1d6;font-size:0.72rem;letter-spacing:0.04em;">
    מעקב שוק יד2 &nbsp;&middot;&nbsp; רעננה &nbsp;&middot;&nbsp; מתעדכן אוטומטית 08:00 ו-20:00
</div>
""", unsafe_allow_html=True)
