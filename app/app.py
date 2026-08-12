# pip install streamlit openai pandas
#
# Запуск: streamlit run blogger_reels_analyzer.py

import json
import time
import sqlite3
import hashlib
import secrets
import statistics
import html
from datetime import datetime
from pathlib import Path

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
                reels_count INTEGER,
                median_views INTEGER,
                viral_count INTEGER,
                product_brief TEXT,
                metrics_json TEXT,
                top_viral_json TEXT,
                result_json TEXT
            )
        """)
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
DEFAULT_BRIEF_TEXT = (
    "Товар: утягивающие майки (женское корректирующее бельё/топы).\n"
    "Ключевые преимущества: незаметны под одеждой, утягивают живот и бока, "
    "удобны на весь день, есть размеры для plus-size.\n"
    "Чего избегать в сценарии: не обесценивать фигуру блогера, не строить ролик "
    "вокруг 'скрыть недостатки' — акцент на уверенность и комфорт, а не на стыд."
)

DEFAULT_SYSTEM_PROMPT = (
    "Ты — Senior креативный директор, ведущий SMM-стратег и топовый сценарист коротких видео "
    "(Reels/Shorts/TikTok). Твоя экспертиза — нативный UGC-контент, который пробивает баннерную слепоту "
    "и рекламную усталость аудитории, и бесшовная адаптация брендов под уникальный Tone of Voice блогера.\n\n"
    "На вход поступает массив с ретроспективой роликов блогера (метрики, краткое описание, иногда реальная "
    "транскрипция речи, дата публикации) и бриф продукта. Твой ответ напрямую парсится автоматизированной "
    "системой — отклонение от формата недопустимо.\n\n"
    "ВАЖНО про актуальность: конкретные тренды, звуки и форматы в коротких видео меняются еженедельно, "
    "и твои собственные знания о 'модных трендах' на момент обучения могут быть уже устаревшими. "
    "НЕ полагайся на память о трендах прошлых лет как на факт. Вместо этого:\n"
    "— Определяй, что реально работает, ИЗ САМИХ ДАННЫХ — при прочих равных отдавай приоритет более "
    "свежим роликам (по полю 'Дата публикации'), а не старым публикациям многолетней давности.\n"
    "— Если видишь явный сдвиг формата в недавних роликах по сравнению со старыми — это сильный сигнал "
    "смены того, что заходит аудитории именно сейчас; отметь это отдельно в audience_summary.\n\n"
    "Твоя задача:\n"
    "1. Аналитика медианы: оценивай вовлечение и просмотры СТРОГО относительно собственной медианы "
    "блогера, а не в абсолютных цифрах и не относительно рынка в целом.\n"
    "2. Деконструкция хука: если для ролика есть поле 'Транскрипция (если есть)' — детально препарируй "
    "не только первые 2-3 секунды целиком, но по возможности отдельно первые доли секунды — именно там "
    "решается досмотр или скролл. Анализируй: тип разрыва ожидания в первом кадре (pattern interrupt), "
    "текст на экране, дублирующий речь (расчёт на просмотр без звука), 'неполированную' нативную "
    "эстетику против срежиссированной рекламной картинки, прямое обращение к зрителю (взгляд в камеру, "
    "'ты/вы'), темп монтажа — а не только жанр ролика целиком.\n"
    "3. Retention по всему ролику: ищи петлевые концовки (конец подводит к пересмотру начала), структуру "
    "'вопрос в начале — ответ в конце', нарочную задержку ответа для удержания внимания.\n"
    "4. Валидация гипотез: жёстко понижай уверенность вывода (strength='предварительная'), если он "
    "основан на маленькой выборке или на одном явном вирусном выбросе (аномалии) — не выдавай "
    "случайность за надёжный паттерн.\n"
    "5. Бесшовная интеграция: сценарий должен выглядеть как естественная часть жизни блогера "
    "('показывай, а не рассказывай', ноль срежиссированности). При интеграции физического товара — "
    "упор на эстетику в кадре, визуальную трансформацию, посадку или решение боли, без продажи «в лоб» "
    "и без рекламных клише.\n"
    "6. Legal compliance: каждый сценарий обязан включать чёткую инструкцию по маркировке рекламы "
    "согласно законодательству (поле ad_marking_note) — строгое требование, не опционально.\n"
    "7. Brand Safety & Fit: если продукт концептуально разрушает образ блогера и ни один формат не "
    "подходит — прямо блокируй интеграцию в verdict_note, без компромиссов и притягивания форматов за уши.\n\n"
    "Отвечай СТРОГО в формате валидного JSON. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО: markdown-разметка (никаких "
    "кодовых блоков), пояснения до или после кода. Только чистый JSON на русском языке.\n"
    "Схема:\n"
    "{\n"
    '  "audience_summary": "строка (включая заметку о сдвиге трендов, если он есть в свежих роликах)",\n'
    '  "patterns": [{"pattern": "строка", "evidence": "строка", "strength": "высокая|средняя|предварительная"}],\n'
    '  "scenarios": [{"title": "строка", "based_on_pattern": "строка", "hook": "строка", '
    '"script": "строка (сценарий по битам: тайминг, действие в кадре, текст, визуальные акценты)", '
    '"caption": "строка", "ad_marking_note": "строка", "fit_score": "высокий|средний|низкий"}],\n'
    '  "verdict_note": "строка"\n'
    "}"
)

init_db()

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

if "manager_logged_in" not in st.session_state:
    st.session_state.manager_logged_in = None

# Загружаем настройки из БД для всех пользователей один раз при старте сессии
if "settings_loaded" not in st.session_state:
    st.session_state.cfg_ai_provider_mode = load_setting_str("cfg_ai_provider_mode", "openrouter")
    st.session_state.cfg_ai_base_url = load_setting_str("cfg_ai_base_url", "https://openrouter.ai/api/v1")
    st.session_state.cfg_ai_key = load_setting_str("cfg_ai_key", "")
    st.session_state.cfg_ai_model = load_setting_str("cfg_ai_model", "anthropic/claude-sonnet-5")
    st.session_state.cfg_max_tokens = load_setting_int("cfg_max_tokens", 3000)
    
    st.session_state.cfg_data_source_mode = load_setting_str("cfg_data_source_mode", "apify")
    st.session_state.cfg_apify_token = load_setting_str("cfg_apify_token", "")
    st.session_state.cfg_apify_actor = load_setting_str("cfg_apify_actor", "apify/instagram-reel-scraper")
    st.session_state.cfg_results_limit = load_setting_int("cfg_results_limit", 25)
    st.session_state.cfg_lookback_days = load_setting_int("cfg_lookback_days", 30)
    st.session_state.cfg_include_transcript = load_setting_bool("cfg_include_transcript", True)
    
    st.session_state.cfg_viral_threshold = load_setting_float("cfg_viral_threshold", 2.5)
    st.session_state.cfg_top_n_viral = load_setting_int("cfg_top_n_viral", 3)
    st.session_state.min_reels_required = load_setting_int("min_reels_required", 8)
    st.session_state.scenarios_count = load_setting_int("scenarios_count", 4)
    
    st.session_state.product_brief_default = load_setting_str("product_brief_default", DEFAULT_BRIEF_TEXT)
    st.session_state.system_prompt_cfg = load_setting_str("system_prompt_cfg", DEFAULT_SYSTEM_PROMPT)

    st.session_state.available_models = []
    st.session_state.model_test_results = {}
    st.session_state.cfg_max_models_to_test = 40
    st.session_state.settings_loaded = True


# ============================================================================
# ФУНКЦИИ ИИ И APIFY
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


REELS_COLUMNS = [
    "Ссылка на ролик", "Просмотры", "Лайки", "Комментарии", "Сохранения",
    "Дата публикации", "Что происходит в ролике (кратко)", "Транскрипция (если есть)"
]

if "reels_data" not in st.session_state:
    st.session_state.reels_data = pd.DataFrame(
        [{"Ссылка на ролик": "", "Просмотры": 0, "Лайки": 0, "Комментарии": 0,
          "Сохранения": 0, "Дата публикации": "", "Что происходит в ролике (кратко)": "",
          "Транскрипция (если есть)": ""} for _ in range(6)]
    )

def build_test_dataframe():
    rows = [
        ("instagram.com/reel/demo1", 210000, 15200, 810, 4100, "2026-05-02", "Примерка нескольких образов подряд под трендовый звук", ""),
        ("instagram.com/reel/demo2", 45000, 1800, 90, 320, "2026-05-06", "Обзор ткани и посадки одного изделия", ""),
        ("instagram.com/reel/demo3", 320000, 28000, 1450, 9200, "2026-05-10", "Юмористический скетч в примерочной с подругой", ""),
    ]
    return pd.DataFrame(rows, columns=REELS_COLUMNS)

def apify_get_first(item: dict, keys, default=""):
    for k in keys:
        val = item.get(k)
        if val not in (None, ""): return val
    return default

def fetch_reels_via_apify(token, actor, targets, results_limit=None, lookback_days=None,
                           include_transcript=False, skip_pinned=True, skip_trial=True, timeout=300):
    if httpx is None: raise RuntimeError("Библиотека httpx не установлена")
    actor_path = actor.strip("/").replace("/", "~")
    url = f"https://api.apify.com/v2/acts/{actor_path}/run-sync-get-dataset-items?token={token}"
    body = {"username": targets, "skipPinnedPosts": skip_pinned, "skipTrialReels": skip_trial, "includeTranscript": include_transcript}
    if results_limit: body["resultsLimit"] = results_limit
    if lookback_days: body["onlyPostsNewerThan"] = f"{lookback_days} days"
    resp = httpx.post(url, json=body, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else data.get("items", [])

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
            "Что происходит в ролике (кратко)": str(caption)[:300], "Транскрипция (если есть)": transcript,
        })
    return pd.DataFrame(rows, columns=REELS_COLUMNS) if rows else pd.DataFrame(columns=REELS_COLUMNS)

def strip_json_fences(text: str) -> str:
    text = text.strip()
    if text.startswith('`' * 3):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.rstrip().endswith('`' * 3):
            text = text.rstrip()[:-3]
    return text.strip()

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

def build_user_prompt(blogger_url, product_brief, metrics_df, median_views, n_scenarios, top_viral_df=None, previous_scenarios=None):
    table_records = metrics_df.drop(columns=["Транскрипция (если есть)"], errors="ignore").to_dict(orient="records")
    viral_block = ""
    if top_viral_df is not None and not top_viral_df.empty:
        viral_records = top_viral_df.to_dict(orient="records")
        viral_block = (
            f"\n\nТоп-{len(viral_records)} самых залётных роликов ЭТОГО блогера "
            f"(здесь есть поле 'Транскрипция (если есть)' — используй именно его для разбора хука и структуры):\n"
            f"{json.dumps(viral_records, ensure_ascii=False, indent=2)}"
        )
    regen_block = ""
    if previous_scenarios:
        prev_lines = "\n".join(
            f"- «{s.get('title', '')}» — хук: {s.get('hook', '')}" for s in previous_scenarios
        )
        regen_block = (
            "\n\nЭТО ПОВТОРНЫЙ ЗАПРОС «ОБНОВИТЬ СЦЕНАРИИ» (без повторного сбора и транскрибации роликов — "
            "данные о роликах блогера те же). Напиши НОВЫЙ набор сценариев на основе тех же данных: "
            "другие хуки, другие ракурсы подачи, по возможности другие anchor-ролики из ретроспективы, если "
            "подходящих несколько. Не повторяй дословно прежние формулировки хуков и сценариев.\n"
            f"Прежние сценарии (их НЕ повторять):\n{prev_lines}"
        )
    return (
        f"Блогер: {blogger_url}\nМедиана просмотров: {median_views:.0f}\nНужно сценариев: {n_scenarios}\n\n"
        f"Бриф о товаре:\n{product_brief}\n\nВсе загруженные ролики:\n"
        f"{json.dumps(table_records, ensure_ascii=False, indent=2)}{viral_block}{regen_block}"
    )

def fallback_result(reason: str):
    return {
        "audience_summary": f"Не удалось получить ответ от ИИ ({reason}). Ниже — заглушка.",
        "patterns": [{"pattern": "Заглушка", "evidence": "демо", "strength": "предварительная"}],
        "scenarios": [{"title": "Демо-сценарий", "based_on_pattern": "—", "hook": "Настройте API-ключ OpenRouter", "script": "—", "caption": "—", "ad_marking_note": "Реклама.", "fit_score": "средний"}],
        "verdict_note": "Заполните ключ ИИ-помощника в настройках.",
    }


def run_ai_analysis(blogger_url, product_brief, metrics_df, median_views, scenarios_count, top_viral_df,
                     provider_mode, base_url, model, max_tokens, system_prompt, api_key, previous_result=None):
    """
    Единая точка вызова ИИ для получения audience_summary/patterns/scenarios.
    Используется и при первом анализе, и при нажатии «🔄 Обновить сценарии»
    (в последнем случае previous_result передаётся, чтобы ИИ написал НОВЫЙ набор
    сценариев по уже собранным и уже транскрибированным роликам — без повторного
    похода в Apify и без повторной транскрибации).
    Возвращает (result_dict, raw_text_or_None, error_detail_or_None).
    """
    if not api_key:
        return fallback_result("не задан API-ключ"), None, None
    if provider_mode == "anthropic_direct" and Anthropic is None:
        return fallback_result("не установлена библиотека anthropic"), None, None
    if provider_mode != "anthropic_direct" and OpenAI is None:
        return fallback_result("не установлена библиотека openai"), None, None

    raw_text = None
    previous_scenarios = (previous_result or {}).get("scenarios") if previous_result else None
    try:
        user_prompt = build_user_prompt(
            blogger_url, product_brief, metrics_df, median_views, scenarios_count, top_viral_df,
            previous_scenarios=previous_scenarios,
        )
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
            raise ValueError("EMPTY_MODEL_RESPONSE")
        result = json.loads(strip_json_fences(raw_text))
        return result, raw_text, None
    except ValueError as exc:
        reason = "лимит модели или пустой ответ" if str(exc) == "EMPTY_MODEL_RESPONSE" else f"ошибка: {exc}"
        return fallback_result(reason), raw_text, None
    except json.JSONDecodeError:
        return fallback_result("не удалось разобрать ответ модели как JSON"), raw_text, None
    except Exception as exc:
        detail = f"{type(exc).__name__}: {exc}"
        return fallback_result(f"ошибка обращения к API: {exc}"), raw_text, detail


def render_full_result(metrics_df, top_viral_df, result):
    """Рендерит метрики + разбор ИИ + сценарии. Общая для первого анализа и после «Обновить сценарии»."""
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
        with patt_cols[i % len(patt_cols)]:
            st.markdown(f"""
                <div class="glass-metric fade-in-container" style="margin-bottom: 14px;">
                    <div class="metric-title">Паттерн</div>
                    <div class="metric-value" style="font-size: 16px;">{html.escape(patt.get("pattern", ""))}</div>
                    <div class="metric-delta" style="color:#94a3b8;">{html.escape(patt.get("evidence", ""))}</div>
                    <span class="pattern-badge {badge_class}">{html.escape(strength)}</span>
                </div>
            """, unsafe_allow_html=True)

    st.markdown("#### Сценарии роликов под товар", unsafe_allow_html=True)
    for scenario in result.get("scenarios", []):
        fit = scenario.get("fit_score", "средний")
        fit_class = {"высокий": "fit-high", "средний": "fit-medium"}.get(fit, "fit-low")
        st.markdown(f"""
            <div class="ai-report-glass fade-in-container">
                <h4 style="margin-top:0;">🎬 {html.escape(scenario.get("title", ""))} <span class="{fit_class}" style="float:right; font-size: 14px;">Fit: {html.escape(fit)}</span></h4>
                <p style="color:#94a3b8; font-size: 13px;">На основе паттерна: {html.escape(scenario.get("based_on_pattern", "—"))}</p>
                <hr style="border-color: rgba(255,255,255,0.1);">
                <p><b>Хук:</b> {html.escape(scenario.get("hook", ""))}</p>
                <p><b>Сценарий:</b><br>{str(html.escape(scenario.get("script", ""))).replace(chr(10), "<br>")}</p>
                <p><b>Подпись к посту:</b> {html.escape(scenario.get("caption", ""))}</p>
            </div>
        """, unsafe_allow_html=True)

    if result.get("verdict_note"):
        st.markdown(f"""<div class="custom-warning fade-in-container"><i class="fa-solid fa-circle-info" style="font-size: 18px;"></i> {html.escape(result.get("verdict_note"))}</div>""", unsafe_allow_html=True)


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
        block = (
            f"🎬 {s.get('title', '')}\n"
            f"На основе: {based_on}\n\n"
            f"Хук: {s.get('hook', '')}\n\n"
            f"Сценарий: {s.get('script', '')}\n\n"
            f"Подпись: {s.get('caption', '')}\n"
            f"{s.get('ad_marking_note', '')}\n"
            f"Fit: {s.get('fit_score', '')}"
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


def save_analysis(manager, blogger_url, blogger_handle, data_source, model_used,
                  reels_count, median_views, viral_count, product_brief,
                  metrics_df, top_viral_df, result):
    try:
        with db_connect() as conn:
            cur = conn.execute("""
                INSERT INTO analyses (manager, blogger_url, blogger_handle, created_at, data_source,
                                      model_used, reels_count, median_views, viral_count, product_brief,
                                      metrics_json, top_viral_json, result_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                manager, blogger_url, blogger_handle, datetime.now().isoformat(timespec="seconds"),
                data_source, model_used, int(reels_count), int(median_views), int(viral_count),
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

def update_analysis_result(analysis_id, result, viral_count=None):
    """Обновляет result_json (и при необходимости viral_count) у уже сохранённой записи —
    используется кнопкой «🔄 Обновить сценарии», чтобы не плодить дубликаты в истории."""
    if not analysis_id:
        return False
    try:
        with db_connect() as conn:
            if viral_count is not None:
                conn.execute(
                    "UPDATE analyses SET result_json = ?, viral_count = ? WHERE id = ?",
                    (json.dumps(result, ensure_ascii=False), int(viral_count), analysis_id),
                )
            else:
                conn.execute(
                    "UPDATE analyses SET result_json = ? WHERE id = ?",
                    (json.dumps(result, ensure_ascii=False), analysis_id),
                )
        return True
    except Exception:
        return False

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

    if is_admin:
        provider_mode_labels = {"openrouter": "OpenRouter (много моделей)", "gemini": "Google Gemini (AI Studio)", "anthropic_direct": "Anthropic напрямую"}
        provider_presets = {
            "openrouter": {"base_url": "https://openrouter.ai/api/v1", "key_label": "API-ключ (OpenRouter)", "key_help": "openrouter.ai/workspaces/default/keys"},
            "gemini": {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai/", "key_label": "API-ключ (Google AI Studio / Gemini)", "key_help": "aistudio.google.com/api-keys"},
        }
        provider_mode_input = st.sidebar.selectbox("Способ вызова ИИ", list(provider_mode_labels.keys()), index=list(provider_mode_labels.keys()).index(st.session_state.cfg_ai_provider_mode), format_func=lambda k: provider_mode_labels[k])

        if provider_mode_input == "anthropic_direct":
            ai_key_input = st.sidebar.text_input("API-ключ Anthropic", value=st.session_state.cfg_ai_key, type="password")
            direct_model_options = ["claude-sonnet-5", "claude-opus-4-8", "claude-haiku-4-5-20251001", "claude-fable-5"]
            ai_model_input = st.sidebar.selectbox("Модель", direct_model_options, index=direct_model_options.index(st.session_state.cfg_ai_model) if st.session_state.cfg_ai_model in direct_model_options else 0)
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

            starter_catalog = STARTER_MODEL_CATALOG if provider_mode_input == "openrouter" else GEMINI_STARTER_CATALOG
            model_catalog = st.session_state.available_models or starter_catalog

            model_choices = [MANUAL_MODEL_OPTION] + model_catalog
            current_ids = [m["id"] for m in model_choices]
            default_index = current_ids.index(st.session_state.cfg_ai_model) if st.session_state.cfg_ai_model in current_ids else 0

            def _format_model_option(m):
                if m["id"] == "__manual__": return m["name"]
                free_icon = '🆓' if m['is_free'] is True else ('💰' if m['is_free'] is False else '•')
                return f"{free_icon} {m['id']}"

            selected_model_entry = st.sidebar.selectbox("Модель", model_choices, index=default_index, format_func=_format_model_option)
            if selected_model_entry["id"] == "__manual__":
                ai_model_input = st.sidebar.text_input("Свой слаг модели", value=st.session_state.cfg_ai_model)
            else:
                ai_model_input = selected_model_entry["id"]

        max_tokens_input = st.sidebar.number_input("Лимит токенов ответа (max_tokens)", min_value=500, max_value=8000, value=st.session_state.cfg_max_tokens, step=100)
        st.sidebar.markdown("---")

        st.sidebar.markdown("### <i class='fa-solid fa-video'></i> Сбор роликов", unsafe_allow_html=True)
        data_source_labels = {"apify": "🤖 Автоматически через Apify", "manual": "✍️ Вручную (таблица)"}
        data_source_input = st.sidebar.selectbox("Источник данных", list(data_source_labels.keys()), index=list(data_source_labels.keys()).index(st.session_state.cfg_data_source_mode), format_func=lambda k: data_source_labels[k])
        
        if data_source_input == "apify":
            apify_token_input = st.sidebar.text_input("Apify API-токен", value=st.session_state.cfg_apify_token, type="password")
            apify_actor_input = st.sidebar.text_input("Актор Apify", value=st.session_state.cfg_apify_actor)
            results_limit_input = st.sidebar.number_input("Роликов с профиля за раз", min_value=5, max_value=100, value=st.session_state.cfg_results_limit, step=5)
            lookback_days_input = st.sidebar.number_input("Глубина в днях", min_value=7, max_value=90, value=st.session_state.cfg_lookback_days, step=1)
            include_transcript_input = st.sidebar.checkbox("Включить реальную транскрипцию", value=st.session_state.cfg_include_transcript)
        else:
            apify_token_input = st.session_state.cfg_apify_token
            apify_actor_input = st.session_state.cfg_apify_actor
            results_limit_input = st.session_state.cfg_results_limit
            lookback_days_input = st.session_state.cfg_lookback_days
            include_transcript_input = st.session_state.cfg_include_transcript

        viral_threshold_input = st.sidebar.slider("Порог «залётности» (× медианы)", 1.5, 5.0, float(st.session_state.cfg_viral_threshold), 0.1)
        top_n_viral_input = st.sidebar.slider("Топ-N залётных роликов", 1, 6, st.session_state.cfg_top_n_viral)
        st.sidebar.markdown("---")
        min_reels_input = st.sidebar.number_input("Мин. роликов для надёжного анализа", min_value=3, max_value=30, value=st.session_state.min_reels_required, step=1)
        scenarios_count_input = st.sidebar.slider("Сколько сценариев генерировать", 2, 6, st.session_state.scenarios_count)
        st.sidebar.markdown("---")
        product_brief_input = st.sidebar.text_area("Бриф о товаре по умолчанию", value=st.session_state.product_brief_default, height=160)
        st.sidebar.markdown("---")
        system_prompt_input = st.sidebar.text_area("Системный промпт для ИИ", value=st.session_state.system_prompt_cfg, height=220)

        # СОХРАНЕНИЕ В БАЗУ ДАННЫХ ДЛЯ ВСЕХ МЕНЕДЖЕРОВ
        if st.sidebar.button("💾 Сохранить глобально", use_container_width=True, type="primary"):
            st.session_state.cfg_ai_provider_mode = provider_mode_input
            st.session_state.cfg_ai_base_url = ai_base_url_input
            st.session_state.cfg_ai_key = ai_key_input
            st.session_state.cfg_ai_model = ai_model_input
            st.session_state.cfg_max_tokens = max_tokens_input
            st.session_state.cfg_data_source_mode = data_source_input
            st.session_state.cfg_apify_token = apify_token_input
            st.session_state.cfg_apify_actor = apify_actor_input
            st.session_state.cfg_results_limit = results_limit_input
            st.session_state.cfg_lookback_days = lookback_days_input
            st.session_state.cfg_include_transcript = include_transcript_input
            st.session_state.cfg_viral_threshold = viral_threshold_input
            st.session_state.cfg_top_n_viral = top_n_viral_input
            st.session_state.min_reels_required = min_reels_input
            st.session_state.scenarios_count = scenarios_count_input
            st.session_state.product_brief_default = product_brief_input
            st.session_state.system_prompt_cfg = system_prompt_input

            set_setting("cfg_ai_provider_mode", provider_mode_input)
            set_setting("cfg_ai_base_url", ai_base_url_input)
            set_setting("cfg_ai_key", ai_key_input)
            set_setting("cfg_ai_model", ai_model_input)
            set_setting("cfg_max_tokens", str(max_tokens_input))
            set_setting("cfg_data_source_mode", data_source_input)
            set_setting("cfg_apify_token", apify_token_input)
            set_setting("cfg_apify_actor", apify_actor_input)
            set_setting("cfg_results_limit", str(results_limit_input))
            set_setting("cfg_lookback_days", str(lookback_days_input))
            set_setting("cfg_include_transcript", str(include_transcript_input))
            set_setting("cfg_viral_threshold", str(viral_threshold_input))
            set_setting("cfg_top_n_viral", str(top_n_viral_input))
            set_setting("min_reels_required", str(min_reels_input))
            set_setting("scenarios_count", str(scenarios_count_input))
            set_setting("product_brief_default", product_brief_input)
            set_setting("system_prompt_cfg", system_prompt_input)
            
            st.sidebar.success("✅ Сохранено глобально! Доступно всем менеджерам.")
    else:
        st.sidebar.info("🔒 Настройки может менять только Администратор.")
        st.sidebar.markdown(f"🤖 **Модель:** `{st.session_state.cfg_ai_model}`")
        st.sidebar.markdown(f"📥 **Источник данных:** {'Apify (авто)' if st.session_state.cfg_data_source_mode == 'apify' else 'Вручную'}")
        st.sidebar.markdown(f"📏 **Мин. роликов:** {st.session_state.min_reels_required}")
        st.sidebar.markdown(f"🧩 **Сценариев за раз:** {st.session_state.scenarios_count}")

    active_provider_mode = st.session_state.cfg_ai_provider_mode
    active_base_url = st.session_state.cfg_ai_base_url
    active_model = st.session_state.cfg_ai_model
    active_max_tokens = st.session_state.cfg_max_tokens
    active_system_prompt = st.session_state.system_prompt_cfg
    active_min_reels = st.session_state.min_reels_required
    active_scenarios_count = st.session_state.scenarios_count
    active_data_source_mode = st.session_state.cfg_data_source_mode
    active_viral_threshold = st.session_state.cfg_viral_threshold
    active_top_n_viral = st.session_state.cfg_top_n_viral

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
                    <span class="history-chip">🤖 {html.escape(record.get("model_used", "—"))}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        with st.expander(f"Открыть разбор и сценарии — @{handle} от {created}"):
            if result.get("audience_summary"):
                st.markdown(f"**Аудитория:** {result['audience_summary']}")
            if patterns:
                st.markdown("**Найденные паттерны:**")
                for p in patterns:
                    st.markdown(f"- **{p.get('pattern','')}** — {p.get('evidence','')} _({p.get('strength','')})_")
            if scenarios:
                st.markdown("**Сценарии:**")
                for s in scenarios:
                    st.markdown(
                        f"**🎬 {s.get('title','')}** _(fit: {s.get('fit_score','—')})_\n\n"
                        f"*На основе:* {s.get('based_on_pattern','—')}\n\n"
                        f"**Хук:** {s.get('hook','')}\n\n"
                        f"**Сценарий:** {s.get('script','')}\n\n"
                        f"**Подпись:** {s.get('caption','')}\n\n---"
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
        blogger_url = st.text_input("Ссылка на профиль блогера (Instagram)", placeholder="https://www.instagram.com/example_blogger/")
        product_brief = st.text_area("Бриф о товаре для адаптации в сценарий", value=st.session_state.product_brief_default, height=120)

        edited_df = None
        if active_data_source_mode == "manual":
            st.markdown("**Ролики блогера** — заполните вручную:")
            edited_df = st.data_editor(
                st.session_state.reels_data, num_rows="dynamic", use_container_width=True, key="reels_editor_widget",
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
        with btn_col1: submit_btn = st.button("🚀 Проанализировать ролики", use_container_width=True)
        with btn_col2: test_btn = st.button("🧪 Заполнить тестовыми роликами", use_container_width=True) if active_data_source_mode == "manual" else False
        st.markdown('</div>', unsafe_allow_html=True)

        if test_btn:
            st.session_state.reels_data = build_test_dataframe()
            if "reels_editor_widget" in st.session_state: del st.session_state["reels_editor_widget"]
            st.rerun()

        if submit_btn:
            if not blogger_url.strip():
                st.markdown("""<div class="custom-error fade-in-container"><i class="fa-solid fa-circle-exclamation" style="font-size: 20px;"></i> Укажите ссылку на блогера.</div>""", unsafe_allow_html=True)
            else:
                apify_debug_raw = None
                apify_debug_error = None
                raw_df = None

                if active_data_source_mode == "manual":
                    st.session_state.reels_data = edited_df
                    raw_df = edited_df
                else:
                    if not st.session_state.cfg_apify_token:
                        st.markdown("""<div class="custom-error fade-in-container"><i class="fa-solid fa-circle-exclamation"></i> Не задан Apify API-токен — впишите его в панели администратора.</div>""", unsafe_allow_html=True)
                    else:
                        username = extract_instagram_username(blogger_url)
                        with st.spinner(f"Собираю ролики @{username} через Apify..."):
                            try:
                                items = fetch_reels_via_apify(
                                    st.session_state.cfg_apify_token, st.session_state.cfg_apify_actor,
                                    targets=[username], results_limit=st.session_state.cfg_results_limit,
                                    lookback_days=st.session_state.cfg_lookback_days, include_transcript=False,
                                )
                                apify_debug_raw = items[0] if items else "(пустой список)"
                                raw_df = apify_items_to_dataframe(items)
                            except Exception as exc:
                                apify_debug_error = f"{type(exc).__name__}: {exc}"

                if apify_debug_raw is not None or apify_debug_error is not None:
                    with st.expander("🔍 Сырой ответ Apify (для отладки)"):
                        if apify_debug_error: st.code(apify_debug_error, language="text")
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

                        if (active_data_source_mode == "apify" and st.session_state.cfg_include_transcript and st.session_state.cfg_apify_token and not top_viral_df.empty):
                            top_links = [l for l in top_viral_df["Ссылка на ролик"].tolist() if l]
                            if top_links:
                                with st.spinner(f"Транскрибирую топ-{len(top_links)} залётных ролика..."):
                                    try:
                                        transcript_items = fetch_reels_via_apify(
                                            st.session_state.cfg_apify_token, st.session_state.cfg_apify_actor,
                                            targets=top_links, results_limit=None, lookback_days=None,
                                            include_transcript=True, timeout=420,
                                        )
                                        transcript_df = apify_items_to_dataframe(transcript_items)
                                        transcript_map = dict(zip(transcript_df["Ссылка на ролик"], transcript_df["Транскрипция (если есть)"]))
                                        top_viral_df = top_viral_df.copy()
                                        top_viral_df["Транскрипция (если есть)"] = top_viral_df["Ссылка на ролик"].map(
                                            lambda u: transcript_map.get(u) or top_viral_df.loc[top_viral_df["Ссылка на ролик"] == u, "Транскрипция (если есть)"].values[0]
                                        )
                                    except Exception as exc:
                                        st.markdown(f"""<div class="custom-warning fade-in-container"><i class="fa-solid fa-triangle-exclamation"></i> Не удалось получить транскрипцию ({type(exc).__name__}: {exc}). Анализ пойдёт без текста речи.</div>""", unsafe_allow_html=True)

                        debug_raw_text = None
                        debug_error_detail = None
                        with st.spinner("ИИ анализирует ролики и пишет сценарии..."):
                            result, debug_raw_text, debug_error_detail = run_ai_analysis(
                                blogger_url, product_brief, metrics_df, median_views, active_scenarios_count,
                                top_viral_df, active_provider_mode, active_base_url, active_model,
                                active_max_tokens, active_system_prompt, st.session_state.cfg_ai_key,
                            )

                        if debug_raw_text is not None or debug_error_detail is not None:
                            with st.expander("🔍 Сырой ответ модели / детали ошибки (для отладки)"):
                                if debug_error_detail: st.code(debug_error_detail, language="text")
                                if debug_raw_text is not None: st.code(debug_raw_text if debug_raw_text else "(модель вернула пустую строку)", language="text")

                        # Считаем сводную статистику по залётности для выгрузки и сохраняем последний
                        # результат анализа в сессии (включая бриф и данные роликов), чтобы кнопки
                        # «Обновить сценарии» и «Выгрузить» ниже могли им пользоваться даже после
                        # перезапуска скрипта при клике на сами кнопки.
                        viral_stats = compute_viral_summary_stats(metrics_df, active_viral_threshold)
                        st.session_state["last_analysis"] = {
                            "blogger_url": blogger_url,
                            "product_brief": product_brief,
                            "metrics_df": metrics_df,
                            "median_views": median_views,
                            "top_viral_df": top_viral_df,
                            "result": result,
                            "viral_stats": viral_stats,
                            "created": datetime.now().strftime("%d.%m.%Y %H:%M"),
                            "saved_id": None,
                        }

                        if result.get("scenarios") and not str(result.get("audience_summary", "")).startswith("Не удалось"):
                            saved_id = save_analysis(
                                manager=selected_manager, blogger_url=blogger_url, blogger_handle=extract_instagram_username(blogger_url),
                                data_source=active_data_source_mode, model_used=active_model, reels_count=valid_count,
                                median_views=median_views, viral_count=len(top_viral_df) if threshold_met else 0,
                                product_brief=product_brief, metrics_df=metrics_df, top_viral_df=top_viral_df, result=result,
                            )
                            if saved_id:
                                st.session_state["last_analysis"]["saved_id"] = saved_id
                                st.success(f"✅ Анализ сохранён в вашу историю (запись №{saved_id}) — смотрите на вкладке «Мои блогеры».")
                            else: st.warning("Не удалось сохранить анализ в историю — результат выше доступен только сейчас.")
                        else:
                            st.caption("Результат не сохранён в историю: ИИ не вернул готовых сценариев.")

        # --- Единый блок отображения последнего анализа: рендер результата + кнопки
        # «Обновить сценарии» (переписать без повторного сбора/транскрибации роликов) и «Выгрузить».
        # Работает и сразу после генерации, и после клика «Обновить сценарии» (через session_state). ---
        if st.session_state.get("last_analysis"):
            la = st.session_state["last_analysis"]
            render_full_result(la["metrics_df"], la["top_viral_df"], la["result"])

            st.markdown("<hr style='margin: 22px 0; opacity:0.2;'>", unsafe_allow_html=True)
            info_col, refresh_col, export_col = st.columns([3, 1, 1])
            with info_col:
                st.markdown(
                    f"📤 **Готово к выгрузке:** анализ @{extract_instagram_username(la['blogger_url'])} "
                    f"({la.get('created', '')}) — можно переписать сценарии или скопировать таблицу для Google Таблиц.",
                )
            with refresh_col:
                refresh_clicked = st.button("🔄 Обновить сценарии", use_container_width=True, key="refresh_scenarios_btn")
            with export_col:
                export_clicked = st.button("📤 Выгрузить", use_container_width=True, key="export_btn_persist", type="primary")

            if refresh_clicked:
                with st.spinner("ИИ переписывает сценарии — без повторного сбора и транскрибации роликов..."):
                    new_result, refresh_raw_text, refresh_error_detail = run_ai_analysis(
                        la["blogger_url"], la["product_brief"], la["metrics_df"], la["median_views"],
                        active_scenarios_count, la["top_viral_df"],
                        active_provider_mode, active_base_url, active_model, active_max_tokens,
                        active_system_prompt, st.session_state.cfg_ai_key, previous_result=la["result"],
                    )
                if refresh_raw_text is not None or refresh_error_detail is not None:
                    with st.expander("🔍 Сырой ответ модели / детали ошибки (обновление сценариев)"):
                        if refresh_error_detail: st.code(refresh_error_detail, language="text")
                        if refresh_raw_text is not None: st.code(refresh_raw_text if refresh_raw_text else "(модель вернула пустую строку)", language="text")

                if new_result.get("scenarios") and not str(new_result.get("audience_summary", "")).startswith("Не удалось"):
                    la["result"] = new_result
                    la["created"] = datetime.now().strftime("%d.%m.%Y %H:%M")
                    st.session_state["last_analysis"] = la
                    if la.get("saved_id"):
                        updated_ok = update_analysis_result(la["saved_id"], new_result)
                        if updated_ok:
                            st.success("✅ Сценарии обновлены — история анализа тоже обновлена.")
                        else:
                            st.warning("Сценарии обновлены, но не удалось обновить запись в истории.")
                    else:
                        st.success("✅ Сценарии обновлены.")
                    st.rerun()
                else:
                    st.error("Не удалось получить новые сценарии от ИИ — прежний результат оставлен без изменений.")

            if export_clicked:
                table_html, tsv_text = build_export_table(la["blogger_url"], la["viral_stats"], la["top_viral_df"], la["result"], all_reels_df=la["metrics_df"])
                open_export_dialog(table_html, tsv_text, {
                    "handle": extract_instagram_username(la["blogger_url"]),
                    "created": la.get("created", ""),
                    "key": "persist",
                })
