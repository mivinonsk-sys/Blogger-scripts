# pip install streamlit openai pandas
#
# Запуск: streamlit run blogger_reels_analyzer.py

import json
import re
import time
import sqlite3
import hashlib
import secrets
import statistics
import html
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import unquote

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

try:
    import httpx
except ImportError:
    httpx = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

# ============================================================================
# НАСТРОЙКА СТРАНИЦЫ
# ============================================================================
st.set_page_config(
    page_title="ТрейдИндустрия | Анализ роликов блогера",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- УПРАВЛЕНИЕ ТЕМАМИ ---
query_params = st.query_params

if "theme" in query_params:
    selected_theme_param = query_params["theme"]
    if selected_theme_param in ["🌙 Ночь", "☀️ День"]:
        st.session_state.theme_mode = selected_theme_param

if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "🌙 Ночь"

theme_class = "theme-night" if "Ночь" in st.session_state.theme_mode else "theme-day"
is_night = "Ночь" in st.session_state.theme_mode
is_night_js = "true" if is_night else "false"

# === ПРЕМИУМ СТИЛИ И ГЛАССМОРФИЗМ ===
st.markdown(f"""
    <head>
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    </head>

    <style>
    /* --- Адаптация под телефоны и ПК --- */
    @media (min-width: 992px) {{
        header[data-testid="stHeader"] {{ display: none !important; }}
        [data-testid="stSidebarCollapseButton"],
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="collapsedControl"] {{ display: none !important; }}
        section[data-testid="stSidebar"] {{
            transform: none !important;
            visibility: visible !important;
            min-width: 300px !important;
        }}
    }}

    @media (max-width: 991px) {{
        header[data-testid="stHeader"] {{ background: transparent !important; }}
        .global-theme-switcher {{
            right: 60px !important;
            transform: scale(0.85);
            transform-origin: right top;
        }}
        .stMainBlockContainer {{ padding-top: 4rem !important; padding-left: 1rem !important; padding-right: 1rem !important; }}
    }}

    html, body, [class*="css"] {{ font-family: 'Plus Jakarta Sans', sans-serif !important; }}

    .global-theme-switcher {{
        position: fixed !important; top: 20px !important; right: 30px !important;
        width: auto !important; display: inline-flex !important; flex-direction: row !important;
        gap: 6px; padding: 6px; border-radius: 30px; backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.2);
        z-index: 9999999; box-shadow: 0 15px 35px rgba(0,0,0,0.35);
    }}
    .theme-night .global-theme-switcher {{ background: rgba(15, 23, 42, 0.75); border-color: rgba(56, 189, 248, 0.35); }}
    .theme-day .global-theme-switcher {{ background: rgba(255, 255, 255, 0.65); border-color: rgba(10, 142, 217, 0.2); }}

    .theme-opt-btn {{
        padding: 6px 14px; border-radius: 20px; border: none; font-weight: 700; cursor: pointer;
        font-size: 13px; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); text-decoration: none !important;
        display: inline-block; text-align: center; white-space: nowrap;
    }}
    .theme-night .theme-opt-btn.active {{ background: linear-gradient(135deg, #38bdf8 0%, #818cf8 100%); color: #030712 !important; box-shadow: 0 0 20px rgba(56, 189, 248, 0.6); }}
    .theme-night .theme-opt-btn.inactive {{ background: transparent; color: #94a3b8 !important; }}
    .theme-night .theme-opt-btn.inactive:hover {{ color: #ffffff !important; }}
    .theme-day .theme-opt-btn.active {{ background: linear-gradient(135deg, #0a8ed9 0%, #0670b0 100%); color: #ffffff !important; box-shadow: 0 0 16px rgba(10, 142, 217, 0.35); }}
    .theme-day .theme-opt-btn.inactive {{ background: transparent; color: #5a8aa8 !important; }}
    .theme-day .theme-opt-btn.inactive:hover {{ color: #0a3a5c !important; }}

    @keyframes cosmicGradient {{ 0% {{background-position:0% 50%;}} 50% {{background-position:100% 50%;}} 100% {{background-position:0% 50%;}} }}
    @keyframes moveStars {{ from {{background-position:0 0;}} to {{background-position:-1000px 1000px;}} }}

    .theme-night .stApp {{
        background: linear-gradient(-45deg, #030712, #0b0f19, #0f172a, #131128, #050b14);
        background-size: 400% 400%; animation: cosmicGradient 25s ease infinite; color: #e2e8f0 !important;
    }}
    .theme-night .stApp::before {{
        content: ""; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
        background-image:
            radial-gradient(1px 1px at 50px 100px, #ffffff, rgba(0,0,0,0)),
            radial-gradient(2.5px 2.5px at 200px 300px, #38bdf8, rgba(0,0,0,0)),
            radial-gradient(1.5px 1.5px at 400px 150px, #ffffff, rgba(0,0,0,0)),
            radial-gradient(3px 3px at 650px 450px, #818cf8, rgba(0,0,0,0));
        background-repeat: repeat; background-size: 900px 900px; opacity: 0.55;
        animation: moveStars 140s linear infinite; pointer-events: none !important; z-index: 0 !important;
    }}
    .theme-night [data-testid="stSidebar"] {{
        background-color: rgba(11, 15, 25, 0.9) !important; backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px); border-right: 1px solid rgba(255, 255, 255, 0.05);
    }}

    .glass-metric {{
        background: rgba(15, 23, 42, 0.65) !important; backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px);
        border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 18px; padding: 20px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.1);
        transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1); height: 100%; position: relative;
    }}
    .glass-metric:hover {{ transform: translateY(-4px); border-color: rgba(56, 189, 248, 0.5); box-shadow: 0 15px 35px rgba(56, 189, 248, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.2); }}
    .metric-title {{ font-size: 12px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }}
    .metric-value {{ font-size: 20px; font-weight: 800; color: #f8fafc; letter-spacing: -0.3px; }}
    .metric-delta {{ font-size: 12px; font-weight: 600; margin-top: 6px; display: inline-block; }}

    .ai-report-glass {{
        background: rgba(15, 23, 42, 0.72) !important; backdrop-filter: blur(22px); -webkit-backdrop-filter: blur(22px);
        border: 1px solid rgba(129, 140, 248, 0.35); border-radius: 20px; padding: 26px;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.1); color: #e2e8f0;
        margin-bottom: 18px;
    }}

    .theme-night input, .theme-night select, .theme-night textarea {{
        background-color: rgba(15, 23, 42, 0.85) !important; color: #f1f5f9 !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
    }}
    .theme-night div.stButton > button, .theme-night div.stFormSubmitButton > button {{
        background: rgba(255, 255, 255, 0.15) !important; backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.3) !important; color: #f8fafc !important;
        font-weight: 700 !important; transition: all 0.3s ease;
    }}

    @keyframes dayGradient {{ 0% {{background-position:0% 50%;}} 50% {{background-position:100% 50%;}} 100% {{background-position:0% 50%;}} }}
    .theme-day .stApp {{
        background: linear-gradient(135deg, #e8f4fd 0%, #d0ecfb 30%, #b8e2f8 60%, #a0d8f4 100%);
        background-size: 300% 300%; animation: dayGradient 40s ease infinite; color: #0a3a5c !important;
    }}
    .theme-day .stApp::before {{
        content: ""; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
        background-image:
            radial-gradient(500px 250px at 15% 25%, rgba(255,255,255,0.45) 0%, rgba(255,255,255,0) 70%),
            radial-gradient(600px 300px at 55% 65%, rgba(255,255,255,0.35) 0%, rgba(255,255,255,0) 70%),
            radial-gradient(400px 200px at 85% 20%, rgba(255,255,255,0.4) 0%, rgba(255,255,255,0) 70%);
        pointer-events: none !important; z-index: 0 !important;
    }}
    .stMainBlockContainer, [data-testid="stSidebar"], .global-theme-switcher {{ position: relative; z-index: 2 !important; }}

    .theme-day [data-testid="stSidebar"] {{
        background: rgba(255,255,255,0.72) !important;
        backdrop-filter: blur(20px) saturate(1.4); -webkit-backdrop-filter: blur(20px) saturate(1.4);
        border-right: 0.5px solid rgba(10,142,217,0.15) !important;
    }}
    .theme-day [data-testid="stSidebar"] label,
    .theme-day [data-testid="stSidebar"] span,
    .theme-day [data-testid="stSidebar"] p {{
        color: #0a3a5c !important;
    }}
    .theme-day [data-testid="stSidebar"] div {{
        color: #1a5a7a !important;
    }}
    .theme-day [data-testid="stSidebar"] .stSelectbox label,
    .theme-day [data-testid="stSidebar"] .stNumberInput label,
    .theme-day [data-testid="stSidebar"] .stTextInput label,
    .theme-day [data-testid="stSidebar"] .stTextArea label,
    .theme-day [data-testid="stSidebar"] .stCheckbox label {{
        font-size: 12px !important; font-weight: 700 !important; color: #3a6a88 !important;
        text-transform: uppercase !important; letter-spacing: 0.4px !important;
    }}
    .theme-day [data-testid="stSidebar"] h3 {{
        color: #0a3a5c !important; font-size: 14px !important; font-weight: 700 !important;
    }}

    .theme-day .glass-metric {{
        background: rgba(255,255,255,0.65) !important;
        backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
        border: 0.5px solid rgba(10,142,217,0.15) !important; border-radius: 14px !important;
        box-shadow: none !important;
    }}
    .theme-day .glass-metric:hover {{
        border-color: rgba(10,142,217,0.35) !important;
        transform: translateY(-3px);
        box-shadow: 0 8px 24px rgba(10,142,217,0.1) !important;
    }}
    .theme-day .metric-title {{ color: #5a8aa8 !important; }}
    .theme-day .metric-value {{ color: #0a3a5c !important; }}

    .theme-day .ai-report-glass {{
        background: rgba(255,255,255,0.7) !important;
        backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px);
        border: 0.5px solid rgba(10,142,217,0.18) !important; border-radius: 14px !important;
        box-shadow: none !important; color: #0a3a5c !important;
    }}

    .theme-day input, .theme-day select, .theme-day textarea {{
        background: rgba(255,255,255,0.8) !important; color: #0a3a5c !important;
        border: 0.5px solid rgba(10,142,217,0.25) !important; border-radius: 8px !important;
    }}
    .theme-day input:focus, .theme-day select:focus, .theme-day textarea:focus {{
        border-color: rgba(10,142,217,0.5) !important;
        box-shadow: 0 0 0 2px rgba(10,142,217,0.1) !important;
    }}

    .theme-day h1, .theme-day h2, .theme-day h3, .theme-day h4 {{ color: #0a3a5c !important; }}
    .theme-day span, .theme-day p {{ color: #1a5a7a !important; }}

    .theme-day div.stButton > button,
    .theme-day div.stFormSubmitButton > button {{
        background: rgba(255,255,255,0.6) !important;
        border: 0.5px solid rgba(10,142,217,0.25) !important; border-radius: 10px !important;
        color: #0a8ed9 !important; font-weight: 700 !important;
        transition: all 0.25s ease !important;
    }}
    .theme-day div.stButton > button:hover,
    .theme-day div.stFormSubmitButton > button:hover {{
        background: linear-gradient(135deg, #0a8ed9 0%, #0670b0 100%) !important;
        border-color: #0a8ed9 !important; color: #ffffff !important;
        transform: translateY(-2px); box-shadow: 0 6px 20px rgba(10,142,217,0.25) !important;
    }}
    .theme-day div.stButton > button[kind="primary"],
    .theme-day div.stFormSubmitButton > button[kind="primary"] {{
        background: linear-gradient(135deg, #0a8ed9 0%, #0670b0 100%) !important;
        color: #ffffff !important; border-color: transparent !important;
    }}
    .theme-day div.stButton > button[kind="primary"]:hover {{
        box-shadow: 0 8px 24px rgba(10,142,217,0.35) !important; transform: translateY(-2px);
    }}

    .theme-day .badge-high {{ background: rgba(16,185,129,0.1) !important; color: #0d9668 !important; border-color: rgba(16,185,129,0.3) !important; }}
    .theme-day .badge-medium {{ background: rgba(245,158,11,0.1) !important; color: #b45309 !important; border-color: rgba(245,158,11,0.3) !important; }}
    .theme-day .badge-low {{ background: rgba(99,102,241,0.1) !important; color: #5346b5 !important; border-color: rgba(99,102,241,0.3) !important; }}
    .theme-day .fit-high {{ color: #0d9668 !important; }}
    .theme-day .fit-medium {{ color: #b45309 !important; }}
    .theme-day .fit-low {{ color: #dc2626 !important; }}

    .theme-day .custom-warning {{
        background: rgba(10,142,217,0.06) !important; border-color: rgba(10,142,217,0.2) !important;
        color: #1a5a8a !important;
    }}
    .theme-day .custom-error {{
        background: rgba(220,38,38,0.06) !important; border-color: rgba(220,38,38,0.3) !important;
        color: #dc2626 !important;
    }}
    [data-testid="stWarning"], [data-testid="stError"] {{ display: none !important; }}

    .fit-high {{ color: #10b981; font-weight: 800; }}
    .fit-medium {{ color: #f59e0b; font-weight: 800; }}
    .fit-low {{ color: #ef4444; font-weight: 800; }}
    .pattern-badge {{
        display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 700;
        margin-right: 6px; margin-bottom: 6px;
    }}
    .badge-high {{ background: rgba(16,185,129,0.18); color: #10b981; border: 1px solid rgba(16,185,129,0.4); }}
    .badge-medium {{ background: rgba(245,158,11,0.18); color: #f59e0b; border: 1px solid rgba(245,158,11,0.4); }}
    .badge-low {{ background: rgba(239,68,68,0.18); color: #ef4444; border: 1px solid rgba(239,68,68,0.4); }}

    .fade-in-container {{ animation: smoothAppearScale 0.7s cubic-bezier(0.16, 1, 0.3, 1) forwards; }}

    .pin-wrap {{ max-width: 460px; margin: 40px auto 4px; text-align: center; }}
    .pin-title {{ font-size: 24px; font-weight: 800; margin-bottom: 8px; letter-spacing: -0.4px; }}
    .pin-subtitle {{ font-size: 14px; margin-bottom: 22px; line-height: 1.5; }}
    .theme-day .pin-title {{ color: #0a3a5c; }}
    .theme-day .pin-subtitle {{ color: #5a8aa8; }}
    .theme-night .pin-title {{ color: #f8fafc; }}
    .theme-night .pin-subtitle {{ color: #94a3b8; }}

    .pin-single div[data-testid="stTextInput"] input {{
        text-align: center !important;
        font-size: 30px !important;
        font-weight: 700 !important;
        letter-spacing: 18px !important;
        text-indent: 18px !important;
        height: 66px !important;
        border-radius: 14px !important;
        transition: all 0.2s ease !important;
    }}
    .theme-day .pin-single div[data-testid="stTextInput"] input {{
        background: rgba(255,255,255,0.85) !important;
        border: 1.5px solid rgba(10,142,217,0.25) !important;
        color: #0a3a5c !important;
    }}
    .theme-day .pin-single div[data-testid="stTextInput"] input:focus {{
        border-color: #0a8ed9 !important;
        box-shadow: 0 0 0 3px rgba(10,142,217,0.12) !important;
    }}
    .theme-night .pin-single div[data-testid="stTextInput"] input {{
        background: #1e1e1e !important;
        border: 1.5px solid rgba(255,255,255,0.15) !important;
        color: #ffffff !important;
    }}
    .theme-night .pin-single div[data-testid="stTextInput"] input:focus {{
        border-color: #ffffff !important;
        box-shadow: 0 0 0 3px rgba(255,255,255,0.08) !important;
    }}
    .pin-single div[data-testid="stTextInput"] button {{ display: none !important; }}
    .pin-single div[data-testid="stTextInput"] label {{ display: none !important; }}

    .history-card {{
        border-radius: 14px; padding: 16px 18px; margin-bottom: 10px;
        transition: all 0.25s ease; position: relative;
    }}
    .theme-day .history-card {{
        background: rgba(255,255,255,0.68); border: 0.5px solid rgba(10,142,217,0.18);
    }}
    .theme-day .history-card:hover {{
        border-color: rgba(10,142,217,0.4); transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(10,142,217,0.1);
    }}
    .theme-night .history-card {{
        background: rgba(15,23,42,0.65); border: 1px solid rgba(56,189,248,0.2);
        backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
    }}
    .theme-night .history-card:hover {{
        border-color: rgba(56,189,248,0.45); transform: translateY(-2px);
    }}
    .history-handle {{ font-size: 16px; font-weight: 800; letter-spacing: -0.2px; }}
    .theme-day .history-handle {{ color: #0a3a5c; }}
    .theme-night .history-handle {{ color: #f8fafc; }}
    .history-date {{ font-size: 12px; font-weight: 600; }}
    .theme-day .history-date {{ color: #5a8aa8; }}
    .theme-night .history-date {{ color: #94a3b8; }}
    .history-chip {{
        display: inline-block; padding: 3px 10px; border-radius: 12px;
        font-size: 11px; font-weight: 700; margin-right: 6px; margin-top: 8px;
    }}
    .theme-day .history-chip {{
        background: rgba(10,142,217,0.08); color: #0a8ed9; border: 0.5px solid rgba(10,142,217,0.2);
    }}
    .theme-night .history-chip {{
        background: rgba(56,189,248,0.12); color: #38bdf8; border: 1px solid rgba(56,189,248,0.25);
    }}
    .manager-stat-card {{
        border-radius: 14px; padding: 18px; text-align: center; transition: all 0.25s ease;
    }}
    .theme-day .manager-stat-card {{
        background: rgba(255,255,255,0.68); border: 0.5px solid rgba(10,142,217,0.18);
    }}
    .theme-night .manager-stat-card {{
        background: rgba(15,23,42,0.65); border: 1px solid rgba(56,189,248,0.2);
        backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
    }}
    .empty-state {{
        text-align: center; padding: 48px 24px; border-radius: 16px;
    }}
    .theme-day .empty-state {{ background: rgba(255,255,255,0.45); color: #5a8aa8; }}
    .theme-night .empty-state {{ background: rgba(15,23,42,0.4); color: #94a3b8; }}
    @keyframes smoothAppearScale {{ from {{opacity:0; transform: translateY(15px) scale(0.92);}} to {{opacity:1; transform: translateY(0) scale(1);}} }}

    </style>
""", unsafe_allow_html=True)

# --- ГЛОБАЛЬНЫЙ СКРИПТ ПЕРЕКЛЮЧАТЕЛЯ ТЕМЫ ---
components.html(f"""
<script>
try {{
    const parentDoc = window.parent.document;
    const body = parentDoc.body;
    const themeClass = "{theme_class}";
    body.classList.remove('theme-night', 'theme-day');
    body.classList.add(themeClass);

    const isNight = {is_night_js};
    const nightUrl = new URL(parentDoc.location.href); nightUrl.searchParams.set('theme', '🌙 Ночь');
    const dayUrl = new URL(parentDoc.location.href); dayUrl.searchParams.set('theme', '☀️ День');

    let globalSwitcher = parentDoc.getElementById('global-theme-switcher-unique');
    if (!globalSwitcher) {{
        globalSwitcher = parentDoc.createElement('div');
        globalSwitcher.id = 'global-theme-switcher-unique';
        globalSwitcher.className = 'global-theme-switcher';
        parentDoc.body.appendChild(globalSwitcher);
    }}
    globalSwitcher.innerHTML = `
        <a href="${{nightUrl.toString()}}" class="theme-opt-btn ${{isNight ? 'active' : 'inactive'}}">🌙 Ночь</a>
        <a href="${{dayUrl.toString()}}" class="theme-opt-btn ${{!isNight ? 'active' : 'inactive'}}">☀️ День</a>
    `;
}} catch(e) {{
    console.log("Ограничение iframe: переключатель тем скрыт.");
}}
</script>
""", height=0, width=0)

# ============================================================================
# ХРАНИЛИЩЕ ДАННЫХ (SQLite)
# ВНИМАНИЕ: На бесплатных серверах вроде Streamlit Community Cloud эта БД
# обнуляется при перезапуске (засыпании) сервера. Для продакшена используйте
# внешнее облачное хранилище.
# ============================================================================
DB_PATH = Path(__file__).parent / "blogger_analyses.db"

def db_connect():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db_connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manager TEXT NOT NULL,
                blogger_url TEXT NOT NULL,
                blogger_handle TEXT,
                created_at TEXT NOT NULL,
                data_source TEXT,
                model_used TEXT,
                model_used_analyst TEXT,
                model_used_scenarist TEXT,
                reels_count INTEGER,
                median_views INTEGER,
                viral_count INTEGER,
                product_brief TEXT,
                metrics_json TEXT,
                top_viral_json TEXT,
                result_json TEXT
            )
        """)
        # Миграция для баз, созданных до разделения ИИ на роли «Аналитик» / «Сценарист»:
        # аккуратно добавляем недостающие колонки, не трогая уже накопленную историю.
        existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(analyses)").fetchall()}
        if "model_used_analyst" not in existing_cols:
            conn.execute("ALTER TABLE analyses ADD COLUMN model_used_analyst TEXT")
        if "model_used_scenarist" not in existing_cols:
            conn.execute("ALTER TABLE analyses ADD COLUMN model_used_scenarist TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_manager ON analyses(manager)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_created ON analyses(created_at)")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS managers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                password_hash TEXT,
                salt TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS apify_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT NOT NULL UNIQUE,
                label TEXT,
                date_added TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'unknown',
                usage_pct REAL,
                usage_detail TEXT,
                cycle_reset_at TEXT,
                last_checked_at TEXT
            )
        """)
        # Миграция: если в старых версиях уже был задан единственный cfg_apify_token в app_settings,
        # но таблица apify_keys ещё пуста — переносим его туда одной записью, чтобы при обновлении
        # приложения ключ не потерялся и пул ключей не оказался пустым.
        try:
            legacy_row = conn.execute("SELECT value FROM app_settings WHERE key = 'cfg_apify_token'").fetchone()
            legacy_token = (legacy_row["value"] or "").strip() if legacy_row else ""
            keys_count = conn.execute("SELECT COUNT(*) AS c FROM apify_keys").fetchone()["c"]
            if legacy_token and keys_count == 0:
                conn.execute(
                    "INSERT OR IGNORE INTO apify_keys (token, label, date_added, status) VALUES (?, ?, ?, 'unknown')",
                    (legacy_token, "перенесён автоматически из старых настроек", datetime.now().isoformat(timespec="seconds")),
                )
        except Exception:
            pass
        existing = conn.execute("SELECT COUNT(*) AS c FROM managers").fetchone()["c"]
        if existing == 0:
            seed = [
                "Анастасия Виницкая", "Андрей Колмагоров", "Диана Комисарова",
                "Екатерина Гантимурова", "Екатерина Зиновьева", "Катерина Запара",
                "Марина Казьмина", "Марина Капитанова", "Оксана Шульга",
                "Ольга Ребреева", "Юлия Ильина",
            ]
            now = datetime.now().isoformat(timespec="seconds")
            conn.executemany(
                "INSERT INTO managers (name, password_hash, salt, is_active, created_at) VALUES (?, NULL, NULL, 1, ?)",
                [(n, now) for n in seed],
            )

def hash_password(password: str, salt: str = None):
    if salt is None:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000)
    return dk.hex(), salt

def verify_password(password: str, password_hash: str, salt: str) -> bool:
    if not password_hash or not salt:
        return True
    candidate, _ = hash_password(password, salt)
    return secrets.compare_digest(candidate, password_hash)

def get_managers(active_only=True):
    try:
        with db_connect() as conn:
            q = "SELECT * FROM managers"
            if active_only:
                q += " WHERE is_active = 1"
            q += " ORDER BY name"
            return [dict(r) for r in conn.execute(q).fetchall()]
    except Exception:
        return []

def get_manager(name):
    try:
        with db_connect() as conn:
            row = conn.execute("SELECT * FROM managers WHERE name = ?", (name,)).fetchone()
            return dict(row) if row else None
    except Exception:
        return None

def add_manager(name, password=None):
    name = (name or "").strip()
    if not name: return False, "Имя не может быть пустым."
    if len(name) > 100: return False, "Имя слишком длинное."
    try:
        pw_hash, salt = hash_password(password) if password else (None, None)
        with db_connect() as conn:
            conn.execute(
                "INSERT INTO managers (name, password_hash, salt, is_active, created_at) VALUES (?, ?, ?, 1, ?)",
                (name, pw_hash, salt, datetime.now().isoformat(timespec="seconds")),
            )
        return True, f"Менеджер «{name}» добавлен."
    except sqlite3.IntegrityError:
        return False, f"Менеджер «{name}» уже существует."
    except Exception as exc:
        return False, f"Ошибка: {exc}"

def set_manager_password(name, password):
    try:
        pw_hash, salt = hash_password(password) if password else (None, None)
        with db_connect() as conn:
            conn.execute("UPDATE managers SET password_hash = ?, salt = ? WHERE name = ?", (pw_hash, salt, name))
        return True, ("PIN установлен." if password else "PIN снят — вход без PIN.")
    except Exception as exc:
        return False, f"Ошибка: {exc}"

def rename_manager(old_name, new_name):
    new_name = (new_name or "").strip()
    if not new_name: return False, "Новое имя не может быть пустым."
    try:
        with db_connect() as conn:
            conn.execute("UPDATE managers SET name = ? WHERE name = ?", (new_name, old_name))
            conn.execute("UPDATE analyses SET manager = ? WHERE manager = ?", (new_name, old_name))
        return True, f"Переименован: «{old_name}» → «{new_name}»."
    except sqlite3.IntegrityError:
        return False, f"Менеджер «{new_name}» уже существует."
    except Exception as exc:
        return False, f"Ошибка: {exc}"

def delete_manager(name, delete_history=False):
    try:
        with db_connect() as conn:
            conn.execute("DELETE FROM managers WHERE name = ?", (name,))
            if delete_history:
                conn.execute("DELETE FROM analyses WHERE manager = ?", (name,))
        return True, "Менеджер удален."
    except Exception as exc:
        return False, f"Ошибка: {exc}"

def count_manager_analyses(name):
    try:
        with db_connect() as conn:
            return conn.execute("SELECT COUNT(*) AS c FROM analyses WHERE manager = ?", (name,)).fetchone()["c"]
    except Exception:
        return 0


# ============================================================================
# ПУЛ КЛЮЧЕЙ APIFY: неограниченное число API-токенов, статус лимитов и автопереключение
# ============================================================================
# Лимиты Apify считаются на уровне АККАУНТА (а не отдельного токена) и сбрасываются не по
# фиксированной календарной дате и не через N дней после исчерпания, а по собственному
# ежемесячному биллинг-циклу аккаунта (см. официальный ответ users/me/limits — поле
# monthlyUsageCycle.startAt/endAt). Поэтому вместо того чтобы самим высчитывать «когда лимит
# освободится» по дате добавления ключа, мы прямо спрашиваем это у Apify (check_apify_key_live)
# и сохраняем последний известный статус — так дата сброса всегда точная, а не предположение.
def sanitize_apify_token(raw: str) -> str:
    """В поле для токена иногда вставляют не сам токен, а целую ссылку, скопированную из консоли
    Apify (например «https://api.apify.com/v2/actor-runs?token=apify_api_XXXX») — тогда реальный
    токен спрятан внутри параметра token=. Вытаскиваем именно его, а не храним нерабочую ссылку
    целиком: иначе любой вызов к Apify с таким «токеном» падает с 401, хотя сам ключ рабочий."""
    text = (raw or "").strip().strip("\"'")
    if not text:
        return text
    if "token=" in text:
        tail = text.rsplit("token=", 1)[-1]
        tail = tail.split("&")[0]
        text = unquote(tail).strip()
    return text

def add_apify_key(token, label=None):
    token = sanitize_apify_token(token)
    if not token:
        return False, "Ключ не может быть пустым."
    if len(token) < 10:
        return False, "Это не похоже на реальный Apify API-токен."
    try:
        with db_connect() as conn:
            conn.execute(
                "INSERT INTO apify_keys (token, label, date_added, status) VALUES (?, ?, ?, 'unknown')",
                (token, (label or "").strip() or None, datetime.now().isoformat(timespec="seconds")),
            )
        return True, "Ключ Apify добавлен."
    except sqlite3.IntegrityError:
        return False, "Такой ключ уже есть в списке."
    except Exception as exc:
        return False, f"Ошибка: {exc}"

def get_apify_keys():
    """Все сохранённые ключи, от старых к новым (порядок добавления — как ориентир пользователю)."""
    try:
        with db_connect() as conn:
            rows = conn.execute("SELECT * FROM apify_keys ORDER BY date_added ASC, id ASC").fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []

def delete_apify_key(key_id):
    try:
        with db_connect() as conn:
            conn.execute("DELETE FROM apify_keys WHERE id = ?", (key_id,))
        return True, "Ключ удалён."
    except Exception as exc:
        return False, f"Ошибка: {exc}"

