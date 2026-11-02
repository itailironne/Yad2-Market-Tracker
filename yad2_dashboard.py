import streamlit as st
import streamlit.components.v1 as components
import numpy as np
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
/* ═══════════════════════════════════════════════════════════════════════════
   Anthropic / Claude.com design system, adapted for a Hebrew RTL data surface.

   TYPEFACE SUBSTITUTION (deliberate, documented):
   The source system specifies Copernicus/Tiempos serif for display and
   StyreneB/Inter for body. None of those — nor the documented open-source
   substitutes (Cormorant Garamond, EB Garamond) — contain Hebrew glyphs, and
   this dashboard is Hebrew-first. Rendering it in them would silently fall back
   per-glyph and destroy the type system it is meant to express.
   So we preserve the SPLIT (editorial serif display + humanist sans body),
   which is the actual brand voice, using Hebrew-capable faces:
     display -> Frank Ruhl Libre  (Hebrew editorial serif, weight 400, negative
                tracking — the closest Hebrew analogue to Copernicus)
     body    -> Assistant         (humanist Hebrew sans, not geometric — the
                same reasoning that makes Inter an acceptable StyreneB stand-in)
     code    -> JetBrains Mono    (as specified; Latin-only is fine here)
   Latin-only text falls through to EB Garamond / Inter inside the same stacks.
   ═══════════════════════════════════════════════════════════════════════════ */
@import url('https://fonts.googleapis.com/css2?family=Frank+Ruhl+Libre:wght@300;400;500;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=EB+Garamond:wght@400;500&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    /* ── Brand & accent ── */
    --primary:            #cc785c;
    --primary-active:     #a9583e;
    --primary-disabled:   #e6dfd8;
    --accent-teal:        #5db8a6;
    --accent-amber:       #e8a55a;

    /* ── Surface ── */
    --canvas:             #faf9f5;
    --surface-soft:       #f5f0e8;
    --surface-card:       #efe9de;
    --surface-cream-strong:#e8e0d2;
    --surface-dark:       #181715;
    --surface-dark-elevated:#252320;
    --surface-dark-soft:  #1f1e1b;
    --hairline:           #e6dfd8;
    --hairline-soft:      #ebe6df;

    /* ── Text ── */
    --ink:                #141413;
    --body-strong:        #252523;
    --body:               #3d3d3a;
    --muted:              #6c6a64;
    --muted-soft:         #8e8b82;
    --on-primary:         #ffffff;
    --on-dark:            #faf9f5;
    --on-dark-soft:       #a09d96;

    /* ── Semantic ── */
    --success:            #5db872;
    --warning:            #d4a017;
    --error:              #c64545;

    /* ── Radius ── */
    --r-xs: 4px; --r-sm: 6px; --r-md: 8px; --r-lg: 12px; --r-xl: 16px; --r-pill: 9999px;

    /* ── Spacing ── */
    --s-xxs: 4px; --s-xs: 8px; --s-sm: 12px; --s-md: 16px;
    --s-lg: 24px; --s-xl: 32px; --s-xxl: 48px;

    /* ── Type stacks ── */
    --font-display: "Frank Ruhl Libre", "EB Garamond", Garamond, "Times New Roman", serif;
    --font-body:    "Assistant", "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    --font-mono:    "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
}

*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] {
    font-family: var(--font-body);
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}
#MainMenu, footer, header { visibility: hidden; }

/* Cream canvas is the brand's defining choice — flat, never a gradient, and
   never the cool gray-white every other analytics tool ships with. */
.stApp { background: var(--canvas); }

/* Move the sidebar to the RTL-conventional right side using flex `order`
   (stAppViewContainer is display:flex/row) instead of flipping `direction`.
   `direction` inherits into every descendant, including BaseWeb's Slider,
   whose thumb-position math breaks under inherited rtl (verified: thumbs
   render up to a full track-width outside the track) — Streamlit/BaseWeb
   don't officially support RTL. `order` only repositions the flex item
   itself, so it sidesteps that entirely. */
[data-testid="stAppViewContainer"] > [data-testid="stSidebar"] { order: 2; }
[data-testid="stAppViewContainer"] > section.main { order: 1; }
.block-container {
    max-width: 1700px !important;
    padding-top: 0.5rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    direction: rtl;
}
[data-testid="stVerticalBlock"] { gap: 0.3rem !important; }
.element-container { margin-bottom: 0 !important; }

/* Keep numerics/charts LTR-friendly inside RTL container */
.kpi-value, .d-value, .stPlotlyChart, .ag-root-wrapper, .stDataFrame { direction: ltr; }
.kpi-value, .d-value { text-align: right; }

/* ── Top filter bar widgets ─────────────────────────────── */
[data-testid="stSlider"] label,
[data-testid="stSelectbox"] label,
.stSlider label, .stSelectbox label {
    color: var(--muted) !important;
    font-family: var(--font-body) !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 1.5px !important;
    padding: 0 0 2px 0 !important;
    margin: 0 !important;
    line-height: 1.4 !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] > div {
    background: var(--canvas) !important;
    border: 1px solid var(--hairline) !important;
    border-radius: var(--r-md) !important;
    min-height: 40px !important;
    font-family: var(--font-body) !important;
    font-size: 14px !important;
    color: var(--ink) !important;
}
[data-testid="stSlider"] { padding-top: 16px !important; }
[data-testid="stSlider"] [data-baseweb="slider"] { padding-top: 6px !important; }
[data-testid="stSlider"] [data-baseweb="slider"] > div > div > div:last-child,
[data-testid="stSlider"] div[role="slider"] { color: var(--primary) !important; }
[data-testid="stTickBar"] { margin-top: 2px !important; }
[data-testid="stTickBarMin"], [data-testid="stTickBarMax"] {
    font-size: 12px !important; color: var(--muted-soft) !important; font-weight: 500 !important;
}
[data-testid="stSidebar"] { direction: rtl; }
[data-testid="stSidebar"] * { text-align: right; }

/* ── Sidebar: the dark product-chrome rail ────────────────
   The system's cream-to-dark contrast is its pacing mechanism. On a single-view
   dashboard there are no page bands to alternate, so the rail carries the dark
   surface and the data canvas stays cream. */
[data-testid="stSidebar"] {
    background: var(--surface-dark) !important;
    border-left: none !important;
    width: 260px !important; min-width: 260px !important;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stSlider label {
    color: var(--on-dark-soft) !important;
    font-size: 12px !important; font-weight: 500 !important;
    text-transform: uppercase !important; letter-spacing: 1.5px !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: var(--surface-dark-elevated) !important;
    border: 1px solid transparent !important;
    border-radius: var(--r-md) !important;
    color: var(--on-dark) !important; font-size: 14px !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] svg { fill: var(--on-dark-soft) !important; }

.sidebar-brand {
    padding: var(--s-lg) 0 var(--s-lg);
    border-bottom: 1px solid var(--surface-dark-elevated);
    margin-bottom: var(--s-lg);
}
/* Anthropic radial spike-mark, rendered flat — no gradient, no glow. */
.sidebar-brand .brand-mark {
    width: 40px; height: 40px;
    background: transparent;
    display: flex; align-items: center; justify-content: center;
    margin: 0 auto var(--s-sm);
}
.sidebar-brand .brand-mark svg {
    width: 26px; height: 26px;
    stroke: var(--primary); fill: none; stroke-width: 2;
    stroke-linecap: round; stroke-linejoin: round;
}
.sidebar-brand h3 {
    font-family: var(--font-display);
    color: var(--on-dark); font-size: 22px; font-weight: 400;
    text-align: center; margin: 0; letter-spacing: -0.3px;
}
.sidebar-brand p {
    font-family: var(--font-body);
    color: var(--on-dark-soft); font-size: 13px; text-align: center;
    margin: 4px 0 0; font-weight: 400;
}

.sidebar-status {
    background: var(--surface-dark-elevated);
    border: none; border-radius: var(--r-lg);
    padding: var(--s-md); margin-top: var(--s-md);
}
.sidebar-status .status-live {
    display: flex; align-items: center; gap: var(--s-xs);
    color: var(--on-dark); font-size: 14px; font-weight: 500; margin-bottom: var(--s-xs);
}
.sidebar-status .live-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--success);
}
.sidebar-status .stat-row {
    color: var(--on-dark-soft); font-size: 13px; margin-top: var(--s-xxs); font-weight: 400;
}
.sidebar-status .delta-pills { display: flex; gap: var(--s-xxs); margin-top: var(--s-sm); flex-wrap: wrap; }
.sidebar-status .dpill {
    font-size: 12px; font-weight: 500; padding: 4px 12px; border-radius: var(--r-pill);
    background: var(--surface-dark-soft); color: var(--on-dark-soft);
}
.sidebar-status .dpill.green { color: var(--success); }
.sidebar-status .dpill.red   { color: var(--error); }
.sidebar-status .dpill.yel   { color: var(--accent-amber); }

.nav-label {
    color: var(--on-dark-soft); font-size: 12px; font-weight: 500;
    text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: var(--s-xs);
}

/* ── Sidebar navigation (styled st.radio, circle hidden) ─────────────── */
[data-testid="stSidebar"] [role="radiogroup"] { gap: 2px !important; }
[data-testid="stSidebar"] [role="radiogroup"] > label {
    padding: 10px var(--s-sm) !important;
    border-radius: var(--r-md) !important;
    color: var(--on-dark-soft) !important;
    font-size: 14px !important; font-weight: 500 !important;
    cursor: pointer;
}
[data-testid="stSidebar"] [role="radiogroup"] > label > div:first-child { display: none !important; }
[data-testid="stSidebar"] [role="radiogroup"] > label[data-checked="true"],
[data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) {
    background: var(--surface-dark-elevated) !important;
    color: var(--on-dark) !important;
}

/* Room-count toggle reuses the same radio, laid out horizontally */
[data-testid="stSidebar"] [role="radiogroup"].horizontal { flex-direction: row !important; }

/* ── Compact top bar ──────────────────────────────────── */
.topbar {
    display: flex; align-items: center; justify-content: flex-start;
    gap: var(--s-sm); padding: var(--s-sm) 0 0;
}
.status-pill {
    display: inline-flex; align-items: center; gap: 6px;
    font-family: var(--font-body);
    font-size: 12px; font-weight: 500; letter-spacing: 1.5px; text-transform: uppercase;
    padding: 4px 12px; border-radius: var(--r-pill);
    background: var(--surface-card); color: var(--ink);
}
.status-pill.ok   { background: var(--surface-card);   color: var(--ink); }
.status-pill.warn { background: var(--surface-cream-strong); color: var(--body-strong); }
.status-pill.err  { background: var(--primary);        color: var(--on-primary); }

/* ── Page header ─────────────────────────────────────── */
.page-header { padding: var(--s-xl) 0 var(--s-lg); }
.page-header .eyebrow {
    font-family: var(--font-body);
    color: var(--muted); font-size: 12px; font-weight: 500;
    text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: var(--s-sm);
}
/* Display headline: serif, weight 400, negative tracking. Never bold. */
.page-header h1 {
    font-family: var(--font-display);
    color: var(--ink); font-size: 48px; font-weight: 400;
    line-height: 1.1; letter-spacing: -1px; margin: 0;
}
.page-header .sub {
    font-family: var(--font-body);
    color: var(--body); font-size: 16px; font-weight: 400;
    line-height: 1.55; margin-top: var(--s-sm);
}
.page-header .sub b { color: var(--body-strong); font-weight: 500; }

