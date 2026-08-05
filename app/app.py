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
    "```json), пояснения до или после кода, обратные кавычки. Только чистый JSON на русском языке.\n"
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
    st.session_state.cfg_ai_base_url = load_setting_str("cfg_ai_base_url", "[https://openrouter.ai/api/v1](https://openrouter.ai/api/v1)")
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
        ("[instagram.com/reel/demo1](https://instagram.com/reel/demo1)", 210000, 15200, 810, 4100, "2026-05-02", "Примерка нескольких образов подряд под трендовый звук", ""),
        ("[instagram.com/reel/demo2](https://instagram.com/reel/demo2)", 45000, 1800, 90, 320, "2026-05-06", "Обзор ткани и посадки одного изделия", ""),
        ("[instagram.com/reel/demo3](https://instagram.com/reel/demo3)", 320000, 28000, 1450, 9200, "2026-05-10", "Юмористический скетч в примерочной с подругой", ""),
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
    url = f"[https://api.apify.com/v2/acts/](https://api.apify.com/v2/acts/){actor_path}/run-sync-get-dataset-items?token={token}"
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
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.rstrip().endswith("
http://googleusercontent.com/immersive_entry_chip/0