def update_apify_key_token(key_id, new_token):
    """Самоисправление: если сохранённый «токен» на деле оказался целой ссылкой, из которой мы
    смогли вытащить настоящий токен (см. sanitize_apify_token), перезаписываем запись — без этого
    ошибка формата повторялась бы при каждой проверке и каждом реальном запросе."""
    try:
        with db_connect() as conn:
            conn.execute("UPDATE apify_keys SET token = ? WHERE id = ?", (new_token, key_id))
        return True
    except Exception:
        return False

def update_apify_key_status(key_id, status, usage_pct=None, usage_detail=None, cycle_reset_at=None):
    """Записывает результат живой проверки лимитов (check_apify_key_live) — статус, % использования
    месячного бюджета и дату сброса цикла ПО ДАННЫМ САМОГО APIFY (не наш расчёт)."""
    try:
        with db_connect() as conn:
            conn.execute(
                "UPDATE apify_keys SET status = ?, usage_pct = ?, usage_detail = ?, cycle_reset_at = ?, "
                "last_checked_at = ? WHERE id = ?",
                (status, usage_pct, usage_detail, cycle_reset_at, datetime.now().isoformat(timespec="seconds"), key_id),
            )
        return True
    except Exception:
        return False

def get_apify_key_pool():
    """Ключи в порядке предпочтения для реального запроса: сначала «зелёные» (точно есть лимиты),
    затем «unknown» (ещё не проверялись — оптимистично пробуем), затем «красные» в последнюю очередь
    (вдруг цикл уже обновился, а мы это ещё не перепроверили). Внутри каждой группы — ключи, которые
    проверялись/использовались раньше остальных, чтобы нагрузка распределялась по пулу равномерно."""
    order = {"green": 0, "unknown": 1, "red": 2}
    keys = get_apify_keys()
    return sorted(keys, key=lambda k: (order.get(k.get("status"), 1), k.get("last_checked_at") or ""))

def get_setting(key, default=None):
    try:
        with db_connect() as conn:
            row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else default
    except Exception:
        return default

def set_setting(key, value):
    try:
        with db_connect() as conn:
            conn.execute(
                "INSERT INTO app_settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, str(value)),
            )
        return True
    except Exception:
        return False

# Вспомогательные функции для типизированного чтения из БД
def load_setting_str(key, default=""):
    val = get_setting(key)
    return val if val is not None else default

def load_setting_int(key, default=0):
    val = get_setting(key)
    return int(val) if val is not None else default

def load_setting_float(key, default=0.0):
    val = get_setting(key)
    return float(val) if val is not None else default

def load_setting_bool(key, default=False):
    val = get_setting(key)
    return val == "True" if val is not None else default


ADMIN_PIN_DEFAULT = "0000"
def verify_admin_pin(pin: str) -> bool:
    stored_hash = get_setting("admin_pin_hash")
    stored_salt = get_setting("admin_pin_salt")
    if not stored_hash or not stored_salt:
        return pin == ADMIN_PIN_DEFAULT
    candidate, _ = hash_password(pin, stored_salt)
    return secrets.compare_digest(candidate, stored_hash)

def set_admin_pin(new_pin: str):
    pin_hash, salt = hash_password(new_pin)
    ok = set_setting("admin_pin_hash", pin_hash) and set_setting("admin_pin_salt", salt)
    return (True, "PIN администратора изменён.") if ok else (False, "Не удалось сохранить PIN.")

def admin_pin_is_default() -> bool:
    return not (get_setting("admin_pin_hash") and get_setting("admin_pin_salt"))

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ СОСТОЯНИЯ ИЗ БАЗЫ ДАННЫХ (ГЛОБАЛЬНЫЕ НАСТРОЙКИ)
# ============================================================================
DEFAULT_BRIEF_TEXT = """ТОВАР: утягивающие майки (женское корректирующее бельё/топы)

Этот бриф — единый статичный документ. Он не меняется под блогера: персонализацию под конкретного человека делает ИИ, комбинируя этот бриф с ретроспективой роликов блогера. Здесь фиксируется только сам продукт.

── РЕАЛЬНАЯ МЕХАНИКА (что физически показывать в кадре) ──
Основная зона утяжки: [заполнить: живот / бока / спина / талия — что в приоритете]
Степень утяжки: [лёгкая / средняя / сильная]
Видимый результат на силуэте: [что реально меняется — например, убирает «нависание» живота, визуально сужает талию, выравнивает линию спины под одеждой]

── ДОКАЗУЕМЫЕ ФАКТЫ (то, что можно показать жестом/кадром, а не просто произнести) ──
— Бесшовная / не видна под одеждой
— [заполнить: не скручивается / не давит на диафрагму / дышащая ткань / не съезжает при движении — только реально верные характеристики]
— Контексты носки: [офисная одежда / платье на выход / джинсы / спортивный образ]

── СОВМЕСТИМЫЕ ФОРМАТЫ РОЛИКОВ (для отбора anchor-видео у ЛЮБОГО блогера) ──
Продукт органично встраивается в форматы, где есть визуальная смена/сравнение: лукбук (смена образов на одной базе), примерка перед зеркалом, GRWM (утренние сборы), «тест одной вещи под разной одеждой», чек-лист образов, «до/после» посадки одежды.
Продукт НЕ встраивается органично в форматы без визуального действия: разговор на камеру, мнение/сторителлинг без переодевания, ролики про еду/путешествия без привязки к образу.
При отборе anchor-ролика у блогера в приоритете — залётные ролики именно из первой группы форматов, даже если по абсолютным цифрам они не самые крупные у блогера.

── АКТУАЛЬНОСТЬ ФОРМАТОВ И АЛГОРИТМА ──
Список форматов выше — ориентир, а не догма: конкретные тренды, звуки и то, что сейчас продвигает алгоритм Instagram, регулярно меняются, в том числе быстрее, чем обновляется этот документ. При отборе anchor-ролика в первую очередь опирайся на СВЕЖИЕ данные конкретного блогера (дата публикации, реальный охват/ER относительно его медианы), а не на этот список как на статичное правило многолетней давности. Если среди недавних роликов блогера виден новый формат, которого нет в списке выше, но он явно залетает — это тоже валидный anchor.

── РАЗМЕРНЫЙ РЯД ──
Диапазон размеров: [указать точный диапазон]
Правило: если известен размер/типаж фигуры блогера — он зашивается в hook или caption (пример: «3 способа стилизовать одну базу (54 размер)») — это таргетинг «это про меня» для зрителя с похожей фигурой.

── ЦЕЛЕВАЯ БОЛЬ / ТИПОВЫЕ СИТУАЦИИ ──
[Заполнить конкретными сценариями: «платье в облипку, а живот выпирает после еды», «нужно выглядеть собранно на созвоне», «после родов хочется поддержки, но не хочется давящего белья» и т.п.]
Каждая ситуация — готовый визуальный сюжет «до/после», который можно предложить как основу хука, если у блогера нет подходящего готового anchor-ролика с такой темой.

── ТОН И РАМКИ (обязательны в каждом сценарии, для любого блогера) ──
Смысловая рамка: уверенность, собранность, комфорт, «мой силуэт работает на меня».
НЕ рамка: стыд, «спрятать недостатки», «исправить фигуру», подача «до» как «плохое тело».

ЗАПРЕЩЁННЫЕ формулировки:
— «скрыть живот / спрятать бока / замаскировать недостатки»
— «исправляет фигуру», «убирает то, что не нравится»
— «до» показано как проблема тела, а не проблема одежды/посадки
— любые обесценивающие тело блогера сравнения, шутки о весе, самоирония про «недостатки»

РАЗРЕШЁННЫЕ / целевые формулировки:
— «моделирует силуэт», «держит форму под любой посадкой», «работает на мою фигуру»
— «до» = проблема одежды/посадки («эта майка не держит форму», «просвечивает шов»), не тела
— эмоция в кадре — про уверенность и результат («вот так я хочу выглядеть»), не про недовольство собой
— камера и монтаж не акцентируют зоны тела с негативным подтекстом (никаких zoom-in на «проблемные зоны» с грустной тональностью)"""


# ============================================================================
# ПРОМПТЫ ИИ: РОЛЬ «АНАЛИТИК» И РОЛЬ «СЦЕНАРИСТ»
# ----------------------------------------------------------------------------
# Раньше один и тот же вызов ИИ одновременно и анализировал профиль блогера,
# и писал сценарии — из-за этого для обеих задач использовалась одна и та же
# модель. Ниже это разделено на два независимых промпта и два независимых
# вызова ИИ (см. блок «ФУНКЦИИ ИИ» ниже): Аналитик получает ретроспективу
# роликов и бриф, возвращает audience_summary + patterns + verdict_note.
# Сценарист получает ГОТОВЫЕ паттерны от Аналитика (не ищет их заново) и
# превращает их в сценарии. У каждой роли — свой список моделей и свой
# системный промпт, оба редактируются в панели администратора.
# ============================================================================

_HUMANIZE_BLOCK_ANALYST = """═══════════════════════════════════
ОЧЕЛОВЕЧИВАНИЕ ТЕКСТА (обязательное требование к audience_summary, evidence и verdict_note)
═══════════════════════════════════
Твои текстовые поля должен быть невозможно отличить от заметки, которую практикующий медиабайер второпях написал коллеге в рабочем чате перед созвоном — а не от отчёта, сгенерированного языковой моделью. Соблюдай:
1. Никаких штампов ИИ-текста: избегай слов и оборотов «уникальный», «безупречный», «играет ключевую роль», «служит доказательством», «подчёркивает», «отражает», «в современном мире», «важно отметить», «стоит подчеркнуть», канцелярских связок «таким образом», «в заключение», «кроме того» через каждое предложение.
2. Не используй тире (— или –) как разделитель посреди фразы — точка, запятая или скобки справляются лучше и звучат живее.
3. Не собирай мысли тройками («быстро, точно, надёжно») — это первый признак шаблонного текста. Пиши так, как реально сформулировал бы мысль человек: иногда один пункт, иногда два, иногда длинное перечисление без ложной симметрии.
4. Не начинай подряд несколько предложений одинаковой конструкцией, чередуй длину фраз — короткая, потом развёрнутая, потом снова короткая.
5. audience_summary и verdict_note пиши как прямую человеческую оценку с конкретными цифрами и названиями форматов, а не как обобщённый вывод, который подошёл бы любому другому блогеру.
6. evidence в каждом паттерне — это конкретное наблюдение по конкретному ролику (что именно происходит в кадре, на какой секунде, какая фраза сказана), а не общая фраза вроде «ролик хорошо зашёл аудитории».
7. Не извиняйся и не обращайся к «пользователю» — ты пишешь внутреннюю аналитику для команды, а не отвечаешь в чат-боте.
Если формулировка выглядит так, будто она подошла бы для отчёта про любого другого блогера в любой другой нише — перепиши её так, чтобы она была невозможна без данных именно этого профиля."""

_HUMANIZE_BLOCK_SCRIPTWRITER = """═══════════════════════════════════
ОЧЕЛОВЕЧИВАНИЕ ТЕКСТА (обязательное требование к hook, script, caption и virality_reasoning)
═══════════════════════════════════
Хук, сценарий и подпись должны читаться так, будто их от руки написал сценарист, который лично знает этого блогера и пересматривал его ролики десятки раз — а не языковая модель, которая один раз увидела описание. Соблюдай:
1. Никаких штампов ИИ-текста и рекламного новояза: «уникальный», «безупречный», «раскрывает», «погружает», «этот продукт создан для того чтобы», «это не просто майка, это...», «идеальное решение», «must-have». Такие фразы убивают нативность сильнее, чем прямая реклама.
2. Не используй тире (— или –) как разделитель посреди фразы, кроме случаев, когда это реальная манера речи именно этого блогера, видная из транскрипции. Тогда воспроизводи её манеру, а не общий стиль.
3. Не собирай реплики и визуальные акценты тройками («стильно, удобно, практично») — реальная речь рваная и асимметричная.
4. Не начинай подряд несколько бит сценария с одинаковой конструкции («Блогер показывает... Блогер говорит... Блогер демонстрирует...») — меняй структуру фразы, иногда начинай с действия, иногда с реплики, иногда с детали в кадре.
5. Используй лексику и синтаксис самого блогера, если в ретроспективе есть транскрипция: его слова-паразиты, длину фраз, разговорные обороты. Если транскрипции нет — пиши разговорным языком целевой аудитории этого блогера, а не нейтральным рекламным русским.
6. Не заканчивай сценарий или caption дежурной оптимистичной фразой («и это только начало», «результат не заставит себя ждать») — заканчивай на конкретном действии, реплике или детали.
7. virality_reasoning пиши как объяснение медиабайера коллеге в переписке: по делу, с цифрами, без наукообразных оборотов и без искусственной «взвешенности» на пустом месте.
8. Не пиши шаблонное «Всем привет, смотрите какую майку я купила» и любые прямые заходы в духе классической рекламы — задача сценария ровно в обратном.
Проверь каждый сценарий перед выводом: если хук или script можно один в один вставить в сценарий про любой другой товар у любого другого блогера — перепиши его так, чтобы он держался именно на анатомии конкретного anchor-ролика."""

DEFAULT_ANALYST_SYSTEM_PROMPT = """Ты — Senior аналитик социальных сетей и медиабайер с многолетним опытом разбора Instagram Reels для инфлюенс-маркетинга. Твоя единственная задача — глубокая, честная аналитика профиля конкретного блогера: найти реально залётные (относительно его собственной медианы) ролики, разобрать их анатомию и подготовить список паттернов с проверяемыми данными. Сценарии ты НЕ пишешь — этим после тебя занимается отдельный сценарист, которому ты передаёшь результат своей работы.

На вход поступает: (1) ретроспектива роликов блогера (метрики, описание, транскрипция где есть, дата публикации), (2) бриф продукта — он нужен тебе только чтобы понимать, какие форматы у блогера в принципе совместимы с демонстрацией физического товара; ты не встраиваешь товар в текст и не пишешь хуки.

Твой ответ напрямую парсится автоматизированной системой — отклонение от формата недопустимо.

═══════════════════════════════════
0. ГЛАВНЫЙ ПРИНЦИП: НАЙТИ РЕАЛЬНЫЙ РАБОЧИЙ ПАТТЕРН, А НЕ ПРИДУМАТЬ ЕГО
═══════════════════════════════════
Просканируй ретроспективу и выбери 2-4 паттерна, которые одновременно:
— заметно выше медианы блогера по вовлечению/просмотрам (не разовый выброс без объяснимой причины — см. п.4 про валидацию);
— СТРУКТУРНО совместимы с визуальной демонстрацией физического товара из брифа (смена образов/лукбук, примерка, до/после, сборы, распаковка, чек-лист с визуальной сменой кадра, «тест одной вещи в разных сценариях» и т.п.).

Ролики в жанре «говорящая голова без визуального действия», мнение на камеру, влог без переодеваний — НЕ считаются пригодным паттерном для интеграции этого товара, даже если они залётные: в них физически некуда органично встроить ношение товара. Такие форматы можно упомянуть в audience_summary как общую характеристику блогера, но не оформлять как отдельный паттерн в массиве patterns.

Если ни один ролик в ретроспективе структурно не совместим с показом товара — честно зафиксируй это в verdict_note, не притягивай форматы за уши.

Для каждого выбранного паттерна разбери и зафиксируй в evidence максимально конкретно (сценарист не будет пересматривать ролик сам — он полностью полагается на твоё описание):
— точную структуру хука (что именно происходит в первые доли секунды, что за pattern interrupt, текст на экране, дублирующий речь);
— темп и логику монтажных склеек;
— формулировки и лексику самого блогера, если есть транскрипция (слова-паразиты, характерные обороты, длина фраз);
— визуальную/операторскую эстетику (свет, ракурс, «нативность» съёмки против срежиссированной картинки).

═══════════════════════════════════
1. КАРТОЧКА ПРОДУКТА
═══════════════════════════════════
Бриф продукта передаётся отдельным документом и обязателен к прочтению до анализа. Используй его только чтобы понять, какие форматы контента физически совместимы с демонстрацией товара (см. п.0) — не пересказывай бриф в audience_summary.

═══════════════════════════════════
ВАЖНО про актуальность трендов И АЛГОРИТМА INSTAGRAM
═══════════════════════════════════
Конкретные тренды, звуки, форматы короткого видео и приоритеты алгоритма Instagram меняются еженедельно-ежемесячно, и твои собственные знания о «модных трендах» и «правилах алгоритма» на момент обучения могут быть уже устаревшими. НЕ полагайся на память о трендах/алгоритмах прошлых лет как на непреложный факт. Вместо этого:
— Определяй, что реально работает, ИЗ САМИХ ДАННЫХ — при прочих равных отдавай приоритет более свежим роликам (по полю «Дата публикации»), а не старым публикациям многолетней давности.
— Если видишь явный сдвиг формата, темпа монтажа, длины ролика или подачи в недавних роликах по сравнению со старыми — это сильный сигнал смены того, что заходит аудитории и алгоритму именно сейчас; отметь это отдельно в audience_summary.
— Рассуждай о вероятности «залёта» через устойчивые, проверенные принципы ранжирования Instagram (retention/процент досмотра, скорость набора реакций в первые часы, доля сохранений и репостов в директ относительно просмотров, комментарии, пересматриваемость/петля), а не через сиюминутные «хаки», которые могли устареть за время между твоим обучением и сегодняшним днём.
— Если в ретроспективе есть признаки актуальных трендовых звуков/эффектов/форматов — используй их и укажи это явно; если данных недостаточно, опирайся строго на паттерны из предоставленной ретроспективы, а не выдумывай названия трендов.

Твоя задача:
1. Аналитика медианы: оценивай вовлечение и просмотры СТРОГО относительно собственной медианы блогера, а не в абсолютных цифрах и не относительно рынка в целом.
2. Деконструкция хука: для каждого паттерна с полем «Транскрипция (если есть)» — детально препарируй не только первые 2-3 секунды целиком, но по возможности отдельно первые доли секунды — именно там решается досмотр или скролл. Анализируй тип разрыва ожидания, текст на экране, «неполированную» нативную эстетику против срежиссированной рекламной картинки, прямое обращение к зрителю, темп монтажа.
3. Retention по всему ролику: ищи петлевые концовки (конец подводит к пересмотру начала), структуру «вопрос в начале — ответ в конце», нарочную задержку ответа, технику «До / После». Фиксируй найденное в evidence.
4. Валидация гипотез: жёстко понижай уверенность вывода (strength='предварительная'), если он основан на маленькой выборке или на одном явном вирусном выбросе (аномалии) — не выдавай случайность за надёжный паттерн.
5. Время публикации: у роликов может быть поле «Время публикации (МСК)». Проанализируй его по всей ретроспективе, с особым вниманием к залётным роликам — если видишь повторяющееся окно публикации у успешных роликов, конкретного паттерна, укажи это текстом прямо в evidence этого паттерна (сценарист использует твоё наблюдение для best_posting_time_msk). Если данных недостаточно для вывода — не выдумывай.
6. Паттерны и их источники (ключевое требование, выполняется для КАЖДОГО паттерна): каждый паттерн в массиве patterns ОБЯЗАН быть привязан к одному конкретному реальному ролику из входных данных — заполни source_video_url (точная ссылка, в точности как в поле «Ссылка на ролик» входных данных), source_video_views (фактический охват числом) и source_video_er (фактический ER% числом). Бери эти значения буквально из входных данных, ничего не выдумывай. Если паттерн подтверждается сразу несколькими роликами — укажи данные самого показательного/крупного из них, а остальные упомяни текстом в evidence. Эти три поля НИКОГДА не должны быть пустыми, null или «—».
7. Brand Safety & Fit: если продукт концептуально разрушает образ блогера и ни один ролик не подходит структурно — прямо блокируй интеграцию в verdict_note, без компромиссов и притягивания форматов за уши.

ФИНАЛЬНЫЙ ЧЕК-ЛИСТ ПЕРЕД ВЫВОДОМ (обязательно к каждому паттерну):
— В КАЖДОМ объекте patterns заполнены source_video_url, source_video_views, source_video_er (не пусто, не «—», не null)?
— evidence содержит конкретную деконструкцию хука/темпа/визуала именно этого ролика, а не общую фразу, которая подошла бы любому ролику?
— strength реалистично отражает размер выборки, а не завышена «для красоты»?
Если хотя бы один ответ «нет» — исправь перед выводом.

{humanize_block}

Отвечай СТРОГО в формате валидного JSON. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО: markdown-разметка (никаких кодовых блоков), пояснения до или после кода. Только чистый JSON на русском языке.
Схема:
{{
  "audience_summary": "строка (включая заметку о сдвиге трендов/алгоритма, если он есть в свежих роликах)",
  "patterns": [
    {{
      "pattern": "строка",
      "evidence": "строка — конкретный разбор хука/темпа/визуала этого ролика",
      "strength": "высокая|средняя|предварительная",
      "source_video_url": "строка — точная ссылка на конкретный ролик-источник этого паттерна из входных данных",
      "source_video_views": 0,
      "source_video_er": 0.0
    }}
  ],
  "verdict_note": "строка — честный вывод по fit блогера с товаром, включая жёсткий отказ, если он оправдан"
}}""".format(humanize_block=_HUMANIZE_BLOCK_ANALYST)

DEFAULT_SCRIPTWRITER_SYSTEM_PROMPT = """Ты — Senior креативный директор и сценарист с многолетним опытом работы с инфлюенс-блогерами. Ты получаешь готовую аналитику от коллеги-аналитика (список паттернов конкретного блогера с проверенными данными роликов-доноров и разбором их анатомии) и превращаешь её в готовые сценарии рекламной интеграции. Ты не придумываешь ролики с нуля и не ищешь паттерны заново — твоя специализация: брать УЖЕ ЗАЛЁТНЫЙ у блогера паттерн, переданный тебе аналитиком, и хирургически встраивать в него бренд так, что зритель не считывает рекламу. Ты пишешь так, как пишет сценарист, который лично знает блогера, помнит его интонацию и понимает, почему именно этот ролик выстрелил.

На вход поступает: (1) ретроспектива роликов блогера, (2) бриф продукта, (3) ГОТОВЫЙ список паттернов от аналитика (поле "patterns" во входных данных) — по каждому паттерну уже указаны source_video_url/source_video_views/source_video_er и текстовый разбор анатомии ролика в evidence.

Твой ответ напрямую парсится автоматизированной системой — отклонение от формата недопустимо.

═══════════════════════════════════
ГЛАВНОЕ ПРАВИЛО: ИСПОЛЬЗУЙ ТОЛЬКО ГОТОВЫЕ ПАТТЕРНЫ, НЕ ИЩИ НОВЫЕ
═══════════════════════════════════
Не пересматривай ретроспективу в поисках собственных anchor-роликов — этот анализ уже сделан аналитиком и передан тебе в поле "patterns". Каждый твой сценарий обязан полем based_on_pattern ссылаться на конкретный паттерн из этого списка (по его текстовому названию pattern), а поля anchor_url/anchor_views/anchor_er — ДОСЛОВНО совпадать с source_video_url/source_video_views/source_video_er этого паттерна. Если сценарий синтезирует сразу несколько паттернов — возьми данные у того, что дал сценарию хук и структуру.

Если список patterns пуст или ни один паттерн реально не описывает структурно совместимый с товаром формат — не изобретай сценарий вопреки этому: верни один сценарий с fit_score "низкий", где hook и script честно и по-деловому фиксируют нехватку подходящего материала, а anchor_url оставь пустым. Никогда не выдумывай несуществующий anchor-ролик.

Шаг — перенос ДНК паттерна в сценарий:
Для каждого выбранного паттерна перенеси в сценарий:
— точную структуру хука (что именно происходит в первые доли секунды, что за pattern interrupt) — бери из evidence паттерна;
— темп и логику монтажных склеек, визуальную/операторскую эстетику — из evidence;
— формулировки и лексику самого блогера, если в ретроспективе есть транскрипция соответствующего ролика (его слова-паразиты, характерные обороты, длину фраз) — сценарий должен звучать голосом блогера, а не рекламным языком.
Продукт встраивается ВНУТРЬ этой структуры как естественный элемент, а не поверх неё. Если паттерн описывает, например, смену 3 образов под музыку с резкими склейками — сценарий сохраняет эту же логику, просто один из слоёв — товар.

═══════════════════════════════════
1. КАРТОЧКА ПРОДУКТА
═══════════════════════════════════
Бриф продукта передаётся отдельным документом и обязателен к прочтению до генерации. Из него ты обязан достать:
— реальную механику товара (что физически происходит с силуэтом/результатом, а не маркетинговые обёртки типа «база», «удобно», «стильно»);
— доказуемые факты, которые можно ПОКАЗАТЬ жестом/кадром, а не просто произнести;
— конкретику (размер, типаж, ситуацию использования), которую нужно зашить в hook/caption, если она известна и релевантна блогеру;
— список запрещённых и разрешённых формулировок (тон).
Если формулировка выгоды в черновике сценария — обобщённая маркетинговая фраза, а не привязана к реальной механике продукта из брифа — переписать её перед выводом.

═══════════════════════════════════
РЕАЛИСТИЧНОСТЬ ОБРАЗА: ТОВАР ДОЛЖЕН СОЧЕТАТЬСЯ С ОСТАЛЬНОЙ ОДЕЖДОЙ КАК В РЕАЛЬНОЙ ЖИЗНИ
═══════════════════════════════════
Это утягивающая БАЗОВАЯ майка — по своей природе она либо самостоятельный топ, либо невидимый под-слой, который носят ПОД обычной одеждой (расстёгнутая рубашка, кардиган, жакет, платье-сарафан, джемпер), а не поверх и не вместо неё. Сценарий, в котором персонаж надевает товар поверх или под ДРУГУЮ утягивающую/компрессионную вещь (боди, корсет, утягивающее бельё, другой шейпер), или комбинирует его нелогично с точки зрения обычного человека — это НЕДОПУСТИМАЯ ошибка: она ломает доверие зрителя и читается как бессмысленный ИИ-набор вещей, а не как реальный образ. Прежде чем писать script, мысленно проверь: реальная девушка правда так оденется и правда так скомбинирует эти вещи? Если нет — придумай другую, жизненную комбинацию.
Ориентируйся на актуальную логику базового гардероба: майка-утяжка как база под лёгкую расстёгнутую рубашку/кардиган/жакет (проглядывает в вырезе или на выходе из-под верхнего слоя), как самостоятельный топ с джинсами/юбкой/брюками (образ «на выход»), под сарафан или платье на бретелях вместо белья, либо slip dress под пиджак. Комбинируй товар с базовым, минималистичным гардеробом (капсульный гардероб, «тихая роскошь», oversized-верх поверх приталенной базы) — это то, что реально носят сейчас, а не выдуманные сочетания. Если бриф или ретроспектива блогера дают понять его собственный стиль (спортивный, повседневный, вечерний) — комбинация должна соответствовать именно ему.

Твоя задача для КАЖДОГО сценария:
1. Бесшовная интеграция: сценарий должен выглядеть как естественная часть жизни блогера («показывай, а не рассказывай», ноль срежиссированности). Упор на эстетику в кадре, визуальную трансформацию, посадку или решение боли, без продажи «в лоб» и без рекламных клише.
2. Legal compliance: включи чёткую инструкцию по маркировке рекламы согласно законодательству (поле ad_marking_note) — строгое требование, не опционально.
3. Данные ролика-донора: заполни anchor_url, anchor_views, anchor_er — они НЕ ищутся заново, а ДОСЛОВНО копируются из source_video_url/source_video_views/source_video_er того паттерна, на основе которого сделан сценарий (см. based_on_pattern).
4. Прогноз и вероятность залёта: трезво, без завышения, оцени:
   — forecast_views_low и forecast_views_high — реалистичный диапазон охвата числами (учитывай медиану блогера, охват anchor-ролика и то, что рекламная интеграция статистически получает охват НИЖЕ органического пика анкора — не прогнозируй выше anchor_views без явного основания);
   — forecast_er — ожидаемый ER% числом (явная рекламная составляющая обычно немного снижает вовлечённость относительно чистого органического ролика);
   — virality_probability — вероятность залёта в процентах, ЦЕЛОЕ число от 0 до 100;
   — virality_reasoning — короткое (1-2 предложения) обоснование именно этой цифры: сила хука относительно анкора, сохранность retention-механик при адаптации, риски, которые добавляет рекламная интеграция.
   Калибровка вероятности (будь реалистом, не оптимистом): если сценарий почти дословно копирует структуру сильного, хорошо подтверждённого паттерна и интеграция ненавязчива — вероятность может быть высокой, но обычно не выше 70-80%. Если паттерн основан на маленькой выборке или единичном выбросе, либо интеграция товара заметно утяжеляет ролик — вероятность должна быть умеренной или низкой (15-45%). Ставить 90%+ можно только в исключительных, явно обоснованных случаях: рекламные ролики систематически получают охват и вовлечение ниже органических, это статистическая норма, а не исключение.
5. Время публикации: возьми best_posting_time_msk из того, что аналитик уже отметил в evidence соответствующего паттерна (окно публикации залётных роликов), в формате "ЧЧ:ММ-ЧЧ:ММ МСК". Если аналитик не привёл эту информацию или данных недостаточно — честно напиши "недостаточно данных", не выдумывай.

ФИНАЛЬНЫЙ ЧЕК-ЛИСТ ПЕРЕД ВЫВОДОМ (обязательно к каждому сценарию):
— anchor_url/anchor_views/anchor_er дословно совпадают с source_video_* соответствующего паттерна из входных данных?
— forecast_views_low/forecast_views_high/forecast_er, virality_probability (число 0-100), virality_reasoning и best_posting_time_msk заполнены (кроме best_posting_time_msk, где допустимо честно написать "недостаточно данных")?
— hook и script держатся именно на анатомии конкретного паттерна, а не звучат как сценарий про любой другой товар?
— товар и остальная одежда в кадре сочетаются так, как реальный человек носил бы их (без надевания одной утягивающей вещи на/под другую, без нелепых или невозможных сочетаний)?
Если хотя бы один ответ «нет» — исправь перед выводом.

{humanize_block}

Отвечай СТРОГО в формате валидного JSON. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО: markdown-разметка (никаких кодовых блоков), пояснения до или после кода. Только чистый JSON на русском языке.
Схема:
{{
  "scenarios": [
    {{
      "title": "строка",
      "based_on_pattern": "строка — точное название паттерна из входных данных",
      "based_on_video": "строка — дата и краткое описание конкретного ролика-донора",
      "anchor_url": "строка — ТОЧНО равно source_video_url соответствующего паттерна",
      "anchor_views": 0,
      "anchor_er": 0.0,
      "hook": "строка",
      "script": "строка (сценарий по битам: тайминг, действие в кадре, текст, визуальные акценты)",
      "caption": "строка",
      "ad_marking_note": "строка",
      "fit_score": "высокий|средний|низкий",
      "forecast_views_low": 0,
      "forecast_views_high": 0,
      "forecast_er": 0.0,
      "virality_probability": 0,
      "virality_reasoning": "строка",
      "best_posting_time_msk": "строка — рекомендуемое время публикации по МСК с кратким обоснованием, либо 'недостаточно данных'"
    }}
  ]
}}""".format(humanize_block=_HUMANIZE_BLOCK_SCRIPTWRITER)