/* ── KPI strip ───────────────────────────────────────── */
.kpi-strip { display: flex; gap: var(--s-sm); flex-wrap: wrap; }
.kpi {
    flex: 1 1 180px; min-height: 132px;
    background: var(--surface-card);
    border: none; border-radius: var(--r-lg);
    padding: var(--s-lg);
    display: flex; flex-direction: column; justify-content: space-between;
}
.kpi-head { display: flex; align-items: center; justify-content: space-between; gap: var(--s-xs); }
.kpi-label {
    font-family: var(--font-body);
    color: var(--muted); font-size: 12px; font-weight: 500;
    text-transform: uppercase; letter-spacing: 1.5px;
}
.kpi-icon {
    width: 32px; height: 32px; border-radius: var(--r-md);
    display: flex; align-items: center; justify-content: center;
    font-size: 15px; background: var(--canvas); color: var(--ink);
}
/* Accent variants stay inside the documented palette — no purple, no cool blue.
   Coral is reserved for the primary metric only, so it stays scarce. */
.kpi.blue   .kpi-icon { background: var(--primary); color: var(--on-primary); }
.kpi.green  .kpi-icon { background: var(--canvas); color: var(--success); }
.kpi.gray   .kpi-icon { background: var(--canvas); color: var(--muted); }
.kpi.orange .kpi-icon { background: var(--canvas); color: var(--accent-amber); }
.kpi.purple .kpi-icon { background: var(--canvas); color: var(--accent-teal); }
/* Big numerics use the serif display face — the system sets prices in
   Copernicus, and these KPIs are the same editorial gesture. */
.kpi-value {
    font-family: var(--font-display);
    color: var(--ink); font-size: 36px; font-weight: 400;
    line-height: 1.15; letter-spacing: -0.5px; margin-top: var(--s-xs);
}
.kpi-sub {
    font-family: var(--font-body);
    color: var(--muted); font-size: 13px; font-weight: 400; margin-top: 2px;
}
.kpi-delta {
    display: inline-flex; align-items: center; gap: 4px;
    font-size: 13px; font-weight: 500; margin-top: var(--s-xs);
}
.kpi-delta.up   { color: var(--success); }
.kpi-delta.down { color: var(--error); }
.kpi-delta.flat { color: var(--muted-soft); }
.kpi-spacer { flex: 1 1 180px; }

/* ── Section labels ──────────────────────────────────── */
.section-label {
    display: flex; align-items: center; gap: var(--s-sm);
    margin: var(--s-xl) 0 var(--s-md);
}
.section-label::before,
.section-label::after { content: none; }
.section-title {
    font-family: var(--font-display);
    color: var(--ink); font-size: 28px; font-weight: 400;
    line-height: 1.2; letter-spacing: -0.3px;
}
.section-desc {
    font-family: var(--font-body);
    color: var(--muted); font-size: 14px; font-weight: 400;
}

/* ── Cards ───────────────────────────────────────────── */
/* Chart cards follow the model-comparison-card pattern: canvas fill + hairline.
   Data ink should dominate, so the card recedes rather than tinting the plot. */
.card {
    background: var(--canvas);
    border: 1px solid var(--hairline);
    border-radius: var(--r-lg);
    padding: var(--s-lg);
    margin-bottom: var(--s-sm);
}
.card-title {
    font-family: var(--font-body);
    color: var(--ink); font-size: 18px; font-weight: 500;
    line-height: 1.4; display: flex; align-items: center; gap: 6px;
}
.card-desc {
    font-family: var(--font-body);
    color: var(--muted); font-size: 14px; font-weight: 400;
    line-height: 1.55; margin-top: var(--s-xxs);
}
.card-desc::before { content: none; }
.card > .card-desc + * { margin-top: var(--s-md); }

/* ── Delta tiles ─────────────────────────────────────── */
.delta-row { display: flex; gap: var(--s-sm); flex-wrap: wrap; }
.delta-tile {
    flex: 1 1 150px;
    background: var(--surface-card);
    border: none; border-radius: var(--r-lg);
    padding: var(--s-md) var(--s-lg);
}
.delta-tile .d-label {
    font-family: var(--font-body);
    color: var(--muted); font-size: 12px; font-weight: 500;
    text-transform: uppercase; letter-spacing: 1.5px;
}
/* Flat colour, no gradient text-fill — the system is colour-block first. */
.delta-tile .d-value {
    font-family: var(--font-display);
    font-size: 28px; font-weight: 400; letter-spacing: -0.3px;
    line-height: 1.2; margin-top: var(--s-xxs);
    color: var(--ink);
    background: none; -webkit-text-fill-color: currentColor;
}
.delta-tile .d-value.green  { color: var(--success); }
.delta-tile .d-value.red    { color: var(--error); }
.delta-tile .d-value.orange { color: var(--accent-amber); }
.delta-tile .d-value.blue   { color: var(--primary); }
.delta-tile .d-sub {
    font-family: var(--font-body);
    color: var(--muted); font-size: 13px; margin-top: 2px;
}

/* ── Notices ─────────────────────────────────────────── */
.info-notice {
    background: var(--surface-card);
    border: none; border-radius: var(--r-lg);
    padding: var(--s-md) var(--s-lg);
    color: var(--body); font-size: 14px; line-height: 1.55;
}
.run-status {
    display: flex; align-items: center; gap: var(--s-sm);
    border-radius: var(--r-lg); padding: var(--s-md) var(--s-lg);
    font-size: 14px; line-height: 1.55;
    background: var(--surface-card); color: var(--body-strong);
    margin-bottom: var(--s-sm);
}
.run-status .icon { font-size: 16px; }
.run-status b { font-weight: 500; color: var(--ink); }
.run-status .meta { color: var(--muted); font-size: 13px; }
.run-status.ok   { background: var(--surface-card); color: var(--body-strong); }
.run-status.warn { background: var(--surface-cream-strong); color: var(--body-strong); }
/* The coral callout is the system's voltage — reserved for the one state that
   genuinely demands attention. */
.run-status.err  { background: var(--primary); color: var(--on-primary); }
.run-status.err b, .run-status.err .meta { color: var(--on-primary); }
.filter-hint {
    font-family: var(--font-body);
    color: var(--muted); font-size: 13px; margin-bottom: var(--s-xs);
}
.filter-hint b { color: var(--ink); font-weight: 500; }

/* ── Change tables ───────────────────────────────────── */
.chg-tbl { width: 100%; border-collapse: collapse; font-family: var(--font-body); }
.chg-tbl th {
    color: var(--muted); font-size: 12px; font-weight: 500;
    text-transform: uppercase; letter-spacing: 1.5px;
    text-align: right; padding: var(--s-xs) var(--s-sm);
    border-bottom: 1px solid var(--hairline);
}
.chg-tbl td {
    color: var(--body); font-size: 14px; padding: var(--s-sm);
    border-bottom: 1px solid var(--hairline-soft);
}
.chg-tbl tr:last-child td { border-bottom: none; }
.chg-tbl .up   { color: var(--success); font-weight: 500; }
.chg-tbl .down { color: var(--error);   font-weight: 500; }
.up   { color: var(--success); }
.down { color: var(--error); }
/* button-primary: coral, 8px radius, 40px tall, white label at 14/500. */
.open-btn {
    display: inline-flex; align-items: center; justify-content: center;
    background: var(--primary); color: var(--on-primary) !important;
    font-family: var(--font-body); font-size: 14px; font-weight: 500;
    padding: 12px 20px; border-radius: var(--r-md);
    text-decoration: none; border: none;
}
.open-btn:active { background: var(--primary-active); }

/* ── Sticky filter bar ───────────────────────────────── */
.filter-bar-wrap {
    position: sticky; top: 0; z-index: 50;
    background: var(--canvas);
    border-bottom: 1px solid var(--hairline);
    padding: var(--s-sm) 0;
    margin-bottom: var(--s-md);
}

/* ── Help tooltip (i) ────────────────────────────────────── */
.tip {
    display: inline-flex; align-items: center; justify-content: center;
    width: 18px; height: 18px; border-radius: 50%;
    background: var(--surface-card); color: var(--muted);
    font-size: 11px; font-weight: 500; cursor: help;
    position: relative; flex-shrink: 0;
}
.tip::after {
    content: attr(data-tip);
    position: absolute; top: calc(100% + 8px); right: 0;
    width: 280px; padding: var(--s-sm) var(--s-md);
    background: var(--surface-dark); color: var(--on-dark);
    font-family: var(--font-body); font-size: 13px; font-weight: 400;
    line-height: 1.55; text-align: right; border-radius: var(--r-md);
    opacity: 0; visibility: hidden; z-index: 100; pointer-events: none;
}
.tip:hover::after { opacity: 1; visibility: visible; }

/* ── Streamlit widgets ───────────────────────────────── */
.stTabs [data-baseweb="tab-list"] { gap: var(--s-xxs); border-bottom: 1px solid var(--hairline); }
.stTabs [data-baseweb="tab"] {
    font-family: var(--font-body); font-size: 14px; font-weight: 500;
    color: var(--muted); padding: var(--s-xs) 14px;
    border-radius: var(--r-md) var(--r-md) 0 0; background: transparent;
}
.stTabs [aria-selected="true"] { background: var(--surface-card); color: var(--ink); }
.stTabs [data-baseweb="tab-panel"] { padding-top: var(--s-md); }

