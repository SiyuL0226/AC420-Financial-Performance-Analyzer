import math

import streamlit as st
import yfinance as yf

from financial_ratios import (
    calculate_profit_margin,
    calculate_roa,
    calculate_roe,
    calculate_current_ratio,
    calculate_debt_to_equity,
    calculate_asset_turnover,
)

# ==================================================
# 1. PAGE SETTINGS AND VISUAL STYLE
# ==================================================
st.set_page_config(
    page_title="Finance Analyzer",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .stApp { background-color: #FCFCFC; }
        section[data-testid="stSidebar"] {
            background-color: #F8F9F9;
            border-right: 1px solid #E5E7EB;
        }
        div.stButton > button[kind="primary"] {
            background-color: #23827C;
            border-color: #23827C;
            color: white;
            border-radius: 9px;
        }
        div.stButton > button[kind="primary"]:hover {
            background-color: #176E69;
            border-color: #176E69;
            color: white;
        }
        div[data-testid="stMetric"] { padding: 6px 4px; }
        div[data-testid="stMetricValue"] { font-weight: 650; }
        div[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 14px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# SIC grouping explicitly assigned for this project.
# Add other tickers here only after you verify their industry classification.
ASSIGNED_SIC = {
    "MSFT": "7372 — Services: Prepackaged Software",
}


def format_ratio(value, is_percent=False):
    """Use the same percent/multiple display rules as the original app."""
    try:
        number = float(value)
        if not math.isfinite(number):
            return "N/A"
        return f"{number:.2%}" if is_percent else f"{number:.2f}x"
    except (TypeError, ValueError):
        return "N/A"


def metric_card(label, value, is_percent=False):
    with st.container(border=True):
        st.metric(label, format_ratio(value, is_percent))


def load_company(ticker):
    """Load one company and calculate the six existing ratios."""
    company = yf.Ticker(ticker)
    income_statement = company.get_income_stmt(freq="yearly")
    balance_sheet = company.get_balance_sheet(freq="yearly")

    if income_statement.empty or balance_sheet.empty:
        raise ValueError("Financial data is unavailable for this ticker.")

    # Company details are helpful for the UI but are not required to calculate ratios.
    try:
        info = company.get_info() or {}
    except Exception:
        info = {}

    fiscal_year_end = income_statement.columns[0]
    if hasattr(fiscal_year_end, "strftime"):
        fiscal_year_end = fiscal_year_end.strftime("%B %Y")
    else:
        fiscal_year_end = str(fiscal_year_end)

    ratios = {
        "ROA": (calculate_roa(income_statement, balance_sheet), True),