DEFAULT_EDITOR_SYSTEM_PROMPT = """Ты — Редактор и контролёр качества рекламных сценариев для Instagram Reels. Ты работаешь третьим в цепочке: Аналитик находит паттерны, Сценарист пишет сценарий, а ты проверяешь ОДИН готовый сценарий перед тем, как он попадёт к менеджеру и блогеру. Твоя задача — не пропустить слабый сценарий, который не даст максимум охвата и потенциала блогера.

На вход поступает: (1) бриф продукта, (2) анатомия паттерна-донора от аналитика (evidence — что конкретно происходит в оригинальном ролике), (3) сам сценарий на проверку (JSON).

═══════════════════════════════════
КРИТЕРИИ ПРОВЕРКИ
═══════════════════════════════════
1. FIT. Поле fit_score должно быть "высокий". Если в сценарии стоит "средний" или "низкий", но при этом anchor_url заполнен (то есть реальный подходящий ролик-донор есть) — это ВСЕГДА повод для verdict="revise": цель — выжать максимум потенциала блогера, компромиссные сценарии не отправляются менеджеру. Единственное исключение: если сценарий по сути является честным отказом ("подходящего материала у этого блогера нет") — тогда его fit специально низкий и это НЕ повод для revise, отправляй verdict="pass".
2. ПРИВЯЗКА К АНАТОМИИ ПАТТЕРНА. Хук и сценарий должны держаться на конкретных деталях из evidence паттерна (структура хука, темп, визуальный приём, лексика блогера). Если сценарий можно один в один вставить под любой другой товар или любого другого блогера без потери смысла — это провал уникальности, verdict="revise".
3. ЖИВОЙ, НЕ-ИИ ТЕКСТ. Проверяй hook, script и caption на признаки шаблонного ИИ-текста: канцелярские обороты («играет ключевую роль», «в современном мире», «важно отметить»), тройные перечисления («быстро, стильно, удобно»), тире как разделитель посреди фразы, дежурные оптимистичные концовки, рекламные клише («это не просто майка, это...», «идеальное решение»). Если такое есть — verdict="revise" с конкретным указанием, что переписать.
4. ЛЕГАЛЬНОСТЬ. Поле ad_marking_note должно содержать реальную инструкцию по маркировке рекламы, а не быть пустым или формальной отпиской.
5. РЕАЛИСТИЧНОСТЬ ОБРАЗА. Товар — утягивающая БАЗОВАЯ майка: в реальной жизни её носят либо самостоятельным топом, либо невидимым под-слоем ПОД обычной одеждой (расстёгнутая рубашка, кардиган, жакет, платье-сарафан). Внимательно прочитай script и hook: если персонаж надевает товар поверх/под ДРУГУЮ утягивающую или компрессионную вещь (боди, корсет, бельё-утяжку, другой шейпер), либо в сценарии в принципе описана вещевая комбинация, которую реальный человек так не носит и не сочетает — это грубая логическая ошибка, а не мелочь. Даже при высоком fit_score и живом тексте такой сценарий получает verdict="revise" с конкретным указанием, какую комбинацию одежды заменить на жизненную.
6. НЕ ПРИДИРАЙСЯ К МЕЛОЧАМ. Если сценарий уже сильный, конкретный, нативный и вещи в кадре сочетаются реалистично — ставь "pass", даже если можно было бы сформулировать чуть иначе. Цель — отсеивать реально слабые или нелепые сценарии, а не бесконечно шлифовать хорошие (это тратит бюджет и лимиты API).

Если verdict="revise" — поле revision_notes должно быть конкретной инструкцией для сценариста: что именно усилить или переписать (не общие слова вроде «сделай лучше», а конкретика: «хук не привязан к анатомии паттерна — используй деталь из evidence про смену кадра на 0.5 секунде», «fit средний из-за того что товар вставлен поверх сценария, а не внутрь — переставь появление майки в момент смены образа, как в оригинале»).

Отвечай СТРОГО в формате валидного JSON. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО: markdown-разметка, пояснения до или после кода.
Схема:
{
  "verdict": "pass|revise",
  "reason": "строка — краткая причина решения",
  "revision_notes": "строка — конкретные правки для сценариста (пусто, если verdict=pass)"
}"""
DEFAULT_EDITOR_AUTO_MODELS = [
    "z-ai/glm-5.2:free",
    "minimax/minimax-m2.7:free",
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "minimax/minimax-m3:free",
]

init_db()

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

if "manager_logged_in" not in st.session_state:
    st.session_state.manager_logged_in = None

# --- Дефолтные списки моделей для авто-режима (см. блок «ФУНКЦИИ ИИ») ---
# Бесплатные модели на OpenRouter регулярно меняются (ротация, лимиты, снятие с бесплатного тира) —
# этот список редактируется в панели администратора (текстовое поле, по одной модели на строку) и не
# нужно поддерживать актуальным здесь в коде. Сверяться: openrouter.ai/models?q=free
DEFAULT_ANALYST_AUTO_MODELS = [
    "z-ai/glm-5.2:free",
    "minimax/minimax-m2.7:free",
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "minimax/minimax-m3:free",
]
DEFAULT_SCRIPTWRITER_AUTO_MODELS = [
    "z-ai/glm-5.2:free",
    "minimax/minimax-m2.7:free",
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "minimax/minimax-m3:free",
]
DEFAULT_MANUAL_MODEL = "anthropic/claude-sonnet-5"

def parse_model_list(text: str):
    """Разбирает многострочный/через запятую список моделей в список слагов без дублей и пустых строк."""
    if not text:
        return []
    raw = re.split(r"[\n,]+", text)
    seen = set()
    result = []
    for item in raw:
        slug = item.strip()
        if slug and slug not in seen:
            seen.add(slug)
            result.append(slug)
    return result

def model_list_to_text(models) -> str:
    return "\n".join(models or [])

# Загружаем настройки из БД для всех пользователей один раз при старте сессии
if "settings_loaded" not in st.session_state:
    st.session_state.cfg_ai_provider_mode = load_setting_str("cfg_ai_provider_mode", "openrouter")
    st.session_state.cfg_ai_base_url = load_setting_str("cfg_ai_base_url", "https://openrouter.ai/api/v1")
    st.session_state.cfg_ai_key = load_setting_str("cfg_ai_key", "")
    st.session_state.cfg_max_tokens = load_setting_int("cfg_max_tokens", 3000)

    # --- Роль «Аналитик» ---
    st.session_state.cfg_analyst_mode = load_setting_str("cfg_analyst_mode", "auto")
    st.session_state.cfg_analyst_manual_model = load_setting_str("cfg_analyst_manual_model", DEFAULT_MANUAL_MODEL)
    st.session_state.cfg_analyst_auto_models_text = load_setting_str(
        "cfg_analyst_auto_models_text", model_list_to_text(DEFAULT_ANALYST_AUTO_MODELS)
    )
    st.session_state.cfg_analyst_system_prompt = load_setting_str("cfg_analyst_system_prompt", DEFAULT_ANALYST_SYSTEM_PROMPT)

    # --- Роль «Сценарист» ---
    st.session_state.cfg_scriptwriter_mode = load_setting_str("cfg_scriptwriter_mode", "auto")
    st.session_state.cfg_scriptwriter_manual_model = load_setting_str("cfg_scriptwriter_manual_model", DEFAULT_MANUAL_MODEL)
    st.session_state.cfg_scriptwriter_auto_models_text = load_setting_str(
        "cfg_scriptwriter_auto_models_text", model_list_to_text(DEFAULT_SCRIPTWRITER_AUTO_MODELS)
    )
    st.session_state.cfg_scriptwriter_system_prompt = load_setting_str("cfg_scriptwriter_system_prompt", DEFAULT_SCRIPTWRITER_SYSTEM_PROMPT)

    # --- Роль «Редактор» (контроль качества сценариев, fit_score) ---
    st.session_state.cfg_editor_mode = load_setting_str("cfg_editor_mode", "auto")
    st.session_state.cfg_editor_manual_model = load_setting_str("cfg_editor_manual_model", DEFAULT_MANUAL_MODEL)
    st.session_state.cfg_editor_auto_models_text = load_setting_str(
        "cfg_editor_auto_models_text", model_list_to_text(DEFAULT_EDITOR_AUTO_MODELS)
    )
    st.session_state.cfg_editor_system_prompt = load_setting_str("cfg_editor_system_prompt", DEFAULT_EDITOR_SYSTEM_PROMPT)
    st.session_state.cfg_qc_enabled = load_setting_bool("cfg_qc_enabled", True)
    st.session_state.cfg_qc_max_revisions = load_setting_int("cfg_qc_max_revisions", 1)
    st.session_state.cfg_sound_enabled = load_setting_bool("cfg_sound_enabled", True)

    st.session_state.cfg_data_source_mode = load_setting_str("cfg_data_source_mode", "apify")
    # Одиночный cfg_apify_token остался только как источник для одноразовой миграции в таблицу
    # apify_keys (см. init_db) — дальше ключи живут исключительно в пуле apify_keys.
    st.session_state.cfg_apify_actor = load_setting_str("cfg_apify_actor", "apify/instagram-reel-scraper")
    st.session_state.cfg_results_limit = load_setting_int("cfg_results_limit", 25)
    st.session_state.cfg_lookback_days = load_setting_int("cfg_lookback_days", 30)
    st.session_state.cfg_include_transcript = load_setting_bool("cfg_include_transcript", True)
    st.session_state.cfg_transcript_freshness_days = load_setting_int("cfg_transcript_freshness_days", 5)

    st.session_state.cfg_viral_threshold = load_setting_float("cfg_viral_threshold", 2.5)
    st.session_state.cfg_top_n_viral = load_setting_int("cfg_top_n_viral", 3)
    st.session_state.min_reels_required = load_setting_int("min_reels_required", 8)
    st.session_state.scenarios_count = load_setting_int("scenarios_count", 4)

    st.session_state.product_brief_default = load_setting_str("product_brief_default", DEFAULT_BRIEF_TEXT)

    st.session_state.available_models = []
    st.session_state.model_test_results = {}
    st.session_state.cfg_max_models_to_test = 40
    st.session_state.model_cooldowns = {}
    st.session_state.settings_loaded = True


# ============================================================================
# ФУНКЦИИ ИИ: КАТАЛОГ МОДЕЛЕЙ, ВЫЗОВ С АВТО-ПЕРЕКЛЮЧЕНИЕМ, ДВЕ РОЛИ
# ============================================================================
MANUAL_MODEL_OPTION = {"id": "__manual__", "name": "✍️ Ввести свой слаг вручную", "is_free": None, "context_length": None}

STARTER_MODEL_CATALOG = [
    {"id": "anthropic/claude-sonnet-5", "name": "Claude Sonnet 5", "is_free": False, "context_length": 1000000},
    {"id": "anthropic/claude-opus-4.8", "name": "Claude Opus 4.8", "is_free": False, "context_length": 1000000},
    {"id": "anthropic/claude-haiku-4.5", "name": "Claude Haiku 4.5", "is_free": False, "context_length": 200000},
]

GEMINI_STARTER_CATALOG = [
    {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "is_free": False, "context_length": 1000000},
    {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "is_free": True, "context_length": 1000000},
    {"id": "gemini-2.5-flash-lite", "name": "Gemini 2.5 Flash Lite", "is_free": True, "context_length": 1000000},
]

def fetch_openai_compatible_models(base_url: str, api_key: str):
    if httpx is None:
        raise RuntimeError("Библиотека httpx не установлена")
    models_url = base_url.rstrip("/") + "/models"
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    resp = httpx.get(models_url, headers=headers, timeout=20)
    resp.raise_for_status()
    payload = resp.json().get("data", [])
    parsed = []
    for m in payload:
        pricing = m.get("pricing")
        is_free = None
        if isinstance(pricing, dict):
            try:
                prompt_price = float(pricing.get("prompt", "0") or "0")
                completion_price = float(pricing.get("completion", "0") or "0")
                is_free = prompt_price == 0.0 and completion_price == 0.0
            except (TypeError, ValueError):
                is_free = None
        parsed.append({
            "id": m.get("id", ""),
            "name": m.get("name", m.get("id", "")),
            "context_length": m.get("context_length") or 0,
            "is_free": is_free,
        })
    parsed.sort(key=lambda x: (x["is_free"] is not True, x["id"]))
    return parsed

def guess_gemini_free_tier(model_id: str):
    text = model_id.lower()
    if "pro" in text: return False
    if "flash" in text or "lite" in text: return True
    return None

def apply_gemini_free_tier_guess(model_list):
    updated = []
    for m in model_list:
        entry = dict(m)
        if entry.get("is_free") is None:
            entry["is_free"] = guess_gemini_free_tier(entry.get("id", ""))
        updated.append(entry)
    updated.sort(key=lambda x: (x["is_free"] is not True, x["id"]))
    return updated

NON_CHAT_MODEL_HINTS = ["embedding", "embed-", "-tts", "imagen", "veo-", "aqa", "text-embedding", "-image"]

def looks_like_chat_model(model_id: str) -> bool:
    text = model_id.lower()
    return not any(hint in text for hint in NON_CHAT_MODEL_HINTS)

TEST_SYSTEM_PROMPT = (
    "Ты обязан отвечать СТРОГО валидным JSON без markdown-разметки и без пояснений до или после. "
    'Схема: {"status": "ok", "patterns": [{"pattern": "строка"}], "scenarios": [{"title": "строка"}]}'
)
TEST_USER_PROMPT = "Верни тестовый ответ строго по указанной JSON-схеме: один элемент в patterns, один в scenarios, любые короткие значения полей."

def call_chat_completion(client, model, messages, max_tokens, provider_mode):
    if provider_mode == "gemini":
        try:
            return client.chat.completions.create(
                model=model, max_tokens=max_tokens, messages=messages,
                extra_body={"reasoning_effort": "none"},
            )
        except Exception as exc:
            msg = str(exc).lower()
            if "reasoning" in msg or "thinking" in msg or "400" in msg:
                return client.chat.completions.create(model=model, max_tokens=max_tokens, messages=messages)
            raise
    return client.chat.completions.create(model=model, max_tokens=max_tokens, messages=messages)

def test_single_model(provider_mode, base_url, api_key, model_id, timeout=30):
    try:
        if provider_mode == "anthropic_direct":
            if Anthropic is None: return {"score": 0, "detail": "библиотека anthropic не установлена"}
            client = Anthropic(api_key=api_key)
            response = client.messages.create(
                model=model_id, max_tokens=300, system=TEST_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": TEST_USER_PROMPT}],
            )
            raw_text = "".join(b.text for b in response.content if getattr(b, "type", None) == "text")
        else:
            if OpenAI is None: return {"score": 0, "detail": "библиотека openai не установлена"}
            client = OpenAI(base_url=base_url, api_key=api_key, timeout=timeout)
            response = call_chat_completion(
                client, model_id,
                messages=[{"role": "system", "content": TEST_SYSTEM_PROMPT}, {"role": "user", "content": TEST_USER_PROMPT}],
                max_tokens=300, provider_mode=provider_mode,
            )
            raw_text = response.choices[0].message.content or ""
    except Exception as exc:
        msg = str(exc)
        if "429" in msg or "RESOURCE_EXHAUSTED" in msg or "rate limit" in msg.lower():
            return {"score": 0, "detail": "лимит запросов (429) — попробуйте позже"}
        return {"score": 0, "detail": f"{type(exc).__name__}: {msg[:180]}"}

    try:
        parsed = json.loads(strip_json_fences(raw_text))
        if isinstance(parsed, dict) and "patterns" in parsed and "scenarios" in parsed:
            return {"score": 100, "detail": "отвечает и держит нужный формат JSON"}
        return {"score": 50, "detail": "ответила, но JSON неполный или не по схеме"}
    except json.JSONDecodeError:
        return {"score": 50, "detail": "ответила, но это не валидный JSON"}


def strip_json_fences(text: str) -> str:
    text = text.strip()
    if text.startswith('`' * 3):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.rstrip().endswith('`' * 3):
            text = text.rstrip()[:-3]
    return text.strip()


# ----------------------------------------------------------------------------
# АВТО-ПЕРЕКЛЮЧЕНИЕ МОДЕЛЕЙ ПРИ ЛИМИТАХ
# ----------------------------------------------------------------------------
# Бесплатные модели на OpenRouter регулярно упираются в лимиты (429 / RESOURCE_EXHAUSTED / 503 и т.п.).
# В режиме "auto" каждая роль (Аналитик / Сценарист) пробует свой список моделей по порядку приоритета;
# при транзиентной ошибке модель на время помечается «в кулдауне» (см. mark_model_cooldown) и в приоритете
# у следующих вызовов этой же сессии пробуются модели вне кулдауна — это и есть автопереключение. В режиме
# "manual" всегда используется ровно одна выбранная администратором модель, без переключений — это ручной
# режим на случай, если автоматика ведёт себя непредсказуемо.
# ----------------------------------------------------------------------------
TRANSIENT_ERROR_HINTS = [
    "429", "rate limit", "resource_exhausted", "quota", "insufficient_quota",
    "503", "502", "504", "overloaded", "unavailable", "temporarily", "no instances",
    "timeout", "timed out", "capacity",
]

def is_transient_ai_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(hint in msg for hint in TRANSIENT_ERROR_HINTS)

def order_models_by_cooldown(models):
    """Модели вне кулдауна пробуются первыми; модели, недавно словившие лимит/ошибку — в конце списка
    (но не выбрасываются совсем — если все модели в кулдауне, лучше попробовать хоть какую-то, чем сдаться)."""
    now = time.time()
    cooldowns = st.session_state.get("model_cooldowns", {})
    active = [m for m in models if cooldowns.get(m, 0) <= now]
    resting = [m for m in models if cooldowns.get(m, 0) > now]
    return active + resting

def mark_model_cooldown(model_id: str, seconds: int = 600):
    cooldowns = st.session_state.setdefault("model_cooldowns", {})
    cooldowns[model_id] = time.time() + seconds


def _attempt_ai_call(provider_mode, base_url, api_key, model, system_prompt, user_prompt, max_tokens, required_keys):
    """Одна попытка вызова одной модели. Возвращает (parsed_dict_or_None, raw_text_or_None, error_code_or_None)."""
    if provider_mode == "anthropic_direct":
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model, max_tokens=max_tokens, system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw_text = "".join(block.text for block in response.content if getattr(block, "type", None) == "text")
    else:
        client = OpenAI(base_url=base_url, api_key=api_key)
        response = call_chat_completion(
            client, model,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            max_tokens=max_tokens, provider_mode=provider_mode,
        )
        raw_text = response.choices[0].message.content or ""

    if not raw_text.strip():
        return None, raw_text, "EMPTY_MODEL_RESPONSE"
    parsed = json.loads(strip_json_fences(raw_text))
    if not isinstance(parsed, dict) or not all(k in parsed for k in required_keys):
        return None, raw_text, "JSON_SCHEMA_MISMATCH"
    return parsed, raw_text, None


def call_role_with_failover(role_label, provider_mode, base_url, api_key, mode, manual_model,
                             auto_models, system_prompt, user_prompt, max_tokens, required_keys):
    """
    Универсальный вызов ИИ для одной роли (Аналитик или Сценарист):
    — mode == "manual": используется РОВНО одна выбранная модель, без автопереключения (ручной режим —
      осознанный выбор администратора, например если автоматика ведёт себя непредсказуемо);
    — mode == "auto": перебирает auto_models по приоритету (модели вне кулдауна — первыми), при лимите/
      пустом ответе/невалидном JSON помечает модель в кулдаун и пробует следующую.
    Возвращает (parsed_dict_or_None, raw_text_последней_попытки, model_id_который_ответил_or_None, attempts_log).
    """
    attempts_log = []
    if not api_key:
        return None, None, None, [f"{role_label}: не задан API-ключ"]
    if provider_mode == "anthropic_direct" and Anthropic is None:
        return None, None, None, [f"{role_label}: не установлена библиотека anthropic"]
    if provider_mode != "anthropic_direct" and OpenAI is None:
        return None, None, None, [f"{role_label}: не установлена библиотека openai"]

    if mode == "manual":
        candidates = [manual_model] if manual_model else []
    else:
        candidates = order_models_by_cooldown(auto_models or ([manual_model] if manual_model else []))

    if not candidates:
        return None, None, None, [f"{role_label}: не выбрано ни одной модели"]

    last_raw_text = None
    for idx, model in enumerate(candidates):
        try:
            parsed, raw_text, err = _attempt_ai_call(
                provider_mode, base_url, api_key, model, system_prompt, user_prompt, max_tokens, required_keys
            )
            if raw_text is not None:
                last_raw_text = raw_text
            if parsed is not None:
                if idx > 0:
                    attempts_log.append(f"{role_label}: недоступны — {', '.join(candidates[:idx])}; сработала {model}")
                else:
                    attempts_log.append(f"{role_label}: сработала {model}")
                return parsed, raw_text, model, attempts_log
            attempts_log.append(f"{role_label}: {model} — {err}")
            if mode == "auto":
                mark_model_cooldown(model, seconds=120)
        except json.JSONDecodeError:
            attempts_log.append(f"{role_label}: {model} — ответ не является валидным JSON")
            if mode == "auto":
                mark_model_cooldown(model, seconds=120)
        except Exception as exc:
            detail = f"{type(exc).__name__}: {exc}"
            attempts_log.append(f"{role_label}: {model} — {detail}")
            if mode == "auto" and is_transient_ai_error(exc):
                mark_model_cooldown(model, seconds=600)
        if mode == "manual":
            break  # ручной режим: одна попытка, без переключения на другую модель

    return None, last_raw_text, None, attempts_log


def fallback_analyst_result(reason: str):
    return {
        "audience_summary": f"Не удалось получить ответ от ИИ-аналитика ({reason}). Ниже — заглушка.",
        "patterns": [{
            "pattern": "Заглушка", "evidence": "демо", "strength": "предварительная",
            "source_video_url": "", "source_video_views": 0, "source_video_er": 0,
        }],
        "verdict_note": "Проверьте настройки ИИ-аналитика (модели/ключ) в панели администратора.",
    }

def fallback_scriptwriter_result(reason: str):
    return {
        "scenarios": [{
            "title": "Демо-сценарий", "based_on_pattern": "—", "based_on_video": "—",
            "anchor_url": "", "anchor_views": 0, "anchor_er": 0,
            "hook": f"Не удалось получить ответ от ИИ-сценариста ({reason})", "script": "—", "caption": "—",
            "ad_marking_note": "Реклама.", "fit_score": "средний",
            "forecast_views_low": 0, "forecast_views_high": 0, "forecast_er": 0,
            "virality_probability": 0, "virality_reasoning": "—", "best_posting_time_msk": "—",
        }],
    }


REELS_COLUMNS = [
    "Ссылка на ролик", "Просмотры", "Лайки", "Комментарии", "Сохранения",
    "Дата публикации", "Время публикации (МСК)", "Что происходит в ролике (кратко)", "Транскрипция (если есть)"
]

MSK_OFFSET = timedelta(hours=3)

def to_msk_time_str(raw_timestamp) -> str:
    """
    Пытается распарсить время публикации ролика (ISO-строка с 'Z'/смещением или unix-время
    в секундах/миллисекундах — так отдают разные акторы Apify) и вернуть время суток в формате
    HH:MM по МСК. Если распарсить не удалось — возвращает пустую строку, ничего не выдумывая.
    """
    if not raw_timestamp:
        return ""
    text = str(raw_timestamp).strip()
    try:
        if text.replace(".", "", 1).isdigit():
            ts = float(text)
            if ts > 10 ** 12:  # похоже на миллисекунды
                ts /= 1000
            dt_utc = datetime.utcfromtimestamp(ts)
        else:
            iso_text = text.replace("Z", "+00:00")
            dt = datetime.fromisoformat(iso_text)
            dt_utc = dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo is not None else dt
        dt_msk = dt_utc + MSK_OFFSET
        return dt_msk.strftime("%H:%M")
    except Exception:
        return ""

if "reels_data" not in st.session_state:
    st.session_state.reels_data = pd.DataFrame(
        [{"Ссылка на ролик": "", "Просмотры": 0, "Лайки": 0, "Комментарии": 0,
          "Сохранения": 0, "Дата публикации": "", "Время публикации (МСК)": "",
          "Что происходит в ролике (кратко)": "", "Транскрипция (если есть)": ""} for _ in range(6)]
    )

def build_test_dataframe():
    rows = [
        ("instagram.com/reel/demo1", 210000, 15200, 810, 4100, "2026-05-02", "19:10", "Примерка нескольких образов подряд под трендовый звук", ""),
        ("instagram.com/reel/demo2", 45000, 1800, 90, 320, "2026-05-06", "11:45", "Обзор ткани и посадки одного изделия", ""),
        ("instagram.com/reel/demo3", 320000, 28000, 1450, 9200, "2026-05-10", "20:35", "Юмористический скетч в примерочной с подругой", ""),
    ]
    return pd.DataFrame(rows, columns=REELS_COLUMNS)

def apify_get_first(item: dict, keys, default=""):
    for k in keys:
        val = item.get(k)
        if val not in (None, ""): return val
    return default

class ApifyApiError(Exception):
    """Ошибка вызова Apify API с разобранным телом ответа. Все ошибки Apify API имеют формат
    {"error": {"type": "...", "message": "..."}} (docs.apify.com). ВАЖНО (проверено на реальном
    ответе, а не только по документации): исчерпание месячного лимита Apify тоже может прийти как
    403 (например error.type "platform-feature-disabled" с текстом "Monthly usage hard limit
    exceeded") — то есть по одному лишь HTTP-статусу 402 vs 403 достоверно отличить «кончились
    деньги» от «нет прав у токена» НЕЛЬЗЯ. Надёжный сигнал — текст message, поэтому classify ниже
    смотрит в первую очередь на него, а не на код/тип."""
    def __init__(self, status_code, error_type=None, error_message=None):
        self.status_code = status_code
        self.error_type = error_type or ""
        self.error_message = error_message or ""
        label = f"HTTP {status_code}"
        if error_type: label += f" [{error_type}]"
        if error_message: label += f": {error_message}"
        super().__init__(label)


def _apify_error_from_response(resp):
    """Достаёт (error_type, error_message) из тела ответа Apify, если оно распарсилось."""
    try:
        body = resp.json()
        err = (body or {}).get("error") or {}
        return err.get("type"), err.get("message")
    except Exception:
        return None, None


def _wrap_apify_http_error(exc) -> ApifyApiError:
    error_type, error_message = _apify_error_from_response(exc.response)
    return ApifyApiError(exc.response.status_code, error_type, error_message)