/* ── Responsive ──────────────────────────────────────── */
@media (max-width: 1024px) {
    .kpi { flex: 1 1 220px; }
}
@media (max-width: 768px) {
    .block-container { padding-left: 1rem !important; padding-right: 1rem !important; }
    .page-header h1 { font-size: 32px; letter-spacing: -0.5px; }
    .section-title { font-size: 22px; }
    .kpi { flex: 1 1 100%; }
    .delta-tile { flex: 1 1 100%; }
}
@media (max-width: 480px) {
    .kpi-strip { gap: var(--s-xs); }
    .kpi { min-height: 124px; padding: var(--s-md); }
    .kpi-value { font-size: 28px; }
}
</style>
""", unsafe_allow_html=True)

# ── Theme colours ────────────────────────────────────────────────────────────────
# Anthropic palette. Coral is the single brand voltage and carries the primary
# series; teal/amber are the documented sparing companions. GREEN/RED stay
# reserved *status* colours (new vs removed, up vs down) and are only ever used
# alongside a label, never as a decorative series colour.
# Legacy CYAN*/PURPLE names are kept as aliases so call sites stay untouched.
CORAL  = "#cc785c"   # primary series  (colors.primary)
TEAL   = "#5db8a6"   # secondary series (colors.accent-teal)
AMBER  = "#e8a55a"   # tertiary        (colors.accent-amber)
GREEN  = "#5db872"   # status: added   (colors.success)
RED    = "#c64545"   # status: removed (colors.error)
CYAN   = CORAL
CYAN2  = TEAL
YELLOW = AMBER
PURPLE = TEAL

def _chart(fig, height=280):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Assistant, Inter, -apple-system, sans-serif", color="#6c6a64", size=11),
        height=height,
        margin=dict(t=8, b=12, l=4, r=4),
        dragmode=False,
        xaxis=dict(gridcolor="#f5f0e8", zerolinecolor="#f5f0e8",
                   tickfont=dict(color="#8e8b82", size=11), showline=False,
                   fixedrange=True),
        yaxis=dict(gridcolor="#f5f0e8", zerolinecolor="#f5f0e8",
                   tickfont=dict(color="#8e8b82", size=11), showline=False, fixedrange=True),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)", font=dict(color="#3d3d3a", size=11)),
        hoverlabel=dict(bgcolor="#141413", bordercolor="#141413", font=dict(color="#f5f0e8", size=12, family="Assistant, Inter, sans-serif")),
        showlegend=False,
    )
    return fig

# Per-chart time filter: a slim native Plotly range slider under each
# time-series chart. Paired with fixedrange=True on the main axis so dragging
# the plot itself still does nothing (keeps click-to-drill-down working on the
# bar charts) — the slider handles are the only way to zoom the date range.
_RANGESLIDER = dict(visible=True, thickness=0.09, bgcolor="#f5f0e8",
                     bordercolor="#e8e2d5", borderwidth=1)

# One-click date-range buttons on every time chart (week / month / 3 months /
# all). Client-side, so switching is instant with no Streamlit rerun; the
# range slider under each chart stays for picking a custom window.
_RANGE_BUTTONS = dict(
    buttons=[dict(count=7,  step="day",   stepmode="backward", label="שבוע"),
             dict(count=1,  step="month", stepmode="backward", label="חודש"),
             dict(count=3,  step="month", stepmode="backward", label="3 חודשים"),
             dict(step="all", label="הכל")],
    x=0, y=1.02, xanchor="left", yanchor="bottom",
    bgcolor="#f5f0e8", activecolor="#e8d5c4", bordercolor="#e8e2d5", borderwidth=1,
    font=dict(size=12, color="#141413", family="Assistant, Inter, sans-serif"),
)

def _date_xaxis(tickformat="%d/%m/%y"):
    return dict(type="date", fixedrange=True, tickformat=tickformat,
                rangeslider=_RANGESLIDER, rangeselector=_RANGE_BUTTONS)

def _daily(x, y, agg="last"):
    """Collapse multiple same-day points into one (no duplicate ticks). Returns
    real Timestamps (not formatted strings) so the x-axis can stay type="date" —
    needed for the per-chart range slider to filter by actual date, not category
    position. Tick/hover text formatting (dd/mm/yy) happens in the layout instead."""
    tmp = pd.DataFrame({"x": pd.to_datetime(x).dt.normalize(), "y": pd.to_numeric(y, errors="coerce")}).dropna()
    if tmp.empty:
        return x, y
    res = tmp.groupby("x")["y"].last() if agg == "last" else tmp.groupby("x")["y"].mean().round()
    res = res[~_spikes(res)]
    return res.index, res.values

SPIKE_WINDOW  = 7      # days in the rolling-median window
SPIKE_MADS    = 3.0    # how many (scaled) MADs off the local median counts as a spike
SPIKE_MIN_REL = 0.08   # ...and at least this far off in relative terms

def _spikes(s):
    """Hampel filter: flag single-day points far off their neighbors' rolling
    median — e.g. 2026-05-17's partial scrape (262 listings in a ~360 series).
    Needs BOTH a robust-statistics outlier (> SPIKE_MADS scaled MADs) and a
    material jump (> SPIKE_MIN_REL), so a flat series with a near-zero MAD
    doesn't lose ordinary small wiggles. A sustained level change is not a
    spike: the median follows it within half a window. The first and last
    points are never flagged — with neighbors on one side only, a genuine new
    level (e.g. today's run after an outage) is indistinguishable from a spike."""
    if len(s) < 5:
        return pd.Series(False, index=s.index)
    med = s.rolling(SPIKE_WINDOW, center=True, min_periods=3).median()
    mad = (s - med).abs().rolling(SPIKE_WINDOW, center=True, min_periods=3).median()
    dev = (s - med).abs()
    flags = (dev > SPIKE_MADS * 1.4826 * mad) & (dev > SPIKE_MIN_REL * med.abs())
    flags.iloc[[0, -1]] = False
    return flags

def _sparse_labels(values, fmt):
    """Direct-label only the first, last, min and max points; blank the rest.
    Keeps time-series readable — never a number on every point — while still
    calling out the extremes and the latest value. Hover shows every point."""
    vals = list(values)
    n = len(vals)
    if n == 0:
        return []
    keep = {0, n - 1}
    try:
        nums = [float(v) for v in vals]
        keep.add(nums.index(min(nums)))
        keep.add(nums.index(max(nums)))
    except Exception:
        pass
    return [fmt(v) if i in keep else "" for i, v in enumerate(vals)]

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

# Sale-scale vs. rent-scale price sanity floor. Rent is a monthly figure
# (~₪3,000-15,000 for this room range), ~100-1000x smaller than sale asking
# prices — reusing the sale floor here would silently discard every real
# rental listing as a "typo". Must match yad2_scraper.py's RENT_CFG /
# SALE_CFG min_sane_price (see the comment there — scraper and dashboard
# filters are required to agree).
MIN_SANE_PRICE = {"sale": 500_000, "rent": 1_500}

# ₪-per-m² sanity band, (min, max). An absolute price floor cannot separate a
# junk listing from a real luxury one: ₪590,000/95 m² (₪6,211/m²) is data-entry
# garbage while ₪21,000,000/600 m² (₪35,000/m²) is a genuine house, and no
# single price threshold splits those. ₪/m² does. Sale's band is tight because
# the data has a clean gap (junk <= 6,800/m², genuine >= 13,462/m²); rent's is
# deliberately loose because monthly rent does not scale with area, so its low
# ₪/m² entries are real large houses. Must match yad2_scraper.py's
# SALE_CFG / RENT_CFG min_sane_ppsqm / max_sane_ppsqm.
SANE_PPSQM = {"sale": (10_000, 100_000), "rent": (10, 500)}

# Tukey fence multiplier for _iqr_outliers(), per deal type. Rent uses the
# 'far out' fence: its feed is small (~110 apartments) and naturally wide, so
# 1.5 hid 11 of 109 genuine listings — e.g. 2 of Neve Zemer's 7 four-room
# rentals — while 3.0 drops only the 2 true extremes. Sale's large, tight feed
# is fine at 1.5 (18 of 648).
IQR_K = {"sale": 1.5, "rent": 3.0}
IQR_MIN_GROUP = 8           # smaller room groups are too thin to estimate quartiles

def _iqr_outliers(df, k=1.5):
    """Boolean mask of rows whose price or ₪/m² falls outside the 1.5×IQR fences
    of their room-count group (4, 4.5 -> 4; 5 -> 5). NaNs are never flagged."""
    mask = pd.Series(False, index=df.index)
    ppsqm = df["price_num"] / df["size_sqm"]
    groups = df["rooms"].fillna(-1).floordiv(1)
    for _, idx in df.groupby(groups).groups.items():
        for s in (df.loc[idx, "price_num"], ppsqm.loc[idx]):
            vals = s.dropna()
            if len(vals) < IQR_MIN_GROUP:
                continue
            q1, q3 = vals.quantile([0.25, 0.75])
            lo, hi = q1 - k * (q3 - q1), q3 + k * (q3 - q1)
            mask.loc[idx] |= s.notna() & ((s < lo) | (s > hi))
    return mask

def deal_path(base_filename, deal_type):
    """Resolve a deal-type-specific data file path. base_filename is the sale
    filename (e.g. 'yad2_history.csv'); for deal_type == 'rent' this inserts
    a '_rent' suffix before the extension, mirroring yad2_scraper.py's
    DealConfig naming."""
    if deal_type != "rent":
        return os.path.join(DATA_DIR, base_filename)
    root, ext = os.path.splitext(base_filename)
    return os.path.join(DATA_DIR, f"{root}_rent{ext}")

def parse_price_num(p):
    p = str(p).replace(",", "").replace("₪", "").strip()
    m = re.search(r"(\d+)", p)
    return int(m.group(1)) if m else None

def _clean_listings(df, deal_type):
    """Every display-time filter, in one place, so the live snapshot and the
    archived reference snapshot behind the KPI deltas are cleaned identically."""
    df = df.copy()
    df["price_num"] = df["price"].apply(parse_price_num)
    for col in ["rooms", "floor", "size_sqm"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    # Drop clearly-invalid listings (Yad2 data-entry typos: ₪12,700 apartments,
    # 10 m² or 11,526 m² sizes) so they don't blow out the slider ranges and skew
    # min-price / price-per-m². Non-destructive — the raw data files keep
    # everything; this only affects what the dashboard displays. Listings with a
    # MISSING price or size are kept (e.g. "price on request").
    min_sane_price = MIN_SANE_PRICE.get(deal_type, 500_000)
    _price_ok = df["price_num"].isna() | (df["price_num"] >= min_sane_price)
    _size_ok  = df["size_sqm"].isna()  | ((df["size_sqm"] >= 25) & (df["size_sqm"] <= 1000))
    # ₪/m² band — only meaningful where both price and size are present, so
    # rows missing either are kept (same policy as the two checks above).
    lo_ppsqm, hi_ppsqm = SANE_PPSQM.get(deal_type, (10_000, 100_000))
    _ppsqm = df["price_num"] / df["size_sqm"]
    _ppsqm_ok = _ppsqm.isna() | ((_ppsqm >= lo_ppsqm) & (_ppsqm <= hi_ppsqm))
    df = df[_price_ok & _size_ok & _ppsqm_ok].reset_index(drop=True)
    def exf(info, idx):
        parts = str(info).split(",")
        return parts[idx].strip() if len(parts) > idx else ""
    df["apt_type"]     = df["info"].apply(lambda x: exf(x, 0) or "דירה")
    # Same rule as the scraper's extract_neighborhood(): the 2nd part is a
    # neighborhood only in "type, neighborhood, city". In "type, city" it is the
    # city, which used to surface as a fake "רעננה" neighborhood (39 sale + 3
    # rent listings on 2026-10-23) in the filter and the DOM-by-area chart.
    df["neighborhood"] = df["info"].apply(lambda x: exf(x, 1) if str(x).count(",") >= 2 else "")

    # Dashboard scope is apartments / garden apartments / duplexes only — drop
    # other Yad2 categories that leak into the search results (roof/penthouse,
    # private houses, land plots, purchase groups, semi-detached) so they don't
    # skew KPIs, charts or the table, and don't show up as filter options.
    df = df[df["apt_type"].isin(["דירה", "דירת גן", "דופלקס"])].reset_index(drop=True)

    # Statistical outliers (Tukey fences: outside 1.5×IQR) on price and ₪/m²,
    # computed per room count so a pricey 5-room isn't judged against 4-rooms.
    # The sanity band above only catches data-entry typos; this also drops
    # genuine-but-atypical listings (a 540 m² "4-room", a ₪2M 5-room) that
    # would otherwise drag averages and stretch chart axes. Display-only, like
    # the filters above — rows missing price or size are kept.
    df = df[~_iqr_outliers(df, IQR_K.get(deal_type, 1.5))].reset_index(drop=True)
    return df

@st.cache_data
def load_current(_mtime, deal_type):
    data_file = deal_path("yad2_raanana_4rooms.json", deal_type)
    with open(data_file, encoding="utf-8") as f:
        raw = json.load(f)
    df = _clean_listings(pd.DataFrame(raw), deal_type)

    fs_path = deal_path("yad2_first_seen.json", deal_type)
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

KPI_REF_DAYS = 7

@st.cache_data(ttl=300)
def load_reference_snapshot_latest(deal_type):
    path = deal_path("yad2_listings_archive.csv", deal_type)
    if not os.path.exists(path):
        return pd.Timestamp.now()
    ts = pd.to_datetime(pd.read_csv(path, encoding="utf-8-sig", usecols=["snapshot_time"])["snapshot_time"],
                        errors="coerce")
    return ts.max()

@st.cache_data(ttl=300)
def load_dom_panel(deal_type):
    """Days-on-market of every listing in the last archived snapshot of each
    day, cleaned exactly like the live view. DOM is shown as a MEDIAN: a few
    listings that have sat on Yad2 for years (posted 2019, 2022 - confirmed on
    the site) dragged the mean far from the typical listing; one of them alone
    moved rent's 4-room average 39 -> 72 -> 30 as it appeared and left. The
    scraper's history files only store means, so the series is rebuilt here
    from the archive (which starts 2026-08-06). Posting dates come from the
    current date_posted cache, which holds the verified/corrected dates."""
    cols = ["date", "rooms", "neighborhood", "apt_type", "dom"]
    path = deal_path("yad2_listings_archive.csv", deal_type)
    if not os.path.exists(path):
        return pd.DataFrame(columns=cols)
    ar = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
    ar["_ts"] = pd.to_datetime(ar["snapshot_time"], errors="coerce")
    ar = ar.dropna(subset=["_ts"])
    ar["_day"] = ar["_ts"].dt.normalize()
    ar = ar[ar["_ts"] == ar.groupby("_day")["_ts"].transform("max")]
    def _json(name):
        try:
            with open(deal_path(name, deal_type), encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    dp, fs = _json("yad2_date_posted.json"), _json("yad2_first_seen.json")
    parts = []
    for day, snap in ar.groupby("_day"):
        snap = snap.drop(columns=["_ts", "_day", "snapshot_time"])
        snap["_lid"] = snap["url"].fillna("").str.split("?").str[0].str.rstrip("/").str.split("/").str[-1]
        snap = snap[snap["_lid"] != ""].drop_duplicates("_lid")
        c = _clean_listings(snap, deal_type)
        posted = (c["_lid"].map(dp).fillna(c["date_posted"]).replace("", np.nan)
                  .fillna(c["_lid"].map(fs)))
        dom = (day - pd.to_datetime(posted, errors="coerce")).dt.days
        parts.append(pd.DataFrame({"date": day, "rooms": c["rooms"].values,
                                   "neighborhood": c["neighborhood"].values,
                                   "apt_type": c["apt_type"].values, "dom": dom.values}))
    if not parts:
        return pd.DataFrame(columns=cols)
    out = pd.concat(parts, ignore_index=True)
    return out[out["dom"] >= 0]

def _rooms_bucket(df, rooms_sel):
    return df[df["rooms"] >= 5] if rooms_sel == "5" else df[(df["rooms"] >= 4) & (df["rooms"] < 5)]

@st.cache_data(ttl=300)
def load_reference_snapshot(deal_type, days=KPI_REF_DAYS):
    """The archived snapshot from ~`days` ago, run through _clean_listings(),
    as the baseline for the KPI deltas. Returns (df, snapshot_time) or
    (None, None). The scraper's history files can't serve as that baseline:
    their stats include houses/penthouses and skip the outlier filter, so
    comparing them to the cleaned KPIs reported a fake -5.7% avg-price move."""
    path = deal_path("yad2_listings_archive.csv", deal_type)
    if not os.path.exists(path):
        return None, None
    ar = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
    ar["_ts"] = pd.to_datetime(ar["snapshot_time"], errors="coerce")
    # Measured back from the latest snapshot, not from now: if the scraper is
    # paused, "7 days before now" can be the current snapshot itself and every
    # KPI then reads 0.0% against its own data.
    latest = ar["_ts"].max()
    past = ar.loc[ar["_ts"] <= latest - pd.Timedelta(days=days), "_ts"]
    if past.empty:
        return None, None
    snap_ts = past.max()
    snap = ar[ar["_ts"] == snap_ts].drop(columns=["_ts", "snapshot_time"])
    snap = snap.assign(_lid=snap["url"].fillna("").str.split("?").str[0].str.rstrip("/").str.split("/").str[-1])
    snap = snap[snap["_lid"] != ""].drop_duplicates("_lid")
    return _clean_listings(snap, deal_type), snap_ts

# History points recorded before a scraper methodology change aren't comparable
# with what came after, so they're blanked (NaN) on load and drop out of every
# time-series chart. Each cutoff is the first run on the new method:
#  - count / avg_active_dom, 2026-05-03: the first week's counts swing 535 ->
#    460 -> 370 as booster-duplicate removal was introduced, and DOM was still
#    bootstrapping from an empty first_seen map (119 -> 183 -> ~155).
#  - avg_price_per_sqm, 2026-07-12: ₪/m² drops 9% overnight (30,750 -> 28,020)
#    while avg price and count stay flat — a size-parsing fix, not the market.
# Rent tracking began after both changes, so it has no cutoffs.
HISTORY_RELIABLE_FROM = {
    "sale": {"count": "2026-05-03", "avg_active_dom": "2026-05-03",
             "avg_price_per_sqm": "2026-07-12"},
    "rent": {},
}

# Success-run gap (days) that makes the next run a catch-up, see the new/removed
# charts. 3-6 day gaps (PC off over a weekend) yield normal-sized bars; only
# week-plus outages (15d, 8d, 17d) produced the distorted ones.
CATCHUP_GAP_DAYS = 7

def _mask_unreliable(df, deal_type):
    for col, since in HISTORY_RELIABLE_FROM.get(deal_type, {}).items():
        if col in df.columns:
            df[col] = df[col].astype(float).where(df["date"] >= since)
    return df

@st.cache_data(ttl=300)
def load_history(deal_type):
    path = deal_path("yad2_history.csv", deal_type)
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["date"] = pd.to_datetime(df["timestamp"])
    df = _mask_unreliable(df, deal_type)
    df = df.rename(columns={"count": "כמות"})
    return df.sort_values("date").reset_index(drop=True)

def _norm_rooms(df):
    if "rooms" in df.columns:
        df["rooms"] = df["rooms"].astype(str).str.replace(r"\.0$", "", regex=True)
    return df

@st.cache_data(ttl=300)
def load_nb_history(deal_type):
    path = deal_path("yad2_neighborhood_history.csv", deal_type)
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["date"] = pd.to_datetime(df["timestamp"])
    return _norm_rooms(_mask_unreliable(df, deal_type)).sort_values("date").reset_index(drop=True)

@st.cache_data(ttl=300)
def load_type_history(deal_type):
    path = deal_path("yad2_type_history.csv", deal_type)
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["date"] = pd.to_datetime(df["timestamp"])
    return _norm_rooms(_mask_unreliable(df, deal_type)).sort_values("date").reset_index(drop=True)

@st.cache_data(ttl=300)
def load_rooms_history(deal_type):
    path = deal_path("yad2_rooms_history.csv", deal_type)
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["date"]  = pd.to_datetime(df["timestamp"])
    df["rooms"] = df["rooms"].astype(str).str.replace(r"\.0$", "", regex=True)
    df = _mask_unreliable(df, deal_type)
    return df.sort_values("date").reset_index(drop=True)

@st.cache_data(ttl=300)
def detect_changes(deal_type):
    # Diff against the one-step-behind snapshot so this shows what changed in the
    # MOST RECENT run. yad2_prev_run.json is overwritten with the current data at
    # the end of every scrape (it seeds the next run's diff), so on its own it
    # equals the current snapshot and every count comes out zero. The scraper
    # keeps yad2_prev_display.json as the run-before-this-one; prefer it, and fall
    # back to prev_run.json only until the next scrape creates the display file.
    data_file = deal_path("yad2_raanana_4rooms.json", deal_type)
    prev_file = deal_path("yad2_prev_display.json", deal_type)
    if not os.path.exists(prev_file):
        prev_file = deal_path("yad2_prev_run.json", deal_type)
    if not os.path.exists(prev_file):
        return None, None, None, None, None
    with open(prev_file, encoding="utf-8") as f:
        prev_list = json.load(f)
    with open(data_file, encoding="utf-8") as f:
        curr_list = json.load(f)
    prev_time = datetime.fromtimestamp(os.path.getmtime(prev_file)).strftime("%d/%m/%Y %H:%M")
    curr_time = datetime.fromtimestamp(os.path.getmtime(data_file)).strftime("%d/%m/%Y %H:%M")
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
def load_run_log(deal_type):
    path = deal_path("yad2_run_log.csv", deal_type)
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.sort_values("timestamp", ascending=False).reset_index(drop=True)

@st.cache_data(ttl=300)
def load_first_seen_map(deal_type):
    path = deal_path("yad2_first_seen.json", deal_type)
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)

@st.cache_data(ttl=300)
def load_dom_log(deal_type):
    path = deal_path("yad2_dom_log.csv", deal_type)
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig")

def build_trends_payload(cur_df, nbh, rooms_sel, deal_type):
    """Live data for the 'מגמות שכונות' page. Sparkline series come from the
    per-(neighborhood × room) history; the CURRENT table values (count, DOM,
    price/m²) are recomputed from the sanity-filtered snapshot so this page
    always agrees with the main dashboard's KPIs (history rows written before
    the sanity filter existed carry typo-inflated price/m²)."""
    if len(nbh) == 0 or "rooms" not in nbh.columns:
        return None
    h = nbh[nbh["rooms"] == rooms_sel].copy()
    if len(h) == 0:
        return None
    h["day"] = h["timestamp"].astype(str).str[:10]
    panel = _rooms_bucket(load_dom_panel(deal_type), rooms_sel)

    if rooms_sel == "5":
        cur = cur_df[cur_df["rooms"] >= 5]
    else:
        cur = cur_df[(cur_df["rooms"] >= 4) & (cur_df["rooms"] < 5)]
    # Drop blanks and the city-name leak ("דירה, רעננה" with no neighborhood
    # makes the 2nd info part the city itself — not a real neighborhood).
    cur = cur[~cur["neighborhood"].isin(["", "רעננה"])]

    today_str = datetime.now().strftime("%Y-%m-%d")
    # Days with a usable count only, so "days" stays aligned with market_count
    all_days = sorted(set(h.loc[h["count"].notna(), "day"]))
    out = []
    for name, grp in cur.groupby("neighborhood"):
        count = int(len(grp))
        if count < 3:
            continue                      # tiny samples are noise
        doms = grp["ימים_בשוק"].dropna()
        doms = doms[doms >= 0]
        dom = round(float(doms.median()), 1) if len(doms) else None
        pp = grp[(grp["size_sqm"] > 0) & grp["price_num"].notna()]
        ppsqm = int((pp["price_num"] / pp["size_sqm"]).mean()) if len(pp) else None

        hh = h[h["neighborhood"] == name].sort_values("date")
        # .dropna(): HISTORY_RELIABLE_FROM blanks pre-cutoff counts
        day_count = hh.groupby("day")["count"].last().dropna()
        pn = panel[panel["neighborhood"] == name]
        day_dom   = pn.groupby(pn["date"].dt.strftime("%Y-%m-%d"))["dom"].median().dropna()
        cser = [int(v) for v in day_count.values]
        dser = [round(float(v), 1) for v in day_dom.values]
        # The snapshot is the truth for "now": replace/append today's point so
        # the sparkline endpoint equals the number shown beside it.
        if len(cser) and day_count.index[-1] == today_str: cser[-1] = count
        else: cser.append(count)
        if dom is not None:
            if len(dser) and len(day_dom) and day_dom.index[-1] == today_str: dser[-1] = dom
            else: dser.append(dom)
        base_c = cser[0] if len(cser) < 8 else cser[-8]
        dom_delta = None
        if dom is not None and len(dser) >= 2:
            base_d = dser[0] if len(dser) < 8 else dser[-8]
            dom_delta = round(dom - base_d, 1)
        out.append({"name": name, "count": count, "count_series": cser,
                    "count_delta": count - base_c, "dom": dom, "dom_series": dser,
                    "dom_delta": dom_delta, "ppsqm": ppsqm})
    if not out:
        return None
    out.sort(key=lambda x: -x["count"])

    # Market-wide series: median DOM across all listings + total count per day
    mdom = panel.groupby(panel["date"].dt.strftime("%Y-%m-%d"))["dom"].median().round(1)
    mcount = h.dropna(subset=["count"]).groupby("day")["count"].sum()
    mc = [int(v) for v in mcount.values]
    total_now = sum(x["count"] for x in out)
    if len(mc) and mcount.index[-1] == today_str: mc[-1] = total_now
    else:
        mc.append(total_now)
        if all_days and all_days[-1] != today_str: all_days.append(today_str)
    mdom_days = list(mdom.index)
    mdom_vals = [float(v) for v in mdom.values]
    _live = cur["ימים_בשוק"].dropna()
    _live = _live[_live >= 0]
    if len(_live):
        wd = round(float(_live.median()), 1)
        if mdom_days and mdom_days[-1] == today_str: mdom_vals[-1] = wd
        else: mdom_days.append(today_str); mdom_vals.append(wd)
    deal_label = "מכירה" if deal_type == "sale" else "השכרה"
    return {
        "generated": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "rooms_label": f"{deal_label} · {rooms_sel} חדרים",
        "days": all_days,
        "neighborhoods": out,
        "market_count": mc,
        "market_dom_days": mdom_days,
        "market_dom_vals": mdom_vals,
    }

# ── Deal-type toggle (sale/rent) must be readable before data loads, but the
# widget itself is rendered later (next to the page-nav radio, §2.1 of the
# rental-tracking plan) — pre-read the session-state key here, standard
# Streamlit "pre-read + later-render" pattern for a value that gates which
# files get loaded rather than just masking already-loaded data. ──────────
st.session_state.setdefault("flt_deal", "sale")
sel_deal = st.session_state["flt_deal"]
deal_label = "מכירה" if sel_deal == "sale" else "השכרה"

data_file_path = deal_path("yad2_raanana_4rooms.json", sel_deal)
if not os.path.exists(data_file_path):
    st.info("אין עדיין נתוני השכרה — יופיעו לאחר הריצה הראשונה של הסקרייפר." if sel_deal == "rent"
            else "אין עדיין נתוני מכירה — יופיעו לאחר הריצה הראשונה של הסקרייפר.")
    st.stop()

# ── Load data ────────────────────────────────────────────────────────────────────
_mtime    = os.path.getmtime(data_file_path)
df        = load_current(_mtime, sel_deal)
if len(df) == 0:
    st.info("אין עדיין מספיק נתונים לתצוגה זו — הם יופיעו לאחר הריצות הבאות.")
    st.stop()
history   = load_history(sel_deal)
nb_hist   = load_nb_history(sel_deal)
type_hist = load_type_history(sel_deal)
rooms_hist = load_rooms_history(sel_deal)
run_log   = load_run_log(sel_deal)
chg      = detect_changes(sel_deal)
new_df, rem_df, price_df, prev_time, curr_time = (
    chg if chg[0] is not None
    else (pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), "—", "—")
)
mod_time = datetime.fromtimestamp(os.path.getmtime(data_file_path)).strftime("%d/%m/%Y %H:%M")

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

mod_age = _hebrew_age(datetime.fromtimestamp(os.path.getmtime(data_file_path)))

# ── Filter option lists + defaults (needed by every page) ────────────────────────
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

# Time-range options for the top filter bar. None = no cutoff ("all").
# 90 days matters here: the history reaches back to 2026-04-24, so 7/30 alone
# hid most of the record.
RANGE_OPTIONS = {"הכל": None, "90 ימים": 90, "30 ימים": 30, "7 ימים": 7}

# Defaults for reset
_defaults = {
    "flt_type":   "הכל",
    "flt_rooms":  "4",
    "flt_deal":   "sale",
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

# ── Sidebar: brand, page navigation, room-count toggle, live status ──────────────
NAV_PAGES = ["📊 סקירה", "🏘️ מגמות שכונות", "📋 כל המודעות", "🔔 פעילות שוק"]
NAV_TO_PAGE = {"📊 סקירה": "overview", "🏘️ מגמות שכונות": "trends",
               "📋 כל המודעות": "listings", "🔔 פעילות שוק": "activity"}
with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
        <div class="brand-mark">
            <svg viewBox="0 0 24 24"><path d="M3 11l9-7 9 7"/><path d="M5 10v9a1 1 0 0 0 1 1h4v-6h4v6h4a1 1 0 0 0 1-1v-9"/></svg>
        </div>
        <h3>Yad2 Market</h3>
        <p>רעננה · מעקב נדל״ן</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="nav-label">תצוגות</div>', unsafe_allow_html=True)
    nav_choice = st.radio("עמוד", NAV_PAGES, label_visibility="collapsed", key="page_nav")

    st.markdown('<div class="nav-label" style="margin-top:16px">עסקה</div>', unsafe_allow_html=True)
    # Primary dataset switch: sale vs. rent are separate Yad2 feeds/files (not a
    # value-split of one feed like the room toggle below), so this must be read
    # BEFORE data loads — see the pre-read block above "Load data". The widget
    # here just renders the same "flt_deal" session-state key that pre-read
    # already initialized; global for every page, same as the room toggle.
    st.radio("עסקה", ["sale", "rent"], horizontal=True,
             format_func=lambda d: "מכירה" if d == "sale" else "השכרה",
             label_visibility="collapsed", key="flt_deal")

    st.markdown('<div class="nav-label" style="margin-top:16px">חדרים</div>', unsafe_allow_html=True)
    # Primary view switch: 4-room OR 5-room (bucket "4" = 4/4.5, "5" = 5+).
    # Global for every page — including neighborhood trends, which used to have
    # its own separate room toggle.
    sel_rooms = st.radio("חדרים", ["4", "5"], horizontal=True,
                         format_func=lambda r: f"{r} חדרים",
                         label_visibility="collapsed", key="flt_rooms")

    if len(run_log) > 0:
        _lr_ok = str(run_log.iloc[0].get("status", "")).lower() != "error"
        st.markdown(f"""
        <div class="sidebar-status">
            <div class="status-live"><span class="live-dot" style="background:{'#5db872' if _lr_ok else '#c64545'}"></span>
                {'נתונים חיים' if _lr_ok else 'שגיאה בריצה האחרונה'}</div>
            <div class="stat-row">עודכן {mod_age}</div>
        </div>
        """, unsafe_allow_html=True)

page = NAV_TO_PAGE[nav_choice]

# ── Page: neighborhood trends — self-contained, doesn't use the shared filters ───
if page == "trends":
    st.markdown(f"""
    <div class="page-header">
        <h1>מגמות שכונות · {deal_label} · {sel_rooms} חדרים</h1>
        <div class="sub">השוואת מלאי, ימים בשוק ומחיר למ״ר בין שכונות</div>
    </div>
    """, unsafe_allow_html=True)
    _payload = build_trends_payload(df, nb_hist, sel_rooms, sel_deal)
    _tpl_path = os.path.join(DATA_DIR, "yad2_trends_page.html")
    if _payload is None:
        st.info("אין עדיין מספיק נתונים היסטוריים לעמוד זה — הוא ייבנה עם הריצות הבאות.")
    elif not os.path.exists(_tpl_path):
        st.error("קובץ התבנית yad2_trends_page.html חסר.")
    else:
        with open(_tpl_path, encoding="utf-8") as _f:
            _tpl = _f.read()
        components.html(_tpl.replace("/*__DATA__*/{}", json.dumps(_payload, ensure_ascii=False)),
                        height=2350, scrolling=True)
    st.stop()

# ── Page header (placeholder — filled below once fdf is known) ───────────────────
header_slot = st.empty()

# ── Top filter bar — shown on Overview & Listings; Activity reads the same ───────
# session-state values without re-rendering the widgets (its own nav item has no
# filter row, so the values it needs come from whatever was last set on the other
# two pages).
if page in ("overview", "listings"):
    st.markdown('<div class="filter-bar-wrap"><div class="filter-bar-anchor"></div>', unsafe_allow_html=True)
    fb_time, fb3, fb4, fb5, fb_reset, _spacer = st.columns([1, 0.9, 0.9, 1, 0.7, 2.6])
    with fb_time:
        # Time range for every history-backed chart. The filtering machinery
        # (_within_range / range_days) already existed but had no widget —
        # quick_range was hardcoded to "הכל", so it never did anything.
        st.selectbox("טווח זמן", list(RANGE_OPTIONS), key="quick_range")
    with fb3:
        sel_type = st.selectbox("סוג נכס", ["הכל"] + apt_types, key="flt_type")
    with fb4:
        sel_floor = st.selectbox("קומה", ["הכל"] + [str(f) for f in floors_opts], key="flt_floor")
    with fb5:
        sel_nb = st.selectbox("שכונה", ["הכל"] + nbs, key="flt_nb")
    with fb_reset:
        if st.button("♺ אפס", help="איפוס כל הפילטרים", use_container_width=True):
            st.session_state["_reset_filters"] = True
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
else:
    sel_type    = st.session_state["flt_type"]
    sel_floor   = st.session_state["flt_floor"]
    sel_nb      = st.session_state["flt_nb"]

# Price/size range filters were removed from the UI (their slider widgets hit a
# Streamlit/BaseWeb RTL rendering bug — see yad2_dashboard.py history). The rest
# of the file still keys its "any filter narrower than the full dataset" checks
# off price_range/size_range, so keep them as the always-full range rather than
# threading a bigger refactor through every one of those call sites.
price_range = (price_min, price_max)
size_range  = (size_min, size_max)

# ── Apply filters ────────────────────────────────────────────────────────────────
size_filled = df["size_sqm"].fillna(size_range[0])
mask = (
    (df["price_num"] >= price_range[0]) & (df["price_num"] <= price_range[1]) &
    (size_filled >= size_range[0])      & (size_filled <= size_range[1])
)
if sel_type  != "הכל": mask &= df["apt_type"]     == sel_type
if sel_nb    != "הכל": mask &= df["neighborhood"] == sel_nb
# Room bucket: "5" = 5+ rooms, "4" = 4 or 4.5 rooms
if sel_rooms == "5":   mask &= df["rooms"] >= 5
else:                  mask &= (df["rooms"] >= 4) & (df["rooms"] < 5)
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
_titles = {"overview": "סקירת שוק רעננה", "listings": "כל המודעות", "activity": "פעילות שוק"}
header_slot.markdown(f"""
<div class="page-header">
    <h1>{_titles[page]} · {deal_label} · {sel_rooms} חדרים</h1>
    <div class="sub">
        <b>{len(fdf):,}</b> מודעות &nbsp;·&nbsp; עודכן <b>{mod_age}</b> &nbsp;<span style="opacity:0.55">({mod_time})</span>
    </div>
</div>
""", unsafe_allow_html=True)

if page == "overview":
    avg_p   = int(fdf["price_num"].mean())    if len(fdf) else 0
    med_p   = int(fdf["price_num"].median())  if len(fdf) else 0
    min_p   = int(fdf["price_num"].min())     if len(fdf) else 0
    # Price per m² = mean of each listing's price/size (average-of-ratios), matching
    # how the history files and trend charts compute it — so the KPI, the chart and
    # the "vs week" delta all agree. (avg-price ÷ avg-size gave a different number.)
    _valid_pps = fdf[(fdf["size_sqm"] > 0) & fdf["price_num"].notna()] if len(fdf) else fdf
    ppsqm   = int((_valid_pps["price_num"] / _valid_pps["size_sqm"]).mean()) if len(_valid_pps) else 0

    # ── Run status banner ─────────────────────────────────────────────────────
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

    # ── KPI strip ──────────────────────────────────────────────────────────────
    def fmt(n): return f"₪{n:,}" if n else "—"

    # Deltas vs the archived snapshot from ~7 days ago, cleaned and filtered
    # exactly like the live KPIs (see load_reference_snapshot).
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
        return f'<div class="kpi-delta {cls}">{arrow} {abs(pct):.1f}% {ref_label}</div>'

    ref_count = ref_avg = ref_med = ref_pps = None
    ref_label = "מול שבוע"
    # Baseline = the same room-count bucket in the archived snapshot ~7 days ago,
    # so the KPI (always one room count, 4 or 5) compares like-for-like.
    ref_df, ref_ts = load_reference_snapshot(sel_deal)
    if ref_df is not None:
        _rm = ref_df["rooms"]
        ref = ref_df[_rm >= 5] if sel_rooms == "5" else ref_df[(_rm >= 4) & (_rm < 5)]
        ref = ref[ref["price_num"].notna()]
        if len(ref):
            ref_count = len(ref)
            ref_avg   = float(ref["price_num"].mean())
            ref_med   = float(ref["price_num"].median())
            _rp       = ref[ref["size_sqm"] > 0]
            ref_pps   = float((_rp["price_num"] / _rp["size_sqm"]).mean()) if len(_rp) else None
        # After an outage the newest snapshot >= 7 days old can be much older —
        # say so rather than claim a week.
        _age_days = (load_reference_snapshot_latest(sel_deal) - ref_ts).days
        if _age_days > KPI_REF_DAYS + 1:
            ref_label = f"מול לפני {_age_days} ימים"

    # The room-count baseline above is valid for the plain 4/5 view. But if a FURTHER
    # filter (neighborhood, type, floor, price, size) is active, the KPI reflects a
    # sub-subset while the baseline is the whole bucket — comparing them is bogus, so
    # hide the pills. sel_rooms is intentionally excluded (it has its own baseline).
    is_filtered = (
        sel_nb != "הכל" or sel_type != "הכל" or sel_floor != "הכל"
        or price_range != (price_min, price_max) or size_range != (size_min, size_max)
    )
    # A missing pill must still emit a non-blank line: an empty string here would
    # leave a whitespace-only line inside the HTML block, which Markdown treats as a
    # block terminator and then renders the following indented cards as raw text.
    # The spacer keeps the flex card's bottom alignment (like .kpi-delta's margin).
    _spacer = '<div class="kpi-spacer"></div>'
    d_count = _spacer if is_filtered else (_kpi_delta(len(fdf), ref_count) or _spacer)
    d_avg   = _spacer if is_filtered else (_kpi_delta(avg_p,    ref_avg)   or _spacer)
    d_med   = _spacer if is_filtered else (_kpi_delta(med_p,    ref_med)   or _spacer)
    d_pps   = _spacer if is_filtered else (_kpi_delta(ppsqm,    ref_pps)   or _spacer)

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
            <div class="kpi-sub">{"ממוצע מחירי מכירה" if sel_deal == "sale" else "ממוצע דמי שכירות"}</div>
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
    # Read the filter-bar value. (Was hardcoded to "הכל", which silently disabled
    # the whole time-range path below.)
    quick_range = st.session_state.get("quick_range", "הכל")

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

        range_days = RANGE_OPTIONS.get(quick_range)
        history_f = _within_range(history,   range_days)
        nb_hist_f = _within_range(nb_hist,   range_days)
        type_hist_f = _within_range(type_hist, range_days)
        rooms_hist_f = _within_range(rooms_hist, range_days)
        # Neighborhood/type history is now split by room bucket — keep only the
        # selected room count so those charts honor the 4/5 toggle (no mixed line).
        if len(nb_hist_f) and "rooms" in nb_hist_f.columns:
            nb_hist_f = nb_hist_f[nb_hist_f["rooms"] == sel_rooms]
        if len(type_hist_f) and "rooms" in type_hist_f.columns:
            type_hist_f = type_hist_f[type_hist_f["rooms"] == sel_rooms]

        using_nb   = chart_nb   != "הכל" and len(nb_hist_f)   > 0
        using_type = chart_type != "הכל" and len(type_hist_f) > 0
        rooms_src  = (rooms_hist_f[rooms_hist_f["rooms"] == sel_rooms].sort_values("date")
                      if len(rooms_hist_f) else rooms_hist_f)
        using_rooms = len(rooms_src) > 0

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
        elif using_rooms:
            # Default view: the selected room-count's own trend line.
            qty_x, qty_y     = rooms_src["date"], rooms_src["count"]
            price_x, price_y = rooms_src["date"], rooms_src["avg_price_per_sqm"]
            scope_label = f"{sel_rooms} חדרים"
        else:
            qty_x, qty_y     = history["date"], history["כמות"]
            price_x, price_y = history["date"], history["avg_price_per_sqm"]
            scope_label = f"{sel_rooms} חדרים"

        # Narrowing filters that the pre-aggregated history files can't slice by.
        # (sel_rooms is NOT here — it has its own per-room-count history.)
        any_narrow_filter = (
            sel_floor != "הכל" or
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
            st.markdown(f'<div class="card"><div class="card-title"><span class="tip" data-tip="כמה מודעות 4-5 חדרים פעילות היו בכל יום. עלייה = יותר היצע, ירידה = פחות היצע (יותר נסגרו ממה שנפתחו).">ⓘ</span>כמות מודעות לאורך זמן</div><div class="card-desc">{qty_label}</div>', unsafe_allow_html=True)
            if any_narrow_filter:
                # Pre-aggregated history can't be sliced by price/size/rooms/floor — show today's filtered count only
                st.markdown(
                    f'<p style="color:#141413;font-size:2rem;font-weight:800;padding:18px 0 4px;">{len(fdf):,} מודעות</p>'
                    f'<p style="color:#3d3d3a;font-size:0.84rem;">תואמות את הפילטרים · היסטוריה לפי מחיר/גודל/חדרים/קומה אינה נשמרת</p>',
                    unsafe_allow_html=True)
            else:
                qty_color = CYAN
                fig_qty = go.Figure()
                _qx, _qy = _daily(qty_x, qty_y)
                fig_qty.add_trace(go.Scatter(
                    x=_qx, y=_qy,
                    mode="lines+markers+text",
                    line=dict(color=qty_color, width=2.8, shape="spline", smoothing=0.3),
                    marker=dict(size=7, color=qty_color, line=dict(color="#faf9f5", width=2)),
                    text=_sparse_labels(_qy, lambda v: f"{int(v):,}"),
                    textposition="top center",
                    textfont=dict(size=11, color="#141413", family="Assistant, Inter, sans-serif"),
                    cliponaxis=False,
                    hovertemplate="<b>%{x|%d/%m/%y}</b><br>%{y} מודעות<extra></extra>"
                ))
                _chart(fig_qty, 320)
                qty_rng = _yrange(_qy)
                fig_qty.update_layout(yaxis_title="מודעות",
                                      xaxis=_date_xaxis(), margin=dict(t=40),
                                      yaxis=dict(range=qty_rng, fixedrange=True,
                                                 gridcolor="#f5f0e8", tickfont=dict(color="#3d3d3a", size=11)))
                st.plotly_chart(fig_qty, use_container_width=True, config=dict(displayModeBar=False, scrollZoom=False))
            st.markdown('</div>', unsafe_allow_html=True)

        # ── Chart 2: Avg price per sqm over time ─────────────────────────────────────
        with gc2:
            st.markdown(f'<div class="card"><div class="card-title"><span class="tip" data-tip="מחיר ממוצע לכל מ״ר על פני כל המודעות הפעילות. זה האינדיקטור הכי טוב למחיר נטו של השוק (מנטרל הבדלי גודל).">ⓘ</span>מחיר ממוצע למ״ר לאורך זמן</div><div class="card-desc">{scope_label} — עולה/יורד = התייקרות/הוזלה</div>', unsafe_allow_html=True)
            # Brand blue line; the up/down trend is already carried by the KPI delta
            # pill and the card description, so the line stays on-brand rather than
            # flashing red whenever prices tick up.
            p_color, fill_col = CYAN, "rgba(204,120,92,0.08)"
            fig_price = go.Figure()
            _px, _py = _daily(price_x, price_y, agg="mean")
            fig_price.add_trace(go.Scatter(
                x=_px, y=_py,
                mode="lines+markers+text",
                line=dict(color=p_color, width=2.8, shape="spline", smoothing=0.3),
                marker=dict(size=7, color=p_color, line=dict(color="#faf9f5", width=2)),
                text=_sparse_labels(_py, lambda v: f"₪{int(v):,}"),
                textposition="top center",
                textfont=dict(size=11, color="#141413", family="Assistant, Inter, sans-serif"),
                cliponaxis=False,
                hovertemplate="<b>%{x|%d/%m/%y}</b><br>₪%{y:,.0f}/מ״ר<extra></extra>"
            ))
            _chart(fig_price, 320)
            p_rng = _yrange(_py)
            fig_price.update_layout(yaxis_title="₪/מ״ר",
                                    xaxis=_date_xaxis(), margin=dict(t=40),
                                    yaxis=dict(range=p_rng, tickformat=",d", fixedrange=True,
                                               gridcolor="#f5f0e8", tickfont=dict(color="#3d3d3a", size=11)))
            st.plotly_chart(fig_price, use_container_width=True, config=dict(displayModeBar=False, scrollZoom=False))
            st.markdown('</div>', unsafe_allow_html=True)

        # ── Chart 5: Avg days on market over time ────────────────────────────────
        st.markdown('<div style="margin-top:14px"></div>', unsafe_allow_html=True)
        gc5, gc6 = st.columns(2, gap="medium")
        with gc5:
            st.markdown(f'<div class="card"><div class="card-title"><span class="tip" data-tip="DOM = Days On Market. כמה ימים מודעה טיפוסית (חציון) כבר באוויר. חציון ולא ממוצע, כדי שכמה מודעות שעומדות שנים לא יעוותו את התמונה. עלייה = מודעות נתקעות (השוק מאט), ירידה = מתחלפות מהר (השוק חם).">ⓘ</span>חציון ימים בשוק לאורך זמן</div><div class="card-desc">חציון DOM של כל המודעות הפעילות · {scope_label}</div>', unsafe_allow_html=True)

            # Median DOM per day from the archive panel, sliced by the same room
            # bucket / neighborhood / type as the view. Hidden under a narrow
            # filter (price/size/floor), which the panel isn't sliced by.
            xs, ys = [], []
            if not any_narrow_filter:
                pdom = _rooms_bucket(load_dom_panel(sel_deal), sel_rooms)
                if sel_nb != "הכל":
                    pdom = pdom[pdom["neighborhood"] == sel_nb]
                if sel_type != "הכל":
                    pdom = pdom[pdom["apt_type"] == sel_type]
                if range_days is not None:
                    pdom = pdom[pdom["date"] >= pd.Timestamp.now().normalize() - pd.Timedelta(days=range_days)]
                if len(pdom):
                    _med = pdom.groupby("date")["dom"].median()
                    _ddx, _ddy = _daily(pd.Series(_med.index), pd.Series(_med.values))
                    xs, ys = list(_ddx), list(_ddy)

            # Live point (today) reflects the active filters via fdf
            live_dom = fdf["ימים_בשוק"].dropna()
            live_dom = live_dom[live_dom >= 0]
            live_med = float(live_dom.median()) if len(live_dom) else None

            today_ts = pd.Timestamp.now().normalize()
            if live_med is not None:
                if xs and xs[-1] == today_ts:
                    ys[-1] = round(live_med, 1)
                else:
                    xs.append(today_ts); ys.append(round(live_med, 1))

            if len(xs) >= 2:
                fig_dom = go.Figure(go.Scatter(
                    x=xs, y=ys,
                    mode="lines+markers+text",
                    line=dict(color=CYAN2, width=2.8, shape="spline", smoothing=0.3),
                    marker=dict(size=7, color=CYAN2, line=dict(color="#faf9f5", width=2)),
                    text=_sparse_labels(ys, lambda v: f"{v:.0f}"),
                    textposition="top center",
                    textfont=dict(size=11, color="#141413", family="Assistant, Inter, sans-serif"),
                    cliponaxis=False,
                    hovertemplate="<b>%{x|%d/%m/%y}</b><br>%{y:.1f} ימים<extra></extra>"
                ))
                _chart(fig_dom, 340)
                dom_rng = _yrange(ys)
                fig_dom.update_layout(yaxis_title="ימים",
                                      xaxis=_date_xaxis(), margin=dict(t=40),
                                      yaxis=dict(range=dom_rng, fixedrange=True,
                                                 gridcolor="#f5f0e8", tickfont=dict(color="#3d3d3a", size=11)))
                st.plotly_chart(fig_dom, use_container_width=True, config=dict(displayModeBar=False, scrollZoom=False))
            elif len(xs) == 1:
                st.markdown(f'<p style="color:#141413;font-size:1.4rem;font-weight:800;padding:16px 0 4px;">{ys[0]:.1f} ימים (חציון)</p><p style="color:#3d3d3a;font-size:0.84rem;">המגמה תיווצר עם ריצות נוספות של ה-Scraper</p>', unsafe_allow_html=True)
            else:
                st.markdown('<p style="color:#3d3d3a;padding:24px 0;">זמין לאחר ריצת ה-Scraper.</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with gc6:
            # Avg DOM per neighborhood (mean days on market by area)
            st.markdown('<div class="card"><div class="card-title"><span class="tip" data-tip="חציון ימים בשוק לכל שכונה. עמודה גבוהה = השכונה איטית למכור, נמוכה = מודעות מתחלפות מהר.">ⓘ</span>חציון ימים בשוק לפי שכונה</div><div class="card-desc">חציון DOM פר שכונה (מסונן)</div>', unsafe_allow_html=True)
            nb_dom = (fdf[fdf["ימים_בשוק"] >= 0]
                        .groupby("neighborhood")
                        .agg(avg_dom=("ימים_בשוק", "median"),
                             n=("ימים_בשוק", "size"))
                        .reset_index())
            nb_dom = nb_dom[(nb_dom["neighborhood"] != "") & (nb_dom["n"] >= 2)]
            nb_dom = nb_dom.sort_values("avg_dom", ascending=True)
            if len(nb_dom):
                # Solid brand blue — the bar length and the sort order already encode
                # days-on-market, so colour stays a single on-brand hue instead of a
                # red/amber/green traffic-light.
                fig_nbdom = go.Figure(go.Bar(
                    x=nb_dom["avg_dom"].round(1),
                    y=nb_dom["neighborhood"],
                    orientation="h",
                    marker=dict(color=CYAN, line=dict(width=0)),
                    text=[f"{d:.0f} ימים · {int(n)} דירות" for d, n in zip(nb_dom["avg_dom"], nb_dom["n"])],
                    textposition="inside",
                    insidetextanchor="middle",
                    textfont=dict(size=12, color="#ffffff", family="Assistant, Inter, sans-serif"),
                    customdata=nb_dom["n"],
                    hovertemplate="<b>%{y}</b><br>%{x:.1f} ימים (חציון)<br>%{customdata} "
                                  + ("דירות למכירה" if sel_deal == "sale" else "דירות להשכרה")
                                  + "<extra></extra>",
                ))
                _chart(fig_nbdom, max(300, len(nb_dom) * 26))
                fig_nbdom.update_layout(
                    xaxis_title="ימים", yaxis_title="",
                    xaxis=dict(fixedrange=True, gridcolor="#f5f0e8",
                               tickfont=dict(color="#3d3d3a", size=11)),
                    yaxis=dict(fixedrange=True, gridcolor="rgba(0,0,0,0)",
                               tickfont=dict(color="#141413", size=11), automargin=True),
                    bargap=0.25,
                )
                st.plotly_chart(fig_nbdom, use_container_width=True, config=dict(displayModeBar=False, scrollZoom=False))
            else:
                st.markdown('<p style="color:#3d3d3a;padding:24px 0;">אין מספיק נתונים לפילוח לפי שכונה.</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # ── New / Removed listings per DAY (deduped by listing ID) ─────────────
        # Uses first_seen.json + dom_log.csv (canonical sources, not run_log which double-counts)
        st.markdown('<div style="margin-top:14px"></div>', unsafe_allow_html=True)
        gc7, gc8 = st.columns(2, gap="medium")

        def _lid(u):
            return (u or "").split("?")[0].rstrip("/").split("/")[-1]

        fs_map = load_first_seen_map(sel_deal)
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

        dom_df_full = load_dom_log(sel_deal)
        if not dom_df_full.empty and "removed_date" in dom_df_full.columns:
            dom_dedup = dom_df_full.copy()
            dom_dedup["_lid"] = dom_dedup["url"].apply(_lid)
            # one removal event per unique listing per date
            dom_dedup = dom_dedup[dom_dedup["_lid"] != ""].drop_duplicates(subset=["_lid", "removed_date"])
            # Drop listings that are currently active — those "removals" are
            # legacy URL-keyed false positives (yad2 randomized URL query strings,
            # so the same listing kept getting flagged as removed and re-added).
            active_ids = {_lid(u) for u in df["url"] if u}
            dom_dedup = dom_dedup[~dom_dedup["_lid"].isin(active_ids)]
            # For listings that were really removed (don't exist now), keep only the
            # LATEST removal date — earlier ones are URL-form changes, not real exits.
            dom_dedup = dom_dedup.sort_values("removed_date").drop_duplicates(subset=["_lid"], keep="last")
            rem_by_date = dom_dedup.groupby("removed_date").size().sort_index()
        else:
            rem_by_date = pd.Series(dtype=int)

        # Honor the top bar's time range. These two series are built straight from
        # first_seen.json / dom_log.csv rather than the history frames, so they
        # don't pass through _within_range() — without this they'd keep showing
        # the full record while every chart above them was clipped.
        if range_days is not None:
            _cut = (pd.Timestamp.now() - pd.Timedelta(days=range_days)).strftime("%Y-%m-%d")
            if len(new_by_date):
                new_by_date = new_by_date[new_by_date.index >= _cut]
            if len(rem_by_date):
                rem_by_date = rem_by_date[rem_by_date.index >= _cut]

        # Catch-up days: the first successful run after a multi-day outage books
        # every listing that appeared or vanished during the gap onto that one
        # date (+419 on 2026-07-07 after an 8-day bot-block, +149 on 2026-10-23
        # after 17 days). Those bars measure the outage, not a day's activity,
        # and squash every other bar, so they're left out of both charts.
        catchup_days, rem_catchup_days = [], []
        if len(run_log) and "status" in run_log.columns:
            _ok_days = pd.Series(sorted(run_log.loc[run_log["status"] == "success", "timestamp"]
                                        .dt.normalize().unique()))
            # Saturday runs are booked on Friday (the scraper's Saturday->Friday rule)
            _ok_days = _ok_days.where(_ok_days.dt.dayofweek != 5, _ok_days - pd.Timedelta(days=1))
            _ok_days = _ok_days.drop_duplicates().reset_index(drop=True)
            _gaps = _ok_days.diff().dt.days
            _idx = list(_ok_days.index[_gaps >= CATCHUP_GAP_DAYS])
            catchup_days = [_ok_days[i].strftime("%Y-%m-%d") for i in _idx]
            # A gap's removals land one run day LATER than its new listings: the
            # removal grace period (2 misses + 24h) confirms them on the next
            # run day, e.g. rent's -120 on 2026-09-03 after the 2026-09-02
            # catch-up. So the removed chart hides that day as well.
            rem_catchup_days = catchup_days + [_ok_days[i + 1].strftime("%Y-%m-%d")
                                               for i in _idx if i + 1 < len(_ok_days)]
        if catchup_days:
            new_by_date = new_by_date[~new_by_date.index.isin(catchup_days)]
            rem_by_date = rem_by_date[~rem_by_date.index.isin(rem_catchup_days)]
            _shown = [d for d in catchup_days if range_days is None or d >= _cut]
            _catchup_note = (
                '<p style="color:#3d3d3a;font-size:0.78rem;margin:2px 0 0;">'
                f'לא מוצגים ימי השלמה אחרי הפסקה בסריקה: {", ".join(pd.to_datetime(_shown).strftime("%d/%m/%y"))}</p>'
                if _shown else "")
        else:
            _catchup_note = ""

        with gc7:
            st.markdown('<div class="card"><div class="card-title"><span class="tip" data-tip="כמה מודעות ייחודיות נראו לראשונה ביום נתון. מקור: yad2_first_seen.json. ספירה לפי מזהה מודעה (לא URL מלא), כך שכפילויות booster לא נספרות. לחיצה על עמודה מציגה את הדירות.">ⓘ</span>מודעות חדשות שנוספו</div><div class="card-desc">לפי יום · ייחודיות בלבד · לחצ/י על עמודה לפירוט</div>', unsafe_allow_html=True)
            if len(new_by_date):
                fig_new = go.Figure(go.Bar(
                    x=new_by_date.index, y=new_by_date.values, customdata=new_by_date.index,
                    marker=dict(color=GREEN, line=dict(width=0)),
                    text=[f"+{int(v)}" for v in new_by_date.values],
                    textposition="outside",
                    textfont=dict(size=11, color="#141413", family="Assistant, Inter, sans-serif"),
                    cliponaxis=False,
                    hovertemplate="<b>%{x}</b><br>+%{y} מודעות חדשות<extra></extra>",
                ))
                _chart(fig_new, 320)
                fig_new.update_layout(yaxis_title="מודעות", bargap=0.3,
                                      xaxis=_date_xaxis("%d/%m"), margin=dict(t=40))
                new_event = st.plotly_chart(
                    fig_new, use_container_width=True,
                    config=dict(displayModeBar=False, scrollZoom=False),
                    on_select="rerun", key="chart_new_listings",
                    selection_mode="points",
                )
                if _catchup_note:
                    st.markdown(_catchup_note, unsafe_allow_html=True)
            else:
                new_event = None
                st.markdown('<p style="color:#3d3d3a;padding:24px 0;">אין נתוני first_seen.</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with gc8:
            _rem_reason = "נמכרו או הוסרו" if sel_deal == "sale" else "הושכרו או הוסרו"
            st.markdown(f'<div class="card"><div class="card-title"><span class="tip" data-tip="כמה מודעות ייחודיות הוסרו מהשוק ביום נתון ({_rem_reason}). מקור: yad2_dom_log.csv, מנוקה מכפילויות booster. לחיצה על עמודה מציגה את הדירות.">ⓘ</span>מודעות שהוסרו</div><div class="card-desc">לפי יום · ייחודיות בלבד · לחצ/י על עמודה לפירוט</div>', unsafe_allow_html=True)
            if len(rem_by_date):
                fig_rem = go.Figure(go.Bar(
                    x=rem_by_date.index, y=rem_by_date.values, customdata=rem_by_date.index,
                    marker=dict(color=RED, line=dict(width=0)),
                    text=[f"-{int(v)}" for v in rem_by_date.values],
                    textposition="outside",
                    textfont=dict(size=11, color="#141413", family="Assistant, Inter, sans-serif"),
                    cliponaxis=False,
                    hovertemplate="<b>%{x}</b><br>-%{y} מודעות הוסרו<extra></extra>",
                ))
                _chart(fig_rem, 320)
                fig_rem.update_layout(yaxis_title="מודעות", bargap=0.3,
                                      xaxis=_date_xaxis("%d/%m"), margin=dict(t=40))
                rem_event = st.plotly_chart(
                    fig_rem, use_container_width=True,
                    config=dict(displayModeBar=False, scrollZoom=False),
                    on_select="rerun", key="chart_removed_listings",
                    selection_mode="points",
                )
                if _catchup_note:
                    st.markdown(_catchup_note, unsafe_allow_html=True)
            else:
                rem_event = None
                st.markdown('<p style="color:#3d3d3a;padding:24px 0;">אין נתוני dom_log.</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # ── Drill-down: clicking a bar above shows the listings for that day ─────
        def _click_date(event):
            try:
                pts = event.selection.points if event else []
                if not pts:
                    return None
                # customdata carries the exact "YYYY-MM-DD" key; x on a date axis
                # may come back with a time suffix.
                cd = pts[0].get("customdata")
                if isinstance(cd, (list, tuple)):
                    cd = cd[0] if cd else None
                return str(cd or pts[0]["x"])[:10]
            except Exception:
                return None

        new_click_date = _click_date(new_event)
        rem_click_date = _click_date(rem_event)

        if new_click_date or rem_click_date:
            st.markdown('<div style="margin-top:14px"></div>', unsafe_allow_html=True)
            fs_map = load_first_seen_map(sel_deal)
            dom_full = load_dom_log(sel_deal)

            # Build details ONLY from the filtered active listings (fdf) so the
            # drill-down respects the filter bar above. Removed listings come from
            # dom_log filtered by neighborhood/type/price/size where those columns
            # exist in dom_log; rooms/floor aren't tracked there so those filters
            # only apply to active listings.
            details_by_lid = {}
            for _, r in fdf.iterrows():
                u = r.get("url") or ""
                if not u: continue
                li = _lid(u)
                details_by_lid[li] = {
                    "מחיר": r.get("price", ""),
                    "שכונה": r.get("neighborhood", "") or (str(r.get("info","")).split(",")[1].strip()
                                                           if len(str(r.get("info","")).split(",")) >= 3 else ""),
                    "סוג": r.get("apt_type", ""),
                    "חדרים": r.get("rooms", ""),
                    "קומה": r.get("floor", ""),
                    'מ"ר': r.get("size_sqm", ""),
                    "קישור": u,
                    "סטטוס": "פעיל",
                }
            if not dom_full.empty:
                dom_filtered = dom_full.copy()
                # Apply the filter-bar selections to dom_log rows where the
                # corresponding columns exist.
                if sel_nb != "הכל" and "neighborhood" in dom_filtered.columns:
                    dom_filtered = dom_filtered[dom_filtered["neighborhood"] == sel_nb]
                if sel_type != "הכל" and "apt_type" in dom_filtered.columns:
                    dom_filtered = dom_filtered[dom_filtered["apt_type"] == sel_type]
                if "price" in dom_filtered.columns:
                    dom_pn = dom_filtered["price"].astype(str).apply(parse_price_num)
                    dom_filtered = dom_filtered[dom_pn.between(price_range[0], price_range[1]) | dom_pn.isna()]
                if "size_sqm" in dom_filtered.columns:
                    dom_sz = pd.to_numeric(dom_filtered["size_sqm"], errors="coerce").fillna(size_range[0])
                    dom_filtered = dom_filtered[dom_sz.between(size_range[0], size_range[1])]
                for _, r in dom_filtered.iterrows():
                    u = r.get("url") or ""
                    li = _lid(u)
                    if not li or li in details_by_lid: continue
                    details_by_lid[li] = {
                        "מחיר": r.get("price", ""),
                        "שכונה": r.get("neighborhood", ""),
                        "סוג": r.get("apt_type", ""),
                        "חדרים": "",
                        "קומה": "",
                        'מ"ר': r.get("size_sqm", ""),
                        "קישור": u,
                        "סטטוס": "הוסר",
                    }

            if new_click_date:
                ids_for_date = [_lid(k) for k, d in fs_map.items() if d == new_click_date]
                rows = [details_by_lid[li] for li in ids_for_date if li in details_by_lid]
                st.markdown(f'<div class="section-title">דירות שנוספו ב־{new_click_date} ({len(rows)})</div>',
                            unsafe_allow_html=True)
                if rows:
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                else:
                    st.markdown('<div class="info-notice">אין נתונים לתאריך הזה.</div>', unsafe_allow_html=True)

            if rem_click_date and not dom_full.empty:
                # Start from the already-filtered dom rows so the drill-down honors
                # the filter bar. active_ids_now is global (any current listing
                # blocks it from being a "real removal") regardless of filters.
                dom_for_date = dom_filtered.copy()
                dom_for_date["_lid"] = dom_for_date["url"].astype(str).apply(_lid)
                dom_for_date = dom_for_date[dom_for_date["_lid"] != ""]
                dom_for_date = dom_for_date.drop_duplicates(subset=["_lid", "removed_date"])
                active_ids_now = {_lid(u) for u in df["url"] if u}
                dom_for_date = dom_for_date[~dom_for_date["_lid"].isin(active_ids_now)]
                dom_for_date = dom_for_date.sort_values("removed_date").drop_duplicates(subset=["_lid"], keep="last")
                dom_for_date = dom_for_date[dom_for_date["removed_date"] == rem_click_date]
                rem_rows = []
                for _, r in dom_for_date.iterrows():
                    rem_rows.append({
                        "מחיר": r.get("price", ""),
                        "שכונה": r.get("neighborhood", ""),
                        "סוג": r.get("apt_type", ""),
                        'מ"ר': r.get("size_sqm", ""),
                        "ימים בשוק": r.get("dom_days", ""),
                        "נראה לראשונה": r.get("first_seen", ""),
                        "קישור": r.get("url", ""),
                    })
                st.markdown(f'<div class="section-title">דירות שהוסרו ב־{rem_click_date} ({len(rem_rows)})</div>',
                            unsafe_allow_html=True)
                if rem_rows:
                    st.dataframe(pd.DataFrame(rem_rows), use_container_width=True, hide_index=True)
                else:
                    st.markdown('<div class="info-notice">אין נתונים לתאריך הזה.</div>', unsafe_allow_html=True)

elif page == "activity":
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
            if sel_rooms == "5": m &= d["_rm"] >= 5
            else:                m &= (d["_rm"] >= 4) & (d["_rm"] < 5)
            if sel_floor != "הכל": m &= d["_fl"] == int(sel_floor)
            return d[m].drop(columns=["_pn","_sz","_rm","_fl","_nb","_tp"], errors="ignore")

        new_df   = _apply_filters(new_df)
        rem_df   = _apply_filters(rem_df)
        price_df = _apply_filters(price_df)

        cuts_n  = len(price_df[price_df["delta"] < 0]) if len(price_df) else 0
        rises_n = len(price_df[price_df["delta"] > 0]) if len(price_df) else 0

        # Count "uniquely new" — listings whose first_seen date matches the current run date
        fs_path = deal_path("yad2_first_seen.json", sel_deal)
        try:
            with open(fs_path, encoding="utf-8") as _f:
                _first_seen = json.load(_f)
        except Exception:
            _first_seen = {}
        curr_date = datetime.fromtimestamp(os.path.getmtime(data_file_path)).strftime("%Y-%m-%d")
        if len(new_df) > 0:
            unique_new = sum(1 for u in new_df.get("url", []) if _first_seen.get(u or "", "") == curr_date)
        else:
            unique_new = 0
        total_ever = len(_first_seen)

        st.markdown(f"""
        <div class="delta-row">
            <div class="delta-tile"><div class="d-label">מודעות חדשות</div><div class="d-value green">+{len(new_df)}</div><div class="d-sub">מתוכן <b>{unique_new}</b> חדשות לחלוטין · מאז {prev_time}</div></div>
            <div class="delta-tile"><div class="d-label">{"הוסרו / נמכרו" if sel_deal == "sale" else "הוסרו / הושכרו"}</div><div class="d-value red">-{len(rem_df)}</div><div class="d-sub">יצאו מהשוק</div></div>
            <div class="delta-tile"><div class="d-label">הורדות מחיר</div><div class="d-value green">{cuts_n}</div><div class="d-sub">מחיר הופחת</div></div>
            <div class="delta-tile"><div class="d-label">עליות מחיר</div><div class="d-value red">{rises_n}</div><div class="d-sub">מחיר עלה</div></div>
        </div>
        <div class="filter-hint" style="margin-bottom:18px">סך-כל המודעות הייחודיות שראינו אי-פעם: <b>{total_ever:,}</b></div>
        """, unsafe_allow_html=True)

        def chg_table(data, mode="normal"):
            if data is None or len(data) == 0:
                st.markdown('<p style="color:#8e8b82;font-size:0.84rem;padding:8px 0;">אין נתונים.</p>', unsafe_allow_html=True)
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
            first_seen_map = load_first_seen_map(sel_deal)
            dom_log_df     = load_dom_log(sel_deal)

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

elif page == "listings":
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
                    this.gui.style.cssText = 'display:inline-block;padding:5px 12px;background:linear-gradient(135deg,#f5f0e8,#efe9de);border:1px solid #e8e0d2;border-radius:8px;color:#a9583e;font-weight:700;text-decoration:none;font-size:0.78rem;';
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
                "border": "1px solid #e6dfd8 !important",
                "border-radius": "14px !important",
                "overflow": "hidden",
                "box-shadow": "0 1px 3px rgba(20,20,19,0.04) !important",
            },
            ".ag-header": {
                "background": "#faf9f5 !important",
                "border-bottom": "1px solid #e6dfd8 !important",
            },
            ".ag-header-cell": {"font-family": "Assistant, Inter, sans-serif !important"},
            ".ag-header-cell-menu-button": {
                "opacity": "1 !important",
                "color": "#8e8b82",
                "transition": "color 0.15s",
            },
            ".ag-header-cell-menu-button:hover": {
                "color": "#cc785c !important",
            },
            ".ag-header-cell-label": {
                "font-weight": "700 !important",
                "font-size": "0.95rem !important",
                "color": "#141413 !important",
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
                "font-family": "Assistant, Inter, sans-serif !important",
                "color": "#141413 !important",
                "border-bottom": "1px solid #f5f0e8 !important",
            },
            ".ag-row:hover": {"background": "#faf9f5 !important"},
            ".ag-row-odd": {"background": "#faf9f5 !important"},
            ".ag-cell": {"display": "flex !important", "align-items": "center !important"},
            ".ag-set-filter-list": {"direction": "rtl"},
        }
    )

st.markdown("""
<div style="text-align:center;padding:28px 0 18px;margin-top:24px;border-top:1px solid #e6dfd8;color:#8e8b82;font-size:0.74rem;font-weight:500;">
    מעקב שוק יד2 · רעננה · מתעדכן 09:00 ו-20:00
</div>
""", unsafe_allow_html=True)
