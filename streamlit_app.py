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
        "ROE": (calculate_roe(income_statement, balance_sheet), True),
        "Profit Margin": (calculate_profit_margin(income_statement), True),
        "Current Ratio": (calculate_current_ratio(balance_sheet), False),
        "Debt-to-Equity": (calculate_debt_to_equity(balance_sheet), False),
        "Asset Turnover": (
            calculate_asset_turnover(income_statement, balance_sheet), False
        ),
    }

    return {
        "ticker": ticker,
        "company_name": info.get("longName") or info.get("shortName") or ticker,
        "sector": info.get("sector") or "Not available",
        "yahoo_industry": info.get("industry") or "Not available",
        "assigned_sic": ASSIGNED_SIC.get(ticker, "Not assigned yet"),
        "fiscal_year_end": fiscal_year_end,
        "income_statement": income_statement,
        "balance_sheet": balance_sheet,
        "ratios": ratios,
    }


# ==================================================
# 2. SESSION STATE: KEEP DATA WHILE CHANGING TABS
# ==================================================
if "report" not in st.session_state:
    st.session_state.report = None
if "has_loaded" not in st.session_state:
    st.session_state.has_loaded = False
if "load_error" not in st.session_state:
    st.session_state.load_error = None

# ==================================================
# 3. LEFT SIDEBAR: COMPANY INPUT + THREE TABS
# ==================================================
with st.sidebar:
    st.markdown("### ↗ Finance Analyzer")
    st.divider()

    ticker = st.text_input("Company", value="MSFT").strip().upper()
    analyze_clicked = st.button(
        "Analyze", type="primary", use_container_width=True
    )

    st.write("")
    page = st.radio(
        "Navigation",
        ["Company Overview", "Financial Analysis", "Industry Comparison"],
        label_visibility="collapsed",
        key="navigation",
    )

    st.divider()
    st.caption("AC420 · Financial Performance Analyzer")

# Load MSFT on the first visit, then load a new ticker when Analyze is clicked.
# Do NOT refetch on each tab change.
if analyze_clicked or not st.session_state.has_loaded:
    st.session_state.has_loaded = True
    st.session_state.report = None
    st.session_state.load_error = None

    if not ticker:
        st.session_state.load_error = "Please enter a stock ticker."
    else:
        with st.spinner(f"Loading financial data for {ticker}..."):
            try:
                st.session_state.report = load_company(ticker)
            except Exception as exc:
                st.session_state.load_error = (
                    f"Unable to retrieve or process financial data for {ticker}: {exc}"
                )

if st.session_state.load_error:
    st.error(st.session_state.load_error)

report = st.session_state.report
if report is None:
    st.info("Enter a valid stock ticker in the sidebar and click Analyze.")
    st.stop()

# The company title stays visible on all three pages.
st.title(report["company_name"])
st.caption(
    f"{report['ticker']} · Fiscal year ended {report['fiscal_year_end']}"
)

# ==================================================
# 4. TAB 1 — COMPANY OVERVIEW
# ==================================================
if page == "Company Overview":
    st.header("Financial Overview")

    # Four headline metrics; values come from existing ratio functions.
    overview_labels = ["ROA", "ROE", "Profit Margin", "Current Ratio"]
    overview_columns = st.columns(4)
    for column, label in zip(overview_columns, overview_labels):
        value, is_percent = report["ratios"][label]
        with column:
            metric_card(label, value, is_percent)

    st.subheader("Company Information")
    with st.container(border=True):
        left, middle, right = st.columns([1, 2, 1.3])
        with left:
            st.caption("Ticker")
            st.write(report["ticker"])
            st.caption("Sector")
            st.write(report["sector"])
        with middle:
            st.caption("Assigned industry classification (SIC)")
            st.write(report["assigned_sic"])
            st.caption("Yahoo Finance industry (reference only)")
            st.write(report["yahoo_industry"])
        with right:
            st.caption("Fiscal year ended")
            st.write(report["fiscal_year_end"])

    st.subheader("Financial Performance Summary")
    with st.container(border=True):
        st.write(
            "Placeholder: Add a short 2–4 sentence assessment of "
            "profitability, liquidity, and overall financial performance."
        )

# ==================================================
# 5. TAB 2 — FINANCIAL ANALYSIS
# ==================================================
elif page == "Financial Analysis":
    st.header("Financial Analysis")
    st.subheader("Financial Ratios")

    ratio_items = list(report["ratios"].items())
    for start in (0, 3):
        columns = st.columns(3)
        for column, (label, (value, is_percent)) in zip(
            columns, ratio_items[start : start + 3]
        ):
            with column:
                metric_card(label, value, is_percent)

    st.subheader("Historical Ratio Trends")
    st.info("Placeholder: Multi-year line charts for the six financial ratios.")

    st.subheader("Year-over-Year Comparison")
    st.info("Placeholder: Annual ratio changes and year-over-year comparisons.")

    st.subheader("DuPont Analysis")
    st.info("Placeholder: ROE = Profit Margin × Asset Turnover × Equity Multiplier.")

    # Raw statements are accessible without a separate main navigation tab.
    with st.expander("View Raw Financial Statements"):
        st.subheader("Income Statement")
        st.dataframe(report["income_statement"], use_container_width=True)
        st.subheader("Balance Sheet")
        st.dataframe(report["balance_sheet"], use_container_width=True)

# ==================================================
# 6. TAB 3 — INDUSTRY COMPARISON
# ==================================================
elif page == "Industry Comparison":
    st.header("Industry Comparison")
    st.caption(f"Assigned classification: {report['assigned_sic']}")

    st.subheader("Compustat Industry Medians")
    st.info("Placeholder: Import the Compustat benchmark CSV for this industry.")

    st.subheader("Company vs. Industry")
    with st.container(border=True):
        st.write("Placeholder: Grouped bar charts comparing each ratio with its industry median.")

    st.subheader("Benchmark Indicators")
    st.info(
        "Placeholder: Show above/below industry-median indicators. "
        "Interpret each ratio before labeling performance as stronger or weaker."
    )