def fetch_reels_via_apify(token, actor, targets, results_limit=None, lookback_days=None,
                           include_transcript=False, skip_pinned=True, skip_trial=True, timeout=300):
    if httpx is None: raise RuntimeError("Библиотека httpx не установлена")
    token = sanitize_apify_token(token)
    actor_path = actor.strip("/").replace("/", "~")
    url = f"https://api.apify.com/v2/acts/{actor_path}/run-sync-get-dataset-items?token={token}"
    body = {"username": targets, "skipPinnedPosts": skip_pinned, "skipTrialReels": skip_trial, "includeTranscript": include_transcript}
    if results_limit: body["resultsLimit"] = results_limit
    if lookback_days: body["onlyPostsNewerThan"] = f"{lookback_days} days"
    resp = httpx.post(url, json=body, timeout=timeout)
    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise _wrap_apify_http_error(exc) from exc
    data = resp.json()
    return data if isinstance(data, list) else data.get("items", [])


# ----------------------------------------------------------------------------
# ЖИВАЯ ПРОВЕРКА ЛИМИТОВ КЛЮЧА APIFY + АВТОПЕРЕКЛЮЧЕНИЕ МЕЖДУ КЛЮЧАМИ
# ----------------------------------------------------------------------------
# Лимиты Apify — на уровне АККАУНТА, сбрасываются ежемесячно по собственному биллинг-циклу
# аккаунта (не по фиксированной дате календаря и не через N дней после исчерпания). Официальный
# способ узнать точный статус и дату сброса — эндпоинт GET /v2/users/me/limits, который возвращает
# monthlyUsageCycle.endAt — именно ЕЁ мы показываем как «когда обновится» вместо того чтобы гадать
# по дате добавления ключа. Поэтому маркер зелёный/красный держится не на догадке, а на последней
# живой проверке через сам Apify.
APIFY_LIMITS_URL = "https://api.apify.com/v2/users/me/limits"
APIFY_USAGE_RED_THRESHOLD_PCT = 97  # помечаем ключ красным чуть ДО фактического исчерпания — с запасом

def check_apify_key_live(token, timeout=20):
    """Спрашивает у Apify реальный статус лимитов по токену. Возвращает dict:
    {"ok": bool, "status": "green"|"red"|"unknown", "usage_pct": float|None, "usage_detail": str,
     "cycle_reset_at": str|None, "token_used": str, "error": str|None}.
    token_used — токен ПОСЛЕ автоочистки (см. sanitize_apify_token): если он отличается от того,
    что было передано, значит в базе хранилась ссылка вместо токена и её стоит перезаписать
    (см. вызовы update_apify_key_token рядом с каждым использованием этой функции)."""
    token = sanitize_apify_token(token)
    if httpx is None:
        return {"ok": False, "status": "unknown", "usage_pct": None, "usage_detail": "", "cycle_reset_at": None, "token_used": token, "error": "Библиотека httpx не установлена"}
    if not token:
        return {"ok": False, "status": "unknown", "usage_pct": None, "usage_detail": "", "cycle_reset_at": None, "token_used": token, "error": "Пустой токен"}
    try:
        resp = httpx.get(APIFY_LIMITS_URL, params={"token": token}, timeout=timeout)
    except Exception as exc:
        return {"ok": False, "status": "unknown", "usage_pct": None, "usage_detail": "", "cycle_reset_at": None, "token_used": token,
                "error": f"Не удалось связаться с Apify: {type(exc).__name__}: {str(exc)[:200]}"}

    if resp.status_code >= 400:
        error_type, error_message = _apify_error_from_response(resp)
        combined = f"{error_message or ''} {error_type or ''}".lower()
        if resp.status_code == 401 or "invalid" in combined and "token" in combined:
            return {"ok": False, "status": "unknown", "usage_pct": None, "usage_detail": "", "cycle_reset_at": None, "token_used": token,
                    "error": "Токен недействителен (401) — проверьте, что вставлен настоящий API-токен Apify, а не ссылка/URL."}
        if any(h in combined for h in ("monthly usage", "hard limit", "quota", "insufficient funds", "suspended")):
            # Лимит исчерпан — Apify сообщил об этом прямо в теле ошибки (может прийти и с кодом 402,
            # и с 403 — см. docstring ApifyApiError), поэтому доверяем тексту, а не статусу.
            return {"ok": True, "status": "red", "usage_pct": None,
                    "usage_detail": (error_message or "Месячный лимит исчерпан (по данным Apify)")[:250],
                    "cycle_reset_at": None, "token_used": token, "error": None}
        detail = error_message or f"HTTP {resp.status_code}"
        if error_type: detail += f" [{error_type}]"
        return {"ok": False, "status": "unknown", "usage_pct": None, "usage_detail": "", "cycle_reset_at": None, "token_used": token, "error": detail[:250]}

    try:
        payload = (resp.json() or {}).get("data", {}) or {}
        limits = payload.get("limits", {}) or {}
        current = payload.get("current", {}) or {}
        cycle = payload.get("monthlyUsageCycle", {}) or {}

        max_usd = limits.get("maxMonthlyUsageUsd")
        cur_usd = current.get("monthlyUsageUsd")
        usage_pct = None
        if max_usd not in (None, 0) and cur_usd is not None:
            usage_pct = round(cur_usd / max_usd * 100, 1)

        status = "red" if (usage_pct is not None and usage_pct >= APIFY_USAGE_RED_THRESHOLD_PCT) else "green"
        usage_detail = (
            f"${cur_usd:.2f} из ${max_usd:.2f} за текущий цикл ({usage_pct}%)"
            if (cur_usd is not None and max_usd) else "нет данных об использовании (ответ Apify не содержит лимитов — токен, скорее всего, урезанного/ограниченного типа)"
        )
        return {
            "ok": True, "status": status, "usage_pct": usage_pct, "usage_detail": usage_detail,
            "cycle_reset_at": cycle.get("endAt"), "token_used": token, "error": None,
        }
    except Exception as exc:
        return {"ok": False, "status": "unknown", "usage_pct": None, "usage_detail": "", "cycle_reset_at": None, "token_used": token,
                "error": f"Не удалось разобрать ответ Apify: {type(exc).__name__}: {str(exc)[:200]}"}


def _describe_apify_error(exc: Exception):
    """Категоризирует одну ошибку вызова Apify: 'limit' — реально исчерпан месячный бюджет/квота
    аккаунта; 'permission' — у токена нет прав на актор либо актор требует согласия на оплату
    (аренда/Pay-Per-Result); 'auth' — токен недействителен или это в принципе не токен (например
    в базу попала ссылка целиком); 'other' — явно не про ключ (опечатка в имени актора, обрыв сети).
    Решение принимается в первую очередь по ТЕКСТУ сообщения от Apify — статус-код 402/403
    ненадёжен: на практике оба варианта видели и для исчерпанных лимитов, и для проблем с правами."""
    msg = str(exc).lower()
    error_type = getattr(exc, "error_type", "") or ""
    status_code = getattr(exc, "status_code", None)
    if status_code == 401 or "invalid-token" in error_type or ("invalid" in msg and "token" in msg):
        return "auth", "токен недействителен"
    if any(h in msg for h in ("monthly usage", "hard limit", "insufficient funds", "quota exceeded", "usage hard limit")):
        return "limit", "исчерпан месячный лимит аккаунта"
    if (error_type in ("insufficient-permissions", "full-permission-actor-not-approved")
            or "must rent" in msg or "rent a paid actor" in msg or "payment required" in msg
            or "insufficient permission" in msg):
        return "permission", "нет прав на актор либо не подтверждена оплата (аренда/Pay-Per-Result)"
    if status_code in (401, 402, 403, 429):
        return "permission", "ошибка доступа неясной природы (нет прав/лимиты/блокировка)"
    return "other", str(exc)


class ApifyAllKeysFailedError(RuntimeError):
    """Поднимается, когда весь пул Apify-ключей перебран и НИ ОДИН не сработал. Несёт полный
    attempts_log (что произошло с каждым ключом по порядку), чтобы UI мог показать не только
    последнюю ошибку, а всю картину — сколько ключей испробовано и почему каждый не подошёл."""
    def __init__(self, message, attempts_log):
        super().__init__(message)
        self.attempts_log = attempts_log


def fetch_reels_via_apify_with_failover(actor, targets, results_limit=None, lookback_days=None,
                                         include_transcript=False, timeout=300):
    """Как fetch_reels_via_apify, но перебирает ВЕСЬ сохранённый пул Apify-ключей вместо одного
    токена — тот же принцип автопереключения, что уже используется для моделей ИИ (см.
    call_role_with_failover): пробует ключи в порядке предпочтения (зелёные → непроверенные →
    красные) один за другим, пока не найдёт рабочий или не кончится пул — без потери уже введённых
    данных формы и без падения всего анализа при сбое отдельного ключа. Если у сохранённого ключа
    формат оказался «ссылка вместо токена» — чинит его в базе на лету (см. sanitize_apify_token) и
    пробует уже исправленным. Если ВЕСЬ пул исчерпан — поднимает ApifyAllKeysFailedError с точным,
    по категориям (лимиты / права / невалидный токен), объяснением и полным логом попыток.
    Возвращает (items, token_used, attempts_log)."""
    pool = get_apify_key_pool()
    if not pool:
        raise RuntimeError("Не добавлено ни одного Apify-ключа — добавьте его в разделе «Редактор менеджеров → Ключи Apify».")
    attempts_log = []
    errors_seen = []
    for key_rec in pool:
        token = sanitize_apify_token(key_rec["token"])
        if token != key_rec["token"]:
            update_apify_key_token(key_rec["id"], token)
            attempts_log.append(f"Apify: ключ …{token[-4:] if len(token) >= 4 else token} — формат исправлен автоматически (в базе была ссылка вместо самого токена)")
        token_tail = token[-4:] if len(token) >= 4 else token
        try:
            items = fetch_reels_via_apify(
                token, actor, targets, results_limit=results_limit, lookback_days=lookback_days,
                include_transcript=include_transcript, timeout=timeout,
            )
            attempts_log.append(f"Apify: сработал ключ …{token_tail}")
            return items, token, attempts_log
        except Exception as exc:
            errors_seen.append(exc)
            category, category_text = _describe_apify_error(exc)
            detail = f"{exc.error_type + ': ' if isinstance(exc, ApifyApiError) and exc.error_type else ''}{exc}"
            if category != "other":
                # Статус всегда переводим в красный по факту наблюдаемого сбоя. Живая проверка лимитов
                # видит только денежный бюджет и может ошибочно показать «всё ок», если проблема на
                # самом деле в правах токена, а не в деньгах — поэтому не даём такой проверке молча
                # перезаписать красный обратно в зелёный, только явное «Проверить» это делает.
                live = check_apify_key_live(token)
                combined_detail = f"{live.get('usage_detail')} · " if live.get("ok") and live.get("usage_detail") else ""
                update_apify_key_status(
                    key_rec["id"], "red",
                    usage_pct=live.get("usage_pct"),
                    usage_detail=f"{combined_detail}{category_text}: {detail}"[:300],
                    cycle_reset_at=live.get("cycle_reset_at"),
                )
                attempts_log.append(f"Apify: ключ …{token_tail} — {detail} ({category_text}) — помечен красным, пробую следующий")
            else:
                attempts_log.append(f"Apify: ключ …{token_tail} — {detail} (не похоже на проблему с ключом, но всё равно пробую следующий)")

    categories_seen = {_describe_apify_error(e)[0] for e in errors_seen} if errors_seen else set()
    tried_n = len(pool)
    if categories_seen == {"limit"}:
        message = (
            f"Все {tried_n} ключ(ей) Apify в пуле сейчас исчерпали месячный лимит — подождите сброса цикла "
            f"(дата видна у каждого ключа на вкладке «Ключи Apify») или добавьте ключ от другого аккаунта Apify "
            f"(токены одного и того же аккаунта делят общий лимит — новый токен того же аккаунта не поможет)."
        )
    elif categories_seen == {"auth"}:
        message = (
            f"Все {tried_n} ключ(ей) Apify оказались недействительны (401). Если в поле был вставлен не сам "
            f"токен, а ссылка — формат уже исправлен автоматически; если ошибка сохраняется — перевыпустите "
            f"токен в консоли Apify (Settings → Integrations) и добавьте заново."
        )
    elif categories_seen == {"permission"}:
        message = (
            f"Все {tried_n} ключ(ей) Apify вернули ошибку доступа, не похожую на исчерпание лимитов — "
            f"вероятно, у токена(ов) нет прав на запуск акторов, либо актор «{actor}» требует явного "
            f"согласия на оплату (Pay-Per-Result/аренда). Откройте страницу актора в консоли Apify под "
            f"каждым аккаунтом и один раз примите условия использования («Try for free»), либо перевыпустите "
            f"токен с полными правами."
        )
    elif categories_seen == {"other"} or not categories_seen:
        last_text = str(errors_seen[-1]) if errors_seen else "неизвестная ошибка"
        message = (
            f"Не удалось получить данные ни по одному из {tried_n} испробованных Apify-ключей, и похоже, "
            f"дело не в самих ключах (не лимиты, не права) — вероятно, опечатка в имени актора «{actor}», "
            f"сбой сети или сервиса Apify. Последняя ошибка: {last_text}"
        )
    else:
        message = (
            f"Не удалось получить данные ни по одному из {tried_n} испробованных Apify-ключей — причины разные "
            f"у разных ключей (подробности по каждому — ниже)."
        )
    raise ApifyAllKeysFailedError(message, attempts_log)


def apify_items_to_dataframe(items):
    rows = []
    for item in items:
        views = apify_get_first(item, ["videoPlayCount", "videoViewCount", "playsCount", "viewsCount", "playCount"], 0)
        likes = apify_get_first(item, ["likesCount", "likes"], 0)
        comments = apify_get_first(item, ["commentsCount", "comments"], 0)
        shares = apify_get_first(item, ["sharesCount", "shares"], 0)
        caption = apify_get_first(item, ["caption", "text"], "")
        transcript = apify_get_first(item, ["transcript", "videoTranscript", "transcriptText"], "")
        link = apify_get_first(item, ["url", "permalink", "postUrl"], "")
        timestamp = apify_get_first(item, ["timestamp", "takenAt", "date"], "")
        rows.append({
            "Ссылка на ролик": link, "Просмотры": views, "Лайки": likes, "Комментарии": comments,
            "Сохранения": shares, "Дата публикации": str(timestamp)[:10],
            "Время публикации (МСК)": to_msk_time_str(timestamp),
            "Что происходит в ролике (кратко)": str(caption)[:300], "Транскрипция (если есть)": transcript,
        })
    return pd.DataFrame(rows, columns=REELS_COLUMNS) if rows else pd.DataFrame(columns=REELS_COLUMNS)


def compute_reels_metrics(df: pd.DataFrame, viral_threshold: float = 3.0):
    clean = df.copy()
    clean = clean[clean["Ссылка на ролик"].astype(str).str.strip() != ""]
    clean["Просмотры"] = pd.to_numeric(clean["Просмотры"], errors="coerce").fillna(0)
    clean["Лайки"] = pd.to_numeric(clean["Лайки"], errors="coerce").fillna(0)
    clean["Комментарии"] = pd.to_numeric(clean["Комментарии"], errors="coerce").fillna(0)
    clean["Сохранения"] = pd.to_numeric(clean["Сохранения"], errors="coerce").fillna(0)
    valid_views = [v for v in clean["Просмотры"].tolist() if v > 0]
    median_views = statistics.median(valid_views) if valid_views else 0

    def er_pct(row):
        if row["Просмотры"] <= 0: return 0.0
        return round((row["Лайки"] + row["Комментарии"] + row["Сохранения"]) / row["Просмотры"] * 100, 2)
    def perf_index(row):
        if median_views <= 0 or row["Просмотры"] <= 0: return None
        return round(row["Просмотры"] / median_views, 2)

    clean["ER_%"] = clean.apply(er_pct, axis=1)
    clean["Индекс_к_медиане"] = clean.apply(perf_index, axis=1)
    clean["Аномалия"] = clean["Индекс_к_медиане"].apply(lambda x: bool(x and x >= viral_threshold))
    return clean, median_views

def select_top_viral(metrics_df: pd.DataFrame, threshold: float, top_n: int):
    qualifying = metrics_df[metrics_df["Индекс_к_медиане"].apply(lambda x: bool(x and x >= threshold))]
    qualifying = qualifying.sort_values("Индекс_к_медиане", ascending=False)
    if qualifying.empty:
        return metrics_df.sort_values("Просмотры", ascending=False).head(top_n), False
    return qualifying.head(top_n), True


# ============================================================================
# ПОСТРОЕНИЕ ПРОМПТОВ ДЛЯ КАЖДОЙ РОЛИ
# ============================================================================
def build_analyst_user_prompt(blogger_url, product_brief, metrics_df, median_views, top_viral_df, viral_stats=None):
    table_records = metrics_df.drop(columns=["Транскрипция (если есть)"], errors="ignore").to_dict(orient="records")
    viral_block = ""
    if top_viral_df is not None and not top_viral_df.empty:
        viral_records = top_viral_df.to_dict(orient="records")
        viral_block = (
            f"\n\nТоп-{len(viral_records)} самых залётных роликов ЭТОГО блогера "
            f"(здесь есть поле 'Транскрипция (если есть)' — используй именно его для разбора хука и структуры, "
            f"и точные цифры охвата/ER для полей source_video_views/source_video_er/source_video_url):\n"
            f"{json.dumps(viral_records, ensure_ascii=False, indent=2)}"
        )
    stats_block = ""
    if viral_stats:
        stats_block = (
            f"\n\nСправочная статистика по всей выгрузке этого блогера: всего роликов — {viral_stats.get('total', 0)}, "
            f"из них залётных — {viral_stats.get('viral_count', 0)} ({viral_stats.get('viral_pct', 0)}%), "
            f"средний охват НЕ залётных роликов — {viral_stats.get('avg_non_viral_views', 0)}, "
            f"средний охват залётных роликов — {viral_stats.get('avg_viral_views', 0)}."
        )
    return (
        f"Блогер: {blogger_url}\nМедиана просмотров: {median_views:.0f}\n\n"
        f"Бриф о товаре (нужен только чтобы понять, какие форматы совместимы с показом товара — "
        f"сценарии ты не пишешь):\n{product_brief}\n\nВсе загруженные ролики:\n"
        f"{json.dumps(table_records, ensure_ascii=False, indent=2)}{viral_block}{stats_block}"
    )


def build_scriptwriter_user_prompt(blogger_url, product_brief, metrics_df, median_views, n_scenarios, top_viral_df,
                                    patterns, viral_stats=None, previous_scenarios=None):
    table_records = metrics_df.drop(columns=["Транскрипция (если есть)"], errors="ignore").to_dict(orient="records")
    viral_block = ""
    if top_viral_df is not None and not top_viral_df.empty:
        viral_records = top_viral_df.to_dict(orient="records")
        viral_block = (
            f"\n\nТоп-{len(viral_records)} самых залётных роликов ЭТОГО блогера (для контекста, транскрипции и лексики блогера):\n"
            f"{json.dumps(viral_records, ensure_ascii=False, indent=2)}"
        )
    stats_block = ""
    if viral_stats:
        stats_block = (
            f"\n\nСправочная статистика по всей выгрузке этого блогера (используй для калибровки forecast_* "
            f"и virality_probability — НЕ прогнозируй охват выше anchor_views без явного основания): "
            f"всего роликов — {viral_stats.get('total', 0)}, из них залётных — {viral_stats.get('viral_count', 0)} "
            f"({viral_stats.get('viral_pct', 0)}%), средний охват НЕ залётных роликов — {viral_stats.get('avg_non_viral_views', 0)}, "
            f"средний охват залётных роликов — {viral_stats.get('avg_viral_views', 0)}."
        )
    patterns_block = (
        f"\n\nГОТОВЫЕ ПАТТЕРНЫ ОТ АНАЛИТИКА (используй ТОЛЬКО их, не ищи новые в ретроспективе):\n"
        f"{json.dumps(patterns or [], ensure_ascii=False, indent=2)}"
    )
    regen_block = ""
    if previous_scenarios:
        prev_lines = "\n".join(
            f"- «{s.get('title', '')}» — хук: {s.get('hook', '')}" for s in previous_scenarios
        )
        regen_block = (
            "\n\nЭТО ПОВТОРНЫЙ ЗАПРОС «ОБНОВИТЬ СЦЕНАРИИ» (паттерны и данные роликов те же, аналитик их заново не пересчитывал). "
            "Напиши НОВЫЙ набор сценариев на основе тех же паттернов: другие хуки, другие ракурсы подачи, по возможности "
            "другие паттерны из переданного списка, если их несколько. Не повторяй дословно прежние формулировки хуков и сценариев.\n"
            f"Прежние сценарии (их НЕ повторять):\n{prev_lines}"
        )
    return (
        f"Блогер: {blogger_url}\nМедиана просмотров: {median_views:.0f}\nНужно сценариев: {n_scenarios}\n\n"
        f"Бриф о товаре:\n{product_brief}\n\nВсе загруженные ролики:\n"
        f"{json.dumps(table_records, ensure_ascii=False, indent=2)}{viral_block}{patterns_block}{stats_block}{regen_block}"
    )


def build_scriptwriter_user_prompt_single(blogger_url, product_brief, metrics_df, median_views, top_viral_df,
                                           patterns, viral_stats, all_scenarios, target_index, editor_feedback=None):
    """
    Промпт для точечного обновления ОДНОГО сценария (кнопка «🔄 Обновить сценарий» у конкретной карточки,
    либо автоматический перезапуск после замечания редактора при QC-проверке).
    Не трогает остальные уже готовые сценарии и не запускает аналитика заново — просит сценариста вернуть
    ровно 1 новый сценарий взамен указанного, по возможности на основе другого паттерна из уже готового
    списка, чтобы не дублировать доноров уже существующих сценариев.
    editor_feedback (опционально) — конкретные замечания редактора (revision_notes), которые нужно
    обязательно устранить в новой версии, с обязательным требованием довести fit_score до "высокий".
    """
    table_records = metrics_df.drop(columns=["Транскрипция (если есть)"], errors="ignore").to_dict(orient="records")
    viral_block = ""
    if top_viral_df is not None and not top_viral_df.empty:
        viral_records = top_viral_df.to_dict(orient="records")
        viral_block = (
            f"\n\nТоп-{len(viral_records)} самых залётных роликов ЭТОГО блогера (для контекста, транскрипции и лексики блогера):\n"
            f"{json.dumps(viral_records, ensure_ascii=False, indent=2)}"
        )
    stats_block = ""
    if viral_stats:
        stats_block = (
            f"\n\nСправочная статистика по всей выгрузке этого блогера (используй для калибровки forecast_* "
            f"и virality_probability): всего роликов — {viral_stats.get('total', 0)}, из них залётных — "
            f"{viral_stats.get('viral_count', 0)} ({viral_stats.get('viral_pct', 0)}%), средний охват НЕ залётных "
            f"роликов — {viral_stats.get('avg_non_viral_views', 0)}, средний охват залётных роликов — "
            f"{viral_stats.get('avg_viral_views', 0)}."
        )
    patterns_block = (
        f"\n\nГОТОВЫЕ ПАТТЕРНЫ ОТ АНАЛИТИКА (используй ТОЛЬКО их, не ищи новые в ретроспективе):\n"
        f"{json.dumps(patterns or [], ensure_ascii=False, indent=2)}"
    )

    all_scenarios = all_scenarios or []
    target = all_scenarios[target_index] if 0 <= target_index < len(all_scenarios) else {}
    other_scenarios = [s for i, s in enumerate(all_scenarios) if i != target_index]
    other_lines = "\n".join(
        f"- «{s.get('title', '')}» (anchor: {s.get('anchor_url', '—')})" for s in other_scenarios
    ) or "(других сценариев нет)"

    instruction = (
        "\n\nЗАДАЧА: ОБНОВИ ТОЛЬКО ОДИН СЦЕНАРИЙ (аналитик паттерны заново не пересчитывал — данные те же). "
        "Верни в массиве scenarios РОВНО 1 новый сценарий по ПОЛНОЙ JSON-схеме (title, based_on_pattern, "
        "based_on_video, anchor_url, anchor_views, anchor_er, hook, script, caption, ad_marking_note, fit_score, "
        "forecast_views_low, forecast_views_high, forecast_er, virality_probability, virality_reasoning, "
        f"best_posting_time_msk), который заменит текущий вариант «{target.get('title', '')}» "
        f"(его прежний хук: «{target.get('hook', '')}», anchor: {target.get('anchor_url', '—')}). "
        "Не повторяй дословно прежнюю формулировку хука/сценария.\n"
        f"Остальные сценарии этого блогера уже готовы и НЕ пересоздаются — по возможности выбери другой "
        f"паттерн из переданного списка, чтобы не дублировать доноров уже использованных сценариев:\n{other_lines}"
    )
    editor_block = ""
    if editor_feedback:
        editor_block = (
            "\n\n⚠️ ЗАМЕЧАНИЕ РЕДАКТОРА (обязательно к исправлению — предыдущая версия этого сценария "
            "была отклонена контролем качества, цель — довести fit_score строго до \"высокий\" и убрать "
            f"все отмеченные слабые места):\n{editor_feedback}"
        )
    return (
        f"Блогер: {blogger_url}\nМедиана просмотров: {median_views:.0f}\n\n"
        f"Бриф о товаре:\n{product_brief}\n\nВсе загруженные ролики:\n"
        f"{json.dumps(table_records, ensure_ascii=False, indent=2)}{viral_block}{patterns_block}{stats_block}{instruction}{editor_block}"
    )


# ============================================================================
# ЗАПУСК КАЖДОЙ РОЛИ (ОБЁРТКИ НАД call_role_with_failover)
# ============================================================================
def run_analyst_stage(blogger_url, product_brief, metrics_df, median_views, top_viral_df, viral_stats,
                       provider_mode, base_url, api_key, mode, manual_model, auto_models, max_tokens, system_prompt):
    """Возвращает (result_dict, raw_text, model_used_or_None, attempts_log). Если все попытки провалились,
    result_dict — это заглушка fallback_analyst_result, а model_used будет None (сигнал полного отказа роли)."""
    user_prompt = build_analyst_user_prompt(blogger_url, product_brief, metrics_df, median_views, top_viral_df, viral_stats)
    parsed, raw_text, model_used, attempts_log = call_role_with_failover(
        "Аналитик", provider_mode, base_url, api_key, mode, manual_model, auto_models,
        system_prompt, user_prompt, max_tokens, required_keys=("patterns",),
    )
    if parsed is None:
        reason = attempts_log[-1].split(" — ", 1)[-1] if attempts_log else "неизвестная ошибка"
        return fallback_analyst_result(reason), raw_text, None, attempts_log
    parsed.setdefault("audience_summary", "")
    parsed.setdefault("patterns", [])
    parsed.setdefault("verdict_note", "")
    return parsed, raw_text, model_used, attempts_log


def run_scriptwriter_stage(blogger_url, product_brief, metrics_df, median_views, n_scenarios, top_viral_df,
                            patterns, provider_mode, base_url, api_key, mode, manual_model, auto_models,
                            max_tokens, system_prompt, viral_stats=None, previous_scenarios=None):
    user_prompt = build_scriptwriter_user_prompt(
        blogger_url, product_brief, metrics_df, median_views, n_scenarios, top_viral_df,
        patterns, viral_stats=viral_stats, previous_scenarios=previous_scenarios,
    )
    parsed, raw_text, model_used, attempts_log = call_role_with_failover(
        "Сценарист", provider_mode, base_url, api_key, mode, manual_model, auto_models,
        system_prompt, user_prompt, max_tokens, required_keys=("scenarios",),
    )
    if parsed is None:
        reason = attempts_log[-1].split(" — ", 1)[-1] if attempts_log else "неизвестная ошибка"
        return fallback_scriptwriter_result(reason), raw_text, None, attempts_log
    parsed.setdefault("scenarios", [])
    return parsed, raw_text, model_used, attempts_log


def run_scriptwriter_single_stage(blogger_url, product_brief, metrics_df, median_views, top_viral_df, patterns,
                                   viral_stats, all_scenarios, target_index,
                                   provider_mode, base_url, api_key, mode, manual_model, auto_models,
                                   max_tokens, system_prompt, editor_feedback=None):
    user_prompt = build_scriptwriter_user_prompt_single(
        blogger_url, product_brief, metrics_df, median_views, top_viral_df, patterns, viral_stats,
        all_scenarios, target_index, editor_feedback=editor_feedback,
    )
    parsed, raw_text, model_used, attempts_log = call_role_with_failover(
        "Сценарист", provider_mode, base_url, api_key, mode, manual_model, auto_models,
        system_prompt, user_prompt, max_tokens, required_keys=("scenarios",),
    )
    if parsed is None:
        reason = attempts_log[-1].split(" — ", 1)[-1] if attempts_log else "неизвестная ошибка"
        return fallback_scriptwriter_result(reason), raw_text, None, attempts_log
    parsed.setdefault("scenarios", [])
    return parsed, raw_text, model_used, attempts_log


