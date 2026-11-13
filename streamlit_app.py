
import html
import math
from pathlib import Path
from urllib.parse import quote, urlparse

import pandas as pd
import streamlit as st
import yfinance as yf

from financial_ratios import (
    calculate_profit_margin, calculate_roa, calculate_roe,
    calculate_current_ratio, calculate_debt_to_equity,
    calculate_asset_turnover,
)

from historical_analysis import (
    ALL_RATIOS, PERCENT_RATIOS,
    calculate_historical_ratios, calculate_yoy_changes,
)

from dupont_analysis import calculate_dupont
from industry_benchmark import calculate_industry_medians


# ==========================================
# PAGE DESIGN AND SETTINGS
# ==========================================

st.set_page_config(
    page_title="Finance Analyzer",
    page_icon=":material/monitoring:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.html("""
<style>
.stApp {
    background: #FCFCFC;
}

section[data-testid="stSidebar"] {
    background: #F8F9F9;
    border-right: 1px solid #E4E7E7;
}

/* Additional spacing above the company heading */
section.main .block-container,
[data-testid="stMainBlockContainer"] {
    max-width: 1150px;
    padding-top: 3.5rem !important;
}

div.stButton > button[kind="primary"] {
    background: #23827C;
    border-color: #23827C;
    color: white;
    border-radius: 9px;
}

div.stButton > button[kind="primary"]:hover {
    background: #176E69;
    border-color: #176E69;
    color: white;
}

div[data-testid="stMetric"] {
    padding: 8px 5px;
}

div[data-testid="stMetricValue"] {
    font-weight: 650;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 14px;
}
</style>
""")


# ==========================================
# INDUSTRY CLASSIFICATIONS
# ==========================================

ASSIGNED_SIC = {
    "MSFT": "7372 — Services: Prepackaged Software",
}

FALLBACK_WEBSITES = {
    "MSFT": "https://www.microsoft.com",
    "AAPL": "https://www.apple.com",
    "GOOGL": "https://www.google.com",
    "GOOG": "https://www.google.com",
    "AMZN": "https://www.amazon.com",
    "NVDA": "https://www.nvidia.com",
    "META": "https://www.meta.com",
}

CSV_PATH = (
    Path(__file__).resolve().parent
    / "data"
    / "compustat_annual.csv"
)


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def is_valid(value):
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError, OverflowError):
        return False


def format_ratio(value, is_percent=False):
    if not is_valid(value):
        return "N/A"

    if is_percent:
        return f"{value:.2%}"

    return f"{value:.2f}x"


def metric_card(label, value, is_percent=False):
    with st.container(border=True):
        st.metric(
            label,
            format_ratio(value, is_percent)
        )


def ratios_for_year(income, balance, year=None):
    return {
        "ROA": (
            calculate_roa(income, balance, year=year),
            True
        ),
        "ROE": (
            calculate_roe(income, balance, year=year),
            True
        ),
        "Profit Margin": (
            calculate_profit_margin(income, year=year),
            True
        ),
        "Current Ratio": (
            calculate_current_ratio(balance, year=year),
            False
        ),
        "Debt-to-Equity": (
            calculate_debt_to_equity(balance, year=year),
            False
        ),
        "Asset Turnover": (
            calculate_asset_turnover(income, balance, year=year),
            False
        ),
    }


# ==========================================
# LOAD COMPANY FINANCIAL DATA
# ==========================================

def load_company(ticker):

    company = yf.Ticker(ticker)

    income = company.get_income_stmt(freq="yearly")
    balance = company.get_balance_sheet(freq="yearly")

    if (
        income is None
        or balance is None
        or income.empty
        or balance.empty
    ):
        raise ValueError(
            "Annual financial statements are unavailable "
            "for this ticker."
        )

    try:
        info = company.get_info() or {}
    except Exception:
        info = {}

    latest_year = max(income.columns)

    return {
        "ticker": ticker,

        "company_name": (
            info.get("longName")
            or info.get("shortName")
            or ticker
        ),

        "sector": (
            info.get("sector") or "Not available"
        ),

        "yahoo_industry": (
            info.get("industry") or "Not available"
        ),

        "assigned_sic": ASSIGNED_SIC.get(
            ticker, "Not assigned yet"
        ),

        "fiscal_year_end": (
            pd.Timestamp(latest_year).strftime("%B %Y")
        ),

        "website": (
            info.get("website")
            or FALLBACK_WEBSITES.get(ticker, "")
        ),

        "income_statement": income,
        "balance_sheet": balance,

        "ratios": ratios_for_year(
            income, balance, year=latest_year
        ),
    }


# ==========================================
# CENTERED COMPANY HEADING WITH LOGO
# ==========================================

def show_company_heading(report):

    name = html.escape(str(report["company_name"]))
    ticker = html.escape(str(report["ticker"]))
    fiscal_year = html.escape(
        str(report["fiscal_year_end"])
    )

    website = str(
        report.get("website") or ""
    ).strip()

    if website and "://" not in website:
        website = "https://" + website

    domain = (
        urlparse(website).hostname
        if website else None
    )

    # Get the company website icon
    if domain and "." in domain:

        logo_url = (
            "https://www.google.com/s2/favicons?domain="
            + quote(domain, safe="")
            + "&sz=128"
        )

        icon_html = (
            f'<img src="{html.escape(logo_url, quote=True)}" '
            f'alt="{ticker} icon" '
            'style="width:26px;height:26px;'
            'object-fit:contain;border-radius:4px;">'
        )

    else:

        initial = ticker[:1] or "?"

        icon_html = (
            '<span style="'
            'width:26px;height:26px;'
            'display:inline-flex;'
            'align-items:center;'
            'justify-content:center;'
            'background:#23827C;'
            'color:white;'
            'border-radius:6px;'
            'font-size:14px;'
            'font-weight:600;">'
            f'{initial}</span>'
        )

    # Fixed spacing and line-height to prevent clipping
    st.html(f"""
    <div style="
        text-align: center;
        padding: 18px 10px 16px;
        margin: 0 auto 28px;
        overflow: visible;
    ">

        <h1 style="
            margin: 0 0 12px;
            padding: 4px 0;
            font-size: clamp(1.8rem, 3.5vw, 2.3rem);
            font-weight: 700;
            line-height: 1.35;
            overflow: visible;
        ">
            {name}
        </h1>

        <div style="
            display: flex;
            align-items: center;
            justify-content: center;
            flex-wrap: wrap;
            gap: 9px;
            color: #697177;
            font-size: 1rem;
            line-height: 1.5;
        ">

            {icon_html}

            <span>
                {ticker} · Fiscal year ended {fiscal_year}
            </span>

        </div>

    </div>
    """)


# ==========================================
# FINANCIAL PERFORMANCE SUMMARY
# ==========================================

def financial_summary(report):

    ratios = report["ratios"]
    name = report["company_name"]

    sentences = []

    pm = ratios["Profit Margin"][0]
    roe = ratios["ROE"][0]
    roa = ratios["ROA"][0]
    current = ratios["Current Ratio"][0]

    if is_valid(pm) and is_valid(roe):
        sentences.append(
            f"{name} reported a net profit margin of "
            f"{format_ratio(pm, True)} and ROE of "
            f"{format_ratio(roe, True)} for its "
            "latest fiscal year."
        )

    if is_valid(roa):
        sentences.append(
            f"ROA was {format_ratio(roa, True)}."
        )

    if is_valid(current):
        sentences.append(
            f"The current ratio was {format_ratio(current)}, "
            "comparing current assets to current liabilities."
        )

    sentences.append(
        "Historical trends and industry medians "
        "provide context for these results."
    )

    return " ".join(sentences)


# ==========================================
# DISPLAY FINANCIAL RATIO CARDS
# ==========================================

def display_ratio_grid(report, names, per_row):

    for start in range(0, len(names), per_row):

        cols = st.columns(per_row)

        for col, name in zip(
            cols, names[start:start + per_row]
        ):

            with col:

                value, is_percent = report["ratios"][name]

                metric_card(
                    name,
                    value,
                    is_percent
                )


# ==========================================
# PAGE 1 — COMPANY OVERVIEW
# ==========================================

def company_overview():

    report = st.session_state.report

    st.header("Financial Overview")

    display_ratio_grid(
        report,
        ["ROA", "ROE", "Profit Margin", "Current Ratio"],
        4
    )

    st.subheader("Company Information")

    with st.container(border=True):

        col1, col2, col3 = st.columns([1, 2, 1.2])

        with col1:
            st.caption("Ticker")
            st.write(report["ticker"])

            st.caption("Sector")
            st.write(report["sector"])

        with col2:
            st.caption("Assigned SIC classification")
            st.write(report["assigned_sic"])

            st.caption("Yahoo Finance industry")
            st.write(report["yahoo_industry"])

        with col3:
            st.caption("Fiscal year ended")
            st.write(report["fiscal_year_end"])

    st.subheader("Financial Performance Summary")

    with st.container(border=True):
        st.write(financial_summary(report))


# ==========================================
# PAGE 2 — FINANCIAL ANALYSIS
# ==========================================

def financial_analysis():

    report = st.session_state.report

    income = report["income_statement"]
    balance = report["balance_sheet"]

    st.header("Financial Analysis")

    # Six Financial Ratios
    st.subheader("Financial Ratios")

    display_ratio_grid(report, ALL_RATIOS, 3)

    # Historical Ratio Trends
    history = calculate_historical_ratios(
        income, balance
    )

    st.subheader("Historical Ratio Trends")

    if history.empty:
        st.warning(
            "Historical annual data is unavailable."
        )

    else:

        selected_ratio = st.selectbox(
            "Choose a ratio to graph",
            ALL_RATIOS
        )

        chart = history[
            ["Fiscal Year", selected_ratio]
        ].copy()

        chart[selected_ratio] = pd.to_numeric(
            chart[selected_ratio],
            errors="coerce"
        )

        if selected_ratio in PERCENT_RATIOS:
            chart[selected_ratio] *= 100

        chart = chart.dropna(
            subset=[selected_ratio]
        )

        if chart.empty:
            st.info(
                "No available values for this ratio."
            )

        else:

            st.line_chart(
                chart.set_index("Fiscal Year")
            )

            st.caption(
                "Chart units: percent (%)"
                if selected_ratio in PERCENT_RATIOS
                else "Chart units: multiples (x)"
            )

        with st.expander("View Historical Ratio Table"):

            display_history = history.copy()

            for label in ALL_RATIOS:

                display_history[label] = (
                    display_history[label].map(
                        lambda v, n=label: format_ratio(
                            v,
                            n in PERCENT_RATIOS
                        )
                    )
                )

            st.dataframe(
                display_history,
                width="stretch",
                hide_index=True
            )

    # Year-over-Year Comparison
    st.subheader("Year-over-Year Comparison")

    if history.empty:
        st.info(
            "Not enough historical data for "
            "year-over-year comparisons."
        )

    else:

        yoy = calculate_yoy_changes(history)
        display_yoy = yoy.copy()

        for label in display_yoy.columns:

            if label == "Fiscal Year":
                continue

            suffix = (
                " pp"
                if label.endswith("(pp)")
                else "x"
            )

            display_yoy[label] = display_yoy[label].map(
                lambda v, unit=suffix: (
                    f"{v:+.2f}{unit}"
                    if is_valid(v)
                    else "N/A"
                )
            )

        st.dataframe(
            display_yoy,
            width="stretch",
            hide_index=True
        )

        st.caption(
            "pp = percentage-point change; "
            "x = change in ratio multiples."
        )

    # DuPont Analysis
    st.subheader("DuPont Analysis")

    years = sorted(
        income.columns,
        reverse=True
    )

    selected_year = st.selectbox(
        "Fiscal year for DuPont analysis",
        years,
        format_func=lambda y: (
            f"FY{pd.Timestamp(y).year}"
        ),
        key=f"dupont_year_{report['ticker']}",
    )

    dupont = calculate_dupont(
        income,
        balance,
        year=selected_year
    )

    if dupont is None:

        st.warning(
            "Insufficient beginning/ending balances "
            "for this fiscal year."
        )

    else:

        st.latex(
            r"\mathrm{ROE}=\mathrm{Profit\ Margin}\times"
            r"\mathrm{Asset\ Turnover}\times"
            r"\mathrm{Equity\ Multiplier}"
        )

        cols = st.columns(4)

        factors = [
            (
                "Profit Margin",
                dupont["profit_margin"],
                True
            ),
            (
                "Asset Turnover",
                dupont["asset_turnover"],
                False
            ),
            (
                "Equity Multiplier",
                dupont["equity_multiplier"],
                False
            ),
            (
                "DuPont ROE",
                dupont["dupont_roe"],
                True
            ),
        ]

        for col, (label, value, is_percent) in zip(
            cols, factors
        ):

            with col:
                metric_card(
                    label,
                    value,
                    is_percent
                )

        st.caption(
            "Check: ROE = Net Income ÷ Average Equity = "
            + format_ratio(
                dupont["calculated_roe"],
                True
            )
        )

    # Raw Financial Statements
    with st.expander("View Raw Financial Statements"):

        income_tab, balance_tab = st.tabs([
            "Income Statement",
            "Balance Sheet"
        ])

        with income_tab:
            st.dataframe(
                income,
                width="stretch"
            )

        with balance_tab:
            st.dataframe(
                balance,
                width="stretch"
            )


# ==========================================
# PAGE 3 — INDUSTRY COMPARISON
# ==========================================

def industry_comparison():

    report = st.session_state.report

    st.header("Industry Comparison")

    st.caption(
        f"Assigned classification: "
        f"{report['assigned_sic']}"
    )

    sic = report["assigned_sic"].split(" ")[0]

    if len(sic) != 4 or not sic.isdigit():

        st.warning(
            "This ticker needs a verified four-digit "
            "SIC code in ASSIGNED_SIC."
        )

        return

    # Load Compustat data
    st.subheader("Compustat Industry Medians")

    uploaded = st.file_uploader(
        "Upload Compustat Fundamentals Annual CSV",
        type="csv"
    )

    if uploaded is not None:

        try:
            st.session_state.compustat_data = (
                pd.read_csv(uploaded)
            )

        except (
            ValueError,
            OSError,
            pd.errors.ParserError
        ) as exc:

            st.error(
                f"Unable to read CSV: {exc}"
            )

            return

    compustat = st.session_state.get(
        "compustat_data"
    )

    if compustat is None and CSV_PATH.exists():

        try:
            compustat = pd.read_csv(CSV_PATH)

        except (
            ValueError,
            OSError,
            pd.errors.ParserError
        ) as exc:

            st.error(
                f"Unable to read local Compustat CSV: {exc}"
            )

            return

    if compustat is None or compustat.empty:

        st.info(
            "No real Compustat data loaded yet. "
            "Upload your export or place it in "
            "data/compustat_annual.csv."
        )

        return

    # Choose fiscal year
    income = report["income_statement"]
    balance = report["balance_sheet"]

    available_years = sorted(
        {
            pd.Timestamp(col).year
            for col in income.columns
        },
        reverse=True
    )

    fyear = st.selectbox(
        "Fiscal year",
        available_years
    )

    peers = compustat.copy()

    peers.columns = (
        peers.columns.astype(str)
        .str.strip()
        .str.lower()
    )

    if "tic" in peers.columns:

        peers = peers.loc[
            peers["tic"]
            .astype("string")
            .str.strip()
            .str.upper()
            != report["ticker"]
        ].copy()

    else:
        st.warning(
            "CSV has no 'tic' column; the target "
            "company cannot be excluded."
        )

    # Calculate industry medians
    try:

        medians = calculate_industry_medians(
            peers,
            sic_code=sic,
            fiscal_year=fyear,
            min_peers=3
        )

    except (
        ValueError,
        TypeError,
        KeyError
    ) as exc:

        st.warning(
            f"Industry medians unavailable: {exc}"
        )

        return

    company_ratios = ratios_for_year(
        income,
        balance,
        year=fyear
    )

    # Build comparison table
    rows = []

    for record in medians.to_dict("records"):

        ratio = record["Ratio"]

        company_value, is_percent = (
            company_ratios[ratio]
        )

        median_value = record["Industry Median"]

        if (
            is_valid(company_value)
            and is_valid(median_value)
        ):

            delta = (
                float(company_value)
                - float(median_value)
            )

            position = (
                "Above median"
                if delta > 0
                else (
                    "Below median"
                    if delta < 0
                    else "At median"
                )
            )

            difference = (
                f"{delta * 100:+.2f} pp"
                if is_percent
                else f"{delta:+.2f}x"
            )

        else:
            position = "N/A"
            difference = "N/A"

        rows.append({
            "Ratio": ratio,

            "Company": format_ratio(
                company_value,
                is_percent
            ),

            "Industry Median": format_ratio(
                median_value,
                is_percent
            ),

            "Difference": difference,
            "Position": position,
            "Peer Count": int(record["Peer Count"]),
        })

    st.caption(
        f"SIC {sic} · FY{fyear} · "
        "Minimum 3 valid peers per ratio. "
        "Above median does not always mean "
        "better performance."
    )

    st.dataframe(
        pd.DataFrame(rows),
        width="stretch",
        hide_index=True
    )

    # Company vs. Industry Chart
    st.subheader("Company vs. Industry")

    selected = st.selectbox(
        "Select ratio",
        ALL_RATIOS
    )

    company_value, is_percent = (
        company_ratios[selected]
    )

    industry_value = medians.set_index(
        "Ratio"
    ).at[selected, "Industry Median"]

    if (
        not is_valid(company_value)
        or not is_valid(industry_value)
    ):

        st.info(
            "Not enough data for this comparison."
        )

    else:

        multiplier = 100 if is_percent else 1

        chart = pd.DataFrame({
            "Source": [
                report["ticker"],
                "Industry Median"
            ],
            "Value": [
                float(company_value) * multiplier,
                float(industry_value) * multiplier
            ],
        }).set_index("Source")

        st.bar_chart(chart)

        st.caption(
            "Chart units: percent (%)"
            if is_percent
            else "Chart units: multiples (x)"
        )

    # Benchmark indicators
    st.subheader("Benchmark Indicators")

    st.write(
        "The Position column shows "
        "above/below-industry-median comparisons. "
        "A higher ratio is not necessarily better, "
        "particularly for leverage."
    )


# ==========================================
# THREE SIDEBAR PAGES WITH ICONS
# ==========================================

overview_page = st.Page(
    company_overview,
    title="Company Overview",
    icon=":material/dashboard:",
    url_path="overview",
    default=True,
)

analysis_page = st.Page(
    financial_analysis,
    title="Financial Analysis",
    icon=":material/show_chart:",
    url_path="analysis",
)

industry_page = st.Page(
    industry_comparison,
    title="Industry Comparison",
    icon=":material/bar_chart:",
    url_path="industry",
)

current_page = st.navigation(
    [
        overview_page,
        analysis_page,
        industry_page
    ],
    position="hidden"
)


# ==========================================
# SIDEBAR
# ==========================================

with st.sidebar:

    st.markdown(
        "### :material/monitoring: Finance Analyzer"
    )

    st.divider()

    ticker = st.text_input(
        "Company",
        value="MSFT"
    ).strip().upper()

    analyze_clicked = st.button(
        "Analyze",
        type="primary",
        width="stretch"
    )

    st.write("")

    st.page_link(
        overview_page,
        label="Company Overview",
        icon=":material/dashboard:"
    )

    st.page_link(
        analysis_page,
        label="Financial Analysis",
        icon=":material/show_chart:"
    )

    st.page_link(
        industry_page,
        label="Industry Comparison",
        icon=":material/bar_chart:"
    )

    st.divider()

    st.caption(
        "AC420 · Financial Performance Analyzer"
    )


# ==========================================
# SESSION STATE
# ==========================================

if "report" not in st.session_state:
    st.session_state.report = None

if "has_loaded" not in st.session_state:
    st.session_state.has_loaded = False

if "load_error" not in st.session_state:
    st.session_state.load_error = None


# ==========================================
# ANALYZE COMPANY
# ==========================================

if analyze_clicked or not st.session_state.has_loaded:

    st.session_state.has_loaded = True
    st.session_state.report = None
    st.session_state.load_error = None

    if not ticker:
        st.session_state.load_error = (
            "Please enter a stock ticker."
        )

    else:

        with st.spinner(
            f"Loading financial data for {ticker}..."
        ):

            try:

                st.session_state.report = (
                    load_company(ticker)
                )

            except Exception as exc:

                st.session_state.load_error = (
                    f"Unable to load {ticker}: {exc}"
                )


# ==========================================
# DISPLAY SELECTED PAGE
# ==========================================

if st.session_state.load_error:
    st.error(st.session_state.load_error)

if st.session_state.report is None:

    st.info(
        "Enter a ticker in the sidebar "
        "and click Analyze."
    )

    st.stop()

show_company_heading(
    st.session_state.report
)

current_page.run()
