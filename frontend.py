import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
import os
import io
import re
from datetime import datetime, timezone, timedelta
import time
import json
import html
from pathlib import Path
from collections import Counter

THEME_COLORS = {
    "ink": "#102033",
    "muted": "#5d6b7d",
    "line": "#d8e0e8",
    "surface": "#ffffff",
    "soft": "#f4f8fb",
    "primary": "#0f766e",
    "primary_dark": "#115e59",
    "accent": "#eab308",
    "accent_soft": "#fef3c7",
}

LOCAL_TIMEZONE = timezone(timedelta(hours=8), "MYT")

PLOTLY_COLORWAY = [
    THEME_COLORS["primary"],
    THEME_COLORS["accent"],
    THEME_COLORS["ink"],
    "#14b8a6",
    "#f59e0b",
]

PLOTLY_CONTINUOUS_SCALE = [
    [0.0, "#eef7f5"],
    [0.55, THEME_COLORS["primary"]],
    [1.0, THEME_COLORS["accent"]],
]


def apply_plotly_theme(fig, height=None):
    fig.update_layout(
        template="plotly_white",
        colorway=PLOTLY_COLORWAY,
        paper_bgcolor=THEME_COLORS["surface"],
        plot_bgcolor="#fbfdfe",
        font=dict(
            family="Inter, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
            color=THEME_COLORS["ink"],
        ),
        title_font=dict(color=THEME_COLORS["ink"], size=18),
        legend=dict(
            bgcolor="rgba(255,255,255,0)",
            bordercolor=THEME_COLORS["line"],
            font=dict(color=THEME_COLORS["muted"]),
        ),
        margin=dict(l=44, r=24, t=44, b=42),
    )
    fig.update_xaxes(
        gridcolor="#e8eef3",
        linecolor=THEME_COLORS["line"],
        tickfont=dict(color=THEME_COLORS["muted"]),
        title_font=dict(color=THEME_COLORS["ink"]),
    )
    fig.update_yaxes(
        gridcolor="#e8eef3",
        linecolor=THEME_COLORS["line"],
        tickfont=dict(color=THEME_COLORS["muted"]),
        title_font=dict(color=THEME_COLORS["ink"]),
    )
    if height:
        fig.update_layout(height=height)
    if fig.layout.title.text is None:
        fig.update_layout(title_text="")
    return fig

