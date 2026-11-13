
import html
import math
from pathlib import Path

import pandas as pd
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

from historical_analysis import (
    ALL_RATIOS,
    PERCENT_RATIOS,
    calculate_historical_ratios,
    calculate_yoy_changes,
)

from dupont_analysis import calculate_dupont

from industry_benchmark import calculate_industry_medians


# ==========================================
# 1. PAGE SETTINGS AND UI DESIGN
# ==========================================

st.set_page_config(
    page_title="Finance Analyzer",
    page_icon=":material/monitoring:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp {
        background: #FCFCFC;
    }

    section[data-testid="stSidebar"] {
        background: #F8F9F9;
        border-right: 1px solid #E4E7E7;
    }

    .block-container {
        max-width: 1150px;
        padding-top: 2rem;
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

    section[data-testid="stSidebar"]
    div[data-testid="stPageLink"] a {
        border-radius: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==========================================
# 2. INDUSTRY CLASSIFICATION
# ==========================================

ASSIGNED_SIC = {
    "MSFT": "7372 — Services: Prepackaged Software"
}

CSV_PATH = (
    Path(__file__).resolve().parent
    / "data"
    / "compustat_annual.csv"
)


# ==========================================
# 3. HELPER FUNCTIONS
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
        return f"{float(value):.2%}"

    return f"{float(value):.2f}x"


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
# 4. LOAD COMPANY FINANCIAL DATA
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
            "Annual financial statements are unavailable."
        )

    try:
        info = company.get_info() or {}
    except Exception:
        info = {}

    latest_year = max(income.columns)

    year_label = pd.Timestamp(
        latest_year
    ).strftime("%B %Y")

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

        "fiscal_year_end": year_label,

        "income_statement": income,

        "balance_sheet": balance,

        "ratios": ratios_for_year(
            income, balance, year=latest_year
        ),
    }


# ==========================================
# 5. CENTERED COMPANY HEADING
# ==========================================