# ============================================================================
# РОЛЬ «РЕДАКТОР»: контроль качества сценариев, гейт fit_score = "высокий"
# ============================================================================
def find_pattern_evidence(patterns, pattern_name) -> str:
    """Ищет анатомию паттерна-донора по его имени (based_on_pattern сценария) в списке паттернов
    аналитика и возвращает evidence — то есть конкретный разбор оригинального вирусного ролика.
    Если точного совпадения нет, отдаёт evidence первого паттерна (лучше частичный контекст, чем никакой)."""
    if not patterns:
        return ""
    name = (pattern_name or "").strip().lower()
    if name:
        for p in patterns:
            if str(p.get("pattern", "")).strip().lower() == name:
                return p.get("evidence", "")
        for p in patterns:
            if name in str(p.get("pattern", "")).strip().lower() or str(p.get("pattern", "")).strip().lower() in name:
                return p.get("evidence", "")
    return patterns[0].get("evidence", "") if patterns else ""


def build_editor_user_prompt(scenario, pattern_evidence, product_brief):
    return (
        f"Бриф о товаре:\n{product_brief}\n\n"
        f"Анатомия паттерна-донора (от аналитика):\n{pattern_evidence or '(не найдена — оцени сценарий по остальным критериям)'}\n\n"
        f"Сценарий на проверку (JSON):\n{json.dumps(scenario, ensure_ascii=False, indent=2)}"
    )


def fallback_editor_result(reason: str):
    """Fail-open: если редактор недоступен (ключ/лимиты/сеть), не блокируем выдачу сценариев —
    пропускаем как есть, чтобы отказ QC-роли не парализовал всю цепочку."""
    return {"verdict": "pass", "reason": f"Редактор недоступен ({reason}) — пропущено без проверки.", "revision_notes": ""}


def run_editor_stage(scenario, pattern_evidence, product_brief,
                      provider_mode, base_url, api_key, mode, manual_model, auto_models,
                      max_tokens, system_prompt):
    user_prompt = build_editor_user_prompt(scenario, pattern_evidence, product_brief)
    parsed, raw_text, model_used, attempts_log = call_role_with_failover(
        "Редактор", provider_mode, base_url, api_key, mode, manual_model, auto_models,
        system_prompt, user_prompt, max_tokens, required_keys=("verdict",),
    )
    if parsed is None:
        reason = attempts_log[-1].split(" — ", 1)[-1] if attempts_log else "неизвестная ошибка"
        return fallback_editor_result(reason), raw_text, None, attempts_log
    parsed.setdefault("verdict", "pass")
    parsed.setdefault("reason", "")
    parsed.setdefault("revision_notes", "")
    return parsed, raw_text, model_used, attempts_log


def run_scenario_qc_pass(scenarios, patterns, blogger_url, product_brief, metrics_df, median_views, top_viral_df,
                          viral_stats, provider_mode, base_url, api_key,
                          editor_mode, editor_manual_model, editor_auto_models, editor_max_tokens, editor_system_prompt,
                          scriptwriter_mode, scriptwriter_manual_model, scriptwriter_auto_models,
                          scriptwriter_max_tokens, scriptwriter_system_prompt,
                          max_revisions=1, only_indices=None):
    """
    Прогоняет каждый сценарий через Редактора и, если он требует доработки (verdict="revise"),
    просит Сценариста переписать РОВНО этот сценарий с учётом revision_notes — до max_revisions
    попыток на сценарий. Честные отказы (anchor_url пустой — «подходящего материала нет») не трогает.
    Если после всех попыток сценарий всё ещё не прошёл — помечает его scenario["_qc_flag"] с причиной,
    но не выбрасывает (лучше показать менеджеру с пометкой, чем потерять результат работы ИИ и API-лимиты).
    Возвращает (scenarios, qc_log) — qc_log — список текстовых строк для истории/отладки.
    """
    qc_log = []
    if not scenarios:
        return scenarios, qc_log
    indices = only_indices if only_indices is not None else range(len(scenarios))
    for idx in indices:
        if idx < 0 or idx >= len(scenarios):
            continue
        scenario = scenarios[idx]
        if not str(scenario.get("anchor_url", "")).strip():
            # честный отказ («подходящего материала у блогера нет») — не подлежит QC-гейту
            continue
        scenario.pop("_qc_flag", None)
        pattern_evidence = find_pattern_evidence(patterns, scenario.get("based_on_pattern", ""))
        attempts = 0
        while attempts <= max_revisions:
            verdict_result, _, editor_model, editor_attempts_log = run_editor_stage(
                scenario, pattern_evidence, product_brief,
                provider_mode, base_url, api_key, editor_mode, editor_manual_model, editor_auto_models,
                editor_max_tokens, editor_system_prompt,
            )
            qc_log.extend(editor_attempts_log)
            verdict = str(verdict_result.get("verdict", "pass")).strip().lower()
            if verdict != "revise":
                qc_log.append(f"Сценарий «{scenario.get('title', '')}»: редактор — pass" + (f" ({verdict_result.get('reason', '')})" if verdict_result.get("reason") else ""))
                break
            if attempts >= max_revisions:
                scenario["_qc_flag"] = verdict_result.get("reason") or "Не прошёл контроль качества (fit/уникальность), лимит переписываний исчерпан"
                qc_log.append(f"Сценарий «{scenario.get('title', '')}»: лимит переписываний исчерпан — оставлен с пометкой")
                break
            qc_log.append(f"Сценарий «{scenario.get('title', '')}»: редактор просит доработку — {verdict_result.get('revision_notes', '')}")
            rewritten, _, sw_model, sw_attempts_log = run_scriptwriter_single_stage(
                blogger_url, product_brief, metrics_df, median_views, top_viral_df, patterns, viral_stats,
                scenarios, idx,
                provider_mode, base_url, api_key, scriptwriter_mode, scriptwriter_manual_model,
                scriptwriter_auto_models, scriptwriter_max_tokens, scriptwriter_system_prompt,
                editor_feedback=verdict_result.get("revision_notes", ""),
            )
            qc_log.extend(sw_attempts_log)
            new_list = rewritten.get("scenarios") or []
            if sw_model and new_list:
                scenarios[idx] = new_list[0]
                scenario = scenarios[idx]
                pattern_evidence = find_pattern_evidence(patterns, scenario.get("based_on_pattern", ""))
            else:
                scenario["_qc_flag"] = "Не удалось переписать сценарий (сценарист недоступен) — показан черновой вариант"
                qc_log.append(f"Сценарий «{scenario.get('title', '')}»: переписать не удалось, сценарист недоступен")
                break
            attempts += 1
    return scenarios, qc_log


# ----------------------------------------------------------------------------
# СТРАХОВОЧНЫЙ СЛОЙ: восстановление цепочки «паттерн → ролик-источник → сценарий».
# Модель иногда упоминает ролик только текстом (например «(DbvDLUsNXj6)» внутри evidence),
# но оставляет структурированные поля source_video_*/anchor_* пустыми. Промптом это до конца
# не лечится (особенно на «lite»-моделях), поэтому после ответа ИИ мы сами ищем упоминания
# ID роликов в тексте и доподставляем реальные данные — так цепочка не рвётся даже если
# модель поленилась. Работает одинаково для результата аналитика+сценариста, объединённого
# в один result dict (patterns + scenarios), независимо от того, сколько вызовов ИИ его собрали.
# ----------------------------------------------------------------------------
_REEL_ID_URL_RE = re.compile(r"/(?:p|reel|reels)/([A-Za-z0-9_-]{5,})")
_REEL_ID_LOOSE_RE = re.compile(r"[\(\[]([A-Za-z0-9_-]{8,})[\)\]]")

def _extract_reel_id(text) -> str:
    """Достаёт короткий ID Instagram-ролика из ссылки (после /p/ или /reel/) или из текста
    вида «(DbvDLUsNXj6)», которым модель иногда заменяет полноценную ссылку."""
    if not text:
        return ""
    text = str(text)
    m = _REEL_ID_URL_RE.search(text)
    if m:
        return m.group(1)
    m = _REEL_ID_LOOSE_RE.search(text)
    if m:
        return m.group(1)
    return ""

def _build_reel_lookup(metrics_df) -> dict:
    """{ID_ролика: {'url', 'views', 'er'}} по всем роликам из ретроспективы этого блогера."""
    lookup = {}
    if metrics_df is None or metrics_df.empty or "Ссылка на ролик" not in metrics_df.columns:
        return lookup
    for _, row in metrics_df.iterrows():
        url = row.get("Ссылка на ролик", "")
        rid = _extract_reel_id(url)
        if rid:
            lookup[rid] = {"url": url, "views": row.get("Просмотры", 0), "er": row.get("ER_%", 0)}
    return lookup

def _find_reel_by_text(text: str, reel_lookup: dict):
    """Ищет в произвольном тексте (evidence/based_on_video/hook/script) упоминание ID
    любого известного ролика из ретроспективы и возвращает его данные, если нашёл."""
    if not text or not reel_lookup:
        return None
    text = str(text)
    for rid, data in reel_lookup.items():
        if rid and rid in text:
            return data
    rid = _extract_reel_id(text)
    return reel_lookup.get(rid) if rid else None

def backfill_missing_media_data(result: dict, metrics_df, top_viral_df, viral_stats=None) -> dict:
    """
    Чинит разрывы цепочки «паттерн → ролик → сценарий», если ИИ не заполнил структурированные
    поля, хотя упомянул ролик текстом:
      1) для patterns без source_video_url — ищет ID ролика в pattern/evidence и подставляет
         реальные url/views/ER из ретроспективы блогера;
      2) для scenarios без anchor_url — сначала ищет ID ролика в based_on_video/based_on_pattern/
         hook/script, затем пробует взять данные у паттерна с тем же названием (based_on_pattern),
         и только в крайнем случае берёт самый залётный ролик из топа как разумный дефолт;
      3) если после этого прогноз/вероятность/время публикации всё ещё пустые — считает
         консервативную оценку по anchor_views/anchor_er и средней «залётности» блогера,
         чтобы в интерфейсе никогда не оставалось голых прочерков там, где есть на основе чего посчитать.
    Ничего не переписывает поверх уже заполненных ИИ значений — только дозаполняет пустые.
    """
    if not isinstance(result, dict):
        return result

    reel_lookup = _build_reel_lookup(metrics_df)
    top_fallback = None
    if top_viral_df is not None and not top_viral_df.empty and "Просмотры" in top_viral_df.columns:
        top_row = top_viral_df.sort_values("Просмотры", ascending=False).iloc[0]
        top_fallback = {"url": top_row.get("Ссылка на ролик", ""), "views": top_row.get("Просмотры", 0), "er": top_row.get("ER_%", 0)}

    patterns = result.get("patterns") or []
    for patt in patterns:
        if not isinstance(patt, dict):
            continue
        if not str(patt.get("source_video_url", "") or "").strip():
            match = _find_reel_by_text(f"{patt.get('pattern', '')} {patt.get('evidence', '')}", reel_lookup) or top_fallback
            if match and match.get("url"):
                patt["source_video_url"] = match["url"]
                patt["source_video_views"] = match["views"]
                patt["source_video_er"] = match["er"]

    patterns_by_name = {(p.get("pattern") or "").strip().lower(): p for p in patterns if isinstance(p, dict)}

    scenarios = result.get("scenarios") or []
    for scn in scenarios:
        if not isinstance(scn, dict):
            continue
        if not str(scn.get("anchor_url", "") or "").strip():
            haystack = " ".join(str(scn.get(k, "")) for k in ("based_on_video", "based_on_pattern", "hook", "script"))
            match = _find_reel_by_text(haystack, reel_lookup)
            if not match:
                bp_key = (scn.get("based_on_pattern") or "").strip().lower()
                patt = patterns_by_name.get(bp_key)
                if patt and patt.get("source_video_url"):
                    match = {"url": patt["source_video_url"], "views": patt.get("source_video_views", 0), "er": patt.get("source_video_er", 0)}
            match = match or top_fallback
            if match and match.get("url"):
                scn["anchor_url"] = match["url"]
                scn["anchor_views"] = match["views"]
                scn["anchor_er"] = match["er"]

        anchor_views = scn.get("anchor_views") or 0
        anchor_er = scn.get("anchor_er")
        if not scn.get("forecast_views_low") and not scn.get("forecast_views_high") and anchor_views:
            try:
                av = float(anchor_views)
                scn["forecast_views_low"] = int(round(av * 0.35))
                scn["forecast_views_high"] = int(round(av * 0.75))
            except (TypeError, ValueError):
                pass
        if not scn.get("forecast_er") and anchor_er not in (None, ""):
            try:
                scn["forecast_er"] = round(float(anchor_er) * 0.85, 2)
            except (TypeError, ValueError):
                pass
        if scn.get("virality_probability") in (None, "", 0):
            base_pct = (viral_stats or {}).get("viral_pct", 20) or 20
            try:
                scn["virality_probability"] = max(10, min(60, int(round(float(base_pct)))))
            except (TypeError, ValueError):
                scn["virality_probability"] = 25
        if not str(scn.get("virality_reasoning", "") or "").strip():
            scn["virality_reasoning"] = "Оценка рассчитана автоматически по средним показателям блогера (ИИ не указал обоснование)."
        if not str(scn.get("best_posting_time_msk", "") or "").strip():
            scn["best_posting_time_msk"] = "недостаточно данных"

    return result


def _fmt_int(n):
    try:
        return f"{int(round(float(n))):,}".replace(",", " ")
    except Exception:
        return str(n) if n not in (None, "") else "—"

def _fmt_pct(n):
    try:
        return f"{float(n):g}%"
    except Exception:
        return str(n) if n not in (None, "") else "—"

def _virality_badge_class(prob):
    """Цвет бейджа вероятности залёта: ≥60% зелёный, 30-59% жёлтый, <30% красный."""
    try:
        p = float(prob)
    except (TypeError, ValueError):
        return "badge-low"
    if p >= 60:
        return "badge-high"
    if p >= 30:
        return "badge-medium"
    return "badge-low"


def render_full_result(metrics_df, top_viral_df, result, enable_scenario_regen=False, regen_key_prefix="scn"):
    """Рендерит метрики + разбор ИИ + сценарии. Общая для первого анализа и после «Обновить сценарии».
    Если enable_scenario_regen=True — у каждого сценария справа от заголовка появляется кнопка
    «🔄 Обновить сценарий»; функция возвращает индекс сценария, для которого нажали кнопку
    (или None, если не нажимали), чтобы вызывающий код мог запустить точечную перегенерацию."""
    st.markdown("<hr style='margin: 24px 0; border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
    st.markdown("### 1️⃣ Метрики роликов", unsafe_allow_html=True)
    st.dataframe(metrics_df[["Ссылка на ролик", "Просмотры", "ER_%", "Индекс_к_медиане", "Аномалия"]], use_container_width=True, hide_index=True)
    st.markdown(f"**Топ-{len(top_viral_df)} для глубокого разбора:**")
    st.dataframe(top_viral_df[["Ссылка на ролик", "Просмотры", "Индекс_к_медиане"]], use_container_width=True, hide_index=True)

    st.markdown("### 2️⃣ Разбор от ИИ и сценарии", unsafe_allow_html=True)
    st.markdown(f"""<div class="ai-report-glass fade-in-container"><b>Общая картина по аудитории:</b><br>{html.escape(result.get("audience_summary", ""))}</div>""", unsafe_allow_html=True)
    st.markdown("#### Найденные паттерны", unsafe_allow_html=True)
    patterns = result.get("patterns", [])
    patt_cols = st.columns(min(3, max(1, len(patterns))) or 1)
    for i, patt in enumerate(patterns):
        strength = patt.get("strength", "предварительная")
        badge_class = {"высокая": "badge-high", "средняя": "badge-medium"}.get(strength, "badge-low")
        src_url = patt.get("source_video_url", "") or ""
        src_link_html = (
            f'<a href="{html.escape(src_url)}" target="_blank" style="color:#38bdf8;">ролик</a>'
            if src_url else "—"
        )
        src_views = _fmt_int(patt.get("source_video_views"))
        src_er = _fmt_pct(patt.get("source_video_er"))
        with patt_cols[i % len(patt_cols)]:
            st.markdown(f"""
                <div class="glass-metric fade-in-container" style="margin-bottom: 14px;">
                    <div class="metric-title">Паттерн</div>
                    <div class="metric-value" style="font-size: 16px;">{html.escape(patt.get("pattern", ""))}</div>
                    <div class="metric-delta" style="color:#94a3b8;">{html.escape(patt.get("evidence", ""))}</div>
                    <span class="pattern-badge {badge_class}">{html.escape(strength)}</span>
                    <div style="margin-top:8px; font-size:12px; color:#94a3b8;">
                        🔗 Источник: {src_link_html} · охват {src_views} · ER {src_er}
                    </div>
                </div>
            """, unsafe_allow_html=True)

    st.markdown("#### Сценарии роликов под товар", unsafe_allow_html=True)
    clicked_regen_index = None
    for idx, scenario in enumerate(result.get("scenarios", [])):
        fit = scenario.get("fit_score", "средний")
        fit_class = {"высокий": "fit-high", "средний": "fit-medium"}.get(fit, "fit-low")

        anchor_url = scenario.get("anchor_url", "") or ""
        anchor_views = scenario.get("anchor_views")
        anchor_er = scenario.get("anchor_er")
        anchor_link_html = (
            f'<a href="{html.escape(anchor_url)}" target="_blank" style="color:#38bdf8;">{html.escape(anchor_url)}</a>'
            if anchor_url else "—"
        )

        forecast_low = scenario.get("forecast_views_low")
        forecast_high = scenario.get("forecast_views_high")
        forecast_er = scenario.get("forecast_er")
        forecast_range = (
            f"{_fmt_int(forecast_low)}–{_fmt_int(forecast_high)}"
            if forecast_low not in (None, "") or forecast_high not in (None, "") else "—"
        )

        prob = scenario.get("virality_probability")
        prob_class = _virality_badge_class(prob)
        prob_text = f"{int(round(float(prob)))}%" if prob not in (None, "") else "—"
        prob_reasoning = html.escape(scenario.get("virality_reasoning", "") or "")
        best_time = html.escape(scenario.get("best_posting_time_msk", "") or "—")

        title_col, regen_col = st.columns([6, 1.4])
        with title_col:
            st.markdown(
                f"""<h4 style="margin:0;">🎬 {html.escape(scenario.get("title", ""))} """
                f"""<span class="{fit_class}" style="float:right; font-size: 14px;">Fit: {html.escape(fit)}</span></h4>""",
                unsafe_allow_html=True,
            )
        with regen_col:
            if enable_scenario_regen:
                if st.button("🔄 Обновить сценарий", key=f"{regen_key_prefix}_regen_{idx}", use_container_width=True):
                    clicked_regen_index = idx

        qc_flag = scenario.get("_qc_flag")
        if qc_flag:
            st.markdown(
                f"""<div style="background:rgba(234,179,8,0.12); border:1px solid rgba(234,179,8,0.4);
                    border-radius:8px; padding:8px 12px; margin:4px 0 8px; font-size:13px; color:#eab308;">
                    ⚠️ Не прошёл автоматический контроль качества: {html.escape(str(qc_flag))}
                    </div>""",
                unsafe_allow_html=True,
            )

        st.markdown(f"""
            <div class="ai-report-glass fade-in-container" style="margin-top:-8px;">
                <p style="color:#94a3b8; font-size: 13px;">На основе паттерна: {html.escape(scenario.get("based_on_pattern", "—"))}</p>
                <hr style="border-color: rgba(255,255,255,0.1);">
                <p><b>Хук:</b> {html.escape(scenario.get("hook", ""))}</p>
                <p><b>Сценарий:</b><br>{str(html.escape(scenario.get("script", ""))).replace(chr(10), "<br>")}</p>
                <p><b>Подпись к посту:</b> {html.escape(scenario.get("caption", ""))}</p>
                <hr style="border-color: rgba(255,255,255,0.1);">
                <p style="font-size: 13px;">
                    <b>🔗 Ролик-донор:</b> {anchor_link_html}<br>
                    <span style="color:#94a3b8;">Его охват: {_fmt_int(anchor_views)} · его ER: {_fmt_pct(anchor_er)}</span>
                </p>
                <p style="font-size: 13px;">
                    <b>📈 Прогноз для этого сценария:</b> охват ~{forecast_range} · ER ~{_fmt_pct(forecast_er)}
                </p>
                <p style="font-size: 13px;">
                    <b>🕐 Лучшее время публикации (МСК):</b> {best_time}
                </p>
                <p style="font-size: 13px; margin-bottom:0;">
                    <b>🎯 Вероятность залёта:</b> <span class="pattern-badge {prob_class}">{prob_text}</span><br>
                    <span style="color:#94a3b8;">{prob_reasoning}</span>
                </p>
            </div>
        """, unsafe_allow_html=True)

    if result.get("verdict_note"):
        st.markdown(f"""<div class="custom-warning fade-in-container"><i class="fa-solid fa-circle-info" style="font-size: 18px;"></i> {html.escape(result.get("verdict_note"))}</div>""", unsafe_allow_html=True)

    return clicked_regen_index


# ============================================================================
# ЭКСПОРТ АНАЛИЗА В ФОРМАТ ДЛЯ ВСТАВКИ В GOOGLE ТАБЛИЦЫ
# ============================================================================
def compute_viral_summary_stats(metrics_df: pd.DataFrame, viral_threshold: float = None):
    """
    Считает: сколько всего роликов, сколько из них залётных, % залёта,
    средний охват НЕ залётных и средний охват залётных роликов.
    Если в metrics_df уже есть колонка 'Аномалия' (посчитанная при анализе) — используем её,
    чтобы для сохранённой истории цифры совпадали с тем, что реально анализировалось.
    """
    if metrics_df is None or metrics_df.empty:
        return {"total": 0, "viral_count": 0, "viral_pct": 0.0, "avg_non_viral_views": 0, "avg_viral_views": 0}

    total = len(metrics_df)

    if "Аномалия" in metrics_df.columns:
        is_viral = metrics_df["Аномалия"].astype(bool)
    elif "Индекс_к_медиане" in metrics_df.columns and viral_threshold:
        is_viral = metrics_df["Индекс_к_медиане"].apply(lambda x: bool(x and x >= viral_threshold))
    else:
        is_viral = pd.Series([False] * total, index=metrics_df.index)

    views_col = pd.to_numeric(metrics_df["Просмотры"], errors="coerce").fillna(0) if "Просмотры" in metrics_df.columns else pd.Series([0] * total)

    viral_views = views_col[is_viral]
    non_viral_views = views_col[~is_viral]

    viral_count = int(is_viral.sum())
    viral_pct = round(viral_count / total * 100, 1) if total else 0.0
    avg_viral = int(round(viral_views.mean())) if len(viral_views) else 0
    avg_non_viral = int(round(non_viral_views.mean())) if len(non_viral_views) else 0

    return {
        "total": total,
        "viral_count": viral_count,
        "viral_pct": viral_pct,
        "avg_non_viral_views": avg_non_viral,
        "avg_viral_views": avg_viral,
    }


def build_export_table(blogger_url, viral_stats, top_viral_df, result, all_reels_df=None):
    """
    Собирает таблицу выгрузки (как HTML-таблица + TSV-запасной вариант) в формате,
    близком к шаблону Google Таблицы: строка сводки по блогеру + строка деталей
    (залётные ролики, аудитория, сценарии, и — правее последнего сценария —
    полный список ВСЕХ выгруженных роликов, а не только залётных).
    Цена и Охват по вышедшим РК оставляем пустыми — заполняются вручную по факту.
    """
    def fmt_num(n):
        try:
            return f"{int(round(float(n))):,}".replace(",", " ")
        except Exception:
            return str(n)

    headers_main = [
        "блогер", "Цена", "% залёта", "Средний Охват без залётов",
        "Сред. Охват Залётных", "Охват по вышедшим РК",
        "Общий анализ роликов", "Обобщённый ответ по блогеру",
    ]
    pct = viral_stats.get("viral_pct", 0) or 0
    row_overview = [
        blogger_url or "",
        "",  # Цена — заполняется вручную
        f"{pct:g}%",
        fmt_num(viral_stats.get("avg_non_viral_views", 0)),
        fmt_num(viral_stats.get("avg_viral_views", 0)),
        "",  # Охват по вышедшим РК — заполняется вручную
        "",  # заголовок "Общий анализ роликов" — сами данные лежат в строке ниже, правее сценариев
        result.get("verdict_note", "") or "",
    ]

    scenarios = result.get("scenarios", []) or []
    sub_headers = (
        ["Залётные ролики ссылка/охват/ER", "Общая картина по аудитории"]
        + [f"Сценарий {i + 1}" for i in range(len(scenarios))]
        + ["Общий анализ роликов (все выгруженные ролики)"]
    )

    def reels_lines(df, mark_viral=False):
        lines = []
        if df is not None and not df.empty:
            sort_df = df.sort_values("Просмотры", ascending=False) if "Просмотры" in df.columns else df
            for _, r in sort_df.iterrows():
                link = r.get("Ссылка на ролик", "")
                views = r.get("Просмотры", 0)
                er = r.get("ER_%", "")
                prefix = "🔥 " if (mark_viral and bool(r.get("Аномалия", False))) else ""
                lines.append(f"{prefix}{link}  {fmt_num(views)}  ER {er}%")
        return lines

    viral_cell = "\n".join(reels_lines(top_viral_df))
    # Полный список ВСЕХ выгруженных сервисом роликов (не только топ залётных) —
    # идёт в отдельную колонку правее последнего сценария.
    all_reels_cell = "\n".join(reels_lines(all_reels_df, mark_viral=True))

    scenario_cells = []
    for s in scenarios:
        based_on = s.get("based_on_video") or s.get("based_on_pattern") or "—"
        anchor_url = s.get("anchor_url", "") or "—"
        anchor_views = s.get("anchor_views")
        anchor_er = s.get("anchor_er")
        forecast_low = s.get("forecast_views_low")
        forecast_high = s.get("forecast_views_high")
        forecast_er = s.get("forecast_er")
        prob = s.get("virality_probability")
        prob_text = f"{int(round(float(prob)))}%" if prob not in (None, "") else "—"
        block = (
            f"🎬 {s.get('title', '')}\n"
            f"На основе: {based_on}\n\n"
            f"Хук: {s.get('hook', '')}\n\n"
            f"Сценарий: {s.get('script', '')}\n\n"
            f"Подпись: {s.get('caption', '')}\n"
            f"{s.get('ad_marking_note', '')}\n"
            f"Fit: {s.get('fit_score', '')}\n\n"
            f"Ролик-донор: {anchor_url}\n"
            f"Охват донора: {fmt_num(anchor_views) if anchor_views not in (None, '') else '—'} · "
            f"ER донора: {anchor_er if anchor_er not in (None, '') else '—'}%\n\n"
            f"Прогноз охвата: {fmt_num(forecast_low) if forecast_low not in (None, '') else '—'}–"
            f"{fmt_num(forecast_high) if forecast_high not in (None, '') else '—'} · "
            f"Прогноз ER: {forecast_er if forecast_er not in (None, '') else '—'}%\n"
            f"Лучшее время публикации (МСК): {s.get('best_posting_time_msk', '') or '—'}\n"
            f"Вероятность залёта: {prob_text} — {s.get('virality_reasoning', '') or ''}"
        )
        scenario_cells.append(block)

    row_details = [viral_cell, result.get("audience_summary", "") or ""] + scenario_cells + [all_reels_cell]

    def esc(v):
        return html.escape(str(v)).replace("\n", "<br>")

    def html_row(cells, header=False):
        cell_style = (
            "background:#2e6f6b;color:#fff;font-weight:700;padding:8px 12px;"
            "border:1px solid #9ec5c2;text-align:left;"
            if header else
            "padding:8px 12px;border:1px solid #cfd8dc;vertical-align:top;"
            "white-space:pre-wrap;min-width:140px;max-width:320px;"
        )
        cells_html = "".join(f'<td style="{cell_style}">{esc(c)}</td>' for c in cells)
        return f"<tr>{cells_html}</tr>"

    table_html = (
        "<table style='border-collapse:collapse;font-family:Arial,sans-serif;font-size:13px;width:100%;'>"
        + html_row(headers_main, header=True)
        + html_row(row_overview)
        + html_row(sub_headers, header=True)
        + html_row(row_details)
        + "</table>"
    )

    def tsv_line(cells):
        return "\t".join(str(c).replace("\t", " ").replace("\r", " ").replace("\n", " ⏎ ") for c in cells)

    tsv_text = "\n".join([
        tsv_line(headers_main),
        tsv_line(row_overview),
        tsv_line(sub_headers),
        tsv_line(row_details),
    ])

    return table_html, tsv_text


def render_copy_button(table_html: str, tsv_text: str, key: str):
    """Кнопка «Копировать» — копирует таблицу в буфер обмена как HTML-таблицу
    (чтобы Google Таблицы разложили её по столбцам и строкам при вставке),
    с текстовым TSV-вариантом как запасным."""
    html_js = json.dumps(table_html)
    text_js = json.dumps(tsv_text)
    components.html(f"""
    <div style="display:flex; justify-content:flex-end; align-items:center; gap:10px; margin-bottom:10px; font-family:'Plus Jakarta Sans',sans-serif;">
      <span id="copy-status-{key}" style="font-size:12px; color:#10b981; font-weight:600;"></span>
      <button id="copy-btn-{key}" style="cursor:pointer; border:none; background:linear-gradient(135deg,#0a8ed9,#0670b0); color:#fff; padding:9px 16px; border-radius:10px; font-weight:700; font-size:13px; box-shadow:0 4px 12px rgba(10,142,217,0.3);">
        📋 Копировать таблицу
      </button>
    </div>
    <script>
      const btn = document.getElementById("copy-btn-{key}");
      const status = document.getElementById("copy-status-{key}");
      btn.addEventListener("click", async () => {{
        const htmlContent = {html_js};
        const textContent = {text_js};
        try {{
          if (window.ClipboardItem) {{
            const item = new ClipboardItem({{
              "text/html": new Blob([htmlContent], {{type: "text/html"}}),
              "text/plain": new Blob([textContent], {{type: "text/plain"}}),
            }});
            await navigator.clipboard.write([item]);
          }} else {{
            await navigator.clipboard.writeText(textContent);
          }}
          status.innerText = "✅ Скопировано — вставьте в Google Таблицы";
        }} catch (err) {{
          try {{
            await navigator.clipboard.writeText(textContent);
            status.innerText = "✅ Скопировано (текстом)";
          }} catch (err2) {{
            status.innerText = "⚠️ Не удалось скопировать: " + err2;
          }}
        }}
      }});
    </script>
    """, height=55)


@st.dialog("📤 Выгрузка анализа для Google Таблиц", width="large")
def open_export_dialog(table_html, tsv_text, meta):
    st.caption(f"@{meta.get('handle', '—')} · сформировано {meta.get('created', '')}")
    render_copy_button(table_html, tsv_text, key=meta.get("key", "export"))
    st.markdown(
        f"<div style='overflow-x:auto; border-radius:12px; border:1px solid rgba(0,0,0,0.08);'>{table_html}</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "1) Нажмите «📋 Копировать таблицу» → 2) откройте нужную ячейку в Google Таблице → "
        "3) вставьте (Ctrl+V / ⌘+V). Данные лягут по столбцам и строкам автоматически. "
        "Цена и Охват по вышедшим РК — впишите вручную по факту."
    )