st.set_page_config(
    page_title="Protein Domain Finder",
    page_icon="https://cdn-icons-png.flaticon.com/512/2947/2947927.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------- CSS to match the clean design ----------
st.markdown("""
<style>
    .stApp {
        background: #ffffff;
    }
    .main-title {
        text-align: center;
        font-size: 2.8rem;
        font-weight: 700;
        color: #1e293b;
        margin-top: 1rem;
        margin-bottom: 0.2rem;
    }
    .subtitle {
        text-align: center;
        font-size: 1.2rem;
        color: #475569;
        margin-bottom: 2rem;
    }
    .input-card {
        background: white;
        border-radius: 20px;
        padding: 1.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        border: 1px solid #e2e8f0;
        margin-bottom: 1.5rem;
    }
    .input-card:empty,
    .ready-card:empty,
    .dashboard-card:empty {
        display: none;
    }
    .ready-card {
        background: #f8fafc;
        border-radius: 16px;
        padding: 1rem 1.5rem;
        margin-top: 1rem;
    }
    .bullet-list {
        padding-left: 1.2rem;
    }
    .bullet-list li {
        margin-bottom: 0.5rem;
    }
    .note-text {
        font-size: 0.9rem;
        color: #64748b;
        text-align: center;
        margin-top: 2rem;
    }
    .stButton > button,
    .stDownloadButton > button,
    .stFormSubmitButton > button {
        background: linear-gradient(135deg, #0f766e 0%, #115e59 100%);
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        border-radius: 40px;
        padding: 0.5rem 1.2rem;
        font-weight: 500;
        border: none;
        opacity: 1 !important;
    }
    .stButton > button:hover,
    .stDownloadButton > button:hover,
    .stFormSubmitButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }
    .stButton > button p,
    .stButton > button span,
    .stFormSubmitButton > button p,
    .stFormSubmitButton > button span,
    .stDownloadButton > button p,
    .stDownloadButton > button span {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        opacity: 1 !important;
        margin: 0 !important;
    }
    .stButton > button:disabled,
    .stDownloadButton > button:disabled,
    .stFormSubmitButton > button:disabled {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        opacity: 1 !important;
        background: #0f766e !important;
    }
    .stFormSubmitButton > button {
        background: linear-gradient(135deg, #0f766e 0%, #115e59 100%) !important;
        color: white !important;
        border-radius: 40px;
        padding: 0.5rem 1.2rem;
        font-weight: 500;
        border: none !important;
    }
    .stFormSubmitButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .stTextArea textarea {
        border-radius: 16px;
        border: 1px solid #cbd5e1;
        font-family: monospace;
        font-size: 0.9rem;
    }
    .top-bar {
        display: flex;
        justify-content: flex-end;
        align-items: center;
        padding: 0.5rem 1rem;
        background: white;
        border-bottom: 1px solid #e2e8f0;
        margin-bottom: 1rem;
    }
    .user-name {
        font-weight: 500;
        margin-right: 1rem;
    }
    .dashboard-card {
        background: #f8fafc;
        border-radius: 20px;
        padding: 1rem;
        text-align: center;
        border: 1px solid #e2e8f0;
    }
    .tooltip-hover {
        border-bottom: 1px dashed #0f766e;
        cursor: help;
    }
    div[data-testid="stAlert"] {
        overflow: visible !important;
    }
    div[data-testid="stAlert"] [data-testid="stMarkdownContainer"],
    div[data-testid="stAlert"] [data-testid="stMarkdownContainer"] p {
        color: #102033 !important;
        line-height: 1.5 !important;
        white-space: normal !important;
        overflow-wrap: anywhere !important;
        word-break: normal !important;
    }
</style>
""", unsafe_allow_html=True)

API_URL = os.getenv("API_URL", "http://localhost:8000")

# Ensure form submit buttons have white text on older Streamlit builds
st.markdown("""
<style>
    .stFormSubmitButton > button, .stFormSubmitButton > button * {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------- MODERN WEBSITE THEME OVERRIDES ----------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    :root {
        --ink: #102033;
        --muted: #5d6b7d;
        --line: #d8e0e8;
        --surface: #ffffff;
        --soft: #f4f8fb;
        --primary: #0f766e;
        --primary-dark: #115e59;
        --accent: #eab308;
    }

    html, body, [class*="css"] {
        font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        color: var(--ink);
    }

    .stApp {
        background: #ffffff !important;
    }

    .block-container {
        max-width: 1220px;
        padding-top: 0.9rem;
        padding-bottom: 3rem;
    }

    header[data-testid="stHeader"] {
        background: transparent;
    }

    div[data-testid="stToolbar"] {
        display: none;
    }

    section[data-testid="stSidebar"],
    div[data-testid="collapsedControl"] {
        display: none !important;
    }

    .site-hero {
        min-height: 330px;
        padding: clamp(1.4rem, 4vw, 3rem);
        border-radius: 8px;
        border: 1px solid rgba(216, 224, 232, 0.88);
        background:
            linear-gradient(120deg, rgba(7, 89, 83, 0.92), rgba(17, 94, 89, 0.70)),
            url("https://images.unsplash.com/photo-1559757148-5c350d0d3c56?auto=format&fit=crop&w=1600&q=80");
        background-size: cover;
        background-position: center;
        color: #ffffff;
        display: flex;
        align-items: center;
        margin-bottom: 1rem;
        box-shadow: 0 24px 70px rgba(24, 44, 64, 0.10);
    }

    .site-hero h1 {
        font-size: clamp(2.3rem, 5vw, 4.2rem);
        line-height: 1.02;
        font-weight: 800;
        color: #ffffff;
        margin: 0 0 0.8rem 0;
        letter-spacing: 0;
    }

    .site-hero p {
        color: rgba(255,255,255,0.88);
        max-width: 42rem;
        line-height: 1.7;
        font-size: 1.05rem;
        margin: 0;
    }

    .eyebrow {
        color: #fef3c7;
        font-size: 0.78rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 0.7rem;
    }

    .hero-stat-row {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.7rem;
        margin-top: 1.6rem;
        max-width: 46rem;
    }

    .hero-stat {
        border: 1px solid rgba(255,255,255,0.28);
        background: rgba(255,255,255,0.13);
        border-radius: 8px;
        padding: 0.85rem 0.95rem;
        backdrop-filter: blur(10px);
    }

    .hero-stat strong {
        display: block;
        font-size: 1.15rem;
        color: #ffffff;
    }

    .hero-stat span {
        color: rgba(255,255,255,0.78);
        font-size: 0.82rem;
    }

    .yt-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 1rem;
        border-bottom: 1px solid #e5e7eb;
        background: #ffffff;
        padding: 0.45rem 0 0.8rem 0;
        margin-bottom: 1rem;
    }

    .brand-row {
        display: flex;
        align-items: center;
    }

    .brand-mark {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 2.6rem;
        height: 2.6rem;
        border-radius: 999px;
        background: linear-gradient(135deg, rgba(15,118,110,0.92), rgba(234,179,8,0.78));
        margin-right: 0.7rem;
    }

    .brand-mark img {
        width: 2rem;
        height: 2rem;
        object-fit: contain;
    }

    .brand-title {
        font-weight: 800;
        font-size: 1.05rem;
        color: var(--ink);
    }

    .brand-subtitle,
    .user-chip {
        color: var(--muted);
        font-size: 0.84rem;
    }

    .user-chip {
        text-align: right;
    }

    .user-chip strong {
        display: block;
        color: var(--ink);
        font-size: 0.96rem;
    }

    .header-search {
        flex: 1;
        max-width: 34rem;
        border: 1px solid #d1d5db;
        border-radius: 999px;
        padding: 0.65rem 1rem;
        color: #64748b;
        background: #fafafa;
        font-size: 0.92rem;
    }

    .header-actions {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 0.55rem;
    }

    .profile-avatar {
        width: 2.55rem;
        height: 2.55rem;
        border-radius: 999px;
        object-fit: cover;
        border: 2px solid #e5e7eb;
    }

    .flat-panel {
        border: 0;
        background: transparent;
        box-shadow: none;
    }

    .main-title {
        text-align: left !important;
        font-size: clamp(2rem, 4vw, 3rem) !important;
        color: var(--ink) !important;
        margin-top: 1.2rem !important;
    }

    .subtitle {
        text-align: left !important;
        color: var(--muted) !important;
        margin-bottom: 1.2rem !important;
    }

    .input-card,
    .dashboard-card,
    .profile-summary {
        background: var(--surface) !important;
        border-radius: 8px !important;
        border: 1px solid var(--line) !important;
        box-shadow: 0 14px 36px rgba(16,32,51,0.07) !important;
    }

    .profile-summary {
        display: grid;
        grid-template-columns: auto minmax(0, 1fr);
        gap: 1rem;
        align-items: center;
        padding: 1rem;
        margin-bottom: 1rem;
    }

    .profile-summary img {
        width: 5.2rem;
        height: 5.2rem;
        object-fit: cover;
        border-radius: 999px;
        border: 3px solid #e5e7eb;
    }

    div[data-testid="stHeading"] h1,
    div[data-testid="stHeading"] h2,
    div[data-testid="stHeading"] h3,
    div[data-testid="stHeading"] h4,
    div[data-testid="stHeading"] p,
    div[data-testid="stMarkdownContainer"] h1,
    div[data-testid="stMarkdownContainer"] h2,
    div[data-testid="stMarkdownContainer"] h3,
    div[data-testid="stMarkdownContainer"] h4,
    div[data-testid="stMarkdownContainer"] > p:not([class]) > strong {
        color: var(--ink) !important;
        -webkit-text-fill-color: var(--ink) !important;
        opacity: 1 !important;
    }

    div[data-testid="stMarkdownContainer"] > p:not([class]),
    div[data-testid="stMarkdownContainer"] > ul li,
    div[data-testid="stMarkdownContainer"] > ol li {
        color: var(--muted) !important;
        -webkit-text-fill-color: var(--muted) !important;
        opacity: 1 !important;
    }

    div[data-testid="stMarkdownContainer"] > p:not([class]) a {
        color: var(--primary) !important;
        -webkit-text-fill-color: var(--primary) !important;
        font-weight: 700;
    }

    div[data-testid="stCaptionContainer"],
    div[data-testid="stCaptionContainer"] p,
    div[data-testid="stCaptionContainer"] span,
    div[data-testid="stCaptionContainer"] a {
        color: var(--muted) !important;
        -webkit-text-fill-color: var(--muted) !important;
        opacity: 1 !important;
    }

    div[data-testid="stCaptionContainer"] a {
        color: var(--primary) !important;
        -webkit-text-fill-color: var(--primary) !important;
        font-weight: 700;
    }

    .page-section-heading {
        color: var(--ink) !important;
        font-size: 1.55rem;
        font-weight: 850;
        line-height: 1.2;
        margin: 1.45rem 0 0.85rem 0;
    }

    .profile-detail {
        display: grid;
        gap: 0.75rem;
        padding-top: 0.3rem;
    }

    .profile-detail div {
        color: var(--muted) !important;
        font-size: 1rem;
        line-height: 1.5;
    }

    .profile-detail strong {
        color: var(--ink) !important;
        font-weight: 800;
    }

    div[data-testid="stMetric"] {
        background: #ffffff !important;
        border: 1px solid var(--line) !important;
        border-radius: 8px !important;
        padding: 0.85rem 1rem !important;
    }

    div[data-testid="stMetricLabel"],
    div[data-testid="stMetricLabel"] p,
    div[data-testid="stMetric"] label,
    div[data-testid="stMetric"] label p {
        color: var(--muted) !important;
        opacity: 1 !important;
        font-weight: 700 !important;
    }

    div[data-testid="stMetricValue"],
    div[data-testid="stMetricValue"] div {
        color: var(--ink) !important;
        opacity: 1 !important;
    }

    .ready-card {
        background: #eef7f5 !important;
        border-radius: 8px !important;
        border: 1px solid #cce7e2 !important;
    }

    .note-text {
        text-align: left !important;
        background: #fffbeb;
        border: 1px solid #fde68a;
        border-radius: 8px;
        padding: 0.85rem 1rem;
    }

    .stButton > button,
    .stDownloadButton > button,
    .stFormSubmitButton > button {
        background: var(--primary) !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        border-radius: 8px !important;
        padding: 0.6rem 1.05rem !important;
        font-weight: 700 !important;
        min-height: 2.8rem;
        transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
        opacity: 1 !important;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover,
    .stFormSubmitButton > button:hover {
        transform: translateY(-1px);
        background: var(--primary-dark) !important;
        box-shadow: 0 8px 22px rgba(15, 118, 110, 0.24) !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }

    .stButton > button p,
    .stButton > button span,
    .stDownloadButton > button p,
    .stDownloadButton > button span,
    .stFormSubmitButton > button p,
    .stFormSubmitButton > button span {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        opacity: 1 !important;
        margin: 0 !important;
    }

    .stTextArea textarea,
    .stTextInput input {
        border-radius: 8px !important;
        border: 1px solid #bfd0dc !important;
        background: #fbfdfe !important;
        color: var(--ink) !important;
        caret-color: var(--primary) !important;
    }

    .stTextArea textarea {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important;
        font-size: 0.9rem !important;
    }

    .stTextArea textarea::placeholder,
    .stTextInput input::placeholder {
        color: #738396 !important;
        opacity: 1 !important;
    }

    .stTextInput input:-webkit-autofill,
    .stTextInput input:-webkit-autofill:hover,
    .stTextInput input:-webkit-autofill:focus {
        -webkit-text-fill-color: var(--ink) !important;
        box-shadow: 0 0 0 1000px #fbfdfe inset !important;
    }

    .stTextInput label,
    .stTextInput label p,
    .stSelectbox label,
    .stSelectbox label p,
    .stCheckbox label,
    .stCheckbox label p,
    .stForm label,
    .stForm label p,
    .stRadio,
    .stRadio label,
    .stRadio label p,
    .stRadio label span,
    div[data-testid="stRadio"],
    div[data-testid="stRadio"] label,
    div[data-testid="stRadio"] label p,
    div[data-testid="stRadio"] label span,
    div[data-testid="stRadio"] [data-testid="stMarkdownContainer"],
    div[data-testid="stRadio"] [data-testid="stMarkdownContainer"] p,
    div[data-testid="stWidgetLabel"],
    div[data-testid="stWidgetLabel"] p {
        color: var(--ink) !important;
        -webkit-text-fill-color: var(--ink) !important;
        font-weight: 700 !important;
        opacity: 1 !important;
    }

    .stTextInput div[data-testid="stInputInstructions"],
    .stTextInput div[data-testid="stInputInstructions"] span,
    div[data-testid="stInputInstructions"],
    div[data-testid="stInputInstructions"] span {
        color: #64748b !important;
        opacity: 1 !important;
    }

    .stFormSubmitButton > button {
        background: var(--primary) !important;
        color: #ffffff !important;
        border: 0 !important;
        border-radius: 8px !important;
        min-height: 3rem !important;
        font-weight: 800 !important;
        box-shadow: 0 10px 24px rgba(15, 118, 110, 0.18) !important;
    }

    .stFormSubmitButton > button:hover {
        background: var(--primary-dark) !important;
        color: #ffffff !important;
        transform: translateY(-1px);
    }

    .st-key-forgot_password_button {
        text-align: right;
        margin-top: -0.3rem;
        margin-bottom: 0.8rem;
    }

    .st-key-forgot_password_button button,
    .st-key-back_to_login_button button,
    .st-key-didnt_get_code_button button {
        width: auto !important;
        min-height: auto !important;
        background: transparent !important;
        color: var(--primary) !important;
        -webkit-text-fill-color: var(--primary) !important;
        border: 0 !important;
        border-radius: 0 !important;
        padding: 0.15rem 0 !important;
        box-shadow: none !important;
        font-size: 0.95rem !important;
        font-weight: 700 !important;
    }

    .st-key-forgot_password_button button p,
    .st-key-forgot_password_button button span,
    .st-key-forgot_password_button button [data-testid="stMarkdownContainer"],
    .st-key-back_to_login_button button p,
    .st-key-back_to_login_button button span,
    .st-key-back_to_login_button button [data-testid="stMarkdownContainer"],
    .st-key-didnt_get_code_button button p,
    .st-key-didnt_get_code_button button span,
    .st-key-didnt_get_code_button button [data-testid="stMarkdownContainer"] {
        color: var(--primary) !important;
        -webkit-text-fill-color: var(--primary) !important;
        opacity: 1 !important;
        font-weight: 800 !important;
        margin: 0 !important;
    }

    .st-key-forgot_password_button button:hover,
    .st-key-back_to_login_button button:hover,
    .st-key-didnt_get_code_button button:hover {
        background: transparent !important;
        color: var(--primary-dark) !important;
        -webkit-text-fill-color: var(--primary-dark) !important;
        box-shadow: none !important;
        text-decoration: underline;
        transform: none;
    }

    .st-key-forgot_password_button button:hover p,
    .st-key-forgot_password_button button:hover span,
    .st-key-back_to_login_button button:hover p,
    .st-key-back_to_login_button button:hover span,
    .st-key-didnt_get_code_button button:hover p,
    .st-key-didnt_get_code_button button:hover span {
        color: var(--primary-dark) !important;
        -webkit-text-fill-color: var(--primary-dark) !important;
    }

    .auth-panel-title {
        text-align: center;
        color: var(--ink);
        font-size: 2.1rem;
        font-weight: 800;
        margin: 2.2rem 0 0.35rem 0;
    }

    .auth-panel-subtitle {
        text-align: center;
        color: var(--muted);
        margin: 0 0 1.35rem 0;
        font-size: 1rem;
        line-height: 1.6;
    }

    .stTabs [data-baseweb="tab"] p {
        color: var(--primary) !important;
        font-weight: 700 !important;
    }

    .stTabs [aria-selected="true"] p {
        color: var(--primary-dark) !important;
    }

    .section-title {
        margin: 0 0 0.45rem 0;
        font-size: 1.35rem;
        font-weight: 800;
        color: var(--ink);
    }

    .section-copy {
        color: var(--muted);
        margin-bottom: 1rem;
        line-height: 1.65;
    }

    div[data-testid="stExpander"] details {
        border-color: var(--line) !important;
        background: #ffffff !important;
    }

    div[data-testid="stExpander"] summary,
    div[data-testid="stExpander"] summary p,
    div[data-testid="stExpander"] summary span {
        color: var(--ink) !important;
        opacity: 1 !important;
    }

    div[data-testid="stExpander"] summary svg {
        color: var(--primary) !important;
        fill: currentColor !important;
        opacity: 1 !important;
    }

    .activity-card {
        background: #ffffff;
        border: 1px solid var(--line);
        border-left: 4px solid var(--primary);
        border-radius: 8px;
        padding: 0.9rem 1rem;
        margin-bottom: 0.75rem;
        color: var(--ink);
    }

    .activity-card strong {
        display: inline-block;
        color: var(--primary-dark) !important;
        font-weight: 800;
        margin-bottom: 0.35rem;
    }

    .activity-card code {
        display: inline-block;
        max-width: 100%;
        background: #eef7f5 !important;
        border: 1px solid #cce7e2;
        border-radius: 6px;
        color: var(--primary-dark) !important;
        font-size: 0.84rem;
        line-height: 1.55;
        padding: 0.2rem 0.42rem;
        white-space: normal;
        overflow-wrap: anywhere;
    }

    .tag {
        display: inline-block;
        background: #dff3ef;
        color: #0f5d56;
        padding: 0.18rem 0.5rem;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 700;
        margin-top: 0.35rem;
    }

    .info-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 1rem;
        margin: 1rem 0 1.2rem 0;
    }

    .info-card {
        background: #ffffff;
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 1rem;
        min-height: 9.5rem;
        box-shadow: 0 10px 26px rgba(16,32,51,0.05);
    }

    .info-card strong {
        display: block;
        color: var(--ink);
        font-size: 1rem;
        margin-bottom: 0.45rem;
    }

    .info-card span,
    .info-card p {
        color: var(--muted);
        font-size: 0.92rem;
        line-height: 1.55;
    }

    .field-primer {
        background: #f8fbfb;
        border: 1px solid var(--line);
        border-left: 4px solid var(--primary);
        border-radius: 8px;
        padding: 1rem 1.1rem;
        margin: 1rem 0 1.2rem 0;
        color: var(--muted);
        line-height: 1.65;
    }

    .field-primer strong {
        display: block;
        color: var(--ink);
        font-size: 1.02rem;
        margin-bottom: 0.35rem;
    }

    .feature-band {
        background:
            linear-gradient(120deg, rgba(15,118,110,0.92), rgba(16,32,51,0.88)),
            url("https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?auto=format&fit=crop&w=1400&q=80");
        background-size: cover;
        background-position: center;
        border-radius: 8px;
        padding: 1.1rem;
        color: #ffffff;
        margin: 1rem 0;
    }

    .feature-band .section-title,
    .feature-band strong {
        color: #ffffff;
    }

    .feature-band p {
        color: rgba(255,255,255,0.82);
        line-height: 1.6;
        margin-bottom: 0;
    }

    .comparison-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 1rem;
        margin: 1rem 0;
    }

    .comparison-card {
        background: #ffffff;
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 1rem;
        box-shadow: 0 10px 26px rgba(16,32,51,0.05);
    }

    .comparison-card strong {
        display: block;
        margin-bottom: 0.45rem;
    }

    .comparison-card span,
    .comparison-card li {
        color: var(--muted);
        line-height: 1.55;
        font-size: 0.92rem;
    }

    .comparison-result {
        border-radius: 8px;
        padding: 0.95rem 1rem;
        margin: 0.85rem 0;
        line-height: 1.55;
        overflow-wrap: anywhere;
        word-break: normal;
    }

    .comparison-result strong {
        display: block;
        margin-bottom: 0.25rem;
        color: var(--ink);
    }

    .comparison-result span {
        color: var(--ink);
    }

    .comparison-result.match {
        background: #ecfdf5;
        border: 1px solid #a7f3d0;
    }

    .comparison-result.no-match {
        background: #fffbeb;
        border: 1px solid #fde68a;
    }

    .knowledge-card {
        background: #ffffff;
        border: 1px solid var(--line);
        border-left: 4px solid var(--primary);
        border-radius: 8px;
        padding: 1rem 1.1rem;
        margin-bottom: 0.85rem;
        box-shadow: 0 10px 26px rgba(16,32,51,0.05);
    }

    .knowledge-card h4 {
        margin: 0 0 0.4rem 0;
        color: var(--ink);
        font-size: 1.05rem;
    }

    .knowledge-row {
        display: grid;
        grid-template-columns: 11rem minmax(0, 1fr);
        gap: 0.65rem;
        padding: 0.35rem 0;
        border-top: 1px solid #eef2f5;
    }

    .knowledge-label {
        color: var(--ink);
        font-weight: 700;
        font-size: 0.86rem;
    }

    .knowledge-value {
        color: var(--muted);
        font-size: 0.9rem;
        line-height: 1.5;
    }

    .explanation-card {
        background: #f8fbfb;
        border: 1px solid var(--line);
        border-left: 4px solid var(--primary);
        border-radius: 8px;
        padding: 1rem 1.1rem;
        margin: 0.8rem 0 1rem 0;
        color: var(--muted);
        line-height: 1.65;
    }

    .explanation-card strong {
        display: block;
        color: var(--ink);
        font-size: 1rem;
        margin-bottom: 0.35rem;
    }

    .explanation-card ul {
        margin: 0.4rem 0 0 1.1rem;
        padding: 0;
    }

    .explanation-card li {
        margin-bottom: 0.25rem;
    }

    .reliability-band {
        background: #102033;
        color: #ffffff;
        border-radius: 8px;
        padding: 1.2rem;
        margin: 1rem 0 1.2rem 0;
        border: 1px solid rgba(255,255,255,0.1);
    }

    .reliability-band p {
        color: rgba(255,255,255,0.76);
        margin-bottom: 0;
        line-height: 1.6;
    }

    .reliability-metrics {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.75rem;
        margin-top: 1rem;
    }

    .reliability-metric {
        background: rgba(255,255,255,0.08);
        border: 1px solid rgba(255,255,255,0.14);
        border-radius: 8px;
        padding: 0.85rem;
    }

    .reliability-metric strong {
        display: block;
        color: #ffffff;
        font-size: 1.25rem;
    }

    .reliability-metric span {
        color: rgba(255,255,255,0.72);
        font-size: 0.82rem;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0.4rem;
        border-bottom: 1px solid var(--line);
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 0.7rem 1rem;
        font-weight: 700;
    }

    .st-key-app_header {
        background: #ffffff;
        border-bottom: 1px solid #e2e8f0;
        padding: 1rem 1.25rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
        border-radius: 0 0 18px 18px;
    }

    .st-key-app_header div[data-testid="stHorizontalBlock"] {
        align-items: center;
        gap: 1rem;
        flex-wrap: wrap;
    }

    .site-brand {
        display: flex;
        align-items: center;
        gap: 0.85rem;
    }

    .site-brand-mark {
        width: 3.1rem;
        height: 3.1rem;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: 16px;
        background: #eef7f5;
        border: 1px solid #d1d5db;
    }

    .site-brand-mark img {
        width: 1.9rem;
        height: 1.9rem;
    }

    .site-brand strong {
        color: #102033;
        font-size: 1rem;
        line-height: 1.2;
    }

    .site-brand small {
        display: block;
        color: #64748b;
        font-size: 0.82rem;
        line-height: 1.25;
    }

    .st-key-app_header .stTextInput input {
        min-height: 3.3rem !important;
        border-radius: 999px !important;
        border: 1px solid #d1d5db !important;
        background: #f8fafc !important;
        padding: 0.75rem 1rem !important;
        color: #102033 !important;
        font-size: 0.96rem !important;
    }

    .st-key-app_header .stTextInput input::placeholder {
        color: #64748b !important;
        opacity: 1 !important;
    }

    .st-key-app_header .stFormSubmitButton button {
        min-height: 3.3rem !important;
        border-radius: 999px !important;
        padding: 0 1.25rem !important;
        font-weight: 800 !important;
        box-shadow: 0 8px 22px rgba(15, 118, 110, 0.18) !important;
        background: #0f766e !important;
        border: 1px solid #0f766e !important;
        color: #ffffff !important;
    }

    .st-key-app_header .stFormSubmitButton button:hover {
        background: #115e59 !important;
        border-color: #115e59 !important;
    }

    .header-nav-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.75rem;
        align-items: center;
        margin-top: 1rem;
    }

    .header-nav-row .stButton > button {
        min-height: 2.9rem !important;
        border-radius: 999px !important;
        padding: 0.7rem 1.2rem !important;
        background: #ffffff !important;
        color: #0f766e !important;
        border: 1px solid #c7e3db !important;
        box-shadow: none !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
    }

    .header-nav-row .stButton > button:hover {
        background: #effaf8 !important;
        color: #0d5e52 !important;
        border-color: #a8d9cf !important;
        box-shadow: none !important;
        transform: none !important;
    }

    .st-key-header_nav_home button,
    .st-key-header_nav_benchmark button,
    .st-key-header_nav_popular button,
    .st-key-header_nav_upload button,
    .st-key-header_nav_admin button {
        width: auto !important;
        min-width: auto !important;
        padding: 0.7rem 1.2rem !important;
        border-radius: 999px !important;
        background: #ffffff !important;
        border: 1px solid #c7e3db !important;
        color: #0f766e !important;
        font-size: 0.95rem !important;
        font-weight: 700 !important;
        box-shadow: none !important;
    }

    .st-key-header_nav_home button::before,
    .st-key-header_nav_benchmark button::before,
    .st-key-header_nav_popular button::before,
    .st-key-header_nav_upload button::before,
    .st-key-header_nav_admin button::before {
        display: none !important;
    }

    .st-key-header_nav_home button:hover,
    .st-key-header_nav_benchmark button:hover,
    .st-key-header_nav_popular button:hover,
    .st-key-header_nav_upload button:hover,
    .st-key-header_nav_admin button:hover {
        background: #effaf8 !important;
        border-color: #a8d9cf !important;
        color: #0d5e52 !important;
        box-shadow: none !important;
        transform: none !important;
    }

    .st-key-header_sidebar_toggle button {
        min-width: 2.8rem !important;
        min-height: 2.8rem !important;
        width: 2.8rem !important;
        height: 2.8rem !important;
        border-radius: 999px !important;
        background: #effaf8 !important;
        color: #0f766e !important;
        border: 1px solid #c7e3db !important;
        box-shadow: none !important;
        padding: 0 !important;
        font-size: 0.95rem !important;
    }

    .st-key-header_sidebar_toggle button::before {
        display: none !important;
    }

    .st-key-header_logo_menu button,
    .st-key-sidebar_close button,
    .st-key-header_profile button,
    .st-key-header_profile_dropdown button,
    .st-key-header_notification button {
        background: none !important;
        border: none !important;
        box-shadow: none !important;
    }

    .st-key-app_header .stImage {
        display: flex;
        justify-content: center;
        min-height: 2.25rem;
        align-items: center;
    }

    .st-key-header_popular button,
    .st-key-header_benchmark button,
    .st-key-header_upload button {
        min-height: 3.5rem !important;
        color: #ffffff !important;
        border-radius: 8px !important;
        font-weight: 800 !important;
        line-height: 1.45 !important;
        border: 0 !important;
    }

    .st-key-youtube_sidebar {
        position: fixed;
        top: 0;
        left: 0;
        bottom: 0;
        width: 16rem;
        overflow-y: auto;
        z-index: 999999;
        background: #0f0f0f;
        color: #f1f1f1;
        padding: 0.9rem 0.8rem 1.4rem 0.8rem;
        border-right: 1px solid #303030;
        box-shadow: 18px 0 45px rgba(0,0,0,0.22);
    }

    .st-key-youtube_sidebar [data-testid="stMarkdownContainer"] p,
    .st-key-youtube_sidebar [data-testid="stMarkdownContainer"] h3 {
        color: #f1f1f1 !important;
    }

    .st-key-youtube_sidebar .stCaptionContainer,
    .st-key-youtube_sidebar small {
        color: #aaa !important;
    }

    .st-key-youtube_sidebar hr {
        border-color: #303030;
        margin: 0.7rem 0;
    }

    .st-key-youtube_sidebar .stButton > button {
        background: transparent !important;
        color: #f1f1f1 !important;
        border: 0 !important;
        border-radius: 10px !important;
        box-shadow: none !important;
        justify-content: flex-start;
        min-height: 2.85rem;
        font-weight: 700 !important;
        padding-left: 0.85rem !important;
    }

    .st-key-youtube_sidebar .stButton > button:hover {
        background: #272727 !important;
        transform: none !important;
        box-shadow: none !important;
    }

    .st-key-youtube_sidebar .stImage img {
        border-radius: 999px;
    }

    .st-key-youtube_sidebar {
        top: 0 !important;
        left: 0 !important;
        bottom: 0 !important;
        width: 17rem !important;
        background: #ffffff !important;
        color: var(--ink) !important;
        border-right: 1px solid #e5e7eb !important;
        padding: 0.9rem 0.8rem 1.1rem 0.8rem !important;
        box-shadow: 18px 0 42px rgba(16,32,51,0.14) !important;
    }

    .st-key-youtube_sidebar [data-testid="stVerticalBlock"] {
        gap: 0.28rem !important;
    }

    .st-key-youtube_sidebar [data-testid="stMarkdownContainer"] p,
    .st-key-youtube_sidebar [data-testid="stMarkdownContainer"] h3 {
        color: var(--ink) !important;
        -webkit-text-fill-color: var(--ink) !important;
    }

    .sidebar-brand {
        display: flex;
        align-items: center;
        gap: 0.65rem;
        min-height: 2.8rem;
        padding-left: 0.15rem;
    }

    .sidebar-brand img {
        width: 2.1rem;
        height: 2.1rem;
        object-fit: contain;
        border-radius: 8px;
        background: #eef7f5;
        border: 1px solid #cce7e2;
        padding: 0.22rem;
    }

    .sidebar-brand strong {
        color: var(--ink);
        font-size: 0.95rem;
        line-height: 1.2;
    }

    .sidebar-section-label {
        color: #64748b;
        font-size: 0.74rem;
        font-weight: 850;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin: 1.1rem 0 0.35rem 0.55rem;
    }

    .st-key-youtube_sidebar .stButton > button {
        min-height: 2.65rem !important;
        border-radius: 8px !important;
        padding: 0.55rem 0.75rem !important;
        background: transparent !important;
        color: var(--ink) !important;
        border: 0 !important;
        box-shadow: none !important;
        justify-content: flex-start !important;
        text-align: left !important;
        font-size: 0.94rem !important;
        font-weight: 700 !important;
        white-space: nowrap !important;
    }

    .st-key-youtube_sidebar .stButton > button p,
    .st-key-youtube_sidebar .stButton > button span,
    .st-key-youtube_sidebar .stButton > button [data-testid="stMarkdownContainer"] {
        color: var(--ink) !important;
        -webkit-text-fill-color: var(--ink) !important;
        display: block !important;
        opacity: 1 !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }

    .st-key-youtube_sidebar .stButton > button:hover {
        background: #f1f5f9 !important;
        color: var(--primary-dark) !important;
        transform: none !important;
        box-shadow: none !important;
    }

    .st-key-youtube_sidebar .stButton > button:hover p,
    .st-key-youtube_sidebar .stButton > button:hover span {
        color: var(--primary-dark) !important;
        -webkit-text-fill-color: var(--primary-dark) !important;
    }

    .st-key-sidebar_close button,
    .st-key-header_sidebar_toggle button {
        width: 2.75rem !important;
        min-width: 2.75rem !important;
        height: 2.7rem !important;
        min-height: 2.7rem !important;
        padding: 0 !important;
        border-radius: 8px !important;
        color: transparent !important;
        font-size: 0 !important;
        border: 1px solid #cce7e2 !important;
        background:
            linear-gradient(var(--primary), var(--primary)) center 36% / 1.2rem 2px no-repeat,
            linear-gradient(var(--primary), var(--primary)) center 50% / 1.2rem 2px no-repeat,
            linear-gradient(var(--primary), var(--primary)) center 64% / 1.2rem 2px no-repeat,
            #ffffff !important;
        box-shadow: none !important;
    }

    .st-key-sidebar_close button {
        background:
            linear-gradient(45deg, var(--primary) 0 0) center / 1.3rem 2px no-repeat,
            linear-gradient(-45deg, var(--primary) 0 0) center / 1.3rem 2px no-repeat,
            #ffffff !important;
    }

    .st-key-sidebar_close button p,
    .st-key-header_sidebar_toggle button p {
        display: none !important;
    }

    .st-key-header_sidebar_toggle button:hover {
        background:
            linear-gradient(#ffffff, #ffffff) center 36% / 1.2rem 2px no-repeat,
            linear-gradient(#ffffff, #ffffff) center 50% / 1.2rem 2px no-repeat,
            linear-gradient(#ffffff, #ffffff) center 64% / 1.2rem 2px no-repeat,
            var(--primary) !important;
        transform: none !important;
        box-shadow: none !important;
    }

    .st-key-sidebar_close button:hover {
        background:
            linear-gradient(45deg, #ffffff 0 0) center / 1.3rem 2px no-repeat,
            linear-gradient(-45deg, #ffffff 0 0) center / 1.3rem 2px no-repeat,
            var(--primary) !important;
    }

    .sidebar-footer {
        margin-top: 1.2rem;
        border-top: 1px solid #e5e7eb;
        padding: 1rem 0.55rem 0 0.55rem;
    }

    .sidebar-footer img {
        width: 2.4rem;
        height: 2.4rem;
        border-radius: 999px;
        object-fit: cover;
        display: block;
        margin-bottom: 0.55rem;
    }

    .sidebar-footer strong {
        display: block;
        color: var(--ink);
        font-size: 0.92rem;
        line-height: 1.25;
        overflow-wrap: anywhere;
    }

    .sidebar-footer span {
        display: block;
        color: var(--muted);
        font-size: 0.78rem;
        line-height: 1.35;
        overflow-wrap: anywhere;
    }

    .st-key-header_logo_menu button,
    .st-key-header_profile_dropdown button,
    .st-key-header_notification button,
    .st-key-header_popular button,
    .st-key-header_benchmark button,
    .st-key-header_upload button {
        width: 3.6rem !important;
        min-width: 3.6rem !important;
        height: 3rem !important;
        min-height: 3rem !important;
        padding: 0 !important;
        border-radius: 8px !important;
        background: var(--primary) !important;
        background-image: none !important;
        color: transparent !important;
        font-size: 0 !important;
        box-shadow: 0 8px 20px rgba(15, 118, 110, 0.18) !important;
        position: relative !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

    .st-key-header_home_button button {
        width: 4.25rem !important;
        min-width: 4.25rem !important;
        height: 3rem !important;
        min-height: 3rem !important;
        padding: 0 !important;
        border-radius: 8px !important;
        background: var(--primary) !important;
        color: transparent !important;
        font-size: 0 !important;
        box-shadow: 0 8px 20px rgba(15, 118, 110, 0.18) !important;
        position: relative !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

    .st-key-header_logo_menu button p,
    .st-key-header_home_button button p,
    .st-key-header_profile_dropdown button p,
    .st-key-header_notification button p,
    .st-key-header_profile_dropdown button svg,
    .st-key-header_notification button svg,
    .st-key-header_popular button p,
    .st-key-header_benchmark button p,
    .st-key-header_upload button p {
        display: none !important;
    }

    .st-key-header_home_button button::before {
        content: none !important;
    }

    .st-key-header_logo_menu button::before,
    .st-key-header_profile_dropdown button::before,
    .st-key-header_notification button::before,
    .st-key-header_popular button::before,
    .st-key-header_benchmark button::before,
    .st-key-header_upload button::before {
        color: #ffffff !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 2rem;
        height: 2rem;
        border-radius: 999px;
        background-color: #ffffff;
    }

    .st-key-header_logo_menu button::before {
        content: "";
        background:
            linear-gradient(#ffffff, #ffffff) center 34% / 1.35rem 2px no-repeat,
            linear-gradient(#ffffff, #ffffff) center 50% / 1.35rem 2px no-repeat,
            linear-gradient(#ffffff, #ffffff) center 66% / 1.35rem 2px no-repeat;
    }

    .st-key-header_home_button button::before {
        content: "" !important;
        display: block !important;
        width: 3rem;
        height: 2.3rem;
        border-radius: 0;
        background-color: transparent;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 96 72'%3E%3Crect x='5' y='7' width='72' height='50' rx='14' fill='%23ffffff'/%3E%3Cpath d='M21 41c9-18 27 18 36 0M21 30c9-18 27 18 36 0' fill='none' stroke='%230f766e' stroke-width='5' stroke-linecap='round'/%3E%3Ccircle cx='24' cy='41' r='4' fill='%23eab308'/%3E%3Ccircle cx='37' cy='30' r='4' fill='%23eab308'/%3E%3Ccircle cx='51' cy='41' r='4' fill='%23eab308'/%3E%3Ccircle cx='64' cy='30' r='4' fill='%23eab308'/%3E%3Ccircle cx='63' cy='45' r='12' fill='none' stroke='%23102033' stroke-width='5'/%3E%3Cpath d='M72 54l12 12' stroke='%23102033' stroke-width='6' stroke-linecap='round'/%3E%3C/svg%3E");
        background-repeat: no-repeat;
        background-position: center;
        background-size: contain;
    }

    .st-key-header_profile_dropdown button::before {
        content: "";
        -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M20 21a8 8 0 0 0-16 0'/%3E%3Ccircle cx='12' cy='7' r='4'/%3E%3C/svg%3E") center / 1.55rem 1.55rem no-repeat;
        mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M20 21a8 8 0 0 0-16 0'/%3E%3Ccircle cx='12' cy='7' r='4'/%3E%3C/svg%3E") center / 1.55rem 1.55rem no-repeat;
    }

    .st-key-header_notification button::before {
        content: "";
        -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M10.3 21a2 2 0 0 0 3.4 0'/%3E%3Cpath d='M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9'/%3E%3C/svg%3E") center / 1.5rem 1.5rem no-repeat;
        mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M10.3 21a2 2 0 0 0 3.4 0'/%3E%3Cpath d='M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9'/%3E%3C/svg%3E") center / 1.5rem 1.5rem no-repeat;
    }

    .st-key-header_popular button::before {
        content: "";
        -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M3 17l6-6 4 4 8-8'/%3E%3Cpath d='M14 7h7v7'/%3E%3C/svg%3E") center / 1.55rem 1.55rem no-repeat;
        mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M3 17l6-6 4 4 8-8'/%3E%3Cpath d='M14 7h7v7'/%3E%3C/svg%3E") center / 1.55rem 1.55rem no-repeat;
    }

    .st-key-header_benchmark button::before {
        content: "";
        -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M4 19V5'/%3E%3Cpath d='M4 19h16'/%3E%3Cpath d='M8 16v-5'/%3E%3Cpath d='M12 16V8'/%3E%3Cpath d='M16 16v-7'/%3E%3Cpath d='M20 16v-3'/%3E%3C/svg%3E") center / 1.55rem 1.55rem no-repeat;
        mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M4 19V5'/%3E%3Cpath d='M4 19h16'/%3E%3Cpath d='M8 16v-5'/%3E%3Cpath d='M12 16V8'/%3E%3Cpath d='M16 16v-7'/%3E%3Cpath d='M20 16v-3'/%3E%3C/svg%3E") center / 1.55rem 1.55rem no-repeat;
    }

    .st-key-header_upload button::before {
        content: "";
        -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M12 3v12'/%3E%3Cpath d='M7 8l5-5 5 5'/%3E%3Cpath d='M5 21h14'/%3E%3C/svg%3E") center / 1.55rem 1.55rem no-repeat;
        mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M12 3v12'/%3E%3Cpath d='M7 8l5-5 5 5'/%3E%3Cpath d='M5 21h14'/%3E%3C/svg%3E") center / 1.55rem 1.55rem no-repeat;
    }

    .st-key-app_header {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 0.8rem 0.9rem 0.7rem 0.9rem;
        margin: 0 0 1.2rem 0;
        box-shadow: 0 12px 30px rgba(16,32,51,0.06);
    }

    .st-key-app_header div[data-testid="stHorizontalBlock"] {
        align-items: center;
        gap: 0.7rem;
    }

    .st-key-app_header [data-testid="stMarkdownContainer"] {
        margin: 0 !important;
    }

    .site-brand {
        display: flex;
        align-items: center;
        gap: 0.7rem;
        min-height: 2.7rem;
        height: 2.7rem;
        overflow: hidden;
    }

    .site-brand-mark {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 2.7rem;
        height: 2.7rem;
        border-radius: 8px;
        background: #eef7f5;
        border: 1px solid #cce7e2;
        overflow: hidden;
        flex: 0 0 auto;
    }

    .site-brand-mark img {
        width: 2.05rem;
        height: 2.05rem;
        object-fit: contain;
        display: block;
    }

    .site-brand strong {
        display: block;
        color: var(--ink);
        font-size: 0.98rem;
        line-height: 1.2;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .site-brand small {
        display: block;
        color: var(--muted);
        font-size: 0.76rem;
        line-height: 1.25;
        white-space: nowrap;
    }

    .header-nav-row {
        display: none;
    }

    .st-key-app_header div[data-testid="stHorizontalBlock"]:has(.st-key-header_nav_home) {
        align-items: stretch !important;
        justify-content: flex-start !important;
        flex-wrap: nowrap !important;
        gap: 0.55rem !important;
        width: 100% !important;
        max-width: 100% !important;
        margin-top: 0.45rem !important;
        overflow-x: auto !important;
        overflow-y: hidden !important;
        scrollbar-width: thin;
    }

    .st-key-app_header div[data-testid="stHorizontalBlock"]:has(.st-key-header_nav_home) > div[data-testid="column"] {
        width: auto !important;
        min-width: 0 !important;
    }

    .st-key-app_header div[data-testid="stHorizontalBlock"]:has(.st-key-header_nav_home) > div[data-testid="column"]:has(.st-key-header_nav_home) {
        flex: 0 0 7.25rem !important;
    }

    .st-key-app_header div[data-testid="stHorizontalBlock"]:has(.st-key-header_nav_home) > div[data-testid="column"]:has(.st-key-header_nav_benchmark) {
        flex: 0 0 9.6rem !important;
    }

    .st-key-app_header div[data-testid="stHorizontalBlock"]:has(.st-key-header_nav_home) > div[data-testid="column"]:has(.st-key-header_nav_popular) {
        flex: 0 0 10.35rem !important;
    }

    .st-key-app_header div[data-testid="stHorizontalBlock"]:has(.st-key-header_nav_home) > div[data-testid="column"]:has(.st-key-header_nav_upload),
    .st-key-app_header div[data-testid="stHorizontalBlock"]:has(.st-key-header_nav_home) > div[data-testid="column"]:has(.st-key-header_nav_admin) {
        flex: 0 0 7.25rem !important;
    }

    .st-key-app_header div[data-testid="stHorizontalBlock"]:has(.st-key-header_nav_home) > div[data-testid="column"]:not(:has(.st-key-header_nav_home)):not(:has(.st-key-header_nav_benchmark)):not(:has(.st-key-header_nav_popular)):not(:has(.st-key-header_nav_upload)):not(:has(.st-key-header_nav_admin)) {
        flex: 1 1 auto !important;
        min-width: 0 !important;
    }

    .st-key-header_nav_home button,
    .st-key-header_nav_benchmark button,
    .st-key-header_nav_popular button,
    .st-key-header_nav_upload button,
    .st-key-header_nav_admin button {
        width: 100% !important;
        min-width: 0 !important;
        max-width: 100% !important;
        min-height: 3rem !important;
        padding: 0.55rem 0.8rem !important;
        border-radius: 12px !important;
        background: #ffffff !important;
        color: var(--ink) !important;
        -webkit-text-fill-color: var(--ink) !important;
        border: 1px solid #d2d8de !important;
        box-shadow: none !important;
        font-size: 0.95rem !important;
        font-weight: 700 !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        gap: 0.55rem !important;
        box-sizing: border-box !important;
        position: relative !important;
        text-align: left !important;
        padding-left: 2.55rem !important;
        padding-right: 0.95rem !important;
    }

    .st-key-header_nav_home button [data-testid="stMarkdownContainer"],
    .st-key-header_nav_benchmark button [data-testid="stMarkdownContainer"],
    .st-key-header_nav_popular button [data-testid="stMarkdownContainer"],
    .st-key-header_nav_upload button [data-testid="stMarkdownContainer"],
    .st-key-header_nav_admin button [data-testid="stMarkdownContainer"] {
        width: auto !important;
        min-width: 0 !important;
        flex: 0 1 auto !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        max-width: 100% !important;
        overflow: hidden !important;
    }

    .st-key-header_nav_home button p,
    .st-key-header_nav_benchmark button p,
    .st-key-header_nav_popular button p,
    .st-key-header_nav_upload button p,
    .st-key-header_nav_admin button p,
    .st-key-header_nav_home button span,
    .st-key-header_nav_benchmark button span,
    .st-key-header_nav_popular button span,
    .st-key-header_nav_upload button span,
    .st-key-header_nav_admin button span,
    .st-key-header_nav_home button div,
    .st-key-header_nav_benchmark button div,
    .st-key-header_nav_popular button div,
    .st-key-header_nav_upload button div,
    .st-key-header_nav_admin button div,
    .st-key-header_nav_home button *,
    .st-key-header_nav_benchmark button *,
    .st-key-header_nav_popular button *,
    .st-key-header_nav_upload button *,
    .st-key-header_nav_admin button * {
        color: var(--ink) !important;
        -webkit-text-fill-color: var(--ink) !important;
        opacity: 1 !important;
        font-size: 0.95rem !important;
        font-weight: 700 !important;
        margin: 0 !important;
        padding: 0 !important;
        text-overflow: ellipsis !important;
    }

    .st-key-header_nav_home button::before,
    .st-key-header_nav_benchmark button::before,
    .st-key-header_nav_popular button::before,
    .st-key-header_nav_upload button::before,
    .st-key-header_nav_admin button::before {
        content: "" !important;
        display: inline-flex !important;
        width: 1.2rem !important;
        height: 1.2rem !important;
        min-width: 1.2rem !important;
        border-radius: 999px !important;
        align-items: center !important;
        justify-content: center !important;
        background-color: #0f766e !important;
        mask-size: contain !important;
        -webkit-mask-size: contain !important;
        mask-repeat: no-repeat !important;
        -webkit-mask-repeat: no-repeat !important;
        mask-position: center !important;
        -webkit-mask-position: center !important;
        position: absolute !important;
        left: 0.9rem !important;
        top: 50% !important;
        transform: translateY(-50%) !important;
    }

    .st-key-header_nav_home button::before {
        -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M3 11l9-8 9 8M5 10v10h14V10M9 20v-6h6v6' fill='none' stroke='black' stroke-width='2.3' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") !important;
        mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M3 11l9-8 9 8M5 10v10h14V10M9 20v-6h6v6' fill='none' stroke='black' stroke-width='2.3' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") !important;
    }

    .st-key-header_nav_benchmark button::before {
        -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M4 19V5h16M4 19h16M8 16v-5M12 16V8M16 16v-7M20 16v-3' fill='none' stroke='black' stroke-width='2.3' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") !important;
        mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M4 19V5h16M4 19h16M8 16v-5M12 16V8M16 16v-7M20 16v-3' fill='none' stroke='black' stroke-width='2.3' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") !important;
    }

    .st-key-header_nav_popular button::before {
        -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M3 17l6-6 4 4 8-8M14 7h7v7' fill='none' stroke='black' stroke-width='2.3' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") !important;
        mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M3 17l6-6 4 4 8-8M14 7h7v7' fill='none' stroke='black' stroke-width='2.3' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") !important;
    }

    .st-key-header_nav_upload button::before {
        -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M12 3v12M7 8l5-5 5 5M5 21h14' fill='none' stroke='black' stroke-width='2.3' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") !important;
        mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M12 3v12M7 8l5-5 5 5M5 21h14' fill='none' stroke='black' stroke-width='2.3' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") !important;
    }

    .st-key-header_nav_admin button::before {
        -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75' fill='none' stroke='black' stroke-width='2.3' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") !important;
        mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75' fill='none' stroke='black' stroke-width='2.3' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") !important;
    }

    .st-key-header_nav_home button::before {
        -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M3 11l9-8 9 8'/%3E%3Cpath d='M5 10v10h14V10'/%3E%3Cpath d='M9 20v-6h6v6'/%3E%3C/svg%3E") center / contain no-repeat;
        mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M3 11l9-8 9 8'/%3E%3Cpath d='M5 10v10h14V10'/%3E%3Cpath d='M9 20v-6h6v6'/%3E%3C/svg%3E") center / contain no-repeat;
    }

    .st-key-header_nav_benchmark button::before {
        -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M4 19V5'/%3E%3Cpath d='M4 19h16'/%3E%3Cpath d='M8 16v-5'/%3E%3Cpath d='M12 16V8'/%3E%3Cpath d='M16 16v-7'/%3E%3Cpath d='M20 16v-3'/%3E%3C/svg%3E") center / contain no-repeat;
        mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M4 19V5'/%3E%3Cpath d='M4 19h16'/%3E%3Cpath d='M8 16v-5'/%3E%3Cpath d='M12 16V8'/%3E%3Cpath d='M16 16v-7'/%3E%3Cpath d='M20 16v-3'/%3E%3C/svg%3E") center / contain no-repeat;
    }

    .st-key-header_nav_popular button::before {
        -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M3 17l6-6 4 4 8-8'/%3E%3Cpath d='M14 7h7v7'/%3E%3C/svg%3E") center / contain no-repeat;
        mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M3 17l6-6 4 4 8-8'/%3E%3Cpath d='M14 7h7v7'/%3E%3C/svg%3E") center / contain no-repeat;
    }

    .st-key-header_nav_upload button::before {
        -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M12 3v12'/%3E%3Cpath d='M7 8l5-5 5 5'/%3E%3Cpath d='M5 21h14'/%3E%3C/svg%3E") center / contain no-repeat;
        mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M12 3v12'/%3E%3Cpath d='M7 8l5-5 5 5'/%3E%3Cpath d='M5 21h14'/%3E%3C/svg%3E") center / contain no-repeat;
    }

    .st-key-header_nav_admin button::before {
        -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2'/%3E%3Ccircle cx='9' cy='7' r='4'/%3E%3Cpath d='M22 21v-2a4 4 0 0 0-3-3.87'/%3E%3Cpath d='M16 3.13a4 4 0 0 1 0 7.75'/%3E%3C/svg%3E") center / contain no-repeat;
        mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2'/%3E%3Ccircle cx='9' cy='7' r='4'/%3E%3Cpath d='M22 21v-2a4 4 0 0 0-3-3.87'/%3E%3Cpath d='M16 3.13a4 4 0 0 1 0 7.75'/%3E%3C/svg%3E") center / contain no-repeat;
    }

    .st-key-header_nav_home button p,
    .st-key-header_nav_benchmark button p,
    .st-key-header_nav_popular button p,
    .st-key-header_nav_upload button p,
    .st-key-header_nav_admin button p,
    .st-key-app_header .stFormSubmitButton button p,
    .st-key-header_account_menu button p {
        white-space: nowrap !important;
        overflow-wrap: normal !important;
        word-break: keep-all !important;
        line-height: 1.2 !important;
    }

    .st-key-header_nav_home button:hover,
    .st-key-header_nav_benchmark button:hover,
    .st-key-header_nav_popular button:hover,
    .st-key-header_nav_upload button:hover,
    .st-key-header_nav_admin button:hover {
        background: #eef7f5 !important;
        color: var(--primary-dark) !important;
        border-color: #cce7e2 !important;
        transform: none !important;
        box-shadow: none !important;
    }

    .st-key-app_header form {
        margin: 0 !important;
    }

    .st-key-app_header .stTextInput input {
        min-height: 2.7rem !important;
        border-radius: 8px !important;
        background: #f8fafc !important;
        border: 1px solid #cbd5e1 !important;
        color: var(--ink) !important;
        font-size: 0.95rem !important;
    }

    .st-key-app_header .stTextInput input::placeholder {
        color: #64748b !important;
        opacity: 1 !important;
    }

    .st-key-app_header .stTextInput input:focus {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 3px rgba(15,118,110,0.12) !important;
    }

    .st-key-app_header .stFormSubmitButton button,
    .st-key-header_account_menu button {
        min-height: 2.7rem !important;
        border-radius: 8px !important;
        padding: 0.45rem 0.8rem !important;
        font-size: 0.9rem !important;
        font-weight: 800 !important;
        box-shadow: none !important;
        transform: none !important;
        white-space: nowrap !important;
    }

    .st-key-app_header .stFormSubmitButton button {
        background: var(--primary) !important;
        color: #ffffff !important;
        border: 1px solid var(--primary) !important;
    }

    .st-key-app_header .stFormSubmitButton button p {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }

    .st-key-header_account_menu button {
        background: #ffffff !important;
        color: var(--primary-dark) !important;
        border: 1px solid #cce7e2 !important;
    }

    .st-key-header_account_menu button p,
    .st-key-header_account_menu button svg {
        color: var(--primary-dark) !important;
        -webkit-text-fill-color: var(--primary-dark) !important;
    }

    .st-key-app_header .stFormSubmitButton button:hover,
    .st-key-header_account_menu button:hover {
        background: var(--primary-dark) !important;
        color: #ffffff !important;
        border-color: var(--primary-dark) !important;
    }

    .st-key-app_header .stFormSubmitButton button:hover p,
    .st-key-header_account_menu button:hover p,
    .st-key-header_account_menu button:hover svg {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }

    .st-key-admin_refresh_dashboard button,
    .st-key-admin_open_benchmark button,
    .st-key-admin_open_popular button,
    .st-key-admin_open_profile button,
    .st-key-admin_delete_selected_user button,
    .st-key-admin-delete-selected-user button {
        background: var(--primary) !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        border-color: var(--primary) !important;
    }

    .st-key-admin_refresh_dashboard button p,
    .st-key-admin_refresh_dashboard button span,
    .st-key-admin_refresh_dashboard button [data-testid="stMarkdownContainer"],
    .st-key-admin_refresh_dashboard button [data-testid="stMarkdownContainer"] > p,
    .st-key-admin-refresh-dashboard button p,
    .st-key-admin-refresh-dashboard button span,
    .st-key-admin-refresh-dashboard button [data-testid="stMarkdownContainer"],
    .st-key-admin-refresh-dashboard button [data-testid="stMarkdownContainer"] > p,
    .st-key-admin_open_benchmark button p,
    .st-key-admin_open_benchmark button span,
    .st-key-admin_open_benchmark button [data-testid="stMarkdownContainer"],
    .st-key-admin_open_benchmark button [data-testid="stMarkdownContainer"] > p,
    .st-key-admin-open-benchmark button p,
    .st-key-admin-open-benchmark button span,
    .st-key-admin-open-benchmark button [data-testid="stMarkdownContainer"],
    .st-key-admin-open-benchmark button [data-testid="stMarkdownContainer"] > p,
    .st-key-admin_open_popular button p,
    .st-key-admin_open_popular button span,
    .st-key-admin_open_popular button [data-testid="stMarkdownContainer"],
    .st-key-admin_open_popular button [data-testid="stMarkdownContainer"] > p,
    .st-key-admin-open-popular button p,
    .st-key-admin-open-popular button span,
    .st-key-admin-open-popular button [data-testid="stMarkdownContainer"],
    .st-key-admin-open-popular button [data-testid="stMarkdownContainer"] > p,
    .st-key-admin_open_profile button p,
    .st-key-admin_open_profile button span,
    .st-key-admin_open_profile button [data-testid="stMarkdownContainer"],
    .st-key-admin_open_profile button [data-testid="stMarkdownContainer"] > p,
    .st-key-admin-open-profile button p,
    .st-key-admin-open-profile button span,
    .st-key-admin-open-profile button [data-testid="stMarkdownContainer"],
    .st-key-admin-open-profile button [data-testid="stMarkdownContainer"] > p,
    .st-key-admin_delete_selected_user button p,
    .st-key-admin_delete_selected_user button span,
    .st-key-admin_delete_selected_user button [data-testid="stMarkdownContainer"],
    .st-key-admin_delete_selected_user button [data-testid="stMarkdownContainer"] > p,
    .st-key-admin-delete-selected-user button p,
    .st-key-admin-delete-selected-user button span,
    .st-key-admin-delete-selected-user button [data-testid="stMarkdownContainer"],
    .st-key-admin-delete-selected-user button [data-testid="stMarkdownContainer"] > p {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        opacity: 1 !important;
    }

    .st-key-admin_refresh_dashboard button:hover,
    .st-key-admin_open_benchmark button:hover,
    .st-key-admin_open_popular button:hover,
    .st-key-admin_open_profile button:hover,
    .st-key-admin_delete_selected_user button:hover,
    .st-key-admin-delete-selected-user button:hover {
        background: var(--primary-dark) !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        border-color: var(--primary-dark) !important;
    }

    .st-key-admin_refresh_dashboard button:hover p,
    .st-key-admin_refresh_dashboard button:hover span,
    .st-key-admin_refresh_dashboard button:hover [data-testid="stMarkdownContainer"] > p,
    .st-key-admin-refresh-dashboard button:hover p,
    .st-key-admin-refresh-dashboard button:hover span,
    .st-key-admin-refresh-dashboard button:hover [data-testid="stMarkdownContainer"] > p,
    .st-key-admin_open_benchmark button:hover p,
    .st-key-admin_open_benchmark button:hover span,
    .st-key-admin_open_benchmark button:hover [data-testid="stMarkdownContainer"] > p,
    .st-key-admin-open-benchmark button:hover p,
    .st-key-admin-open-benchmark button:hover span,
    .st-key-admin-open-benchmark button:hover [data-testid="stMarkdownContainer"] > p,
    .st-key-admin_open_popular button:hover p,
    .st-key-admin_open_popular button:hover span,
    .st-key-admin_open_popular button:hover [data-testid="stMarkdownContainer"] > p,
    .st-key-admin-open-popular button:hover p,
    .st-key-admin-open-popular button:hover span,
    .st-key-admin-open-popular button:hover [data-testid="stMarkdownContainer"] > p,
    .st-key-admin_open_profile button:hover p,
    .st-key-admin_open_profile button:hover span,
    .st-key-admin_open_profile button:hover [data-testid="stMarkdownContainer"] > p,
    .st-key-admin-open-profile button:hover p,
    .st-key-admin-open-profile button:hover span,
    .st-key-admin-open-profile button:hover [data-testid="stMarkdownContainer"] > p,
    .st-key-admin_delete_selected_user button:hover p,
    .st-key-admin_delete_selected_user button:hover span,
    .st-key-admin_delete_selected_user button:hover [data-testid="stMarkdownContainer"] > p,
    .st-key-admin-delete-selected-user button:hover p,
    .st-key-admin-delete-selected-user button:hover span,
    .st-key-admin-delete-selected-user button:hover [data-testid="stMarkdownContainer"] > p {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }

    div[data-baseweb="popover"],
    div[data-testid="stPopoverBody"] {
        background: #ffffff !important;
        color: var(--ink) !important;
        border: 1px solid var(--line) !important;
        border-radius: 8px !important;
        box-shadow: 0 18px 42px rgba(16,32,51,0.16) !important;
    }

    div[data-baseweb="popover"] > div,
    div[data-baseweb="popover"] [data-testid="stVerticalBlock"],
    div[data-baseweb="popover"] [data-testid="stPopoverBody"],
    div[data-testid="stPopoverBody"] > div,
    div[data-testid="stPopoverBody"] [data-testid="stVerticalBlock"] {
        background: #ffffff !important;
        color: var(--ink) !important;
    }

    div[data-baseweb="popover"] [data-testid="stMarkdownContainer"] p,
    div[data-baseweb="popover"] [data-testid="stCaptionContainer"],
    div[data-baseweb="popover"] [data-testid="stCaptionContainer"] p,
    div[data-testid="stPopoverBody"] [data-testid="stMarkdownContainer"] p,
    div[data-testid="stPopoverBody"] [data-testid="stCaptionContainer"],
    div[data-testid="stPopoverBody"] [data-testid="stCaptionContainer"] p {
        color: var(--ink) !important;
        -webkit-text-fill-color: var(--ink) !important;
        opacity: 1 !important;
    }

    div[data-baseweb="popover"] .stButton > button,
    div[data-testid="stPopoverBody"] .stButton > button {
        background: #eef7f5 !important;
        color: var(--primary-dark) !important;
        border: 1px solid #cce7e2 !important;
        box-shadow: none !important;
    }

    div[data-baseweb="popover"] .stButton > button p,
    div[data-testid="stPopoverBody"] .stButton > button p {
        color: var(--primary-dark) !important;
        -webkit-text-fill-color: var(--primary-dark) !important;
    }

    div[data-baseweb="popover"] .stButton > button:hover,
    div[data-testid="stPopoverBody"] .stButton > button:hover {
        background: var(--primary) !important;
        color: #ffffff !important;
        border-color: var(--primary) !important;
    }

    div[data-baseweb="popover"] .stButton > button:hover p,
    div[data-testid="stPopoverBody"] .stButton > button:hover p {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }

    div[data-baseweb="popover"] .st-key-menu_sign_out button,
    div[data-testid="stPopoverBody"] .st-key-menu_sign_out button {
        background: #dc2626 !important;
        color: #ffffff !important;
        border-color: #dc2626 !important;
    }

    div[data-baseweb="popover"] .st-key-menu_sign_out button p,
    div[data-testid="stPopoverBody"] .st-key-menu_sign_out button p {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }

    .stFormSubmitButton > button,
    .stFormSubmitButton > button * ,
    .stFormSubmitButton > button [data-testid="stMarkdownContainer"] p {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        opacity: 1 !important;
    }

    div[data-testid="stInputInstructions"],
    div[data-testid="stInputInstructions"] *,
    .stTextInput div[data-testid="stInputInstructions"],
    .stTextInput div[data-testid="stInputInstructions"] * {
        color: #64748b !important;
        -webkit-text-fill-color: #64748b !important;
        opacity: 1 !important;
    }

    .stButton > button,
    .stButton > button *,
    .stButton > button [data-testid="stMarkdownContainer"],
    .stButton > button [data-testid="stMarkdownContainer"] *,
    .stDownloadButton > button,
    .stDownloadButton > button *,
    .stDownloadButton > button [data-testid="stMarkdownContainer"],
    .stDownloadButton > button [data-testid="stMarkdownContainer"] *,
    .stFormSubmitButton > button,
    .stFormSubmitButton > button *,
    .stFormSubmitButton > button [data-testid="stMarkdownContainer"],
    .stFormSubmitButton > button [data-testid="stMarkdownContainer"] * {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        opacity: 1 !important;
    }

    .st-key-youtube_sidebar .stButton > button,
    .st-key-youtube_sidebar .stButton > button *,
    .st-key-youtube_sidebar .stButton > button [data-testid="stMarkdownContainer"],
    .st-key-youtube_sidebar .stButton > button [data-testid="stMarkdownContainer"] * {
        color: var(--ink) !important;
        -webkit-text-fill-color: var(--ink) !important;
    }

    .st-key-youtube_sidebar .stButton > button:hover,
    .st-key-youtube_sidebar .stButton > button:hover *,
    .st-key-youtube_sidebar .stButton > button:hover [data-testid="stMarkdownContainer"],
    .st-key-youtube_sidebar .stButton > button:hover [data-testid="stMarkdownContainer"] * {
        color: var(--primary-dark) !important;
        -webkit-text-fill-color: var(--primary-dark) !important;
    }

    .st-key-header_nav_home button,
    .st-key-header_nav_home button *,
    .st-key-header_nav_benchmark button,
    .st-key-header_nav_benchmark button *,
    .st-key-header_nav_popular button,
    .st-key-header_nav_popular button *,
    .st-key-header_nav_upload button,
    .st-key-header_nav_upload button *,
    .st-key-header_nav_admin button,
    .st-key-header_nav_admin button *,
    .st-key-header_account_menu button,
    .st-key-header_account_menu button * {
        color: var(--ink) !important;
        -webkit-text-fill-color: var(--ink) !important;
    }

    .st-key-header_account_menu button,
    .st-key-header_account_menu button * {
        color: var(--primary-dark) !important;
        -webkit-text-fill-color: var(--primary-dark) !important;
    }

    .st-key-header_account_menu button:hover,
    .st-key-header_account_menu button:hover * {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }

    .st-key-forgot_password_button button,
    .st-key-forgot_password_button button *,
    .st-key-back_to_login_button button,
    .st-key-back_to_login_button button *,
    .st-key-didnt_get_code_button button,
    .st-key-didnt_get_code_button button *,
    div[data-baseweb="popover"] .stButton > button,
    div[data-baseweb="popover"] .stButton > button *,
    div[data-testid="stPopoverBody"] .stButton > button,
    div[data-testid="stPopoverBody"] .stButton > button * {
        color: var(--primary-dark) !important;
        -webkit-text-fill-color: var(--primary-dark) !important;
    }

    .st-key-forgot_password_button button:hover,
    .st-key-forgot_password_button button:hover *,
    .st-key-back_to_login_button button:hover,
    .st-key-back_to_login_button button:hover *,
    .st-key-didnt_get_code_button button:hover,
    .st-key-didnt_get_code_button button:hover * {
        color: var(--primary-dark) !important;
        -webkit-text-fill-color: var(--primary-dark) !important;
    }

    div[data-baseweb="popover"] .stButton > button:hover,
    div[data-baseweb="popover"] .stButton > button:hover *,
    div[data-testid="stPopoverBody"] .stButton > button:hover,
    div[data-testid="stPopoverBody"] .stButton > button:hover *,
    div[data-baseweb="popover"] .st-key-menu_sign_out button,
    div[data-baseweb="popover"] .st-key-menu_sign_out button *,
    div[data-testid="stPopoverBody"] .st-key-menu_sign_out button,
    div[data-testid="stPopoverBody"] .st-key-menu_sign_out button * {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }

    .st-key-analyze_sequence_button button,
    .st-key-analyze_sequence_button button *,
    .st-key-analyze_sequence_button button [data-testid="stMarkdownContainer"],
    .st-key-analyze_sequence_button button [data-testid="stMarkdownContainer"] *,
    .st-key-analyze-sequence-button button,
    .st-key-analyze-sequence-button button *,
    .st-key-analyze-sequence-button button [data-testid="stMarkdownContainer"],
    .st-key-analyze-sequence-button button [data-testid="stMarkdownContainer"] * {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        opacity: 1 !important;
    }

    .stApp .st-key-analyze_sequence_button button div[data-testid="stMarkdownContainer"] p,
    .stApp .st-key-analyze_sequence_button button div[data-testid="stMarkdownContainer"] > p:not([class]),
    .stApp .st-key-analyze-sequence-button button div[data-testid="stMarkdownContainer"] p,
    .stApp .st-key-analyze-sequence-button button div[data-testid="stMarkdownContainer"] > p:not([class]),
    .stApp div.stButton > button[kind="primary"] div[data-testid="stMarkdownContainer"] p,
    .stApp div.stButton > button[kind="primary"] div[data-testid="stMarkdownContainer"] > p:not([class]),
    .stApp div.stButton > button[data-testid="baseButton-primary"] div[data-testid="stMarkdownContainer"] p,
    .stApp div.stButton > button[data-testid="baseButton-primary"] div[data-testid="stMarkdownContainer"] > p:not([class]) {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        opacity: 1 !important;
    }

    .stButton > button,
    .stDownloadButton > button,
    .stFormSubmitButton > button,
    .stButton > button *,
    .stDownloadButton > button *,
    .stFormSubmitButton > button * {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }

    .stButton > button,
    .stDownloadButton > button,
    .stFormSubmitButton > button {
        background: linear-gradient(135deg, #0f766e 0%, #115e59 100%) !important;
        border: none !important;
        border-radius: 999px !important;
        padding: 0.75rem 1.15rem !important;
        font-weight: 700 !important;
        min-height: 2.8rem !important;
        box-shadow: 0 8px 20px rgba(15, 118, 110, 0.2) !important;
        opacity: 1 !important;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover,
    .stFormSubmitButton > button:hover {
        background: #115e59 !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 10px 24px rgba(15, 118, 110, 0.28) !important;
    }

    .stButton > button:disabled,
    .stDownloadButton > button:disabled,
    .stFormSubmitButton > button:disabled {
        background: #5a7c6e !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        opacity: 0.7 !important;
    }

    .st-key-youtube_sidebar .stButton > button,
    .st-key-youtube_sidebar .stDownloadButton > button,
    .st-key-youtube_sidebar .stFormSubmitButton > button {
        background: #0f766e !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        border: none !important;
        border-radius: 12px !important;
        box-shadow: none !important;
    }

    .st-key-youtube_sidebar [data-testid="stMarkdownContainer"] p,
    .st-key-youtube_sidebar [data-testid="stMarkdownContainer"] h3,
    .st-key-youtube_sidebar .stCaptionContainer,
    .st-key-youtube_sidebar small {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }

    @media (max-width: 760px) {
        .st-key-youtube_sidebar {
            width: min(16rem, 88vw);
        }
        .hero-stat-row {
            grid-template-columns: 1fr;
        }
        .info-grid,
        .comparison-grid,
        .reliability-metrics,
        .knowledge-row {
            grid-template-columns: 1fr;
        }
        .yt-header {
            align-items: flex-start;
            flex-direction: column;
        }
        .header-search {
            width: 100%;
            max-width: none;
        }
        .user-chip {
            text-align: left;
        }
    }

    @media (max-width: 1050px) {
        .st-key-app_header div[data-testid="stHorizontalBlock"] {
            flex-wrap: wrap;
        }
        .st-key-app_header div[data-testid="column"] {
            min-width: fit-content;
        }
    }

    /* Final UI button and label overrides */
    .stButton > button,
    .stDownloadButton > button,
    .stFormSubmitButton > button,
    .stButton > button *,
    .stDownloadButton > button *,
    .stFormSubmitButton > button * {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }

    .stButton > button,
    .stDownloadButton > button,
    .stFormSubmitButton > button {
        background: linear-gradient(135deg, #0f766e 0%, #115e59 100%) !important;
        border: none !important;
        border-radius: 999px !important;
        padding: 0.75rem 1.15rem !important;
        min-height: 2.8rem !important;
        box-shadow: 0 10px 24px rgba(15, 118, 110, 0.2) !important;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover,
    .stFormSubmitButton > button:hover {
        background: #115e59 !important;
        box-shadow: 0 12px 28px rgba(15, 118, 110, 0.28) !important;
        transform: translateY(-1px) !important;
    }

    .stButton > button:disabled,
    .stDownloadButton > button:disabled,
    .stFormSubmitButton > button:disabled {
        background: #5a7c6e !important;
        color: #ffffff !important;
        opacity: 0.7 !important;
    }

    /* Header top bar and nav button override */
    .st-key-app_header {
        background: #ffffff;
        border-bottom: 1px solid #e2e8f0;
        box-shadow: 0 14px 40px rgba(15, 23, 42, 0.08);
        padding: 1rem 1.25rem 0.95rem 1.25rem;
        margin-bottom: 1.5rem;
        border-radius: 0 0 20px 20px;
    }

    .st-key-app_header div[data-testid="stHorizontalBlock"] {
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        flex-wrap: wrap;
    }

    .site-brand {
        display: flex;
        align-items: center;
        gap: 0.9rem;
        min-width: 0;
    }

    .site-brand strong {
        color: #102033;
        font-size: 1rem;
        line-height: 1.2;
    }

    .site-brand small {
        display: block;
        color: #64748b;
        font-size: 0.82rem;
        line-height: 1.3;
    }

    .st-key-app_header .stTextInput input {
        min-height: 3.05rem !important;
        border-radius: 999px !important;
        border: 1px solid #d1d5db !important;
        background: #f8fafc !important;
        padding: 0.8rem 1rem !important;
        color: #102033 !important;
        font-size: 0.95rem !important;
    }

    .st-key-app_header .stTextInput input::placeholder {
        color: #64748b !important;
        opacity: 1 !important;
    }

    .st-key-app_header .stFormSubmitButton button {
        min-height: 3.05rem !important;
        border-radius: 999px !important;
        padding: 0 1.3rem !important;
        background: #0f766e !important;
        border: 1px solid #0f766e !important;
        color: #ffffff !important;
        font-weight: 800 !important;
        box-shadow: 0 10px 24px rgba(15, 118, 110, 0.18) !important;
    }

    .st-key-app_header .stFormSubmitButton button:hover {
        background: #115e59 !important;
        border-color: #115e59 !important;
    }

    .header-nav-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.75rem;
        align-items: center;
        margin-top: 1rem;
        padding-top: 0.85rem;
        border-top: 1px solid #e2e8f0;
    }

    .header-nav-row .stButton > button,
    .st-key-header_nav_home button,
    .st-key-header_nav_benchmark button,
    .st-key-header_nav_popular button,
    .st-key-header_nav_upload button,
    .st-key-header_nav_admin button {
        min-height: 2.95rem !important;
        border-radius: 999px !important;
        padding: 0.75rem 1.25rem !important;
        background: #0f766e !important;
        border: 1px solid #0f766e !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        box-shadow: none !important;
    }

    .header-nav-row .stButton > button:hover,
    .st-key-header_nav_home button:hover,
    .st-key-header_nav_benchmark button:hover,
    .st-key-header_nav_popular button:hover,
    .st-key-header_nav_upload button:hover,
    .st-key-header_nav_admin button:hover {
        background: #115e59 !important;
        border-color: #115e59 !important;
        color: #ffffff !important;
        transform: none !important;
    }

    .st-key-header_nav_home button p,
    .st-key-header_nav_benchmark button p,
    .st-key-header_nav_popular button p,
    .st-key-header_nav_upload button p,
    .st-key-header_nav_admin button p,
    .st-key-header_nav_home button span,
    .st-key-header_nav_benchmark button span,
    .st-key-header_nav_popular button span,
    .st-key-header_nav_upload button span,
    .st-key-header_nav_admin button span {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }

    .st-key-header_nav_home button::before,
    .st-key-header_nav_benchmark button::before,
    .st-key-header_nav_popular button::before,
    .st-key-header_nav_upload button::before,
    .st-key-header_nav_admin button::before {
        display: none !important;
    }

    .st-key-header_sidebar_toggle button {
        min-width: 2.75rem !important;
        min-height: 2.75rem !important;
        width: 2.75rem !important;
        height: 2.75rem !important;
        border-radius: 999px !important;
        background: #effaf8 !important;
        color: #0f766e !important;
        border: 1px solid #d1d5db !important;
        box-shadow: none !important;
    }

    .st-key-header_sidebar_toggle button::before {
        display: none !important;
    }

    .st-key-app_header .stImage {
        display: flex;
        justify-content: center;
        min-height: 2.25rem;
        align-items: center;
    }
</style>
""", unsafe_allow_html=True)

# ---------- SESSION STATE ----------
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = None
if 'backend_token' not in st.session_state:
    st.session_state.backend_token = None
if 'predictions_made' not in st.session_state:
    st.session_state.predictions_made = 0
if 'auth_mode' not in st.session_state:
    st.session_state.auth_mode = "login"
if 'reset_password_token' not in st.session_state:
    st.session_state.reset_password_token = None
if 'reset_password_email' not in st.session_state:
    st.session_state.reset_password_email = None
if 'reset_password_notice' not in st.session_state:
    st.session_state.reset_password_notice = None
if 'reset_code' not in st.session_state:
    st.session_state.reset_code = None
if 'last_prediction_result' not in st.session_state:
    st.session_state.last_prediction_result = None
if 'last_prediction_sequence' not in st.session_state:
    st.session_state.last_prediction_sequence = ""
if 'nav_page' not in st.session_state:
    st.session_state.nav_page = "Home"
if 'show_upload_panel' not in st.session_state:
    st.session_state.show_upload_panel = False
if 'show_sidebar' not in st.session_state:
    st.session_state.show_sidebar = False
if 'home_sequence_input' not in st.session_state:
    st.session_state.home_sequence_input = "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHGKKVADALTNAVAHVDDMPNALSALSDLHAHKLRVDPVNFKLLSHCLLVTLAAHLPAEFTPAVHASLDKFLASVSTVLTSKYR"
if 'pending_header_prediction' not in st.session_state:
    st.session_state.pending_header_prediction = False
if 'header_search_query' not in st.session_state:
    st.session_state.header_search_query = ""
if 'header_search_feedback' not in st.session_state:
    st.session_state.header_search_feedback = ""
if 'domain_search_result' not in st.session_state:
    st.session_state.domain_search_result = None

# ---------- HELPER FUNCTIONS ----------
def make_authenticated_request(endpoint, method="POST", data=None, files=None):
    headers = {"Authorization": f"Bearer {st.session_state.backend_token}"} if st.session_state.backend_token else {}
    if method == "POST":
        if files:
            return requests.post(f"{API_URL}{endpoint}", files=files, headers=headers, timeout=60)
        else:
            return requests.post(f"{API_URL}{endpoint}", json=data, headers=headers, timeout=30)
    else:
        return requests.get(f"{API_URL}{endpoint}", headers=headers, timeout=30)

def api_error_message(response):
    if response.status_code == 404:
        return "Password reset is not available on the current backend. Restart or redeploy the FastAPI server with the latest app.py."
    if response.status_code == 503:
        return "Password reset delivery is not configured yet. Add SMTP settings to send the reset code by email."
    try:
        payload = response.json()
        detail = payload.get("detail")
        if isinstance(detail, list):
            return "; ".join(str(item.get("msg", item)) for item in detail)
        if detail:
            return str(detail)
    except Exception:
        pass
    return response.text or "Request failed."

def valid_account_password(password):
    return len(password) >= 8 and bool(re.search(r"[A-Za-z]", password)) and bool(re.search(r"\d", password))

def get_query_params():
    if hasattr(st, "query_params"):
        return dict(st.query_params)
    return st.experimental_get_query_params()

def get_query_param(name):
    value = get_query_params().get(name)
    if isinstance(value, list):
        return value[0] if value else None
    return value

def set_query_param(name, value):
    if hasattr(st, "query_params"):
        st.query_params[name] = value
        return
    params = get_query_params()
    params[name] = value
    st.experimental_set_query_params(**params)

def remove_query_param(name):
    if hasattr(st, "query_params"):
        st.query_params.pop(name, None)
        return
    params = get_query_params()
    params.pop(name, None)
    st.experimental_set_query_params(**params)

def clear_query_params():
    if hasattr(st, "query_params"):
        st.query_params.clear()
        return
    st.experimental_set_query_params()


SAMPLE_FASTA_CONTENT = """>sample_globin|Globin-like domain\nMGDVEKGKKIFVQKCAQCHTVEKGGKHKTGPNLHGLFGRKTGQAPGFSYTDANKNKGITWKEETLMEYLENPKKYIPGTKMIFAGIKKKKEERADLIAYLKKATNE\n\n>sample_zinc_finger|Zinc finger domain\nACQRCGPKCYATKSIQKAHQGTVH\n\n>sample_kinase|Protein kinase domain\nMGKTGIVTKKSRGQGITVKKVSDDLEVTLKDLGKATKGLGGSDSAKLGLSVVTRIPANKGQPGNPMVPIIIYFNHPDLSGTFEGSGHPLVGKPNHVIYQPGENRPGSDGYSTIIVKLPQSQVMLGPGKGDFGAVVIQERDMNQFSKHEVGLDPHKRVGVDVVMIKDQAVVTVPGKTGPKSIVTGSDVSIKREEGQATGQKVVFTKRGDLYVAGYPETGQYVGDSGGPLVGKSSVLMPGKTIMDEYTAG\n\n>sample_immunoglobulin|Immunoglobulin domain\nDIVMTQSPLSSSASLGDRVTITCRASQSISSYLNWYQQKPGQAPKRLIYSSNIYHDWLNGYTLSYASVWYQQKPGQAPLRLIYFTDYWGQGTLVTVSS\n\n>sample_transmembrane|Transmembrane helix\nMGLAILAALALMALAAALAAALAAALAA\n\n>sample_serine_protease|Serine protease domain\nIVGGYTCGANTVPYQVSLNSGYHFCGGSLINSDGTHHVSYTKKPGTNIRYSPNIVGPYLQPWDVSIKKGSEDPNQGSLRPVGGGTVQGDSGGPLVQGFTVFGPRVSVGGRFVLTAAHIMRQGIVGGHSITKQMFDRSLHSNDPGELKVKGHNVSRAGDLGVRVFVYGGHSTYPTGPKVASKEPVFINKYDTGGTYRLADLGYGGHSVDSKDVVYNYT"""

def parse_fasta_string_simple(fasta_string: str):
    proteins = []
    header = None
    sequence_lines = []
    for line in fasta_string.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(">"):
            if header and sequence_lines:
                proteins.append({
                    "header": header,
                    "sequence": "".join(sequence_lines).replace(" ", ""),
                })
            header = stripped[1:].strip()
            sequence_lines = []
        elif not stripped.startswith(";"):
            sequence_lines.append(stripped)
    if header and sequence_lines:
        proteins.append({
            "header": header,
            "sequence": "".join(sequence_lines).replace(" ", ""),
        })
    return proteins


def get_first_sequence_from_fasta_bytes(file_bytes):
    try:
        fasta_text = file_bytes.decode("utf-8")
    except Exception:
        fasta_text = file_bytes.decode("utf-8", errors="replace")
    proteins = parse_fasta_string_simple(fasta_text)
    return proteins


def persist_login(data):
    st.session_state.backend_token = data["access_token"]
    st.session_state.user_info = data["user"]
    st.session_state.authenticated = True
    if data.get("user", {}).get("role") == "admin":
        st.session_state.nav_page = "Home"
        st.session_state.show_upload_panel = False
    set_query_param("auth_token", data["access_token"])

def clear_password_reset_state():
    st.session_state.reset_password_token = None
    st.session_state.reset_password_email = None
    st.session_state.reset_password_notice = None
    st.session_state.reset_code = None
    st.session_state.pop("reset_password_email_input", None)
    remove_query_param("reset_token")

def restore_password_reset_from_url():
    token = get_query_param("reset_token")
    if token:
        remove_query_param("reset_token")

def restore_login_from_url():
    if st.session_state.authenticated:
        return

    token = get_query_param("auth_token")
    if not token:
        return

    try:
        resp = requests.get(
            f"{API_URL}/api/user/profile",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        if resp.status_code == 200:
            profile = resp.json()
            st.session_state.backend_token = token
            st.session_state.user_info = {
                "user_id": profile.get("user_id"),
                "email": profile.get("email"),
                "name": profile.get("name", profile.get("email", "User")),
                "picture": profile.get("picture"),
                "role": profile.get("role", "user"),
                "is_active": profile.get("is_active", True),
            }
            st.session_state.authenticated = True
        else:
            remove_query_param("auth_token")
    except Exception:
        remove_query_param("auth_token")

def logout():
    st.session_state.authenticated = False
    st.session_state.user_info = None
    st.session_state.backend_token = None
    st.session_state.user_data = {}
    st.session_state.history = []
    st.session_state.profile_cache_token = None
    clear_query_params()
    st.rerun()

restore_password_reset_from_url()
restore_login_from_url()

def render_explanation(title, points):
    cleaned_points = [str(point) for point in points if point]
    if not cleaned_points:
        return
    items = "".join(f"<li>{html.escape(point)}</li>" for point in cleaned_points)
    st.markdown(f"""
    <div class="explanation-card">
        <strong>{html.escape(title)}</strong>
        <ul>{items}</ul>
    </div>
    """, unsafe_allow_html=True)

def describe_length(length):
    if length < 50:
        return "This is a very short sequence, so it may be a peptide, motif, or fragment rather than a full protein."
    if length < 120:
        return "This is a small protein-sized sequence, which often represents a compact domain or a short functional protein."
    if length < 300:
        return "This is a medium-length protein sequence, a common range for single-domain enzymes and binding proteins."
    if length < 500:
        return "This is a large protein sequence and may contain more than one functional region."
    return "This is a very large sequence, so multiple domains or repeated regions are possible."

def explain_sequence_result(sequence, result):
    analysis_results = result.get("analysis_results", {}) or {}
    props = analysis_results.get("physicochemical_properties", {}) or {}
    predictions = result.get("rule_based_predictions", []) or []
    matched_records = result.get("predictions", []) or []
    seq_clean = "".join(c for c in sequence.upper() if c.isalpha())
    length = len(seq_clean)

    points = [describe_length(length)]
    if predictions:
        top_prediction = predictions[0]
        domain = top_prediction.get("domain", "the classified domain")
        confidence = float(top_prediction.get("confidence", 0) or 0)
        info = get_domain_knowledge(domain)
        points.append(
            f"The strongest rule-based match is {domain} at {confidence:.0%} confidence. {info['main_function']}"
        )
    else:
        points.append("No domain rule matched strongly, so the interpretation should rely more on the property charts and any dataset matches.")

    if matched_records:
        names = [record.get("protein_name") or record.get("name") or record.get("protein_id") for record in matched_records[:2]]
        names = [name for name in names if name]
        if names:
            points.append(f"The dataset comparison found similar record(s): {', '.join(names)}.")

    gravy = props.get("gravy")
    if gravy is not None:
        if gravy > 0.5:
            points.append("The positive GRAVY score suggests the sequence is relatively hydrophobic, which can indicate membrane-contacting or buried regions.")
        elif gravy < -0.5:
            points.append("The negative GRAVY score suggests the sequence is relatively water-friendly and may be exposed to solvent.")
        else:
            points.append("The GRAVY score is near neutral, suggesting a balance of hydrophobic and hydrophilic residues.")

    return points

def explain_physicochemical_properties(props):
    points = []
    p_i = props.get("isoelectric_point")
    instability = props.get("instability_index")
    hydrophobic_ratio = props.get("hydrophobic_ratio")
    charge_density = props.get("charge_density")

    if p_i is not None:
        if p_i >= 8.5:
            points.append(f"The pI is {p_i:.2f}, so this protein is classified as basic and may carry more positive charge around neutral pH.")
        elif p_i <= 5.5:
            points.append(f"The pI is {p_i:.2f}, so this protein is classified as acidic and may carry more negative charge around neutral pH.")
        else:
            points.append(f"The pI is {p_i:.2f}, close to neutral compared with strongly acidic or basic proteins.")

    if instability is not None:
        if instability < 40:
            points.append(f"The instability index is {instability:.1f}, which suggests the sequence is likely stable by this rule-of-thumb metric.")
        else:
            points.append(f"The instability index is {instability:.1f}, which suggests the sequence may be less stable or more flexible.")

    if hydrophobic_ratio is not None:
        points.append(f"About {hydrophobic_ratio:.0%} of the residues are hydrophobic, helping explain whether the protein may bury regions inside a fold or interact with membranes.")

    if charge_density is not None:
        if charge_density > 0.05:
            points.append("The charge density leans positive, which can support binding to negatively charged molecules such as DNA, RNA, or acidic protein surfaces.")
        elif charge_density < -0.05:
            points.append("The charge density leans negative, which can affect solubility and interaction with positively charged binding partners.")
        else:
            points.append("The charge density is balanced, so no strong positive or negative bias dominates the whole sequence.")

    return points

def explain_amino_acid_composition(composition):
    if not composition:
        return []
    sorted_comp = sorted(composition.items(), key=lambda item: item[1], reverse=True)
    top = [(aa, pct) for aa, pct in sorted_comp[:3] if pct > 0]
    points = []
    if top:
        top_text = ", ".join(f"{aa} ({pct:.1f}%)" for aa, pct in top)
        points.append(f"The most common residues are {top_text}; these residues have the largest influence on the bar chart.")

    cysteine = composition.get("C", 0)
    proline = composition.get("P", 0)
    charged = composition.get("D", 0) + composition.get("E", 0) + composition.get("K", 0) + composition.get("R", 0) + composition.get("H", 0)
    if cysteine >= 5:
        points.append(f"Cysteine is relatively high at {cysteine:.1f}%, which can point to disulfide bonds or metal-binding motifs.")
    if proline >= 10:
        points.append(f"Proline is high at {proline:.1f}%, which can create bends, rigid turns, or linker-like regions.")
    if charged >= 25:
        points.append(f"Charged residues make up about {charged:.1f}% of the sequence, so electrostatic interactions may matter for this protein.")
    if not points:
        points.append("The composition chart shows no single residue class dominating strongly, so the sequence appears chemically mixed.")
    return points

def explain_detected_motifs(motifs):
    if not motifs:
        return []
    motif_meanings = {
        "zinc_finger": "a possible zinc-binding DNA/RNA/protein interaction pattern",
        "leucine_zipper": "a repeated leucine pattern often linked with protein dimerization",
        "glycosylation_site": "a possible site where sugar groups may be attached",
        "phosphorylation_site": "a possible regulatory site for kinase signaling",
        "nuclear_localization": "a basic-residue cluster that may help nuclear import",
        "transmembrane": "a hydrophobic stretch that may cross or contact a membrane",
    }
    points = []
    for motif, positions in motifs.items():
        if not positions:
            continue
        readable = motif.replace("_", " ")
        meaning = motif_meanings.get(motif, "a sequence pattern worth checking against biological context")
        shown_positions = ", ".join(str(pos + 1) for pos in positions[:4])
        extra = " and more" if len(positions) > 4 else ""
        points.append(f"{readable.title()} was found near residue position(s) {shown_positions}{extra}; this suggests {meaning}.")
    return points

def explain_residue_profile(hydro_values, charge_values):
    if not hydro_values:
        return []
    avg_hydro = sum(hydro_values) / len(hydro_values)
    positive_count = sum(1 for charge in charge_values if charge > 0)
    negative_count = sum(1 for charge in charge_values if charge < 0)
    high_hydro_positions = [idx + 1 for idx, value in enumerate(hydro_values) if value >= 2.5]
    points = []

    if avg_hydro > 0.5:
        points.append("The hydrophobicity line sits mostly above neutral, suggesting many residues prefer buried protein cores or membrane-like environments.")
    elif avg_hydro < -0.5:
        points.append("The hydrophobicity line sits mostly below neutral, suggesting many residues are water-friendly and likely surface-exposed.")
    else:
        points.append("The hydrophobicity line moves around neutral, suggesting mixed buried and exposed regions along the sequence.")

    if high_hydro_positions:
        first_region = high_hydro_positions[:5]
        points.append(f"Hydrophobic peaks appear near residue position(s) {', '.join(map(str, first_region))}; longer clusters can mark buried segments or membrane-contacting stretches.")

    if positive_count > negative_count:
        points.append("The charge trace has more positive than negative positions, so basic residues are more frequent in this sequence.")
    elif negative_count > positive_count:
        points.append("The charge trace has more negative than positive positions, so acidic residues are more frequent in this sequence.")
    else:
        points.append("The charge trace is balanced between positive and negative residues.")
    return points

# ---------- SPECIAL FEATURE 1: Residue property viewer (hydrophobicity & charge) ----------
def show_residue_properties(sequence):
    # Simple hydrophobicity scale (Kyte-Doolittle)
    hydrophobicity = {
        'A': 1.8, 'C': 2.5, 'D': -3.5, 'E': -3.5, 'F': 2.8,
        'G': -0.4, 'H': -3.2, 'I': 4.5, 'K': -3.9, 'L': 3.8,
        'M': 1.9, 'N': -3.5, 'P': -1.6, 'Q': -3.5, 'R': -4.5,
        'S': -0.8, 'T': -0.7, 'V': 4.2, 'W': -0.9, 'Y': -1.3
    }
    charges = {'K': 1, 'R': 1, 'H': 0.5, 'D': -1, 'E': -1}
    seq_clean = ''.join([c for c in sequence if c in hydrophobicity])
    if not seq_clean:
        st.warning("Cannot display residue properties - sequence contains unknown characters.")
        return
    hydro_values = [hydrophobicity.get(aa, 0) for aa in seq_clean]
    charge_values = [charges.get(aa, 0) for aa in seq_clean]
    df = pd.DataFrame({
        'Position': list(range(1, len(seq_clean)+1)),
        'Hydrophobicity': hydro_values,
        'Charge': charge_values
    })
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['Position'],
        y=df['Hydrophobicity'],
        mode='lines+markers',
        name='Hydrophobicity',
        line=dict(color=THEME_COLORS["primary"], width=2.5),
        marker=dict(size=4, color=THEME_COLORS["primary"]),
    ))
    fig.add_trace(go.Scatter(
        x=df['Position'],
        y=df['Charge'],
        mode='lines+markers',
        name='Charge',
        line=dict(color=THEME_COLORS["accent"], width=2.5),
        marker=dict(size=4, color=THEME_COLORS["accent"]),
    ))
    fig.update_layout(title="Hydrophobicity & Charge along Sequence", xaxis_title="Residue Position", yaxis_title="Score")
    apply_plotly_theme(fig, height=350)
    st.plotly_chart(fig, use_container_width=True)
    render_explanation("How to read this residue graph", explain_residue_profile(hydro_values, charge_values))