def show_company_heading(report):

    name = html.escape(str(report["company_name"]))
    ticker = html.escape(str(report["ticker"]))
    year = html.escape(str(report["fiscal_year_end"]))

    st.markdown(
        f"""
        <div style="
            text-align: center;
            margin: 6px 0 32px 0;
        ">
            <h1 style="
                margin: 0 0 8px 0;
                font-size: 2.5rem;
                font-weight: 750;
                line-height: 1.2;
            ">
                {name}
            </h1>

            <p style="
                margin: 0;
                color: #697177;
                font-size: 1rem;
            ">
                {ticker} · Fiscal year ended {year}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ==========================================
# 6. AUTOMATIC FINANCIAL SUMMARY
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
            f"{name} recorded a net profit margin of "
            f"{format_ratio(pm, True)} and return on equity "
            f"of {format_ratio(roe, True)} for the most "
            "recent reported fiscal year."
        )

    elif is_valid(pm):

        sentences.append(
            "The reported net profit margin was "
            f"{format_ratio(pm, True)}."
        )

    if is_valid(roa):
        sentences.append(
            f"Return on assets was {format_ratio(roa, True)}."
        )

    if is_valid(current):
        sentences.append(
            f"The current ratio was {format_ratio(current)}, "
            "comparing reported current assets with "
            "current liabilities."
        )

    sentences.append(
        "To evaluate whether these figures are strong "
        "or weak, review the historical trends and "
        "comparable industry medians."
    )

    return " ".join(sentences)


# ==========================================
# 7. DISPLAY RATIO CARDS
# ==========================================

def display_ratio_grid(report, names, columns_count):

    for start in range(
        0, len(names), columns_count
    ):

        cols = st.columns(columns_count)

        for col, label in zip(
            cols,
            names[start:start + columns_count]
        ):

            value, is_percent = report["ratios"][label]

            with col:
                metric_card(
                    label, value, is_percent
                )


# ==========================================
# TAB 1 — COMPANY OVERVIEW
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

        first, middle, last = st.columns(
            [1, 2, 1.2]
        )

        with first:
            st.caption("Ticker")
            st.write(report["ticker"])

            st.caption("Sector")
            st.write(report["sector"])

        with middle:
            st.caption("Assigned SIC industry")
            st.write(report["assigned_sic"])

            st.caption("Yahoo Finance industry")
            st.write(report["yahoo_industry"])

        with last:
            st.caption("Fiscal year ended")
            st.write(report["fiscal_year_end"])

    st.subheader("Financial Performance Summary")

    with st.container(border=True):
        st.write(financial_summary(report))


# ==========================================
# TAB 2 — FINANCIAL ANALYSIS
# ==========================================

def financial_analysis():

    report = st.session_state.report

    income = report["income_statement"]
    balance = report["balance_sheet"]

    st.header("Financial Analysis")

    # --------------------------------------
    # SIX FINANCIAL RATIOS
    # --------------------------------------

    st.subheader("Financial Ratios")

    display_ratio_grid(
        report,
        ALL_RATIOS,
        3
    )

    # --------------------------------------
    # HISTORICAL RATIO TRENDS
    # --------------------------------------

    history = calculate_historical_ratios(
        income,
        balance
    )

    st.subheader("Historical Ratio Trends")

    if history.empty:

        st.warning(
            "Historical annual financial data is unavailable."
        )

    else:

        selected_ratio = st.selectbox(
            "Choose a ratio to graph",
            ALL_RATIOS,
            key="trend_ratio"
        )

        chart_df = history[
            ["Fiscal Year", selected_ratio]
        ].copy()

        chart_df[selected_ratio] = pd.to_numeric(
            chart_df[selected_ratio],
            errors="coerce"
        )

        if selected_ratio in PERCENT_RATIOS:
            chart_df[selected_ratio] *= 100

        chart_df = chart_df.dropna(
            subset=[selected_ratio]
        )

        if chart_df.empty:
            st.info(
                "No multi-year values are available "
                "for this ratio."
            )

        else:

            st.line_chart(
                chart_df.set_index("Fiscal Year")
            )

            if selected_ratio in PERCENT_RATIOS:
                st.caption("Chart units: percent (%)")
            else:
                st.caption("Chart units: multiples (x)")

        with st.expander(
            "View Historical Ratio Table"
        ):

            table = history.copy()

            for label in ALL_RATIOS:

                table[label] = table[label].map(
                    lambda val, name=label: format_ratio(
                        val,
                        name in PERCENT_RATIOS
                    )
                )

            st.dataframe(
                table,
                use_container_width=True,
                hide_index=True
            )

    # --------------------------------------
    # YEAR-OVER-YEAR COMPARISON
    # --------------------------------------

    st.subheader("Year-over-Year Comparison")

    if history.empty:

        st.info(
            "No years are available for "
            "year-over-year analysis."
        )

    else:

        yoy = calculate_yoy_changes(history)

        display_yoy = yoy.copy()

        for column in display_yoy.columns:

            if column == "Fiscal Year":
                continue

            if column.endswith("(pp)"):
                unit = " pp"
            else:
                unit = "x"

            display_yoy[column] = (
                display_yoy[column].map(
                    lambda val, suffix=unit: (
                        f"{float(val):+.2f}{suffix}"
                        if is_valid(val)
                        else "N/A"
                    )
                )
            )

        st.dataframe(
            display_yoy,
            use_container_width=True,
            hide_index=True
        )

        st.caption(
            "pp = percentage-point change; "
            "x = change in ratio multiples. "
            "Missing values mean no comparable "
            "consecutive years."
        )

    # --------------------------------------
    # DUPONT ANALYSIS
    # --------------------------------------

    st.subheader("DuPont Analysis")

    years = sorted(
        income.columns,
        reverse=True
    )

    year_end = st.selectbox(
        "Fiscal year for DuPont analysis",
        years,
        format_func=lambda value: (
            f"FY{pd.Timestamp(value).year}"
        ),
        key=f"dupont_year_{report['ticker']}"
    )

    dupont = calculate_dupont(
        income,
        balance,
        year=year_end
    )

    if dupont is None:

        st.warning(
            "Not enough financial data to "
            "calculate DuPont ROE for this year."
        )

    else:

        st.latex(
            r"\mathrm{ROE} = "
            r"\mathrm{Profit\ Margin}"
            r"\times \mathrm{Asset\ Turnover}"
            r"\times \mathrm{Equity\ Multiplier}"
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
            "Check: ROE from Net Income ÷ "
            "Average Equity = "
            f"{format_ratio(dupont['calculated_roe'], True)}. "
            "Average assets and average equity are "
            "used in the DuPont components."
        )

    # --------------------------------------
    # RAW FINANCIAL STATEMENTS
    # --------------------------------------

    with st.expander(
        "View Raw Financial Statements"
    ):

        income_tab, balance_tab = st.tabs([
            "Income Statement",
            "Balance Sheet"
        ])

        with income_tab:
            st.dataframe(
                income,
                use_container_width=True
            )

        with balance_tab:
            st.dataframe(
                balance,
                use_container_width=True
            )


# ==========================================
# TAB 3 — INDUSTRY COMPARISON
# ==========================================

def industry_comparison():

    report = st.session_state.report

    st.header("Industry Comparison")

    st.caption(
        f"Assigned classification: "
        f"{report['assigned_sic']}"
    )

    sic_code = report["assigned_sic"].split(" ")[0]

    if not (
        len(sic_code) == 4
        and sic_code.isdigit()
    ):

        st.warning(
            "This company does not yet have a "
            "verified four-digit SIC classification. "
            "Add it to ASSIGNED_SIC."
        )

        return

    # --------------------------------------
    # LOAD COMPUSTAT DATA
    # --------------------------------------

    st.subheader("Compustat Industry Medians")

    st.write(
        "Provide Compustat Fundamentals Annual "
        "observations to calculate industry medians."
    )

    upload = st.file_uploader(
        "Upload a Compustat annual CSV",
        type="csv",
        key="compustat_upload"
    )

    if upload is not None:

        try:
            st.session_state["compustat_data"] = (
                pd.read_csv(upload)
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
                f"Unable to read CSV: {exc}"
            )

            return

    if compustat is None or compustat.empty:

        st.info(
            "No Compustat observations loaded. "
            "Upload real peer-company data or save "
            "it as data/compustat_annual.csv."
        )

        return

    # --------------------------------------
    # CHOOSE FISCAL YEAR
    # --------------------------------------

    income = report["income_statement"]
    balance = report["balance_sheet"]

    available_years = sorted(
        {
            pd.Timestamp(col).year
            for col in income.columns
        },
        reverse=True
    )

    fiscal_year = st.selectbox(
        "Compare fiscal year",
        available_years,
        key="benchmark_fyear"
    )

    # --------------------------------------
    # EXCLUDE SELECTED COMPANY
    # --------------------------------------

    eligible = compustat.copy()

    eligible.columns = (
        eligible.columns
        .astype(str)
        .str.strip()
        .str.lower()
    )

    if "tic" in eligible.columns:

        eligible = eligible.loc[
            eligible["tic"]
            .astype("string")
            .str.strip()
            .str.upper()
            != report["ticker"]
        ].copy()

        st.caption(
            "The selected company is excluded "
            "from its industry peer group."
        )

    else:

        st.caption(
            "Ticker identifiers are missing, "
            "so the selected company cannot "
            "be explicitly excluded."
        )

    if (
        "sale" not in eligible.columns
        and "revt" in eligible.columns
    ):

        st.error(
            "Your CSV contains 'revt' but not 'sale'. "
            "Please export the Compustat 'sale' field."
        )

        return

    # --------------------------------------
    # CALCULATE INDUSTRY MEDIANS
    # --------------------------------------

    try:

        medians = calculate_industry_medians(
            eligible,
            sic_code=sic_code,
            fiscal_year=fiscal_year,
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
        year=fiscal_year
    )

    # --------------------------------------
    # COMPARISON TABLE
    # --------------------------------------

    rows = []

    for item in medians.to_dict("records"):

        label = item["Ratio"]

        company_value, is_percent = (
            company_ratios[label]
        )

        median_value = item["Industry Median"]

        comparable = (
            is_valid(company_value)
            and is_valid(median_value)
        )

        if comparable:

            delta = (
                float(company_value)
                - float(median_value)
            )

            if delta > 1e-12:
                position = "Above median"
            elif delta < -1e-12:
                position = "Below median"
            else:
                position = "At median"

            if is_percent:
                delta_text = f"{delta * 100:+.2f} pp"
            else:
                delta_text = f"{delta:+.2f}x"

        else:

            position = "N/A"
            delta_text = "N/A"

        rows.append({
            "Ratio": label,

            "Company": format_ratio(
                company_value, is_percent
            ),

            "Industry Median": format_ratio(
                median_value, is_percent
            ),

            "Difference": delta_text,

            "Position": position,

            "Peer Count": int(item["Peer Count"])
        })

    st.caption(
        f"SIC {sic_code} · FY{fiscal_year} · "
        "Minimum three valid peers per ratio. "
        "Above median does not automatically "
        "mean stronger performance."
    )

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True
    )

    # --------------------------------------
    # COMPANY VS. INDUSTRY CHART
    # --------------------------------------

    st.subheader("Company vs. Industry")

    selected_ratio = st.selectbox(
        "Select a ratio",
        ALL_RATIOS,
        key="benchmark_selected_ratio"
    )

    values = medians.set_index("Ratio")

    median = values.loc[
        selected_ratio,
        "Industry Median"
    ]

    company_value, is_percent = (
        company_ratios[selected_ratio]
    )

    if not (
        is_valid(company_value)
        and is_valid(median)
    ):

        st.info(
            "Not enough comparable observations "
            "for this ratio and fiscal year."
        )

    else:

        scale = 100 if is_percent else 1

        chart_df = pd.DataFrame({
            "Source": [
                report["ticker"],
                "Industry Median"
            ],

            "Value": [
                float(company_value) * scale,
                float(median) * scale
            ]
        }).set_index("Source")

        st.bar_chart(chart_df)

        if is_percent:
            st.caption("Chart units: percent (%)")
        else:
            st.caption("Chart units: multiples (x)")

    # --------------------------------------
    # BENCHMARK INDICATORS
    # --------------------------------------

    st.subheader("Benchmark Indicators")

    st.write(
        "The Position column shows whether "
        "each company ratio is above or below "
        "the industry median. Interpretation "
        "depends on the ratio: higher debt-to-equity "
        "may indicate greater leverage, while "
        "a higher profit margin may indicate "
        "stronger profitability."
    )


# ==========================================
# 8. SIDEBAR NAVIGATION WITH ICONS
# ==========================================

overview_page = st.Page(
    company_overview,
    title="Company Overview",
    icon=":material/dashboard:",
    url_path="overview",
    default=True
)

analysis_page = st.Page(
    financial_analysis,
    title="Financial Analysis",
    icon=":material/show_chart:",
    url_path="analysis"
)

comparison_page = st.Page(
    industry_comparison,
    title="Industry Comparison",
    icon=":material/bar_chart:",
    url_path="industry"
)

current_page = st.navigation(
    [
        overview_page,
        analysis_page,
        comparison_page
    ],
    position="hidden"
)


# ==========================================
# 9. SIDEBAR
# ==========================================

with st.sidebar:

    st.markdown(
        "### :material/monitoring: Finance Analyzer"
    )

    st.divider()

    ticker = st.text_input(
        "Company",
        value="MSFT",
        key="ticker_input"
    ).strip().upper()

    analyze_clicked = st.button(
        "Analyze",
        type="primary",
        use_container_width=True
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
        comparison_page,
        label="Industry Comparison",
        icon=":material/bar_chart:"
    )

    st.divider()

    st.caption(
        "AC420 · Financial Performance Analyzer"
    )


# ==========================================
# 10. SESSION STATE
# ==========================================

if "has_loaded" not in st.session_state:
    st.session_state.has_loaded = False

if "report" not in st.session_state:
    st.session_state.report = None

if "load_error" not in st.session_state:
    st.session_state.load_error = None


# ==========================================
# 11. ANALYZE COMPANY
# ==========================================

if (
    analyze_clicked
    or not st.session_state.has_loaded
):

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
                    f"Unable to load financial data "
                    f"for {ticker}: {exc}"
                )


# ==========================================
# 12. DISPLAY SELECTED PAGE
# ==========================================

if st.session_state.load_error:
    st.error(st.session_state.load_error)

if st.session_state.report is None:

    st.info(
        "Enter a valid ticker in the sidebar "
        "and click Analyze."
    )

    st.stop()

show_company_heading(
    st.session_state.report
)

current_page.run()