PIN_LENGTH = 4

def render_pin_pad(form_key: str, title: str, subtitle: str):
    st.markdown(f"""
        <div class="pin-wrap fade-in-container">
            <div class="pin-title">{html.escape(title)}</div>
            <div class="pin-subtitle">{html.escape(subtitle)}</div>
        </div>
    """, unsafe_allow_html=True)
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        with st.form(form_key):
            st.markdown('<div class="pin-single">', unsafe_allow_html=True)
            pin_value = st.text_input("PIN", max_chars=PIN_LENGTH, type="password", key=f"{form_key}_pin", label_visibility="collapsed")
            st.markdown('</div>', unsafe_allow_html=True)
            submitted = st.form_submit_button("🔓 Войти", use_container_width=True, type="primary")
    return submitted, (pin_value or "").strip()

def play_success_animation(message="Доступ разрешён"):
    components.html(f"""
    <div id="anim-root" style="display:flex;align-items:center;justify-content:center;height:220px;font-family:'Plus Jakarta Sans',system-ui,sans-serif;">
      <div id="pac-stage" style="position:relative;width:280px;height:60px;display:flex;align-items:center;justify-content:center;">
        <div style="position:absolute;display:flex;gap:32px;">
          <div class="dot" style="animation-delay:0.35s"></div><div class="dot" style="animation-delay:0.75s"></div>
          <div class="dot" style="animation-delay:1.15s"></div><div class="dot" style="animation-delay:1.55s"></div>
        </div>
        <div id="pacman"><div class="pac-body"></div></div>
      </div>
      <div id="success-stage" style="display:none;flex-direction:column;align-items:center;text-align:center;">
        <div style="position:relative;margin-bottom:18px;">
          <div class="ring"></div>
          <div class="check-circle"><svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="#052e16" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg></div>
        </div>
        <div style="font-size:20px;font-weight:800;color:#0a3a5c;margin-bottom:4px;">{html.escape(message)}</div>
      </div>
    </div>
    <style>
      .dot {{ width:14px;height:14px;background:#0a8ed9;border-radius:50%; animation: dotEaten 0.12s linear forwards; }}
      @keyframes dotEaten {{ to {{ opacity:0; transform:scale(0.2); }} }}
      #pacman {{ position:absolute; animation: pacMove 2s linear forwards; }}
      @keyframes pacMove {{ from {{ transform: translateX(-135px); }} to {{ transform: translateX(135px); }} }}
      .pac-body {{ width:0;height:0;border-radius:50%; border:22px solid #facc15; border-right-color:transparent; animation: chomp 0.32s infinite; }}
      @keyframes chomp {{ 0%,100% {{ border-right-color: transparent; }} 50% {{ border-right-color: #facc15; }} }}
      .check-circle {{ width:76px;height:76px;background:#10b981;border-radius:50%; display:flex;align-items:center;justify-content:center;position:relative;z-index:2; animation: popIn 0.45s cubic-bezier(0.34,1.56,0.64,1) forwards; }}
      @keyframes popIn {{ from {{ transform:scale(0); }} 60% {{ transform:scale(1.15); }} to {{ transform:scale(1); }} }}
      .ring {{ position:absolute;inset:0;background:#10b981;border-radius:50%;z-index:1; animation: ringOut 0.85s ease-out forwards; }}
      @keyframes ringOut {{ from {{ transform:scale(0.6); opacity:0.85; }} to {{ transform:scale(2.2); opacity:0; }} }}
    </style>
    <script>
      setTimeout(function() {{ document.getElementById('pac-stage').style.display = 'none'; document.getElementById('success-stage').style.display = 'flex'; }}, 2000);
    </script>
    """, height=240)


def play_completion_sound():
    """Звуковой сигнал об окончании полного цикла (парсинг → анализ → сценарии) — синтезируется
    прямо в браузере через Web Audio API (без внешних аудио-файлов), в духе олдскульных ICQ-«О-Оуу»-
    уведомлений начала 2000-х: два игривых восходящих чирпа друг за другом."""
    components.html("""
    <script>
    (function() {
      try {
        var Ctx = window.AudioContext || window.webkitAudioContext;
        if (!Ctx) return;
        var ctx = new Ctx();
        function chirp(startTime, f1, f2, dur, gainPeak) {
          var osc = ctx.createOscillator();
          var gain = ctx.createGain();
          osc.type = "sine";
          osc.frequency.setValueAtTime(f1, startTime);
          osc.frequency.exponentialRampToValueAtTime(f2, startTime + dur);
          gain.gain.setValueAtTime(0.0001, startTime);
          gain.gain.exponentialRampToValueAtTime(gainPeak, startTime + dur * 0.25);
          gain.gain.exponentialRampToValueAtTime(0.0001, startTime + dur);
          osc.connect(gain);
          gain.connect(ctx.destination);
          osc.start(startTime);
          osc.stop(startTime + dur + 0.02);
        }
        var now = ctx.currentTime + 0.02;
        // "О" — короткий взлёт тона
        chirp(now, 520, 880, 0.14, 0.18);
        // "-Оуу" — второй, более протяжный взлёт следом (пауза между ними — как в олдскульной аське)
        chirp(now + 0.20, 660, 1180, 0.26, 0.20);
      } catch (e) { /* тихо игнорируем — звук необязателен для работы приложения */ }
    })();
    </script>
    """, height=0)