# ---------- SPECIAL FEATURE 2: Domain rule explanation tooltip ----------
def domain_rule_tooltip(domain_name):
    rules = {
        "Globin": "Length 140-160 aa, pI 7.0-8.5, hydrophobic ratio >0.45, conserved H/F/L residues.",
        "Zinc Finger": "Length 20-40 aa, at least 2 Cys and 2 His, zinc finger motif, MW <10 kDa.",
        "Kinase": "Length 250-300 aa, contains DFG/APE motif, instability index <40, high S/T content.",
        "Immunoglobulin": "Length 90-110 aa, at least 2 Cys, pI 4.5-6.5.",
        "Transmembrane": "GRAVY 0.7-2.0, hydrophobic ratio >0.6, helix content 0.4-0.7.",
        "Serine Protease": "Length 220-260 aa, catalytic triad (H/D/S), contains GDSGG motif, pI 8.0-10.0."
    }
    return rules.get(domain_name, "No rule explanation available.")

def get_domain_knowledge(domain_name):
    knowledge = {
        "Globin": {
            "main_function": "Binds heme groups so proteins can transport, store, or sense oxygen and other small gases.",
            "subfunction": "Supports reversible oxygen binding in hemoglobin and myoglobin; some globins also participate in nitric oxide and oxygen sensing.",
            "where_found": "Common in vertebrate blood and muscle tissue, and also found in many bacteria, plants, and invertebrates.",
            "examples": "Hemoglobin alpha/beta, myoglobin, neuroglobin.",
        },
        "Zinc Finger": {
            "main_function": "Uses zinc ions to stabilize a compact fold that commonly binds DNA, RNA, proteins, or lipids.",
            "subfunction": "Often controls gene expression by helping transcription factors recognize specific DNA sequences.",
            "where_found": "Very common in eukaryotic regulatory proteins, especially nuclear transcription factors.",
            "examples": "C2H2 zinc finger proteins, steroid hormone receptors, nucleic-acid binding regulators.",
        },
        "Kinase": {
            "main_function": "Transfers phosphate groups, usually from ATP, to target molecules to regulate cellular activity.",
            "subfunction": "Controls signaling, metabolism, cell-cycle progression, immune response, and protein activity switches.",
            "where_found": "Found across bacteria, plants, animals, and fungi; abundant in cell signaling pathways.",
            "examples": "Protein kinases, receptor tyrosine kinases, serine/threonine kinases.",
        },
        "Immunoglobulin": {
            "main_function": "Forms stable recognition surfaces used for immune binding and cell-cell interactions.",
            "subfunction": "Supports antibody antigen recognition, receptor binding, and adhesion between cells.",
            "where_found": "Antibodies, T-cell receptors, and many cell-surface proteins in vertebrate immune systems.",
            "examples": "Antibody variable/constant regions, T-cell receptors, cell adhesion molecules.",
        },
        "Transmembrane": {
            "main_function": "Anchors proteins in biological membranes or forms channels and transport routes through membranes.",
            "subfunction": "Enables signaling, ion transport, nutrient movement, and receptor activation across lipid bilayers.",
            "where_found": "Cell membranes, mitochondrial membranes, endoplasmic reticulum, bacterial plasma membranes.",
            "examples": "GPCR helices, ion channels, transporters, membrane receptors.",
        },
        "Serine Protease": {
            "main_function": "Cuts peptide bonds in proteins using a catalytic serine residue.",
            "subfunction": "Drives digestion, blood clotting, immune defense, protein processing, and enzyme activation cascades.",
            "where_found": "Digestive systems, blood plasma, immune pathways, bacteria, and many secreted enzyme systems.",
            "examples": "Trypsin, chymotrypsin, thrombin, elastase.",
        },
    }
    return knowledge.get(domain_name, {
        "main_function": "This classified domain is associated with conserved structural or biochemical behavior.",
        "subfunction": "Review the classification confidence and rule explanation to interpret the likely role.",
        "where_found": "Presence depends on the protein family, organism, and cellular context.",
        "examples": "No curated examples available for this classification.",
    })

@st.cache_data(show_spinner=False)
def load_benchmark_summary(modified_time: float = 0.0):
    result_path = Path("benchmark_results.csv")
    if not result_path.exists():
        return {
            "has_results": False,
            "accuracy": "Pending",
            "tested": "Not run",
            "matched": "Not run",
            "method": "Run scop_benchmark.py with a SCOP-style labelled dataset to generate benchmark_results.csv.",
        }

    try:
        df = pd.read_csv(result_path)
        if df.empty or "match" not in df.columns:
            raise ValueError("benchmark_results.csv is missing benchmark rows or a match column")
        matches = df["match"].astype(bool)
        accuracy = matches.mean()
        return {
            "has_results": True,
            "accuracy": f"{accuracy:.1%}",
            "tested": f"{len(df):,}",
            "matched": f"{int(matches.sum()):,}",
            "method": "Measured from benchmark_results.csv using labelled SCOP-style domain comparisons.",
        }
    except Exception as exc:
        return {
            "has_results": False,
            "accuracy": "Unavailable",
            "tested": "Check file",
            "matched": "Check file",
            "method": f"Could not read benchmark_results.csv: {exc}",
        }

@st.cache_data(show_spinner=False)
def fetch_user_data(token: str):
    profile = {}
    history = []

    try:
        profile_resp = requests.get(f"{API_URL}/api/user/profile", headers={"Authorization": f"Bearer {token}"}, timeout=30)
        if profile_resp.status_code == 200:
            profile = profile_resp.json()
    except Exception:
        pass

    try:
        history_resp = requests.get(f"{API_URL}/api/predictions/history", headers={"Authorization": f"Bearer {token}"}, timeout=30)
        if history_resp.status_code == 200:
            history = history_resp.json()
    except Exception:
        pass

    return profile, history