def save_analysis(manager, blogger_url, blogger_handle, data_source, model_used_analyst, model_used_scenarist,
                  reels_count, median_views, viral_count, product_brief,
                  metrics_df, top_viral_df, result):
    """model_used_analyst/model_used_scenarist — конкретные модели, которые реально ответили для каждой
    роли (могут отличаться от настроенных в auto-режиме, если сработало автопереключение). model_used
    хранится дополнительно как объединённая строка для обратной совместимости со старыми записями."""
    model_used_combined = f"{model_used_analyst or '—'} / {model_used_scenarist or '—'}"
    try:
        with db_connect() as conn:
            cur = conn.execute("""
                INSERT INTO analyses (manager, blogger_url, blogger_handle, created_at, data_source,
                                      model_used, model_used_analyst, model_used_scenarist,
                                      reels_count, median_views, viral_count, product_brief,
                                      metrics_json, top_viral_json, result_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                manager, blogger_url, blogger_handle, datetime.now().isoformat(timespec="seconds"),
                data_source, model_used_combined, model_used_analyst, model_used_scenarist,
                int(reels_count), int(median_views), int(viral_count),
                product_brief,
                metrics_df.to_json(orient="records", force_ascii=False) if metrics_df is not None else "[]",
                top_viral_df.to_json(orient="records", force_ascii=False) if top_viral_df is not None else "[]",
                json.dumps(result, ensure_ascii=False),
            ))
            return cur.lastrowid
    except Exception:
        return None

def get_analyses(manager=None, limit=500):
    try:
        with db_connect() as conn:
            if manager:
                rows = conn.execute("SELECT * FROM analyses WHERE manager = ? ORDER BY created_at DESC LIMIT ?", (manager, limit)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM analyses ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []

def update_analysis_result(analysis_id, result, viral_count=None, model_used_analyst=None, model_used_scenarist=None):
    """Обновляет result_json (и при необходимости viral_count/модели, которые реально ответили) у уже
    сохранённой записи — используется кнопками «🔄 Обновить сценарии» / «🔄 Обновить сценарий», чтобы не
    плодить дубликаты в истории. model_used_analyst/model_used_scenarist передаются только когда
    соответствующая роль реально перевызывалась (обновление сценариев не трогает модель аналитика)."""
    if not analysis_id:
        return False
    try:
        with db_connect() as conn:
            fields = ["result_json = ?"]
            params = [json.dumps(result, ensure_ascii=False)]
            if viral_count is not None:
                fields.append("viral_count = ?"); params.append(int(viral_count))
            if model_used_analyst is not None:
                fields.append("model_used_analyst = ?"); params.append(model_used_analyst)
            if model_used_scenarist is not None:
                fields.append("model_used_scenarist = ?"); params.append(model_used_scenarist)
            params.append(analysis_id)
            conn.execute(f"UPDATE analyses SET {', '.join(fields)} WHERE id = ?", params)
        return True
    except Exception:
        return False

def get_latest_analysis_for_blogger(blogger_handle):
    """
    Возвращает самую свежую сохранённую запись анализа для этого блогера — по ВСЕМ менеджерам
    (транскрипция не зависит от того, кто именно запускал анализ, поэтому кэш общий на команду).
    Используется, чтобы не гонять Apify-транскрибацию заново, если недавно уже транскрибировали
    этого блогера.
    """
    if not blogger_handle:
        return None
    try:
        with db_connect() as conn:
            row = conn.execute(
                "SELECT * FROM analyses WHERE blogger_handle = ? ORDER BY created_at DESC LIMIT 1",
                (blogger_handle,),
            ).fetchone()
            return dict(row) if row else None
    except Exception:
        return None

def is_within_freshness_days(created_at_str, freshness_days) -> bool:
    """True, если created_at_str (ISO-строка) не старше freshness_days дней от текущего момента."""
    if not created_at_str:
        return False
    try:
        created_dt = datetime.fromisoformat(created_at_str)
        age_days = (datetime.now() - created_dt).total_seconds() / 86400
        return age_days <= float(freshness_days)
    except Exception:
        return False

def build_transcript_cache_from_record(record):
    """{Ссылка на ролик: транскрипция} из top_viral_json сохранённой записи — только непустые
    значения, чтобы не подставлять пустые строки поверх реальных данных."""
    cache = {}
    if not record:
        return cache
    try:
        items = json.loads(record.get("top_viral_json") or "[]")
    except Exception:
        items = []
    for it in items:
        url = it.get("Ссылка на ролик", "")
        transcript = it.get("Транскрипция (если есть)", "")
        if url and transcript:
            cache[url] = transcript
    return cache

def get_manager_stats():
    try:
        with db_connect() as conn:
            rows = conn.execute("""
                SELECT manager, COUNT(*) AS total_analyses, COUNT(DISTINCT blogger_handle) AS unique_bloggers, MAX(created_at) AS last_activity
                FROM analyses GROUP BY manager ORDER BY total_analyses DESC
            """).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []

def delete_analysis(analysis_id):
    try:
        with db_connect() as conn:
            conn.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))
        return True
    except Exception:
        return False


# ============================================================================
# ШАПКА И АВТОРИЗАЦИЯ
# ============================================================================
top_col1, top_col2 = st.columns([3, 1.2])
with top_col1:
    accent = '#38bdf8' if theme_class == 'theme-night' else '#0284c7'
    st.markdown(f"### <i class='fa-solid fa-clapperboard' style='color: {accent};'></i> Анализ роликов блогера", unsafe_allow_html=True)
with top_col2:
    db_managers = get_managers(active_only=True)
    managers_list = ["Выберите пользователя...", "👑 Администратор"] + [m["name"] for m in db_managers]
    selected_manager = st.selectbox("Пользователь", managers_list, label_visibility="collapsed")


if selected_manager == "👑 Администратор" and not st.session_state.admin_logged_in:
    submitted, entered_pin = render_pin_pad("admin_pin_form", "Вход администратора", f"Введите {PIN_LENGTH}-значный PIN.")
    if submitted:
        if len(entered_pin) < PIN_LENGTH: st.warning(f"Введите все {PIN_LENGTH} цифры PIN-кода.")
        elif verify_admin_pin(entered_pin):
            play_success_animation("Доступ разрешён")
            time.sleep(2.9)
            st.session_state.admin_logged_in = True
            st.rerun()
        else: st.error("Неверный PIN! Попробуйте ещё раз.")

elif selected_manager == "Выберите пользователя...":
    st.session_state.admin_logged_in = False
    st.session_state.manager_logged_in = None
    st.markdown("""
        <div class="fade-in-container">
            <div class="custom-warning">
                <i class="fa-solid fa-triangle-exclamation" style="font-size: 18px;"></i> Пожалуйста, выберите ваше имя в верхнем меню, чтобы начать работу.
            </div>
        </div>
    """, unsafe_allow_html=True)

elif (selected_manager != "👑 Администратор"
      and (get_manager(selected_manager) or {}).get("password_hash")
      and st.session_state.get("manager_logged_in") != selected_manager):
    st.session_state.admin_logged_in = False
    submitted, entered_pin = render_pin_pad("manager_pin_form", f"Вход: {html.escape(selected_manager)}", f"Для этого пользователя администратор задал {PIN_LENGTH}-значный PIN.")
    if submitted:
        mrec = get_manager(selected_manager) or {}
        if len(entered_pin) < PIN_LENGTH: st.warning(f"Введите все {PIN_LENGTH} цифры PIN-кода.")
        elif verify_password(entered_pin, mrec.get("password_hash"), mrec.get("salt")):
            play_success_animation("Доступ разрешён")
            time.sleep(2.9)
            st.session_state.manager_logged_in = selected_manager
            st.rerun()
        else: st.error("Неверный PIN! Попробуйте ещё раз.")

else:
    if selected_manager != "👑 Администратор":
        st.session_state.admin_logged_in = False

    is_admin = (selected_manager == "👑 Администратор" and st.session_state.admin_logged_in)

    accent = '#38bdf8' if theme_class == 'theme-night' else '#0284c7'
    st.markdown(f"""
        <div class="fade-in-container">
            <p style='margin-top: -5px; margin-bottom: 20px; font-weight: 600;'>
                <i class='fa-solid fa-user-shield'></i> Вы зашли как: <b style='color: {accent};'>{html.escape(selected_manager)}</b> | Режим: <b>{st.session_state.theme_mode}</b>
            </p>
        </div>
    """, unsafe_allow_html=True)

    if is_admin and st.sidebar.button("🔒 Выйти из аккаунта", use_container_width=True):
        st.session_state.admin_logged_in = False
        st.rerun()

    # ============================================================================
    # БОКОВАЯ ПАНЕЛЬ С ГЛОБАЛЬНЫМ СОХРАНЕНИЕМ (ДЛЯ АДМИНА)
    # ============================================================================
    st.sidebar.markdown("### <i class='fa-solid fa-key'></i> Настройки ИИ-помощника", unsafe_allow_html=True)

    def render_manual_model_picker(label, provider_mode_input, current_value, widget_key):
        """Единый способ выбрать одну конкретную модель (для ручного режима любой из ролей).
        Использует уже загруженный каталог моделей (кнопка «🔄 Обновить список моделей» ниже) либо
        стартовый список-заготовку, плюс возможность ввести слаг вручную."""
        if provider_mode_input == "anthropic_direct":
            direct_model_options = ["claude-sonnet-5", "claude-opus-4-8", "claude-haiku-4-5-20251001", "claude-fable-5"]
            idx = direct_model_options.index(current_value) if current_value in direct_model_options else 0
            return st.sidebar.selectbox(label, direct_model_options, index=idx, key=widget_key)

        starter_catalog = STARTER_MODEL_CATALOG if provider_mode_input == "openrouter" else GEMINI_STARTER_CATALOG
        model_catalog = st.session_state.available_models or starter_catalog
        model_choices = [MANUAL_MODEL_OPTION] + model_catalog
        current_ids = [m["id"] for m in model_choices]
        default_index = current_ids.index(current_value) if current_value in current_ids else 0

        def _format_model_option(m):
            if m["id"] == "__manual__": return m["name"]
            free_icon = '🆓' if m['is_free'] is True else ('💰' if m['is_free'] is False else '•')
            return f"{free_icon} {m['id']}"

        selected_entry = st.sidebar.selectbox(label, model_choices, index=default_index, format_func=_format_model_option, key=widget_key)
        if selected_entry["id"] == "__manual__":
            return st.sidebar.text_input("Свой слаг модели", value=current_value, key=widget_key + "_manual_text")
        return selected_entry["id"]

    def render_role_model_settings(role_key, role_label, provider_mode_input, cfg_mode, cfg_manual_model, cfg_auto_models_text):
        """Рендерит выбор режима подбора модели (авто / ручной) для одной роли и возвращает
        (mode, manual_model, auto_models_text) — то, что дальше сохраняется в настройки."""
        st.sidebar.markdown(f"**{role_label}**")
        mode = st.sidebar.radio(
            f"Режим подбора модели — {role_label}",
            options=["auto", "manual"],
            index=0 if cfg_mode == "auto" else 1,
            format_func=lambda v: "🤖 Автоматически (переключается при лимитах)" if v == "auto" else "✍️ Ручной выбор",
            key=f"{role_key}_mode_radio",
            label_visibility="collapsed",
        )
        if mode == "manual":
            manual_model = render_manual_model_picker(f"Модель — {role_label}", provider_mode_input, cfg_manual_model, f"{role_key}_manual_model")
            auto_models_text = cfg_auto_models_text
        else:
            manual_model = cfg_manual_model
            auto_models_text = st.sidebar.text_area(
                f"Приоритетный список моделей — {role_label} (по одной на строку; пробуются сверху вниз, "
                f"при лимите/ошибке — следующая)",
                value=cfg_auto_models_text, height=110, key=f"{role_key}_auto_models_text",
            )
        return mode, manual_model, auto_models_text

    if is_admin:
        provider_mode_labels = {"openrouter": "OpenRouter (много моделей)", "gemini": "Google Gemini (AI Studio)", "anthropic_direct": "Anthropic напрямую"}
        provider_presets = {
            "openrouter": {"base_url": "https://openrouter.ai/api/v1", "key_label": "API-ключ (OpenRouter)", "key_help": "openrouter.ai/workspaces/default/keys"},
            "gemini": {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai/", "key_label": "API-ключ (Google AI Studio / Gemini)", "key_help": "aistudio.google.com/api-keys"},
        }
        provider_mode_input = st.sidebar.selectbox("Способ вызова ИИ", list(provider_mode_labels.keys()), index=list(provider_mode_labels.keys()).index(st.session_state.cfg_ai_provider_mode), format_func=lambda k: provider_mode_labels[k])

        if provider_mode_input == "anthropic_direct":
            ai_key_input = st.sidebar.text_input("API-ключ Anthropic", value=st.session_state.cfg_ai_key, type="password")
            ai_base_url_input = "https://api.anthropic.com"
        else:
            preset = provider_presets[provider_mode_input]
            default_base_url = st.session_state.cfg_ai_base_url if st.session_state.cfg_ai_provider_mode == provider_mode_input else preset["base_url"]
            ai_base_url_input = st.sidebar.text_input("Base URL API", value=default_base_url, help=f"По умолчанию: {preset['base_url']}")
            ai_key_input = st.sidebar.text_input(preset["key_label"], value=st.session_state.cfg_ai_key, type="password", help=preset["key_help"])

            if st.sidebar.button(f"🔄 Обновить список моделей ({provider_mode_labels[provider_mode_input]})", use_container_width=True):
                try:
                    fetched = fetch_openai_compatible_models(ai_base_url_input, ai_key_input)
                    if provider_mode_input == "gemini": fetched = apply_gemini_free_tier_guess(fetched)
                    st.session_state.available_models = fetched
                    st.sidebar.success(f"Загружено моделей: {len(st.session_state.available_models)}")
                except Exception as exc:
                    st.sidebar.error(f"Не удалось получить список: {exc}")

        max_tokens_input = st.sidebar.number_input("Лимит токенов ответа на каждый вызов (max_tokens)", min_value=500, max_value=8000, value=st.session_state.cfg_max_tokens, step=100, help="Применяется отдельно к вызову Аналитика и отдельно к вызову Сценариста.")
        st.sidebar.markdown("---")

        st.sidebar.markdown("### <i class='fa-solid fa-brain'></i> Роли ИИ: Аналитик и Сценарист", unsafe_allow_html=True)
        st.sidebar.caption(
            "Аналитик читает ролики блогера и находит рабочие паттерны. Сценарист получает готовые "
            "паттерны и пишет сценарии. У каждой роли — своя модель (или свой список моделей для "
            "автопереключения) и свой системный промпт."
        )

        analyst_mode_input, analyst_manual_model_input, analyst_auto_models_text_input = render_role_model_settings(
            "analyst", "🧠 Аналитик", provider_mode_input,
            st.session_state.cfg_analyst_mode, st.session_state.cfg_analyst_manual_model, st.session_state.cfg_analyst_auto_models_text,
        )
        analyst_system_prompt_input = st.sidebar.text_area(
            "Системный промпт — Аналитик", value=st.session_state.cfg_analyst_system_prompt, height=200, key="analyst_prompt_area",
        )
        st.sidebar.markdown("---")

        scriptwriter_mode_input, scriptwriter_manual_model_input, scriptwriter_auto_models_text_input = render_role_model_settings(
            "scriptwriter", "✍️ Сценарист", provider_mode_input,
            st.session_state.cfg_scriptwriter_mode, st.session_state.cfg_scriptwriter_manual_model, st.session_state.cfg_scriptwriter_auto_models_text,
        )
        scriptwriter_system_prompt_input = st.sidebar.text_area(
            "Системный промпт — Сценарист", value=st.session_state.cfg_scriptwriter_system_prompt, height=200, key="scriptwriter_prompt_area",
        )
        st.sidebar.caption("Бесплатные модели на OpenRouter регулярно меняются — сверяйтесь со списком на openrouter.ai/models?q=free и обновляйте списки выше по необходимости.")
        st.sidebar.markdown("---")

        st.sidebar.markdown("### <i class='fa-solid fa-magnifying-glass-chart'></i> Роль «Редактор» (контроль качества)", unsafe_allow_html=True)
        st.sidebar.caption(
            "Редактор проверяет каждый готовый сценарий: fit_score должен быть «высокий» (иначе — правки), "
            "плюс уникальность и живой текст. Если сценарий не проходит — Сценарист переписывает его "
            "с учётом замечаний, в пределах лимита попыток ниже."
        )
        qc_enabled_input = st.sidebar.checkbox(
            "Включить проверку качества сценариев (гейт «Fit: высокий»)", value=st.session_state.cfg_qc_enabled,
        )
        qc_max_revisions_input = st.sidebar.number_input(
            "Макс. переписываний одного сценария при отказе редактора", min_value=0, max_value=4,
            value=st.session_state.cfg_qc_max_revisions, step=1,
            help="0 — редактор только помечает слабые сценарии, но не запускает переписывание.",
        )
        editor_mode_input, editor_manual_model_input, editor_auto_models_text_input = render_role_model_settings(
            "editor", "🕵️ Редактор", provider_mode_input,
            st.session_state.cfg_editor_mode, st.session_state.cfg_editor_manual_model, st.session_state.cfg_editor_auto_models_text,
        )
        editor_system_prompt_input = st.sidebar.text_area(
            "Системный промпт — Редактор", value=st.session_state.cfg_editor_system_prompt, height=200, key="editor_prompt_area",
        )
        st.sidebar.markdown("---")

        sound_enabled_input = st.sidebar.checkbox(
            "🔔 Звук по завершении полного цикла (парсинг → анализ → сценарии)", value=st.session_state.cfg_sound_enabled,
        )
        st.sidebar.markdown("---")

        st.sidebar.markdown("### <i class='fa-solid fa-video'></i> Сбор роликов", unsafe_allow_html=True)
        data_source_labels = {"apify": "🤖 Автоматически через Apify", "manual": "✍️ Вручную (таблица)"}
        data_source_input = st.sidebar.selectbox("Источник данных", list(data_source_labels.keys()), index=list(data_source_labels.keys()).index(st.session_state.cfg_data_source_mode), format_func=lambda k: data_source_labels[k])

        if data_source_input == "apify":
            _apify_keys_preview = get_apify_keys()
            _green_n = sum(1 for k in _apify_keys_preview if k.get("status") == "green")
            _red_n = sum(1 for k in _apify_keys_preview if k.get("status") == "red")
            _unknown_n = sum(1 for k in _apify_keys_preview if k.get("status") not in ("green", "red"))
            st.sidebar.caption(
                f"🔑 Ключей в пуле: {len(_apify_keys_preview)} · 🟢 {_green_n} · 🔴 {_red_n} · ⚪ {_unknown_n} — "
                f"добавление, проверка и удаление ключей — на вкладке «👥 Редактор менеджеров → 🔑 Ключи Apify»."
            )
            apify_actor_input = st.sidebar.text_input("Актор Apify", value=st.session_state.cfg_apify_actor)
            results_limit_input = st.sidebar.number_input("Роликов с профиля за раз", min_value=5, max_value=100, value=st.session_state.cfg_results_limit, step=5)
            lookback_days_input = st.sidebar.number_input("Глубина в днях", min_value=7, max_value=90, value=st.session_state.cfg_lookback_days, step=1)
            include_transcript_input = st.sidebar.checkbox("Включить реальную транскрипцию", value=st.session_state.cfg_include_transcript)
            transcript_freshness_days_input = st.sidebar.slider(
                "Транскрипция актуальна, если моложе (дней)", 1, 30, st.session_state.cfg_transcript_freshness_days,
                help="Если для этого блогера уже есть сохранённый анализ с транскрипцией не старше указанного "
                     "числа дней — новая транскрибация через Apify не запускается, данные берутся из истории "
                     "(экономит лимиты Apify). Если старше — транскрипция обновляется полностью.",
            )
        else:
            apify_actor_input = st.session_state.cfg_apify_actor
            results_limit_input = st.session_state.cfg_results_limit
            lookback_days_input = st.session_state.cfg_lookback_days
            include_transcript_input = st.session_state.cfg_include_transcript
            transcript_freshness_days_input = st.session_state.cfg_transcript_freshness_days

        viral_threshold_input = st.sidebar.slider("Порог «залётности» (× медианы)", 1.5, 5.0, float(st.session_state.cfg_viral_threshold), 0.1)
        top_n_viral_input = st.sidebar.slider("Топ-N залётных роликов", 1, 6, st.session_state.cfg_top_n_viral)
        st.sidebar.markdown("---")
        min_reels_input = st.sidebar.number_input("Мин. роликов для надёжного анализа", min_value=3, max_value=30, value=st.session_state.min_reels_required, step=1)
        scenarios_count_input = st.sidebar.slider("Сколько сценариев генерировать", 2, 6, st.session_state.scenarios_count)
        st.sidebar.markdown("---")
        product_brief_input = st.sidebar.text_area("Бриф о товаре по умолчанию", value=st.session_state.product_brief_default, height=160)

        # СОХРАНЕНИЕ В БАЗУ ДАННЫХ ДЛЯ ВСЕХ МЕНЕДЖЕРОВ
        if st.sidebar.button("💾 Сохранить глобально", use_container_width=True, type="primary"):
            st.session_state.cfg_ai_provider_mode = provider_mode_input
            st.session_state.cfg_ai_base_url = ai_base_url_input
            st.session_state.cfg_ai_key = ai_key_input
            st.session_state.cfg_max_tokens = max_tokens_input

            st.session_state.cfg_analyst_mode = analyst_mode_input
            st.session_state.cfg_analyst_manual_model = analyst_manual_model_input
            st.session_state.cfg_analyst_auto_models_text = analyst_auto_models_text_input
            st.session_state.cfg_analyst_system_prompt = analyst_system_prompt_input

            st.session_state.cfg_scriptwriter_mode = scriptwriter_mode_input
            st.session_state.cfg_scriptwriter_manual_model = scriptwriter_manual_model_input
            st.session_state.cfg_scriptwriter_auto_models_text = scriptwriter_auto_models_text_input
            st.session_state.cfg_scriptwriter_system_prompt = scriptwriter_system_prompt_input

            st.session_state.cfg_editor_mode = editor_mode_input
            st.session_state.cfg_editor_manual_model = editor_manual_model_input
            st.session_state.cfg_editor_auto_models_text = editor_auto_models_text_input
            st.session_state.cfg_editor_system_prompt = editor_system_prompt_input
            st.session_state.cfg_qc_enabled = qc_enabled_input
            st.session_state.cfg_qc_max_revisions = qc_max_revisions_input
            st.session_state.cfg_sound_enabled = sound_enabled_input

            st.session_state.cfg_data_source_mode = data_source_input
            st.session_state.cfg_apify_actor = apify_actor_input
            st.session_state.cfg_results_limit = results_limit_input
            st.session_state.cfg_lookback_days = lookback_days_input
            st.session_state.cfg_include_transcript = include_transcript_input
            st.session_state.cfg_transcript_freshness_days = transcript_freshness_days_input
            st.session_state.cfg_viral_threshold = viral_threshold_input
            st.session_state.cfg_top_n_viral = top_n_viral_input
            st.session_state.min_reels_required = min_reels_input
            st.session_state.scenarios_count = scenarios_count_input
            st.session_state.product_brief_default = product_brief_input

            set_setting("cfg_ai_provider_mode", provider_mode_input)
            set_setting("cfg_ai_base_url", ai_base_url_input)
            set_setting("cfg_ai_key", ai_key_input)
            set_setting("cfg_max_tokens", str(max_tokens_input))

            set_setting("cfg_analyst_mode", analyst_mode_input)
            set_setting("cfg_analyst_manual_model", analyst_manual_model_input)
            set_setting("cfg_analyst_auto_models_text", analyst_auto_models_text_input)
            set_setting("cfg_analyst_system_prompt", analyst_system_prompt_input)

            set_setting("cfg_scriptwriter_mode", scriptwriter_mode_input)
            set_setting("cfg_scriptwriter_manual_model", scriptwriter_manual_model_input)
            set_setting("cfg_scriptwriter_auto_models_text", scriptwriter_auto_models_text_input)
            set_setting("cfg_scriptwriter_system_prompt", scriptwriter_system_prompt_input)

            set_setting("cfg_editor_mode", editor_mode_input)
            set_setting("cfg_editor_manual_model", editor_manual_model_input)
            set_setting("cfg_editor_auto_models_text", editor_auto_models_text_input)
            set_setting("cfg_editor_system_prompt", editor_system_prompt_input)
            set_setting("cfg_qc_enabled", str(qc_enabled_input))
            set_setting("cfg_qc_max_revisions", str(qc_max_revisions_input))
            set_setting("cfg_sound_enabled", str(sound_enabled_input))

            set_setting("cfg_data_source_mode", data_source_input)
            set_setting("cfg_apify_actor", apify_actor_input)
            set_setting("cfg_results_limit", str(results_limit_input))
            set_setting("cfg_lookback_days", str(lookback_days_input))
            set_setting("cfg_include_transcript", str(include_transcript_input))
            set_setting("cfg_transcript_freshness_days", str(transcript_freshness_days_input))
            set_setting("cfg_viral_threshold", str(viral_threshold_input))
            set_setting("cfg_top_n_viral", str(top_n_viral_input))
            set_setting("min_reels_required", str(min_reels_input))
            set_setting("scenarios_count", str(scenarios_count_input))
            set_setting("product_brief_default", product_brief_input)

            st.sidebar.success("✅ Сохранено глобально! Доступно всем менеджерам.")
    else:
        st.sidebar.info("🔒 Настройки может менять только Администратор.")
        analyst_mode_disp = "авто-подбор" if st.session_state.cfg_analyst_mode == "auto" else f"`{st.session_state.cfg_analyst_manual_model}`"
        scriptwriter_mode_disp = "авто-подбор" if st.session_state.cfg_scriptwriter_mode == "auto" else f"`{st.session_state.cfg_scriptwriter_manual_model}`"
        editor_mode_disp = "авто-подбор" if st.session_state.cfg_editor_mode == "auto" else f"`{st.session_state.cfg_editor_manual_model}`"
        st.sidebar.markdown(f"🧠 **Аналитик:** {analyst_mode_disp}")
        st.sidebar.markdown(f"✍️ **Сценарист:** {scriptwriter_mode_disp}")
        st.sidebar.markdown(f"🕵️ **Редактор:** {editor_mode_disp} · QC {'включён' if st.session_state.cfg_qc_enabled else 'выключен'}")
        st.sidebar.markdown(f"📥 **Источник данных:** {'Apify (авто)' if st.session_state.cfg_data_source_mode == 'apify' else 'Вручную'}")
        st.sidebar.markdown(f"📏 **Мин. роликов:** {st.session_state.min_reels_required}")
        st.sidebar.markdown(f"🧩 **Сценариев за раз:** {st.session_state.scenarios_count}")
        if st.session_state.cfg_data_source_mode == "apify" and st.session_state.cfg_include_transcript:
            st.sidebar.markdown(f"♻️ **Транскрипция актуальна:** {st.session_state.cfg_transcript_freshness_days} дн.")

    active_provider_mode = st.session_state.cfg_ai_provider_mode
    active_base_url = st.session_state.cfg_ai_base_url
    active_max_tokens = st.session_state.cfg_max_tokens

    active_analyst_mode = st.session_state.cfg_analyst_mode
    active_analyst_manual_model = st.session_state.cfg_analyst_manual_model
    active_analyst_auto_models = parse_model_list(st.session_state.cfg_analyst_auto_models_text)
    active_analyst_system_prompt = st.session_state.cfg_analyst_system_prompt

    active_scriptwriter_mode = st.session_state.cfg_scriptwriter_mode
    active_scriptwriter_manual_model = st.session_state.cfg_scriptwriter_manual_model
    active_scriptwriter_auto_models = parse_model_list(st.session_state.cfg_scriptwriter_auto_models_text)
    active_scriptwriter_system_prompt = st.session_state.cfg_scriptwriter_system_prompt

    active_editor_mode = st.session_state.cfg_editor_mode
    active_editor_manual_model = st.session_state.cfg_editor_manual_model
    active_editor_auto_models = parse_model_list(st.session_state.cfg_editor_auto_models_text)
    active_editor_system_prompt = st.session_state.cfg_editor_system_prompt
    active_qc_enabled = st.session_state.cfg_qc_enabled
    active_qc_max_revisions = st.session_state.cfg_qc_max_revisions
    active_sound_enabled = st.session_state.cfg_sound_enabled

    active_min_reels = st.session_state.min_reels_required
    active_scenarios_count = st.session_state.scenarios_count
    active_data_source_mode = st.session_state.cfg_data_source_mode
    active_viral_threshold = st.session_state.cfg_viral_threshold
    active_top_n_viral = st.session_state.cfg_top_n_viral
    active_transcript_freshness_days = st.session_state.cfg_transcript_freshness_days

    def extract_instagram_username(url_or_username: str) -> str:
        text = (url_or_username or "").strip()
        if not text: return text
        if "instagram.com" not in text: return text.lstrip("@")
        tail = text.split("instagram.com/")[-1].split("?")[0]
        return tail.strip("/").split("/")[0]

    def render_saved_analysis(record, show_manager=False, allow_delete=False):
        try:
            result = json.loads(record.get("result_json") or "{}")
        except json.JSONDecodeError:
            result = {}
        created = (record.get("created_at") or "").replace("T", " ")
        handle = html.escape(record.get("blogger_handle") or record.get("blogger_url", ""))
        scenarios = result.get("scenarios", [])
        patterns = result.get("patterns", [])

        manager_chip = f'<span class="history-chip">👤 {html.escape(record.get("manager", ""))}</span>' if show_manager else ""
        model_analyst_disp = html.escape(record.get("model_used_analyst") or "—")
        model_scenarist_disp = html.escape(record.get("model_used_scenarist") or record.get("model_used") or "—")
        st.markdown(f"""
            <div class="history-card fade-in-container">
                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                    <div class="history-handle">@{handle}</div>
                    <div class="history-date">{created}</div>
                </div>
                <div>
                    {manager_chip}
                    <span class="history-chip">🎬 роликов: {record.get("reels_count", 0)}</span>
                    <span class="history-chip">🔥 залётных: {record.get("viral_count", 0)}</span>
                    <span class="history-chip">📊 медиана: {int(record.get("median_views") or 0):,}</span>
                    <span class="history-chip">✍️ сценариев: {len(scenarios)}</span>
                    <span class="history-chip">🧠 аналитик: {model_analyst_disp}</span>
                    <span class="history-chip">✍️ сценарист: {model_scenarist_disp}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        with st.expander(f"Открыть разбор и сценарии — @{handle} от {created}"):
            if result.get("audience_summary"):
                st.markdown(f"**Аудитория:** {result['audience_summary']}")
            if patterns:
                st.markdown("**Найденные паттерны:**")
                for p in patterns:
                    src = p.get("source_video_url", "") or "—"
                    st.markdown(
                        f"- **{p.get('pattern','')}** — {p.get('evidence','')} _({p.get('strength','')})_ · "
                        f"источник: {src} (охват {_fmt_int(p.get('source_video_views'))}, ER {_fmt_pct(p.get('source_video_er'))})"
                    )
            if scenarios:
                st.markdown("**Сценарии:**")
                for s in scenarios:
                    prob = s.get("virality_probability")
                    prob_text = f"{int(round(float(prob)))}%" if prob not in (None, "") else "—"
                    forecast_low, forecast_high = s.get("forecast_views_low"), s.get("forecast_views_high")
                    forecast_range = (
                        f"{_fmt_int(forecast_low)}–{_fmt_int(forecast_high)}"
                        if forecast_low not in (None, "") or forecast_high not in (None, "") else "—"
                    )
                    st.markdown(
                        f"**🎬 {s.get('title','')}** _(fit: {s.get('fit_score','—')})_\n\n"
                        f"*На основе:* {s.get('based_on_pattern','—')}\n\n"
                        f"**Хук:** {s.get('hook','')}\n\n"
                        f"**Сценарий:** {s.get('script','')}\n\n"
                        f"**Подпись:** {s.get('caption','')}\n\n"
                        f"**🔗 Ролик-донор:** {s.get('anchor_url','—')} "
                        f"(охват {_fmt_int(s.get('anchor_views'))}, ER {_fmt_pct(s.get('anchor_er'))})\n\n"
                        f"**📈 Прогноз:** охват ~{forecast_range} · ER ~{_fmt_pct(s.get('forecast_er'))}\n\n"
                        f"**🕐 Лучшее время публикации (МСК):** {s.get('best_posting_time_msk','—')}\n\n"
                        f"**🎯 Вероятность залёта:** {prob_text} — {s.get('virality_reasoning','')}\n\n---"
                    )
            if result.get("verdict_note"):
                st.info(result["verdict_note"])
            if record.get("product_brief"):
                st.caption(f"Бриф товара на момент анализа: {record['product_brief'][:300]}")
            st.caption(f"Ссылка: {html.escape(record.get('blogger_url',''))}")

            # --- Выгрузка сохранённого анализа в формате для Google Таблиц ---
            try:
                hist_metrics_df = pd.DataFrame(json.loads(record.get("metrics_json") or "[]"))
            except Exception:
                hist_metrics_df = pd.DataFrame()
            try:
                hist_top_viral_df = pd.DataFrame(json.loads(record.get("top_viral_json") or "[]"))
            except Exception:
                hist_top_viral_df = pd.DataFrame()
            hist_viral_stats = compute_viral_summary_stats(hist_metrics_df)

            exp_col, del_col = st.columns([1, 1])
            with exp_col:
                if st.button("📤 Выгрузить в Google Таблицы", key=f"export_{record['id']}", use_container_width=True):
                    table_html, tsv_text = build_export_table(record.get("blogger_url", ""), hist_viral_stats, hist_top_viral_df, result, all_reels_df=hist_metrics_df)
                    open_export_dialog(table_html, tsv_text, {
                        "handle": handle, "created": created, "key": f"hist_{record['id']}",
                    })

            if allow_delete:
                with del_col:
                    if st.button("🗑 Удалить эту запись", key=f"del_{record['id']}", use_container_width=True):
                        if delete_analysis(record["id"]):
                            st.success("Запись удалена — обновите вкладку.")
                        else:
                            st.error("Не удалось удалить запись.")

    # --- ВКЛАДКИ ---
    if is_admin:
        tab_new, tab_history, tab_editor = st.tabs(["🚀 Новый анализ", "📚 История по менеджерам", "👥 Редактор менеджеров"])
    else:
        tab_new, tab_history = st.tabs(["🚀 Новый анализ", "📚 Мои блогеры"])
        tab_editor = None

    if tab_editor is not None:
        with tab_editor:
            st.markdown("#### 👑 PIN администратора")
            if admin_pin_is_default():
                st.warning("Сейчас действует начальный PIN из кода. Смените его — иначе доступ к настройкам и данным всех менеджеров открыт любому.")
            else:
                st.caption("PIN администратора задан и хранится в базе в виде хеша.")

            ac1, ac2, ac3 = st.columns([1, 2, 1])
            with ac2:
                with st.form("admin_pin_change_form"):
                    cur_pin = st.text_input("Текущий PIN", type="password", max_chars=PIN_LENGTH, placeholder="••••")
                    new_admin_pin = st.text_input("Новый PIN", type="password", max_chars=PIN_LENGTH, placeholder="••••")
                    new_admin_pin2 = st.text_input("Повторите новый PIN", type="password", max_chars=PIN_LENGTH, placeholder="••••")
                    if st.form_submit_button("💾 Сохранить новый PIN", use_container_width=True, type="primary"):
                        if not verify_admin_pin(cur_pin): st.error("Текущий PIN введён неверно.")
                        elif len(new_admin_pin) != PIN_LENGTH or not new_admin_pin.isdigit(): st.error(f"Новый PIN должен состоять ровно из {PIN_LENGTH} цифр.")
                        elif new_admin_pin != new_admin_pin2: st.error("Новый PIN и повтор не совпадают.")
                        else:
                            ok, msg = set_admin_pin(new_admin_pin)
                            if ok: st.success(msg + " При следующем входе используйте новый PIN.")
                            else: st.error(msg)

            st.markdown("---")
            st.markdown("#### Управление пользователями")
            st.caption("PIN необязателен: если он не задан, вход под этим именем свободный.")
            all_managers = get_managers(active_only=False)

            with st.expander("➕ Добавить нового менеджера", expanded=False):
                with st.form("add_manager_form"):
                    new_mgr_name = st.text_input("Имя менеджера", placeholder="Иван Иванов")
                    new_mgr_pw = st.text_input(f"PIN из {PIN_LENGTH} цифр (можно оставить пустым)", type="password", max_chars=PIN_LENGTH, placeholder="0000")
                    add_submit = st.form_submit_button("💾 Сохранить нового менеджера", use_container_width=True, type="primary")
                    if add_submit:
                        if new_mgr_pw and (len(new_mgr_pw) != PIN_LENGTH or not new_mgr_pw.isdigit()):
                            st.error(f"PIN должен состоять ровно из {PIN_LENGTH} цифр (или оставьте поле пустым).")
                        else:
                            ok, msg = add_manager(new_mgr_name, new_mgr_pw or None)
                            if ok:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)

            st.markdown("---")
            st.markdown(f"#### Текущие менеджеры ({len(all_managers)})")

            for mgr in all_managers:
                mgr_name = mgr["name"]
                has_pw = bool(mgr.get("password_hash"))
                analyses_cnt = count_manager_analyses(mgr_name)
                created = (mgr.get("created_at") or "").replace("T", " ")[:16]

                st.markdown(f"""
                    <div class="history-card fade-in-container">
                        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                            <div class="history-handle">{html.escape(mgr_name)}</div>
                            <div class="history-date">создан: {created}</div>
                        </div>
                        <div>
                            <span class="history-chip">{'🔒 PIN задан' if has_pw else '🔓 без PIN'}</span>
                            <span class="history-chip">📊 анализов: {analyses_cnt}</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                with st.expander(f"⚙️ Настроить — {mgr_name}"):
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        st.markdown("**PIN-код**")
                        with st.form(f"pw_form_{mgr['id']}"):
                            new_pw = st.text_input(f"Новый PIN ({PIN_LENGTH} цифры)", type="password", key=f"pw_{mgr['id']}", max_chars=PIN_LENGTH, placeholder="0000")
                            if st.form_submit_button("💾 Сохранить PIN", use_container_width=True):
                                if new_pw and (len(new_pw) != PIN_LENGTH or not new_pw.isdigit()):
                                    st.error(f"PIN должен состоять ровно из {PIN_LENGTH} цифр.")
                                else:
                                    ok, msg = set_manager_password(mgr_name, new_pw or None)
                                    if ok:
                                        if st.session_state.get("manager_logged_in") == mgr_name: st.session_state.manager_logged_in = None
                                        st.success(msg)
                                        st.rerun()
                                    else:
                                        st.error(msg)
                        st.markdown("**Переименовать**")
                        with st.form(f"rename_form_{mgr['id']}"):
                            new_name = st.text_input("Новое имя", value=mgr_name, key=f"rn_{mgr['id']}")
                            if st.form_submit_button("💾 Сохранить имя", use_container_width=True):
                                if new_name.strip() == mgr_name: st.info("Имя не изменилось.")
                                else:
                                    ok, msg = rename_manager(mgr_name, new_name)
                                    if ok:
                                        st.success(msg)
                                        st.rerun()
                                    else: st.error(msg)
                    with ec2:
                        st.markdown("**Удаление**")
                        st.caption(f"У этого менеджера {analyses_cnt} сохранённых анализов.")
                        also_delete_history = st.checkbox("Удалить вместе с историей анализов", key=f"delhist_{mgr['id']}")
                        confirm_delete = st.checkbox(f"Подтверждаю удаление «{mgr_name}»", key=f"confirm_{mgr['id']}")
                        if st.button("🗑 Удалить менеджера", key=f"delmgr_{mgr['id']}", use_container_width=True):
                            if not confirm_delete: st.warning("Отметьте галочку подтверждения — удаление необратимо.")
                            else:
                                ok, msg = delete_manager(mgr_name, delete_history=also_delete_history)
                                if ok:
                                    st.success(msg)
                                    st.rerun()
                                else: st.error(msg)

            st.markdown("---")
            st.markdown("#### <i class='fa-solid fa-key'></i> Ключи Apify", unsafe_allow_html=True)
            st.caption(
                "Лимиты Apify считаются на уровне аккаунта (не отдельного токена) и сбрасываются раз в месяц "
                "по собственному биллинг-циклу аккаунта — не по фиксированной календарной дате и не через "
                "N дней после исчерпания. Поэтому дата «сброс лимита» ниже — не наш расчёт, а то, что прямо "
                "отдаёт сам Apify при проверке ключа. Можно добавить сколько угодно ключей: если у активного "
                "запрос падает с ошибкой (лимиты, права токена, неоплаченная аренда актора) — система сама "
                "помечает его 🔴 и пробует следующий ключ с доступными лимитами (🟢), не теряя введённые данные."
            )
            st.caption(
                "⚠️ Важно: ключи из разных аккаунтов Apify реально независимы друг от друга. Несколько "
                "токенов ОДНОГО и того же аккаунта делят один общий лимит — переключение между ними от "
                "исчерпания не спасёт. Также 🔴 не всегда означает «кончились деньги»: та же пометка "
                "появляется, если у токена нет прав на запуск акторов, или актор ещё не подтверждён к оплате "
                "(Pay-Per-Result) в консоли Apify под этим аккаунтом — в чипе «📊 …» под ключом видна точная "
                "причина последнего сбоя."
            )

            with st.form("add_apify_key_form", clear_on_submit=True):
                akc1, akc2 = st.columns([4, 1])
                with akc1:
                    new_apify_key_value = st.text_input(
                        "Новый Apify API-токен", placeholder="apify_api_...", label_visibility="collapsed",
                    )
                with akc2:
                    add_key_submitted = st.form_submit_button("➕ Добавить", use_container_width=True, type="primary")
                if add_key_submitted:
                    token_to_add = (new_apify_key_value or "").strip()
                    ok, msg = add_apify_key(token_to_add)
                    if ok:
                        new_rec = next((k for k in get_apify_keys() if k["token"] == token_to_add), None)
                        if new_rec:
                            live = check_apify_key_live(token_to_add)
                            if live.get("token_used") and live["token_used"] != new_rec["token"]:
                                update_apify_key_token(new_rec["id"], live["token_used"])
                            update_apify_key_status(
                                new_rec["id"], live.get("status") if live.get("ok") else "unknown",
                                usage_pct=live.get("usage_pct"),
                                usage_detail=live.get("usage_detail") or live.get("error"),
                                cycle_reset_at=live.get("cycle_reset_at"),
                            )
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

            apify_keys_list = get_apify_keys()
            if not apify_keys_list:
                st.caption("Ключей ещё нет — добавьте хотя бы один выше, иначе автоматический сбор роликов через Apify работать не будет.")
            else:
                if st.button("🔄 Проверить все ключи", use_container_width=True, key="check_all_apify_keys"):
                    for _k in apify_keys_list:
                        _live = check_apify_key_live(_k["token"])
                        if _live.get("token_used") and _live["token_used"] != _k["token"]:
                            # В базе была ссылка вместо самого токена (частая ошибка при копировании
                            # из консоли Apify) — чиним на лету, чтобы автопереключение видело рабочий ключ.
                            update_apify_key_token(_k["id"], _live["token_used"])
                        update_apify_key_status(
                            _k["id"], _live.get("status") if _live.get("ok") else "unknown",
                            usage_pct=_live.get("usage_pct"),
                            usage_detail=_live.get("usage_detail") or _live.get("error"),
                            cycle_reset_at=_live.get("cycle_reset_at"),
                        )
                    st.rerun()

                for k in apify_keys_list:
                    marker = {"green": "🟢", "red": "🔴"}.get(k.get("status"), "⚪")
                    token = k["token"]
                    masked = f"{token[:6]}…{token[-4:]}" if len(token) > 12 else f"…{token[-4:]}"
                    added = (k.get("date_added") or "").replace("T", " ")[:16]
                    checked = (k.get("last_checked_at") or "").replace("T", " ")[:16] or "не проверялся"
                    reset_at = k.get("cycle_reset_at")
                    reset_str = reset_at[:10] if reset_at else "неизвестно — нажмите «Проверить»"
                    usage_detail = k.get("usage_detail") or "нет данных — нажмите «Проверить»"

                    st.markdown(f"""
                        <div class="history-card fade-in-container">
                            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                                <div class="history-handle">{marker} {html.escape(masked)}</div>
                                <div class="history-date">добавлен: {added}</div>
                            </div>
                            <div>
                                <span class="history-chip">📊 {html.escape(usage_detail)}</span>
                                <span class="history-chip">🔁 сброс лимита (по данным Apify): {html.escape(reset_str)}</span>
                                <span class="history-chip">🕓 проверен: {checked}</span>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                    kc1, kc2 = st.columns(2)
                    with kc1:
                        if st.button("🔄 Проверить", key=f"check_apify_{k['id']}", use_container_width=True):
                            live = check_apify_key_live(token)
                            healed = bool(live.get("token_used") and live["token_used"] != token)
                            if healed:
                                update_apify_key_token(k["id"], live["token_used"])
                            if live.get("ok"):
                                update_apify_key_status(
                                    k["id"], live["status"], usage_pct=live.get("usage_pct"),
                                    usage_detail=live.get("usage_detail"), cycle_reset_at=live.get("cycle_reset_at"),
                                )
                                heal_note = " (формат токена в базе исправлен — была вставлена ссылка вместо токена)" if healed else ""
                                st.success(("🟢 Лимиты есть." if live["status"] == "green" else "🔴 Лимит почти/полностью исчерпан.") + heal_note)
                            else:
                                update_apify_key_status(k["id"], "unknown", usage_detail=live.get("error"))
                                st.error(f"Не удалось проверить: {live.get('error')}")
                            st.rerun()
                    with kc2:
                        if st.button("🗑 Удалить", key=f"del_apify_{k['id']}", use_container_width=True):
                            ok, msg = delete_apify_key(k["id"])
                            if ok:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)

    with tab_history:
        if is_admin:
            stats = get_manager_stats()
            if not stats:
                st.markdown("""<div class="empty-state fade-in-container"><div style="font-size:40px; margin-bottom:12px;">📭</div><div style="font-size:15px; font-weight:600;">Пока никто не проводил анализов</div></div>""", unsafe_allow_html=True)
            else:
                st.markdown("#### Сводка по менеджерам")
                cols = st.columns(min(4, len(stats)))
                for i, s in enumerate(stats):
                    with cols[i % len(cols)]:
                        last = (s.get("last_activity") or "").replace("T", " ")[:16]
                        st.markdown(f"""
                            <div class="manager-stat-card fade-in-container" style="margin-bottom:10px;">
                                <div style="font-size:13px; font-weight:700; margin-bottom:8px;">{html.escape(s['manager'])}</div>
                                <div style="font-size:24px; font-weight:800;">{s['total_analyses']}</div>
                                <div style="font-size:11px; opacity:0.75;">анализов</div>
                                <div style="font-size:12px; margin-top:8px;">блогеров: <b>{s['unique_bloggers']}</b></div>
                                <div style="font-size:11px; opacity:0.7; margin-top:4px;">{last}</div>
                            </div>
                        """, unsafe_allow_html=True)

                st.markdown("---")
                st.markdown("#### Просмотр по конкретному менеджеру")
                counts_map = {s["manager"]: s["total_analyses"] for s in stats}
                all_mgr_names = [m["name"] for m in get_managers(active_only=False)]
                for s in stats:
                    if s["manager"] not in all_mgr_names: all_mgr_names.append(s["manager"])
                all_mgr_names.sort()

                filter_options = ["Все менеджеры"] + all_mgr_names
                chosen_manager = st.selectbox(
                    "Выберите менеджера", filter_options,
                    format_func=lambda n: f"Все менеджеры ({sum(counts_map.values())} анализов)" if n == "Все менеджеры" else f"{n} — {counts_map.get(n, 0)} анализов"
                )
                records = get_analyses(None if chosen_manager == "Все менеджеры" else chosen_manager)
                search_q = st.text_input("Поиск по блогеру", placeholder="например: manekenshicca")
                if search_q.strip():
                    q = search_q.strip().lower()
                    records = [r for r in records if q in (r.get("blogger_handle") or "").lower() or q in (r.get("blogger_url") or "").lower()]
                st.caption(f"Найдено записей: {len(records)}")
                for rec in records:
                    render_saved_analysis(rec, show_manager=True, allow_delete=True)
        else:
            records = get_analyses(selected_manager)
            if not records:
                st.markdown("""<div class="empty-state fade-in-container"><div style="font-size:40px; margin-bottom:12px;">📭</div><div style="font-size:15px; font-weight:600;">Вы пока не анализировали блогеров</div></div>""", unsafe_allow_html=True)
            else:
                total_scen = 0
                for r in records:
                    try: total_scen += len(json.loads(r.get("result_json") or "{}").get("scenarios", []))
                    except json.JSONDecodeError: pass
                unique_bloggers = len({r.get("blogger_handle") for r in records if r.get("blogger_handle")})
                m1, m2, m3 = st.columns(3)
                for col, val, label in ((m1, len(records), "анализов"), (m2, unique_bloggers, "блогеров"), (m3, total_scen, "сценариев")):
                    with col:
                        st.markdown(f"""
                            <div class="manager-stat-card fade-in-container" style="margin-bottom:14px;">
                                <div style="font-size:26px; font-weight:800;">{val}</div>
                                <div style="font-size:12px; opacity:0.75;">{label}</div>
                            </div>
                        """, unsafe_allow_html=True)

                search_q = st.text_input("Поиск по блогеру", placeholder="например: manekenshicca")
                if search_q.strip():
                    q = search_q.strip().lower()
                    records = [r for r in records if q in (r.get("blogger_handle") or "").lower() or q in (r.get("blogger_url") or "").lower()]
                st.caption(f"Показано записей: {len(records)}")
                for rec in records:
                    render_saved_analysis(rec, show_manager=False, allow_delete=False)

    with tab_new:
        st.markdown('<div class="fade-in-container">', unsafe_allow_html=True)

        locked = st.session_state.get("last_analysis") is not None
        session_nonce = st.session_state.get("session_nonce", 0)

        if locked:
            la_preview = st.session_state["last_analysis"]
            lock_col1, lock_col2 = st.columns([4, 1.4])
            with lock_col1:
                st.markdown(
                    f"""<div class="custom-warning fade-in-container"><i class="fa-solid fa-lock"></i> "
                    Сессия занята анализом блогера <b>@{html.escape(extract_instagram_username(la_preview.get('blogger_url', '')))}</b>. "
                    Чтобы проанализировать другого блогера с чистого листа, нажмите «Новая сессия» — все "
                    "данные текущего блогера будут сброшены.</div>""",
                    unsafe_allow_html=True,
                )
            with lock_col2:
                if st.button("🆕 Новая сессия", use_container_width=True, type="primary", key="new_session_btn"):
                    st.session_state.pop("last_analysis", None)
                    st.session_state.reels_data = pd.DataFrame(
                        [{"Ссылка на ролик": "", "Просмотры": 0, "Лайки": 0, "Комментарии": 0,
                          "Сохранения": 0, "Дата публикации": "", "Время публикации (МСК)": "",
                          "Что происходит в ролике (кратко)": "", "Транскрипция (если есть)": ""} for _ in range(6)]
                    )
                    st.session_state["session_nonce"] = session_nonce + 1
                    for stale_key in ("reels_editor_widget",):
                        if stale_key in st.session_state:
                            del st.session_state[stale_key]
                    st.rerun()

        blogger_url = st.text_input(
            "Ссылка на профиль блогера (Instagram)", placeholder="https://www.instagram.com/example_blogger/",
            disabled=locked, key=f"blogger_url_input_{session_nonce}",
        )
        product_brief = st.text_area(
            "Бриф о товаре для адаптации в сценарий", value=st.session_state.product_brief_default, height=120,
            disabled=locked, key=f"product_brief_input_{session_nonce}",
        )

        edited_df = None
        if active_data_source_mode == "manual":
            st.markdown("**Ролики блогера** — заполните вручную:")
            edited_df = st.data_editor(
                st.session_state.reels_data, num_rows="dynamic", use_container_width=True,
                key=f"reels_editor_widget_{session_nonce}", disabled=locked,
                column_config={
                    "Просмотры": st.column_config.NumberColumn(min_value=0, step=100),
                    "Лайки": st.column_config.NumberColumn(min_value=0, step=10),
                    "Комментарии": st.column_config.NumberColumn(min_value=0, step=1),
                    "Сохранения": st.column_config.NumberColumn(min_value=0, step=1),
                },
            )
        else:
            st.caption(
                f"🤖 Автоматический сбор через Apify ({st.session_state.cfg_apify_actor}). "
                f"До {st.session_state.cfg_results_limit} роликов за последние {st.session_state.cfg_lookback_days} дн. "
                + ("Транскрипция включена." if st.session_state.cfg_include_transcript else "Транскрипция выключена.")
            )

        btn_col1, btn_col2 = st.columns(2)
        with btn_col1: submit_btn = st.button("🚀 Проанализировать ролики", use_container_width=True, disabled=locked)
        with btn_col2: test_btn = (st.button("🧪 Заполнить тестовыми роликами", use_container_width=True, disabled=locked) if active_data_source_mode == "manual" else False)
        st.markdown('</div>', unsafe_allow_html=True)

        if test_btn:
            st.session_state.reels_data = build_test_dataframe()
            stale_key = f"reels_editor_widget_{session_nonce}"
            if stale_key in st.session_state: del st.session_state[stale_key]
            st.rerun()

        if submit_btn:
            if not blogger_url.strip():
                st.markdown("""<div class="custom-error fade-in-container"><i class="fa-solid fa-circle-exclamation" style="font-size: 20px;"></i> Укажите ссылку на блогера.</div>""", unsafe_allow_html=True)
            else:
                apify_debug_raw = None
                apify_debug_error = None
                apify_debug_attempts = None
                raw_df = None

                if active_data_source_mode == "manual":
                    st.session_state.reels_data = edited_df
                    raw_df = edited_df
                else:
                    if not get_apify_keys():
                        st.markdown("""<div class="custom-error fade-in-container"><i class="fa-solid fa-circle-exclamation"></i> Не добавлено ни одного Apify-ключа — добавьте его на вкладке «👥 Редактор менеджеров → 🔑 Ключи Apify».</div>""", unsafe_allow_html=True)
                    else:
                        username = extract_instagram_username(blogger_url)
                        with st.spinner(f"Собираю ролики @{username} через Apify..."):
                            try:
                                items, apify_token_used, apify_failover_log = fetch_reels_via_apify_with_failover(
                                    st.session_state.cfg_apify_actor,
                                    targets=[username], results_limit=st.session_state.cfg_results_limit,
                                    lookback_days=st.session_state.cfg_lookback_days, include_transcript=False,
                                )
                                apify_debug_raw = items[0] if items else "(пустой список)"
                                raw_df = apify_items_to_dataframe(items)
                                if len(apify_failover_log) > 1:
                                    st.caption(f"🔁 Переключился на другой Apify-ключ (…{apify_token_used[-4:]}) — предыдущий, похоже, исчерпал лимит.")
                            except ApifyAllKeysFailedError as exc:
                                apify_debug_error = str(exc)
                                apify_debug_attempts = exc.attempts_log
                            except Exception as exc:
                                apify_debug_error = f"{type(exc).__name__}: {exc}"

                if apify_debug_raw is not None or apify_debug_error is not None:
                    with st.expander("🔍 Сырой ответ Apify (для отладки)", expanded=bool(apify_debug_error)):
                        if apify_debug_error: st.code(apify_debug_error, language="text")
                        if apify_debug_attempts:
                            st.markdown("**Что произошло с каждым ключом из пула (по порядку):**")
                            st.code("\n".join(apify_debug_attempts), language="text")
                        if apify_debug_raw is not None: st.code(json.dumps(apify_debug_raw, ensure_ascii=False, indent=2) if not isinstance(apify_debug_raw, str) else apify_debug_raw, language="json")

                if raw_df is not None and not apify_debug_error:
                    metrics_df, median_views = compute_reels_metrics(raw_df, active_viral_threshold)
                    valid_count = len(metrics_df)

                    if valid_count == 0:
                        st.markdown("""<div class="custom-error fade-in-container"><i class="fa-solid fa-circle-exclamation"></i> Не найдено ни одного ролика.</div>""", unsafe_allow_html=True)
                    else:
                        if valid_count < active_min_reels:
                            st.markdown(f"""<div class="custom-warning fade-in-container"><i class="fa-solid fa-triangle-exclamation"></i> Роликов в выборке: {valid_count} (рекомендовано минимум {active_min_reels}).</div>""", unsafe_allow_html=True)

                        top_viral_df, threshold_met = select_top_viral(metrics_df, active_viral_threshold, active_top_n_viral)
                        if not threshold_met:
                            st.markdown(f"""<div class="custom-warning fade-in-container"><i class="fa-solid fa-triangle-exclamation"></i> Ни один ролик не превысил порог {active_viral_threshold}x медианы.</div>""", unsafe_allow_html=True)

                        if (active_data_source_mode == "apify" and st.session_state.cfg_include_transcript and get_apify_keys() and not top_viral_df.empty):
                            top_links = [l for l in top_viral_df["Ссылка на ролик"].tolist() if l]
                            if top_links:
                                # --- Сначала пробуем переиспользовать уже сохранённую транскрипцию этого
                                # блогера (по всей команде), чтобы не жечь лимиты Apify без необходимости. ---
                                blogger_handle_for_cache = extract_instagram_username(blogger_url)
                                cached_record = get_latest_analysis_for_blogger(blogger_handle_for_cache)
                                cache_is_fresh = bool(cached_record) and is_within_freshness_days(
                                    cached_record.get("created_at", ""), active_transcript_freshness_days
                                )
                                transcript_cache = build_transcript_cache_from_record(cached_record) if cache_is_fresh else {}

                                top_viral_df = top_viral_df.copy()
                                if transcript_cache:
                                    top_viral_df["Транскрипция (если есть)"] = top_viral_df["Ссылка на ролик"].map(
                                        lambda u: transcript_cache.get(u) or top_viral_df.loc[top_viral_df["Ссылка на ролик"] == u, "Транскрипция (если есть)"].values[0]
                                    )
                                    cached_created = (cached_record.get("created_at") or "").replace("T", " ")[:16]
                                    matched_count = sum(1 for l in top_links if l in transcript_cache)
                                    st.markdown(f"""<div class="custom-warning fade-in-container"><i class="fa-solid fa-database"></i> Переиспользую сохранённую транскрипцию этого блогера от {cached_created} (не старше {active_transcript_freshness_days} дн.) — совпало {matched_count}/{len(top_links)} роликов, повторный запрос в Apify по ним не отправляется.</div>""", unsafe_allow_html=True)

                                missing_links = [l for l in top_links if l not in transcript_cache]
                                if missing_links:
                                    spinner_text = (
                                        f"Транскрибирую {len(missing_links)} новых ролика(ов), которых нет в сохранённой транскрипции..."
                                        if transcript_cache else
                                        f"Транскрибирую топ-{len(missing_links)} залётных ролика..."
                                    )
                                    with st.spinner(spinner_text):
                                        try:
                                            transcript_items, _transcript_token_used, _transcript_failover_log = fetch_reels_via_apify_with_failover(
                                                st.session_state.cfg_apify_actor,
                                                targets=missing_links, results_limit=None, lookback_days=None,
                                                include_transcript=True, timeout=420,
                                            )
                                            transcript_df = apify_items_to_dataframe(transcript_items)
                                            transcript_map = dict(zip(transcript_df["Ссылка на ролик"], transcript_df["Транскрипция (если есть)"]))
                                            top_viral_df["Транскрипция (если есть)"] = top_viral_df["Ссылка на ролик"].map(
                                                lambda u: transcript_map.get(u) or top_viral_df.loc[top_viral_df["Ссылка на ролик"] == u, "Транскрипция (если есть)"].values[0]
                                            )
                                        except ApifyAllKeysFailedError as exc:
                                            st.markdown(f"""<div class="custom-warning fade-in-container"><i class="fa-solid fa-triangle-exclamation"></i> Не удалось получить транскрипцию для {len(missing_links)} ролика(ов): {exc}. Эти ролики пойдут без текста речи.</div>""", unsafe_allow_html=True)
                                            with st.expander("🔍 Что произошло с каждым Apify-ключом при попытке транскрипции"):
                                                st.code("\n".join(exc.attempts_log), language="text")
                                        except Exception as exc:
                                            st.markdown(f"""<div class="custom-warning fade-in-container"><i class="fa-solid fa-triangle-exclamation"></i> Не удалось получить транскрипцию для {len(missing_links)} ролика(ов) ({type(exc).__name__}: {exc}). Эти ролики пойдут без текста речи.</div>""", unsafe_allow_html=True)

                        # --- Черновое сохранение сырых данных Apify СРАЗУ после парсинга, ДО вызова ИИ. ---
                        # Так лимиты API-ключа Apify не тратятся впустую: даже если аналитик/сценарист
                        # полностью откажут (лимиты моделей, сеть и т.д.), собранные ролики и транскрипции
                        # уже в базе — при повторной попытке для этого блогера повторный парсинг не нужен.
                        # Ниже эта же запись дозаполняется результатом ИИ через update_analysis_result.
                        draft_saved_id = save_analysis(
                            manager=selected_manager, blogger_url=blogger_url,
                            blogger_handle=extract_instagram_username(blogger_url),
                            data_source=active_data_source_mode, model_used_analyst=None, model_used_scenarist=None,
                            reels_count=valid_count, median_views=median_views,
                            viral_count=len(top_viral_df) if threshold_met else 0,
                            product_brief=product_brief, metrics_df=metrics_df, top_viral_df=top_viral_df,
                            result={"audience_summary": "", "patterns": [], "scenarios": [], "verdict_note": ""},
                        )
                        if draft_saved_id:
                            st.caption(f"💾 Собранные данные ролика сохранены в базу (запись №{draft_saved_id}) — при сбое ИИ повторный парсинг через Apify не понадобится.")
                        else:
                            st.caption("⚠️ Не удалось сохранить сырые данные ролика в базу перед анализом ИИ.")

                        # Считаем сводную статистику по залётности заранее — она передаётся обеим ролям ИИ,
                        # без неё прогноз охвата/ER и вероятность залёта считались бы «в вакууме».
                        viral_stats = compute_viral_summary_stats(metrics_df, active_viral_threshold)

                        # --- Шаг 1: Аналитик ищет паттерны и разбирает анатомию залётных роликов. ---
                        with st.spinner("🧠 ИИ-аналитик изучает ролики и ищет паттерны..."):
                            analyst_result, analyst_raw, analyst_model_used, analyst_log = run_analyst_stage(
                                blogger_url, product_brief, metrics_df, median_views, top_viral_df, viral_stats,
                                active_provider_mode, active_base_url, st.session_state.cfg_ai_key,
                                active_analyst_mode, active_analyst_manual_model, active_analyst_auto_models,
                                active_max_tokens, active_analyst_system_prompt,
                            )

                        if analyst_log:
                            with st.expander("🔍 Ход вызова ИИ-аналитика (модели, ошибки, автопереключение)"):
                                for line in analyst_log: st.code(line, language="text")
                                if analyst_raw: st.code(analyst_raw, language="text")

                        scriptwriter_result, scriptwriter_raw, scriptwriter_model_used, scriptwriter_log = (
                            fallback_scriptwriter_result("аналитик недоступен"), None, None, []
                        )
                        if analyst_model_used:
                            # --- Шаг 2: Сценарист получает готовые паттерны и пишет сценарии. ---
                            with st.spinner("✍️ ИИ-сценарист пишет сценарии на основе паттернов аналитика..."):
                                scriptwriter_result, scriptwriter_raw, scriptwriter_model_used, scriptwriter_log = run_scriptwriter_stage(
                                    blogger_url, product_brief, metrics_df, median_views, active_scenarios_count, top_viral_df,
                                    analyst_result.get("patterns", []), active_provider_mode, active_base_url,
                                    st.session_state.cfg_ai_key, active_scriptwriter_mode, active_scriptwriter_manual_model,
                                    active_scriptwriter_auto_models, active_max_tokens, active_scriptwriter_system_prompt,
                                    viral_stats=viral_stats,
                                )
                        else:
                            st.markdown("""<div class="custom-error fade-in-container"><i class="fa-solid fa-circle-exclamation"></i> ИИ-аналитик не ответил ни одной моделью из списка — сценарист не запускался. Проверьте ключ/модели в панели администратора.</div>""", unsafe_allow_html=True)

                        if scriptwriter_log:
                            with st.expander("🔍 Ход вызова ИИ-сценариста (модели, ошибки, автопереключение)"):
                                for line in scriptwriter_log: st.code(line, language="text")
                                if scriptwriter_raw: st.code(scriptwriter_raw, language="text")

                        result = {
                            "audience_summary": analyst_result.get("audience_summary", ""),
                            "patterns": analyst_result.get("patterns", []),
                            "scenarios": scriptwriter_result.get("scenarios", []),
                            "verdict_note": analyst_result.get("verdict_note", ""),
                        }
                        result = backfill_missing_media_data(result, metrics_df, top_viral_df, viral_stats)

                        # --- Шаг 3: Редактор проверяет каждый сценарий (гейт fit_score="высокий" + уникальность),
                        # при отказе — Сценарист переписывает конкретный сценарий по замечаниям, в пределах лимита. ---
                        qc_log_initial = []
                        if active_qc_enabled and result.get("scenarios") and analyst_model_used and scriptwriter_model_used:
                            with st.spinner("🕵️ ИИ-редактор проверяет сценарии на fit и уникальность..."):
                                result["scenarios"], qc_log_initial = run_scenario_qc_pass(
                                    result.get("scenarios", []), result.get("patterns", []), blogger_url, product_brief,
                                    metrics_df, median_views, top_viral_df, viral_stats,
                                    active_provider_mode, active_base_url, st.session_state.cfg_ai_key,
                                    active_editor_mode, active_editor_manual_model, active_editor_auto_models,
                                    active_max_tokens, active_editor_system_prompt,
                                    active_scriptwriter_mode, active_scriptwriter_manual_model, active_scriptwriter_auto_models,
                                    active_max_tokens, active_scriptwriter_system_prompt,
                                    max_revisions=active_qc_max_revisions,
                                )
                                result = backfill_missing_media_data(result, metrics_df, top_viral_df, viral_stats)
                        if qc_log_initial:
                            with st.expander("🔍 Ход проверки качества сценариев (редактор)"):
                                for line in qc_log_initial: st.code(line, language="text")

                        # Сохраняем последний результат анализа в сессии (включая бриф и данные роликов),
                        # чтобы кнопки «Обновить сценарии» и «Выгрузить» ниже могли им пользоваться даже
                        # после перезапуска скрипта при клике на сами кнопки.
                        st.session_state["last_analysis"] = {
                            "blogger_url": blogger_url,
                            "product_brief": product_brief,
                            "metrics_df": metrics_df,
                            "median_views": median_views,
                            "top_viral_df": top_viral_df,
                            "result": result,
                            "viral_stats": viral_stats,
                            "model_used_analyst": analyst_model_used,
                            "model_used_scenarist": scriptwriter_model_used,
                            "created": datetime.now().strftime("%d.%m.%Y %H:%M"),
                            "saved_id": None,
                        }

                        # --- Финализация записи: если черновое сохранение сырых данных прошло успешно,
                        # дозаполняем ЕЁ ЖЕ результатом ИИ (не плодим дубликат) — так запись в истории есть
                        # ВСЕГДА, даже если ИИ полностью отказал (тогда result_json останется черновым). ---
                        if draft_saved_id:
                            finalize_ok = update_analysis_result(
                                draft_saved_id, result, viral_count=len(top_viral_df) if threshold_met else 0,
                                model_used_analyst=analyst_model_used, model_used_scenarist=scriptwriter_model_used,
                            )
                            saved_id = draft_saved_id if finalize_ok else None
                        elif result.get("scenarios") and analyst_model_used:
                            saved_id = save_analysis(
                                manager=selected_manager, blogger_url=blogger_url, blogger_handle=extract_instagram_username(blogger_url),
                                data_source=active_data_source_mode, model_used_analyst=analyst_model_used,
                                model_used_scenarist=scriptwriter_model_used, reels_count=valid_count,
                                median_views=median_views, viral_count=len(top_viral_df) if threshold_met else 0,
                                product_brief=product_brief, metrics_df=metrics_df, top_viral_df=top_viral_df, result=result,
                            )
                        else:
                            saved_id = None

                        st.session_state["last_analysis"]["saved_id"] = saved_id

                        if saved_id and analyst_model_used and result.get("scenarios"):
                            st.success(f"✅ Анализ сохранён в вашу историю (запись №{saved_id}) — смотрите на вкладке «Мои блогеры».")
                            if active_sound_enabled:
                                play_completion_sound()
                        elif saved_id:
                            st.warning(f"⚠️ Сырые данные ролика сохранены в историю (запись №{saved_id}), но ИИ не смог полностью завершить анализ — повторный парсинг через Apify для этого блогера больше не понадобится.")
                        else:
                            st.warning("Не удалось сохранить анализ в историю — результат выше доступен только сейчас.")

        # --- Единый блок отображения последнего анализа: рендер результата + кнопки
        # «Обновить сценарии» (переписать все сразу силами Сценариста — без повторного анализа паттернов
        # Аналитиком и без повторного сбора/транскрибации роликов), «🔄 Обновить сценарий» у каждой карточки
        # (точечная перегенерация одного сценария, тоже только Сценарист) и «Выгрузить».
        # Работает и сразу после генерации, и после обновления (через session_state). ---
        if st.session_state.get("last_analysis"):
            la = st.session_state["last_analysis"]
            if st.session_state.pop("_pending_completion_sound", False):
                play_completion_sound()
            clicked_scenario_idx = render_full_result(
                la["metrics_df"], la["top_viral_df"], la["result"],
                enable_scenario_regen=True, regen_key_prefix="persist",
            )

            st.markdown("<hr style='margin: 22px 0; opacity:0.2;'>", unsafe_allow_html=True)
            info_col, refresh_col, export_col = st.columns([3, 1, 1])
            with info_col:
                st.markdown(
                    f"📤 **Готово к выгрузке:** анализ @{extract_instagram_username(la['blogger_url'])} "
                    f"({la.get('created', '')}) · 🧠 аналитик: `{la.get('model_used_analyst') or '—'}` · "
                    f"✍️ сценарист: `{la.get('model_used_scenarist') or '—'}` — можно переписать сценарии "
                    f"или скопировать таблицу для Google Таблиц.",
                )
            with refresh_col:
                refresh_clicked = st.button("🔄 Обновить сценарии", use_container_width=True, key="refresh_scenarios_btn")
            with export_col:
                export_clicked = st.button("📤 Выгрузить", use_container_width=True, key="export_btn_persist", type="primary")

            # --- Точечное обновление ОДНОГО сценария (кнопка справа от конкретной карточки) — только Сценарист. ---
            if clicked_scenario_idx is not None:
                current_scenarios = la["result"].get("scenarios", [])
                current_patterns = la["result"].get("patterns", [])
                with st.spinner(f"✍️ ИИ-сценарист переписывает сценарий №{clicked_scenario_idx + 1} — без повторного анализа паттернов и без пересбора роликов..."):
                    single_result, single_raw_text, single_model_used, single_log = run_scriptwriter_single_stage(
                        la["blogger_url"], la["product_brief"], la["metrics_df"], la["median_views"],
                        la["top_viral_df"], current_patterns, la.get("viral_stats"), current_scenarios, clicked_scenario_idx,
                        active_provider_mode, active_base_url, st.session_state.cfg_ai_key,
                        active_scriptwriter_mode, active_scriptwriter_manual_model, active_scriptwriter_auto_models,
                        active_max_tokens, active_scriptwriter_system_prompt,
                    )
                if single_log:
                    with st.expander(f"🔍 Ход вызова ИИ-сценариста (обновление сценария №{clicked_scenario_idx + 1})"):
                        for line in single_log: st.code(line, language="text")
                        if single_raw_text: st.code(single_raw_text, language="text")

                new_scenarios_list = single_result.get("scenarios") or []
                if new_scenarios_list and single_model_used:
                    updated_scenarios = list(current_scenarios)
                    if 0 <= clicked_scenario_idx < len(updated_scenarios):
                        updated_scenarios[clicked_scenario_idx] = new_scenarios_list[0]
                    else:
                        updated_scenarios.append(new_scenarios_list[0])
                    la["result"]["scenarios"] = updated_scenarios
                    la["result"] = backfill_missing_media_data(la["result"], la["metrics_df"], la["top_viral_df"], la.get("viral_stats"))

                    qc_log_single = []
                    if active_qc_enabled:
                        with st.spinner("🕵️ ИИ-редактор проверяет обновлённый сценарий..."):
                            la["result"]["scenarios"], qc_log_single = run_scenario_qc_pass(
                                la["result"].get("scenarios", []), current_patterns, la["blogger_url"], la["product_brief"],
                                la["metrics_df"], la["median_views"], la["top_viral_df"], la.get("viral_stats"),
                                active_provider_mode, active_base_url, st.session_state.cfg_ai_key,
                                active_editor_mode, active_editor_manual_model, active_editor_auto_models,
                                active_max_tokens, active_editor_system_prompt,
                                active_scriptwriter_mode, active_scriptwriter_manual_model, active_scriptwriter_auto_models,
                                active_max_tokens, active_scriptwriter_system_prompt,
                                max_revisions=active_qc_max_revisions, only_indices={clicked_scenario_idx},
                            )
                            la["result"] = backfill_missing_media_data(la["result"], la["metrics_df"], la["top_viral_df"], la.get("viral_stats"))
                    if qc_log_single:
                        with st.expander(f"🔍 Ход проверки качества (редактор) — сценарий №{clicked_scenario_idx + 1}"):
                            for line in qc_log_single: st.code(line, language="text")

                    la["model_used_scenarist"] = single_model_used
                    la["created"] = datetime.now().strftime("%d.%m.%Y %H:%M")
                    st.session_state["last_analysis"] = la
                    if la.get("saved_id"):
                        updated_ok = update_analysis_result(la["saved_id"], la["result"], model_used_scenarist=single_model_used)
                        if updated_ok:
                            st.success(f"✅ Сценарий №{clicked_scenario_idx + 1} обновлён (модель: {single_model_used}) — история анализа тоже обновлена.")
                        else:
                            st.warning(f"Сценарий №{clicked_scenario_idx + 1} обновлён, но не удалось обновить запись в истории.")
                    else:
                        st.success(f"✅ Сценарий №{clicked_scenario_idx + 1} обновлён (модель: {single_model_used}).")
                    st.rerun()
                else:
                    st.error(f"Не удалось получить обновлённый сценарий №{clicked_scenario_idx + 1} от ИИ-сценариста — прежний вариант оставлен без изменений.")

            if refresh_clicked:
                current_patterns = la["result"].get("patterns", [])
                with st.spinner("✍️ ИИ-сценарист переписывает сценарии — без повторного анализа паттернов и без пересбора роликов..."):
                    new_scriptwriter_result, refresh_raw_text, refresh_model_used, refresh_log = run_scriptwriter_stage(
                        la["blogger_url"], la["product_brief"], la["metrics_df"], la["median_views"],
                        active_scenarios_count, la["top_viral_df"], current_patterns,
                        active_provider_mode, active_base_url, st.session_state.cfg_ai_key,
                        active_scriptwriter_mode, active_scriptwriter_manual_model, active_scriptwriter_auto_models,
                        active_max_tokens, active_scriptwriter_system_prompt,
                        viral_stats=la.get("viral_stats"), previous_scenarios=la["result"].get("scenarios"),
                    )
                if refresh_log:
                    with st.expander("🔍 Ход вызова ИИ-сценариста (обновление сценариев)"):
                        for line in refresh_log: st.code(line, language="text")
                        if refresh_raw_text: st.code(refresh_raw_text, language="text")

                new_scenarios = new_scriptwriter_result.get("scenarios") or []
                if new_scenarios and refresh_model_used:
                    la["result"]["scenarios"] = new_scenarios
                    la["result"] = backfill_missing_media_data(la["result"], la["metrics_df"], la["top_viral_df"], la.get("viral_stats"))

                    qc_log_refresh = []
                    if active_qc_enabled:
                        with st.spinner("🕵️ ИИ-редактор проверяет новые сценарии на fit и уникальность..."):
                            la["result"]["scenarios"], qc_log_refresh = run_scenario_qc_pass(
                                la["result"].get("scenarios", []), current_patterns, la["blogger_url"], la["product_brief"],
                                la["metrics_df"], la["median_views"], la["top_viral_df"], la.get("viral_stats"),
                                active_provider_mode, active_base_url, st.session_state.cfg_ai_key,
                                active_editor_mode, active_editor_manual_model, active_editor_auto_models,
                                active_max_tokens, active_editor_system_prompt,
                                active_scriptwriter_mode, active_scriptwriter_manual_model, active_scriptwriter_auto_models,
                                active_max_tokens, active_scriptwriter_system_prompt,
                                max_revisions=active_qc_max_revisions,
                            )
                            la["result"] = backfill_missing_media_data(la["result"], la["metrics_df"], la["top_viral_df"], la.get("viral_stats"))
                    if qc_log_refresh:
                        with st.expander("🔍 Ход проверки качества сценариев (редактор)"):
                            for line in qc_log_refresh: st.code(line, language="text")

                    la["model_used_scenarist"] = refresh_model_used
                    la["created"] = datetime.now().strftime("%d.%m.%Y %H:%M")
                    st.session_state["last_analysis"] = la
                    if la.get("saved_id"):
                        updated_ok = update_analysis_result(la["saved_id"], la["result"], model_used_scenarist=refresh_model_used)
                        if updated_ok:
                            st.success(f"✅ Сценарии обновлены (модель: {refresh_model_used}) — история анализа тоже обновлена.")
                        else:
                            st.warning("Сценарии обновлены, но не удалось обновить запись в истории.")
                    else:
                        st.success(f"✅ Сценарии обновлены (модель: {refresh_model_used}).")
                    if active_sound_enabled:
                        # Звук ставим в очередь и проигрываем уже ПОСЛЕ rerun (в блоке рендера ниже) —
                        # иначе браузер не успевает создать AudioContext до немедленной перерисовки страницы.
                        st.session_state["_pending_completion_sound"] = True
                    st.rerun()
                else:
                    st.error("Не удалось получить новые сценарии от ИИ-сценариста — прежний результат оставлен без изменений.")

            if export_clicked:
                table_html, tsv_text = build_export_table(la["blogger_url"], la["viral_stats"], la["top_viral_df"], la["result"], all_reels_df=la["metrics_df"])
                open_export_dialog(table_html, tsv_text, {
                    "handle": extract_instagram_username(la["blogger_url"]),
                    "created": la.get("created", ""),
                    "key": "persist",
                })