def get_cached_user_state():
    token = st.session_state.backend_token
    if not token:
        return st.session_state.user_info or {}, []

    cache_token = st.session_state.get("profile_cache_token")
    if cache_token == token and "user_data" in st.session_state and "history" in st.session_state:
        return st.session_state.user_data, st.session_state.history

    user_data, history = fetch_user_data(token)
    st.session_state.user_data = user_data or st.session_state.user_info or {}
    st.session_state.history = history
    st.session_state.profile_cache_token = token
    return st.session_state.user_data, st.session_state.history

def format_history_timestamp(timestamp):
    if not timestamp:
        return "Unknown time"

    try:
        parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        local_time = parsed.astimezone(LOCAL_TIMEZONE)
        time_label = local_time.strftime("%I:%M %p").lstrip("0")
        return f"{local_time.strftime('%d %b %Y')}, {time_label}"
    except ValueError:
        return str(timestamp).replace("T", " ")[:19]

def truncate_text(value, limit):
    text = str(value or "")
    return f"{text[:limit]}..." if len(text) > limit else text

def clean_suggestion_title(value):
    text = str(value or "").strip()
    text = re.sub(r"[()\[\]{}]", "", text)
    return re.sub(r"\s+", " ", text).strip()

def map_scop_label_to_domain(scop_label):
    label = (scop_label or "").lower()
    mapping = {
        "globin": "Globin",
        "immunoglobulin": "Immunoglobulin",
        "kinase": "Kinase",
        "zinc finger": "Zinc Finger",
        "transmembrane": "Transmembrane",
        "membrane": "Transmembrane",
        "serine protease": "Serine Protease",
        "protease": "Serine Protease",
    }
    for key, domain in mapping.items():
        if key in label:
            return domain
    return "Other / not covered yet"

DOMAIN_OPTIONS = ["", "Globin", "Zinc Finger", "Kinase", "Immunoglobulin", "Transmembrane", "Serine Protease"]

def compare_prediction_with_scop(predicted_domain, scop_label):
    scop_domain = map_scop_label_to_domain(scop_label)
    return {
        "predicted_domain": predicted_domain or "No classification yet",
        "scop_domain": scop_domain,
        "match": predicted_domain == scop_domain,
    }

def render_scop_comparison_panel(key_prefix, suggested_domain="", show_summary=False):
    st.markdown('<div class="section-title">Benchmark Comparison</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-copy">Compare the latest classified domain with a known SCOP-style label or fold.</div>',
        unsafe_allow_html=True,
    )

    default_index = DOMAIN_OPTIONS.index(suggested_domain) if suggested_domain in DOMAIN_OPTIONS else 0
    col_a, col_b = st.columns([1, 1])
    with col_a:
        predicted_domain = st.selectbox(
            "Classified domain",
            DOMAIN_OPTIONS,
            index=default_index,
            key=f"{key_prefix}_predicted_domain",
            help="Analyze a sequence first to fill this automatically, or choose the classified domain manually.",
        )
    with col_b:
        scop_label = st.text_input(
            "Known SCOP label or fold",
            placeholder="Example: globin-like, immunoglobulin-like beta-sandwich, protein kinase-like",
            key=f"{key_prefix}_scop_label",
        )

    if st.button("Compare Classification", type="primary", key=f"{key_prefix}_compare"):
        if not predicted_domain:
            st.warning("Choose a classified domain before comparing.")
        elif not scop_label.strip():
            st.warning("Enter a known SCOP label or fold before comparing.")
        else:
            comparison = compare_prediction_with_scop(predicted_domain, scop_label)
            if comparison["match"]:
                st.markdown(
                    f"""
                    <div class="comparison-result match">
                        <strong>Match found</strong>
                        <span>Both point to {html.escape(comparison['predicted_domain'])}.</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"""
                    <div class="comparison-result no-match">
                        <strong>No direct match</strong>
                        <span>Classification: {html.escape(comparison['predicted_domain'])}. SCOP-style label maps to: {html.escape(comparison['scop_domain'])}.</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            st.caption(f"Mapped SCOP-style label: {comparison['scop_domain']}")

    if show_summary:
        benchmark_summary = load_benchmark_summary()
        st.markdown(f"""
        <div class="comparison-grid">
            <div class="comparison-card">
                <strong>Saved SCOP benchmark</strong>
                <span>Accuracy: {benchmark_summary["accuracy"]}<br>Sequences tested: {benchmark_summary["tested"]}<br>Correct matches: {benchmark_summary["matched"]}</span>
            </div>
            <div class="comparison-card">
                <strong>Similar websites and tools</strong>
                <span>Comparable tools include InterProScan, Pfam/HMMER, SMART, NCBI CDD, and SUPERFAMILY/SCOPe. Those tools are larger reference platforms; this website focuses on a small set of domains with simpler explanations and visual residue properties.</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

def render_domain_knowledge_cards(predictions):
    st.subheader("Protein Domain Knowledge")
    for pred in predictions:
        domain = pred.get("domain", "Unknown")
        confidence = float(pred.get("confidence", 0) or 0)
        info = get_domain_knowledge(domain)
        st.markdown(f"""
        <div class="knowledge-card">
            <h4>{domain} <span class="tag">{confidence:.0%} confidence</span></h4>
            <div class="knowledge-row">
                <div class="knowledge-label">Main function</div>
                <div class="knowledge-value">{info["main_function"]}</div>
            </div>
            <div class="knowledge-row">
                <div class="knowledge-label">Subfunction</div>
                <div class="knowledge-value">{info["subfunction"]}</div>
            </div>
            <div class="knowledge-row">
                <div class="knowledge-label">Where found</div>
                <div class="knowledge-value">{info["where_found"]}</div>
            </div>
            <div class="knowledge-row">
                <div class="knowledge-label">Examples</div>
                <div class="knowledge-value">{info["examples"]}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ---------- AUTHENTICATION PAGE ----------
if not st.session_state.authenticated:
    st.markdown("""
    <section class="site-hero">
        <div>
            <div class="eyebrow">Protein classification workspace</div>
            <h1>Protein Domain Finder</h1>
            <p>Analyze amino acid sequences, detect likely functional domains, and keep a searchable history of classifications in one polished research dashboard.</p>
            <div class="hero-stat-row">
                <div class="hero-stat"><strong>6 domain families</strong><span>Rule-based coverage</span></div>
                <div class="hero-stat"><strong>Live dashboard</strong><span>Profile and history</span></div>
                <div class="hero-stat"><strong>FastAPI backend</strong><span>Saved authenticated results</span></div>
            </div>
        </div>
    </section>
    """, unsafe_allow_html=True)
    st.markdown("""
    <div class="field-primer">
        <strong>New to protein domains?</strong>
        Proteins are tiny working molecules inside cells. A protein domain is a useful part of a protein, like a section that helps bind oxygen, pass through a cell membrane, or control chemical signals. This tool lets you paste a protein sequence and receive a plain-language classification of what useful parts may be present.
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<p class="main-title">Welcome Back</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Sign in to continue to your protein analysis workspace.</p>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.session_state.auth_mode == "forgot_password":
            st.markdown("### Reset your password")
            st.caption("Enter your account email. If it exists, we will generate a 6-digit reset code for you.")
            with st.form("forgot_password_form"):
                reset_email = st.text_input(
                    "Email",
                    value=st.session_state.get("login_email", ""),
                    key="forgot_password_email",
                )
                if st.form_submit_button("Send reset code", use_container_width=True):
                    with st.spinner("Sending reset code..."):
                        try:
                            resp = requests.post(
                                f"{API_URL}/api/auth/forgot-password",
                                json={"email": reset_email},
                                timeout=30,
                            )
                            if resp.status_code == 200:
                                payload = resp.json()
                                st.session_state.reset_password_email = reset_email.strip()
                                st.session_state.reset_password_email_input = reset_email.strip()
                                st.session_state.reset_password_notice = payload.get(
                                    "message",
                                    "Password reset code has been generated.",
                                )
                                st.session_state.reset_code = payload.get("code")
                                st.session_state.auth_mode = "reset_password"
                                st.rerun()
                            else:
                                st.error(api_error_message(resp))
                        except requests.RequestException as exc:
                            st.error(f"Could not request password reset: {exc}")
            if st.button("Back to login", key="back_to_login_button"):
                clear_password_reset_state()
                st.session_state.auth_mode = "login"
                st.rerun()
        elif st.session_state.auth_mode == "reset_password":
            reset_email = st.session_state.get("reset_password_email") or st.session_state.get("forgot_password_email", "")
            if st.session_state.get("reset_password_notice"):
                st.success(st.session_state.reset_password_notice)
            if st.session_state.get("reset_code"):
                st.info(f"Reset code: **{st.session_state.reset_code}**")
            st.markdown("### Create a new password")
            col1, col2 = st.columns([1, 1])
            with col2:
                if st.button("Resend code", use_container_width=False, key="didnt_get_code_button", help="Request a new reset code"):
                    st.session_state.auth_mode = "forgot_password"
                    st.rerun()
            if reset_email:
                st.caption(f"Enter the reset code for {reset_email}")
            with st.form("reset_password_form"):
                reset_email_input = st.text_input("Email", value=reset_email, key="reset_password_email_input")
                reset_code = st.text_input("Reset Code", max_chars=6)
                new_password = st.text_input("New Password", type="password", help="Min 8 chars, letters & numbers")
                confirm_password = st.text_input("Confirm New Password", type="password")
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.form_submit_button("Reset Password", use_container_width=True):
                        if not reset_email_input.strip():
                            st.error("Email is required")
                        elif not reset_code.strip():
                            st.error("Reset code is required")
                        elif new_password != confirm_password:
                            st.error("Passwords do not match")
                        elif not valid_account_password(new_password):
                            st.error("Password must be at least 8 characters with letters and numbers")
                        else:
                            with st.spinner("Resetting password..."):
                                try:
                                    resp = requests.post(
                                        f"{API_URL}/api/auth/reset-password",
                                        json={
                                            "email": reset_email_input,
                                            "code": reset_code,
                                            "password": new_password,
                                        },
                                        timeout=30,
                                    )
                                    if resp.status_code == 200:
                                        st.success(resp.json().get("message", "Password reset successful."))
                                        clear_password_reset_state()
                                        st.session_state.auth_mode = "login"
                                        time.sleep(0.8)
                                        st.rerun()
                                    else:
                                        st.error(api_error_message(resp))
                                except requests.RequestException as exc:
                                    st.error(f"Could not reset password: {exc}")
            if st.button("Back to login", key="back_to_login_button"):
                clear_password_reset_state()
                st.session_state.auth_mode = "login"
                st.rerun()
        else:
            tab_login, tab_signup = st.tabs(["Login", "Sign Up"])
            with tab_login:
                with st.form("login_form"):
                    email = st.text_input("Email", key="login_email")
                    password = st.text_input("Password", type="password", key="login_password")
                    if st.form_submit_button("Login", use_container_width=True):
                        with st.spinner("Logging in..."):
                            resp = requests.post(f"{API_URL}/api/auth/login", json={"email": email, "password": password}, timeout=30)
                            if resp.status_code == 200:
                                data = resp.json()
                                persist_login(data)
                                st.success("Logged in! Redirecting...")
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error(resp.json().get("detail", "Invalid credentials"))
                if st.button("Forgot password?", key="forgot_password_button"):
                    st.session_state.auth_mode = "forgot_password"
                    st.rerun()
            with tab_signup:
                account_type = st.radio(
                    "Account type",
                    ["Normal User", "Administrator"],
                    horizontal=True,
                    key="signup_account_type",
                )
                with st.form("signup_form"):
                    name = st.text_input("Full Name", key="signup_name")
                    email = st.text_input("Email", key="signup_email")
                    password = st.text_input("Password", type="password", help="Min 8 chars, letters & numbers", key="signup_password")
                    confirm = st.text_input("Confirm Password", type="password", key="signup_confirm")
                    setup_code = ""
                    if account_type == "Administrator":
                        setup_code = st.text_input("Admin Setup Code", type="password", key="signup_admin_setup_code")
                    submit_label = "Create Admin Account" if account_type == "Administrator" else "Create Account"
                    if st.form_submit_button(submit_label, use_container_width=True):
                        if password != confirm:
                            st.error("Passwords do not match")
                        elif not valid_account_password(password):
                            st.error("Password must be at least 8 characters with letters and numbers")
                        elif account_type == "Administrator" and not setup_code.strip():
                            st.error("Admin setup code is required")
                        else:
                            creating_label = "Creating admin account..." if account_type == "Administrator" else "Creating account..."
                            with st.spinner(creating_label):
                                if account_type == "Administrator":
                                    resp = requests.post(
                                            f"{API_URL}/api/admin/signup",
                                            json={
                                                "name": name,
                                                "email": email,
                                                "password": password,
                                                "setup_code": setup_code,
                                            },
                                            timeout=30,
                                        )
                                else:
                                    resp = requests.post(
                                        f"{API_URL}/api/auth/signup",
                                        json={"name": name, "email": email, "password": password},
                                        timeout=30,
                                    )
                                if resp.status_code == 200:
                                    data = resp.json()
                                    persist_login(data)
                                    success_label = "Admin account created! Redirecting..." if account_type == "Administrator" else "Account created! Redirecting..."
                                    st.success(success_label)
                                    time.sleep(0.5)
                                    st.rerun()
                                else:
                                    st.error(api_error_message(resp))
    st.stop()

# ---------- MAIN APP (authenticated) - website dashboard ----------
user_data, history = get_cached_user_state()

avatar_url = user_data.get("picture") or "https://cdn-icons-png.flaticon.com/512/3135/3135715.png"
is_admin = user_data.get("role") == "admin"

if st.session_state.show_sidebar:
    st.markdown(
        """
        <style>
            .block-container {
                max-width: none;
                padding-left: 17.4rem;
            }
            @media (max-width: 900px) {
                .block-container {
                    padding-left: 1rem;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

def go_to(page, upload=False):
    if page == "Popular Searches":
        page = "Suggestions"
    st.session_state.nav_page = page
    st.session_state.show_upload_panel = upload

def handle_header_search(query):
    cleaned = (query or "").strip()
    if not cleaned:
        st.session_state.header_search_feedback = "Type a sequence, UniProt ID, domain, or page name to search."
        return

    lowered = cleaned.lower()
    route_keywords = [
        (("admin", "users", "manage users"), "Admin", False),
        (("benchmark", "scop", "compare", "accuracy"), "Benchmark", False),
        (("suggestion", "suggestions", "popular", "trending"), "Suggestions", False),
        (("history", "recent", "saved"), "History Searches", False),
        (("profile", "account", "user"), "Profile", False),
        (("download", "report", "json"), "Downloads", False),
        (("upload", "fasta file"), "Home", True),
        (("home", "analyze", "prediction", "classification"), "Home", False),
    ]
    for keywords, page, upload in route_keywords:
        if any(keyword in lowered for keyword in keywords):
            st.session_state.pending_header_prediction = False
            st.session_state.domain_search_result = None
            if page == "Admin" and not is_admin:
                st.session_state.header_search_feedback = "Admin access is only available to admin accounts."
            else:
                st.session_state.header_search_feedback = f"Opened {page}."
                go_to(page, upload=upload)
            return

    domain_terms = {
        "globin": "Globin",
        "zinc finger": "Zinc Finger",
        "zinc": "Zinc Finger",
        "kinase": "Kinase",
        "immunoglobulin": "Immunoglobulin",
        "transmembrane": "Transmembrane",
        "membrane": "Transmembrane",
        "serine protease": "Serine Protease",
        "protease": "Serine Protease",
    }
    for term, domain in domain_terms.items():
        if term in lowered:
            st.session_state.domain_search_result = domain
            st.session_state.pending_header_prediction = False
            st.session_state.header_search_feedback = f"Showing domain information for {domain}."
            go_to("Home")
            return

    st.session_state.domain_search_result = None
    st.session_state.home_sequence_input = cleaned
    st.session_state.pending_header_prediction = True
    st.session_state.header_search_feedback = "Loaded your search into the Home analyzer."
    go_to("Home")

def toggle_sidebar():
    st.session_state.show_sidebar = not st.session_state.show_sidebar

def sidebar_nav_button(label, page, key, upload=False):
    active = st.session_state.nav_page == page and (
        st.session_state.show_upload_panel if upload else not st.session_state.show_upload_panel
    )
    if active:
        st.markdown(
            f"""
            <style>
                .st-key-{key} button {{
                    background: #eef7f5 !important;
                    color: #0f5d56 !important;
                    font-weight: 800 !important;
                }}
                .st-key-{key} button p,
                .st-key-{key} button span {{
                    color: #0f5d56 !important;
                    -webkit-text-fill-color: #0f5d56 !important;
                }}
            </style>
            """,
            unsafe_allow_html=True,
        )
    if st.button(label, key=key, use_container_width=True):
        go_to(page, upload=upload)
        st.session_state.show_sidebar = False
        st.rerun()

if st.session_state.show_sidebar:
    st.markdown('<div class="st-key-youtube_sidebar">', unsafe_allow_html=True)
    with st.container():
        close_col, brand_col = st.columns([0.34, 1.66])
        with close_col:
            if st.button("Close menu", key="sidebar_close", help="Close menu", use_container_width=True):
                toggle_sidebar()
                st.rerun()
        with brand_col:
            st.markdown(
                """
                <div class="sidebar-brand">
                    <img src="https://cdn-icons-png.flaticon.com/512/2947/2947927.png" alt="Protein Domain Finder logo">
                    <strong>Protein Domain Finder</strong>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown('<div class="sidebar-section-label">Main</div>', unsafe_allow_html=True)
        sidebar_nav_button("Dashboard" if is_admin else "Home", "Home", "side_home")
        if not is_admin:
            sidebar_nav_button("Upload", "Home", "side_upload", upload=True)
        sidebar_nav_button("Benchmark", "Benchmark", "side_benchmark")
        sidebar_nav_button("Suggestions", "Suggestions", "side_popular")
        st.markdown('<div class="sidebar-section-label">Workspace</div>', unsafe_allow_html=True)
        if is_admin:
            sidebar_nav_button("Manage Users", "Admin", "side_admin")
        sidebar_nav_button("Profile", "Profile", "side_profile")
        sidebar_nav_button("Search History", "History Searches", "side_history")
        sidebar_nav_button("Reports", "Downloads", "side_downloads")
        st.markdown(
            f"""
            <div class="sidebar-footer">
                <img src="{html.escape(avatar_url)}" alt="User avatar">
                <strong>{html.escape(user_data.get('name', 'User'))}</strong>
                <span>{html.escape(user_data.get('email', 'Signed in'))}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="st-key-app_header">', unsafe_allow_html=True)
with st.container():
    menu_col, brand_col, search_col, account_col = st.columns([0.5, 3.15, 5.35, 1.45])
    with menu_col:
        if st.button("Open menu", key="header_sidebar_toggle", help="Open menu", use_container_width=True):
            toggle_sidebar()
            st.rerun()
    with brand_col:
        st.markdown(
            """
            <div class="site-brand">
                <span class="site-brand-mark">
                    <img src="https://cdn-icons-png.flaticon.com/512/2947/2947927.png" alt="Protein Domain Finder logo">
                </span>
                <span>
                    <strong>Protein Domain Finder</strong>
                    <small>Research workspace</small>
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with search_col:
        with st.form("header_search_form", clear_on_submit=False):
            search_input_col, search_button_col = st.columns([4.8, 1.55])
            with search_input_col:
                st.text_input(
                    "Search",
                    placeholder="Search a sequence, UniProt ID, domain, SCOP, history...",
                    key="header_search_query",
                    label_visibility="collapsed",
                )
            with search_button_col:
                search_submitted = st.form_submit_button("Search", use_container_width=True)
        if search_submitted:
            handle_header_search(st.session_state.header_search_query)
            st.rerun()
    with account_col:
        with st.expander("Account"):
            st.image(avatar_url, width=56)
            st.markdown(f"**{user_data.get('name', 'User')}**")
            st.caption(user_data.get("email", ""))
            if st.button("Profile", key="menu_profile", use_container_width=True):
                go_to("Profile")
            if st.button("History", key="menu_history", use_container_width=True):
                go_to("History Searches")
            if st.button("Downloads", key="menu_downloads", use_container_width=True):
                go_to("Downloads")
            if is_admin and st.button("Admin Dashboard", key="menu_admin", use_container_width=True):
                go_to("Admin")
            if st.button("Sign out", key="menu_sign_out", use_container_width=True):
                logout()

    st.markdown('<div class="header-nav-row">', unsafe_allow_html=True)
    if is_admin:
        nav_home, nav_benchmark, nav_popular, nav_admin, nav_spacer = st.columns([1.45, 1.55, 1.65, 1.15, 4.2])
    else:
        nav_home, nav_benchmark, nav_popular, nav_upload, nav_spacer = st.columns([1.15, 1.55, 1.65, 1.15, 4.5])
    with nav_home:
        if st.button("Dashboard" if is_admin else "Home", key="header_nav_home", use_container_width=True):
            go_to("Home")
    with nav_benchmark:
        if st.button("Benchmark", key="header_nav_benchmark", use_container_width=True):
            go_to("Benchmark")
    with nav_popular:
        if st.button("Suggestions", key="header_nav_popular", use_container_width=True):
            go_to("Suggestions")
    if is_admin:
        with nav_admin:
            if st.button("Users", key="header_nav_admin", use_container_width=True):
                go_to("Admin")
    else:
        with nav_upload:
            if st.button("Upload", key="header_nav_upload", use_container_width=True):
                go_to("Home", upload=True)
    st.markdown('</div>', unsafe_allow_html=True)

if st.session_state.header_search_feedback:
    st.caption(st.session_state.header_search_feedback)

current_page = st.session_state.nav_page
if is_admin and current_page == "Home":
    current_page = "Admin"

# ---------- HOME TAB ----------
if current_page == "Home":
    st.markdown('<p class="main-title">Analyze Protein Domains</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Paste a protein sequence. The website classifies possible domains and explains the result in simple words.</p>', unsafe_allow_html=True)

    st.markdown("""
    <div class="field-primer">
        <strong>A quick guide before you start</strong>
        A protein sequence is written as a chain of one-letter amino acid codes, such as A, C, D, E, F, and G. The order of those letters affects how the protein folds and what it can do. This app compares the sequence against domain clues and returns a practical explanation, so you do not need prior bioinformatics experience to read the result.
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-grid">
        <div class="info-card">
            <strong>What it does</strong>
            <span>It reads an amino acid sequence and looks for signs of known protein domains, such as globin, kinase, zinc finger, and transmembrane regions.</span>
        </div>
        <div class="info-card">
            <strong>How It Works</strong>
            <span>It checks simple clues: sequence length, repeated patterns, amino acid makeup, molecular properties, and rules for each domain family.</span>
        </div>
        <div class="info-card">
            <strong>Why It Helps</strong>
            <span>Instead of only showing technical data, it tells users what the classified domain may do and why the website chose it.</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    benchmark_summary = load_benchmark_summary()
    st.markdown(f"""
    <div class="reliability-band">
        <div class="eyebrow">Reliability and accuracy test</div>
        <div class="section-title" style="color:#ffffff;">Evidence behind the classification engine</div>
        <p>{benchmark_summary["method"]} In simple terms, the website classifies a domain, then checks whether it matches a known SCOP-style answer.</p>
        <div class="reliability-metrics">
            <div class="reliability-metric"><strong>{benchmark_summary["accuracy"]}</strong><span>Benchmark accuracy</span></div>
            <div class="reliability-metric"><strong>{benchmark_summary["tested"]}</strong><span>Sequences tested</span></div>
            <div class="reliability-metric"><strong>{benchmark_summary["matched"]}</strong><span>Correct matches</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.show_upload_panel:
        st.markdown('<div class="input-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Upload FASTA File</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-copy">Upload a FASTA file or download an example file with multiple sample sequences. You can load the first sequence into the editor, or upload the full file to the backend database.</div>', unsafe_allow_html=True)
        fasta_file = st.file_uploader("Choose FASTA file", type=["fa", "fasta", "txt"], help="Select a FASTA file containing one or more protein sequences.")
        sample_col, download_col = st.columns([1, 1])
        with sample_col:
            if st.button("Load example sequence", key="load_sample_sequence"):
                sample_proteins = parse_fasta_string_simple(SAMPLE_FASTA_CONTENT)
                if sample_proteins:
                    st.session_state.home_sequence_input = sample_proteins[0]["sequence"]
                    st.success("Example sequence loaded into the input area.")
                else:
                    st.error("Unable to load the example FASTA sequence.")
        with download_col:
            st.download_button(
                "Download example FASTA",
                data=SAMPLE_FASTA_CONTENT,
                file_name="example_sequences.fasta",
                mime="text/plain",
                help="Download an example FASTA file containing multiple sample sequences.",
            )
        fasta_file_bytes = None
        fasta_file_info = None
        if fasta_file is not None:
            try:
                fasta_file_bytes = fasta_file.getvalue() if hasattr(fasta_file, "getvalue") else fasta_file.read()
            except Exception:
                fasta_file_bytes = fasta_file.read()
            if fasta_file_bytes is not None:
                proteins = get_first_sequence_from_fasta_bytes(fasta_file_bytes)
                fasta_file_info = {
                    "count": len(proteins),
                    "first_header": proteins[0]["header"] if proteins else "",
                    "first_length": len(proteins[0]["sequence"]) if proteins else 0,
                }
        if fasta_file_info:
            st.info(f"Detected {fasta_file_info['count']} sequence(s). First sequence: {fasta_file_info['first_header']} ({fasta_file_info['first_length']} aa)")
            load_col, upload_col = st.columns([1, 1])
            with load_col:
                if st.button("Load first sequence", key="load_first_sequence"):
                    proteins = get_first_sequence_from_fasta_bytes(fasta_file_bytes)
                    if not proteins:
                        st.error("No valid FASTA sequence found in the uploaded file.")
                    else:
                        st.session_state.home_sequence_input = proteins[0]["sequence"]
                        st.success("First sequence loaded into the input area.")
            with upload_col:
                if st.button("Upload FASTA to database", key="upload_fasta_to_db"):
                    with st.spinner("Uploading FASTA file..."):
                        try:
                            files = {"file": (fasta_file.name, io.BytesIO(fasta_file_bytes), "text/plain")}
                            resp = make_authenticated_request("/api/upload-fasta", files=files)
                            if resp.status_code == 200:
                                payload = resp.json()
                                st.success(payload.get("message", "FASTA file uploaded successfully."))
                                added = payload.get("new_proteins_added")
                                skipped = payload.get("duplicates_skipped")
                                st.write(f"New proteins added: {added}. Duplicates skipped: {skipped}.")
                            else:
                                st.error(api_error_message(resp))
                        except Exception as exc:
                            st.error(f"Upload failed: {exc}")
        elif fasta_file is not None:
            st.warning("This file did not contain recognizable FASTA sequences. Please upload a valid FASTA file.")
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.domain_search_result:
        domain_name = st.session_state.domain_search_result
        st.markdown("---")
        st.markdown(f'<div class="section-title">Search Result: {html.escape(domain_name)}</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-copy">This domain is covered by the classification engine. Run a sequence below to compare your protein against this and other domain rules.</div>',
            unsafe_allow_html=True,
        )
        render_domain_knowledge_cards([{"domain": domain_name, "confidence": 1.0}])
    
    st.markdown('<div class="input-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Sequence Input</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-copy">Paste a FASTA sequence or a plain amino acid sequence. Amino acids are usually written as one-letter codes such as A, C, D, E, F, and G.</div>', unsafe_allow_html=True)
    user_input = st.text_area("**Protein Sequence**", height=200, key="home_sequence_input")
    if user_input:
        seq_len = len(user_input.replace(" ", "").replace("\n", ""))
        st.caption(f"{seq_len} amino acids")
    else:
        st.caption("0 amino acids")
    
    col_btn, _ = st.columns([1, 3])
    with col_btn:
        analyze_btn = st.button("Analyze Sequence", type="primary", key="analyze_sequence_button", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="ready-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">What You Get</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-copy">Each run gives a short report that is useful even if the user is new to protein analysis.</div>', unsafe_allow_html=True)
    st.markdown("""
    <ul class="bullet-list">
        <li><strong>Classified domain</strong> - the most likely protein domain and confidence score</li>
        <li><strong>Simple explanation</strong> - what the domain may do in the protein</li>
        <li><strong>SCOP comparison</strong> - compare classifications with a known reference label</li>
    </ul>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="feature-band">
        <div class="eyebrow">Special feature</div>
        <div class="section-title">Residue-by-residue property map</div>
        <p>Many tools stop after naming a domain. This website also shows how hydrophobicity and charge change along the sequence, so users can see which parts may sit inside a membrane, bind other molecules, or form important active regions.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="note-text"><strong>Note:</strong> Paste your protein sequence in single-letter amino acid code. The rule engine recognises globin, zinc finger, kinase, immunoglobulin, transmembrane, and serine protease domains.</div>', unsafe_allow_html=True)
    
    # Prediction and special features
    run_prediction = (analyze_btn or st.session_state.pending_header_prediction) and user_input
    if run_prediction:
        st.session_state.pending_header_prediction = False
        with st.spinner("Analyzing sequence..."):
            prog = st.progress(0)
            for i in range(100):
                time.sleep(0.005)
                prog.progress(i+1)
            try:
                resp = make_authenticated_request("/api/predict", method="POST",
                                                  data={"query": user_input, "use_rule_based": True, "analyze_sequence": True})
                prog.empty()
                if resp.status_code == 200:
                    result = resp.json()
                    st.session_state.last_prediction_result = result
                    analyzed_sequence = result.get("analyzed_sequence", user_input)
                    st.session_state.last_prediction_sequence = analyzed_sequence
                    top_predictions = result.get("rule_based_predictions") or []
                    st.session_state.home_scop_predicted_domain = top_predictions[0].get("domain", "") if top_predictions else ""
                    st.session_state.predictions_made += 1
                    st.balloons()
                    st.success("Classification complete!")

                    for warning in result.get("warnings", []):
                        st.warning(warning)

                    query_info = result.get("query_info", {})
                    if query_info:
                        st.caption(
                            f"Input type: {query_info.get('input_type', 'sequence')} | "
                            f"Analyzed length: {query_info.get('analyzed_length', len(analyzed_sequence))} amino acids | "
                            f"Dataset matches: {query_info.get('matched_dataset_records', 0)}"
                        )
                    render_explanation("Protein sequence interpretation", explain_sequence_result(analyzed_sequence, result))

                    if result.get("predictions"):
                        st.subheader("Matched Dataset Records")
                        dataset_rows = []
                        for protein in result["predictions"]:
                            dataset_rows.append({
                                "Protein ID": protein.get("protein_id"),
                                "Name": protein.get("protein_name"),
                                "Organism": protein.get("organism"),
                                "Domain / Family": protein.get("domain_family") or protein.get("domain"),
                                "Function": protein.get("function"),
                                "Length": protein.get("length"),
                            })
                        st.dataframe(pd.DataFrame(dataset_rows), use_container_width=True)
                    
                    if result.get('rule_based_predictions'):
                        st.subheader("Classified Domains")
                        df_rules = pd.DataFrame(result['rule_based_predictions'])
                        # Add tooltip column using HTML
                        tooltip_html = []
                        for domain in df_rules['domain']:
                            explanation = domain_rule_tooltip(domain)
                            tooltip_html.append(f'<span class="tooltip-hover" title="{explanation}">Info</span>')
                        df_rules['Rule explanation'] = tooltip_html
                        st.dataframe(df_rules[['domain','confidence','description','Rule explanation']], use_container_width=True)
                        render_domain_knowledge_cards(result['rule_based_predictions'])
                    else:
                        st.info("No known domain rule matched strongly for this sequence. The physicochemical analysis below is still calculated from the submitted amino-acid sequence.")
                    
                    if result.get('analysis_results'):
                        st.subheader("Physicochemical Properties")
                        props = result['analysis_results'].get('physicochemical_properties', {})
                        cols = st.columns(4)
                        cols[0].metric("Molecular Weight", f"{props.get('molecular_weight',0):.0f} Da")
                        cols[1].metric("Isoelectric Point", f"{props.get('isoelectric_point',0):.2f}")
                        cols[2].metric("Instability Index", f"{props.get('instability_index',0):.1f}")
                        cols[3].metric("GRAVY", f"{props.get('gravy',0):.2f}")
                        render_explanation("What these protein properties mean", explain_physicochemical_properties(props))
                        
                        if result['analysis_results'].get('amino_acid_composition'):
                            st.subheader("Amino Acid Composition")
                            composition = result['analysis_results']['amino_acid_composition']
                            aa_df = pd.DataFrame(list(composition.items()), columns=['AA','%'])
                            fig = px.bar(aa_df, x='AA', y='%', title="Amino Acid Composition by Residue", color='%', color_continuous_scale=PLOTLY_CONTINUOUS_SCALE)
                            fig.update_traces(marker_line_color=THEME_COLORS["surface"], marker_line_width=1)
                            apply_plotly_theme(fig, height=360)
                            st.plotly_chart(fig, use_container_width=True)
                            render_explanation("What the composition graph shows", explain_amino_acid_composition(composition))
                        
                        if result['analysis_results'].get('motifs_found'):
                            st.subheader("Detected Motifs")
                            motifs_found = result['analysis_results']['motifs_found']
                            st.json(motifs_found)
                            render_explanation("Why these motifs matter", explain_detected_motifs(motifs_found))
                    
                    # Special feature: Residue property viewer
                    st.subheader("Residue-by-Residue Properties")
                    show_residue_properties(analyzed_sequence)
                    
                    st.download_button("Download Report (JSON)", data=json.dumps(result, indent=2), file_name=f"classification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", mime="application/json")
                else:
                    st.error(api_error_message(resp))
            except Exception as e:
                st.error(f"Error: {str(e)}")

    last_predictions = (st.session_state.last_prediction_result or {}).get("rule_based_predictions", [])
    suggested_domain = last_predictions[0].get("domain", "") if last_predictions else ""
    if st.session_state.last_prediction_result:
        st.markdown("---")
        render_scop_comparison_panel("home_scop", suggested_domain=suggested_domain, show_summary=True)
    else:
        st.markdown("---")
        st.info("Run a classification first, then the benchmark comparison button will appear here with the classified domain filled in.")

# ---------- BENCHMARK PAGE ----------
elif current_page == "Benchmark":
    st.markdown('<p class="main-title">Benchmark and SCOP Compare</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">SCOP is a reference system that groups proteins by structural class and fold. This page helps compare your classification with a known SCOP-style label.</p>', unsafe_allow_html=True)

    last_predictions = (st.session_state.last_prediction_result or {}).get("rule_based_predictions", [])
    suggested_domain = last_predictions[0].get("domain", "") if last_predictions else ""
    render_scop_comparison_panel("benchmark_scop", suggested_domain=suggested_domain, show_summary=True)

# ---------- ADMIN PAGE ----------
elif current_page == "Admin":
    if not is_admin:
        st.error("Admin access required.")
        st.stop()

    headers = {"Authorization": f"Bearer {st.session_state.backend_token}"}
    try:
        admin_resp = requests.get(f"{API_URL}/api/admin/users", headers=headers, timeout=30)
    except requests.RequestException as exc:
        st.error(f"Could not load admin users: {exc}")
        admin_resp = None

    stats_payload = {}
    try:
        stats_resp = make_authenticated_request("/api/stats", method="GET")
        if stats_resp.status_code == 200:
            stats_payload = stats_resp.json()
    except requests.RequestException:
        stats_payload = {}

    if admin_resp is None:
        st.stop()
    if admin_resp.status_code != 200:
        st.error(api_error_message(admin_resp))
        st.stop()

    admin_payload = admin_resp.json()
    admin_users = admin_payload.get("users", [])

    rows = []
    for item in admin_users:
        rows.append({
            "Name": item.get("name", ""),
            "Email": item.get("email", ""),
            "Role": item.get("role", "user"),
            "Active": item.get("is_active", True),
            "Classifications": item.get("predictions_count", 0),
            "Saved Searches": item.get("saved_searches", 0),
            "Created": (item.get("created_at") or "")[:10],
            "Last Login": (item.get("last_login") or "")[:10],
            "User ID": item.get("user_id", ""),
        })
    users_df = pd.DataFrame(rows)
    saved_searches = stats_payload.get("saved_searches", sum(item.get("saved_searches", 0) for item in admin_users))
    benchmark_summary = load_benchmark_summary()

    st.markdown('<p class="main-title">Admin Dashboard</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Manage users, review account activity, and monitor the protein analysis workspace.</p>', unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Users", admin_payload.get("total_users", 0))
    c2.metric("Active Users", admin_payload.get("active_users", 0))
    c3.metric("Admins", admin_payload.get("admin_users", 0))
    c4.metric("Saved Searches", saved_searches)
    c5.metric("Benchmark Accuracy", benchmark_summary.get("accuracy", "Unavailable"))

    st.markdown('<div class="section-title">Workspace Overview</div>', unsafe_allow_html=True)
    overview_col, actions_col = st.columns([1.25, 0.75])
    with overview_col:
        o1, o2, o3 = st.columns(3)
        o1.metric("Protein Records", stats_payload.get("total_proteins", "Unavailable"))
        o2.metric("Known Domains", stats_payload.get("unique_domains", "Unavailable"))
        o3.metric("Suggestions", stats_payload.get("popular_searches", "Unavailable"))
    with actions_col:
        st.markdown('<div class="section-copy">Admin quick actions</div>', unsafe_allow_html=True)
        a1, a2 = st.columns(2)
        with a1:
            if st.button("Refresh", key="admin_refresh_dashboard", use_container_width=True):
                fetch_user_data.clear()
                st.rerun()
            if st.button("Benchmark", key="admin_open_benchmark", use_container_width=True):
                go_to("Benchmark")
                st.rerun()
        with a2:
            if st.button("Suggestions", key="admin_open_popular", use_container_width=True):
                go_to("Suggestions")
                st.rerun()
            if st.button("Profile", key="admin_open_profile", use_container_width=True):
                go_to("Profile")
                st.rerun()

    if not admin_users:
        st.info("No users found.")
    else:
        chart_col, recent_col = st.columns([1, 1])
        with chart_col:
            st.subheader("Roles")
            role_counts = users_df["Role"].fillna("user").value_counts().reset_index()
            role_counts.columns = ["Role", "Count"]
            fig_roles = px.pie(
                role_counts,
                names="Role",
                values="Count",
                hole=0.45,
                color_discrete_sequence=PLOTLY_COLORWAY,
            )
            fig_roles.update_traces(textposition="inside", textinfo="percent+label")
            fig_roles.update_layout(
                height=310,
                margin=dict(l=20, r=20, t=20, b=20),
                paper_bgcolor=THEME_COLORS["surface"],
                font=dict(color=THEME_COLORS["ink"]),
                showlegend=True,
            )
            st.plotly_chart(fig_roles, use_container_width=True)
        with recent_col:
            st.subheader("Account Status")
            status_df = users_df.copy()
            status_df["Status"] = status_df["Active"].map(lambda active: "Active" if active else "Disabled")
            status_counts = status_df["Status"].value_counts().reset_index()
            status_counts.columns = ["Status", "Count"]
            fig_status = px.bar(
                status_counts,
                x="Status",
                y="Count",
                color="Status",
                color_discrete_sequence=[THEME_COLORS["primary"], THEME_COLORS["accent"]],
            )
            fig_status.update_layout(showlegend=False)
            apply_plotly_theme(fig_status, height=310)
            st.plotly_chart(fig_status, use_container_width=True)

        st.subheader("Recent Accounts")
        st.dataframe(
            users_df[["Name", "Email", "Role", "Active", "Classifications", "Saved Searches", "Created", "Last Login"]],
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("---")
        st.subheader("Manage User")
        options = {
            f"{item.get('name', 'User')} - {item.get('email', '')} ({item.get('role', 'user')})": item
            for item in admin_users
        }
        selected_label = st.selectbox("Select user", list(options.keys()))
        selected_user = options[selected_label]
        selected_user_id = selected_user.get("user_id")

        with st.form("admin_user_update_form"):
            edit_name = st.text_input("Name", value=selected_user.get("name", ""))
            edit_role = st.selectbox(
                "Role",
                ["user", "admin"],
                index=1 if selected_user.get("role") == "admin" else 0,
            )
            edit_active = st.checkbox("Account active", value=selected_user.get("is_active", True))
            if st.form_submit_button("Save User Changes", use_container_width=True):
                update_resp = requests.patch(
                    f"{API_URL}/api/admin/users/{selected_user_id}",
                    headers=headers,
                    json={"name": edit_name, "role": edit_role, "is_active": edit_active},
                    timeout=30,
                )
                if update_resp.status_code == 200:
                    fetch_user_data.clear()
                    st.success("User updated.")
                    st.rerun()
                else:
                    st.error(api_error_message(update_resp))

        st.markdown("---")
        st.subheader("Danger Zone")
        confirm_delete = st.checkbox(f"I understand this deletes {selected_user.get('email', 'this user')} and their saved searches.")
        if st.button("Delete Selected User", type="primary", disabled=not confirm_delete, key="admin_delete_selected_user", use_container_width=False):
            delete_resp = requests.delete(
                f"{API_URL}/api/admin/users/{selected_user_id}",
                headers=headers,
                timeout=30,
            )
            if delete_resp.status_code == 200:
                st.success(delete_resp.json().get("message", "User deleted."))
                st.rerun()
            else:
                st.error(api_error_message(delete_resp))

# ---------- PROFILE TAB (with User Dashboard) ----------
elif current_page == "Profile":
    st.markdown('<p class="main-title">User Profile</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Manage account details and keep the existing classification dashboard in one place.</p>', unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="profile-summary">
        <img src="{avatar_url}" alt="User profile picture">
        <div>
            <div class="section-title">{user_data.get('name', 'User')}</div>
            <div class="section-copy">{user_data.get('email', 'No email available')}</div>
            <span class="tag">{user_data.get('auth_provider', 'account').title()} account</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Dashboard row 1: stats cards
    total_pred = user_data.get('predictions_count', 0)
    # Determine favourite domain from history
    all_domains = []
    for pred in history:
        domains = [d['domain'] for d in pred.get('result', {}).get('rule_based_predictions', [])]
        all_domains.extend(domains)
    fav_domain = Counter(all_domains).most_common(1)
    fav_domain_name = fav_domain[0][0] if fav_domain else "None"
    last_active = user_data.get('last_login', '')
    last_active_str = last_active[:10] if last_active else "Not available"
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.metric("Total Classifications", total_pred)
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.metric("Favourite Domain", fav_domain_name)
        st.markdown('</div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.metric("Last Active", last_active_str)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Dashboard row 2: classification trend (mock line chart using timestamps)
    if history:
        timestamps = [pred.get('timestamp', '')[:10] for pred in history if pred.get('timestamp')]
        date_counts = Counter(timestamps)
        trend_df = pd.DataFrame(date_counts.items(), columns=['Date', 'Classifications']).sort_values('Date')
        if not trend_df.empty:
            st.markdown('<div class="page-section-heading">Classification Trend</div>', unsafe_allow_html=True)
            fig = px.line(trend_df, x='Date', y='Classifications', markers=True, title="Number of classifications per day")
            fig.update_traces(
                line=dict(color=THEME_COLORS["primary"], width=3),
                marker=dict(color=THEME_COLORS["accent"], size=8, line=dict(color=THEME_COLORS["surface"], width=1)),
            )
            apply_plotly_theme(fig, height=360)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No classification history yet. Make your first classification on the Home tab.")
    
    # Dashboard row 3: top classified domains bar chart
    if all_domains:
        domain_counts = Counter(all_domains)
        top_domains_df = pd.DataFrame(domain_counts.most_common(5), columns=['Domain', 'Count'])
        st.markdown('<div class="page-section-heading">Your Most Classified Domains</div>', unsafe_allow_html=True)
        fig = px.bar(top_domains_df, x='Domain', y='Count', title="Most Classified Domains by Count", color='Count', color_continuous_scale=PLOTLY_CONTINUOUS_SCALE)
        fig.update_traces(marker_line_color=THEME_COLORS["surface"], marker_line_width=1)
        apply_plotly_theme(fig, height=360)
        st.plotly_chart(fig, use_container_width=True)
    
    # Account info card
    st.markdown("---")
    st.markdown('<div class="page-section-heading">Account Information</div>', unsafe_allow_html=True)
    col_a, col_b = st.columns([1,2])
    with col_a:
        st.image(user_data.get('picture', 'https://cdn-icons-png.flaticon.com/512/3135/3135715.png'), width=120)
    with col_b:
        st.markdown(f"""
        <div class="profile-detail">
            <div><strong>Name:</strong> {html.escape(str(user_data.get('name', 'N/A')))}</div>
            <div><strong>Email:</strong> {html.escape(str(user_data.get('email', 'N/A')))}</div>
            <div><strong>Member since:</strong> {html.escape(str(user_data.get('created_at', 'N/A')[:10] if user_data.get('created_at') else 'N/A'))}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Recent history (compact list)
    st.markdown("---")
    st.markdown('<div class="page-section-heading">Recent Activity</div>', unsafe_allow_html=True)
    if history:
        for pred in history[:5]:
            timestamp_label = html.escape(format_history_timestamp(pred.get('timestamp', '')))
            query = html.escape(truncate_text(pred.get('query', ''), 60))
            domains = [d.get('domain', '') for d in pred.get('result', {}).get('rule_based_predictions', []) if d.get('domain')]
            domain_label = html.escape(" - ".join(domains) if domains else "No domain saved")
            st.markdown(f"""
            <div class="activity-card">
                <strong>{timestamp_label}</strong><br>
                <code>{query}</code><br>
                <span class="tag">{domain_label}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No activity yet. Use the Home tab to classify domains.")

# ---------- HISTORY SEARCHES PAGE ----------
elif current_page == "History Searches":
    st.markdown('<p class="main-title">History Searches</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Review your recent protein sequence searches and classifications.</p>', unsafe_allow_html=True)

    if history:
        for pred in history:
            timestamp_label = html.escape(format_history_timestamp(pred.get('timestamp', '')))
            query = html.escape(truncate_text(pred.get('query', ''), 120))
            domains = [d.get('domain', '') for d in pred.get('result', {}).get('rule_based_predictions', []) if d.get('domain')]
            domain_label = html.escape(" - ".join(domains) if domains else "No domain saved")
            st.markdown(f"""
            <div class="activity-card">
                <strong>{timestamp_label}</strong><br>
                <code>{query}</code><br>
                <span class="tag">{domain_label}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No saved searches yet. Analyze a sequence on the Home page first.")

# ---------- DOWNLOADS PAGE ----------
elif current_page == "Downloads":
    st.markdown('<p class="main-title">Downloads</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Download the latest classification report generated in this session.</p>', unsafe_allow_html=True)

    if st.session_state.last_prediction_result:
        st.download_button(
            "Download Latest Report (JSON)",
            data=json.dumps(st.session_state.last_prediction_result, indent=2),
            file_name=f"classification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            type="primary",
        )
        if st.session_state.last_prediction_sequence:
            st.code(st.session_state.last_prediction_sequence, language=None)
    else:
        st.info("No downloadable report yet. Run a classification on the Home page first.")

# ---------- SUGGESTIONS PAGE ----------
elif current_page in ("Suggestions", "Popular Searches"):
    st.markdown('<p class="main-title">Protein Suggestions</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Suggested sequences from user activity and curated examples you can reuse.</p>', unsafe_allow_html=True)
    
    real_popular = []
    try:
        pop_resp = make_authenticated_request("/api/popular-searches", method="GET")
        if pop_resp.status_code == 200:
            real_popular = pop_resp.json()
    except:
        pass
    
    decoy_searches = [
        {"query": "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHGKKVADALTNAVAHVDDMPNALSALSDLHAHKLRVDPVNFKLLSHCLLVTLAAHLPAEFTPAVHASLDKFLASVSTVLTSKYR", "count": 42, "name": "Hemoglobin Alpha (P69905)"},
        {"query": "CCHHRRKKHHCC", "count": 38, "name": "Zinc Finger (C2H2 type)"},
        {"query": "KVFGRCELAAAMKRHGLDNYRGYSLGNWVCAAKFESNFNTQATNRNTDGSTDYGILQINSRWWCNDGRTPGSRNLCNIPCSALLSSDITASVNCAKKIVSDGNGMNAWVAWRNRCKGTDVQAWIRGCRL", "count": 27, "name": "Lysozyme C (P61626)"},
        {"query": "MSTPQRSTUVWXYZABCDEFGHIKLMNOP", "count": 19, "name": "Kinase-like Domain Pattern"},
        {"query": "P69905", "count": 15, "name": "UniProt ID: Hemoglobin subunit alpha"}
    ]
    
    combined = []
    for item in real_popular[:5]:
        combined.append({"query": item.get("query"), "count": item.get("count"), "name": item.get("query", "")[:50]})
    existing_queries = {d["query"] for d in combined if d.get("query")}
    for decoy in decoy_searches:
        if decoy["query"] not in existing_queries:
            combined.append(decoy)
            if len(combined) >= 10:
                break
    
    if combined:
        for i, item in enumerate(combined, 1):
            title = clean_suggestion_title(item.get('name') or item.get('query', '')[:50])
            with st.expander(f"#{i} - {title}"):
                st.code(item['query'], language=None)
                if st.button(f"Use this sequence", key=f"use_{i}"):
                    st.info("Go to the Home tab, paste this sequence, and click Analyze.")
    else:
        st.info("No suggestions recorded yet. Be the first to contribute!")
    
    st.markdown("---")
    
