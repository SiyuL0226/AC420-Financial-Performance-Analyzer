
"""Industry Benchmark Comparison for AC420 Financial Performance Analyzer.

Primary source:
    Precomputed FY2015–2025 WRDS Compustat industry benchmarks,
    grouped by 2-digit SIC.

Expected files:
    output/industry_benchmarks_final.csv
    output/ticker_industry_mapping_final.csv

All percentage ratios are stored as decimals.
"""

from pathlib import Path

import numpy as np
import pandas as pd

try:
    from historical_analysis import ALL_RATIOS, PERCENT_RATIOS
except ImportError:
    ALL_RATIOS = [
        "ROA", "ROE", "Profit Margin",
        "Current Ratio", "Debt-to-Equity", "Asset Turnover"
    ]
    PERCENT_RATIOS = ["ROA", "ROE", "Profit Margin"]


DATA_DIR = Path(__file__).resolve().parent / "output"

BENCHMARK_FILE = DATA_DIR / "industry_benchmarks_final.csv"
MAPPING_FILE = DATA_DIR / "ticker_industry_mapping_final.csv"

RATIO_NAMES = {
    "ROA": "roa",
    "ROE": "roe",
    "Profit Margin": "profit_margin",
    "Current Ratio": "current_ratio",
    "Debt-to-Equity": "debt_to_equity",
    "Asset Turnover": "asset_turnover",
    "Interest Coverage": "interest_coverage",
}


# ------------------------------------------------------------
# 1. Load precomputed benchmark data
# ------------------------------------------------------------

def load_mapping():
    """Load ticker-to-industry mapping."""
    mapping = pd.read_csv(MAPPING_FILE)

    required = {"tic", "sic", "sic2", "industry_name"}
    missing = required - set(mapping.columns)
    if missing:
        raise ValueError(f"Mapping CSV missing columns: {sorted(missing)}")

    mapping["tic"] = (
        mapping["tic"].astype(str).str.upper().str.strip()
    )

    return mapping


def load_benchmarks():
    """Load annual industry median benchmarks."""
    benchmarks = pd.read_csv(BENCHMARK_FILE)

    required = {"sic2", "fyear", "industry_name"}
    missing = required - set(benchmarks.columns)
    if missing:
        raise ValueError(f"Benchmark CSV missing columns: {sorted(missing)}")

    benchmarks["sic2"] = pd.to_numeric(
        benchmarks["sic2"], errors="coerce"
    )
    benchmarks["fyear"] = pd.to_numeric(
        benchmarks["fyear"], errors="coerce"
    )

    return benchmarks


# ------------------------------------------------------------
# 2. Identify a company's industry
# ------------------------------------------------------------

def identify_industry(ticker):
    """Identify a company's SIC industry using its ticker."""
    ticker = str(ticker).upper().strip()
    mapping = load_mapping()

    match = mapping.loc[mapping["tic"] == ticker]

    if match.empty:
        return None

    company = match.iloc[0]

    return {
        "ticker": ticker,
        "sic": int(company["sic"]),
        "sic2": int(company["sic2"]),
        "industry_name": str(company["industry_name"]),
    }


# ------------------------------------------------------------
# 3. Retrieve industry benchmarks by ticker and fiscal year
# ------------------------------------------------------------

def get_industry_benchmark(ticker, year):
    """Retrieve precomputed industry medians for a ticker/year."""
    industry = identify_industry(ticker)

    if industry is None:
        return None

    benchmarks = load_benchmarks()

    match = benchmarks.loc[
        (benchmarks["sic2"] == industry["sic2"])
        & (benchmarks["fyear"] == int(year))
    ]

    if match.empty:
        return None

    record = match.iloc[0]
    ratios = {}

    for display_name, column_name in RATIO_NAMES.items():
        median = pd.to_numeric(
            record.get(f"{column_name}_median", np.nan),
            errors="coerce",
        )
        count = pd.to_numeric(
            record.get(f"{column_name}_count", 0),
            errors="coerce",
        )

        ratios[display_name] = {
            "median": float(median) if pd.notna(median) else None,
            "count": int(count) if pd.notna(count) else 0,
        }

    return {
        "ticker": industry["ticker"],
        "sic": industry["sic"],
        "sic2": industry["sic2"],
        "industry_name": industry["industry_name"],
        "fyear": int(year),
        "ratios": ratios,
    }


# ------------------------------------------------------------
# 4. Retrieve industry medians by SIC
# ------------------------------------------------------------

def calculate_industry_medians(
    compustat_data,
    sic_code,
    fiscal_year,
    min_peers=5,
):
    """Legacy-compatible interface for SIC-based benchmark lookup.

    Uses precomputed 2-digit SIC medians rather than recalculating
    medians from the supplied raw Compustat DataFrame.

    Note: A four-digit SIC is mapped to its first two digits.
    This changes the peer-group definition from the original
    exact-four-digit-SIC implementation.
    """
    if min_peers < 1:
        raise ValueError("min_peers must be at least 1.")

    code = str(sic_code).strip()

    if code.endswith(".0"):
        code = code[:-2]

    if not code.isdigit() or len(code) not in (2, 4):
        raise ValueError("Provide a 2-digit or 4-digit SIC code.")

    sic2 = int(code[:2])

    benchmarks = load_benchmarks()

    match = benchmarks.loc[
        (benchmarks["sic2"] == sic2)
        & (benchmarks["fyear"] == int(fiscal_year))
    ]

    if match.empty:
        raise ValueError(
            f"No benchmark found for SIC2 {sic2}, FY{fiscal_year}."
        )

    record = match.iloc[0]
    rows = []

    for ratio in ALL_RATIOS:
        column = RATIO_NAMES.get(ratio)

        if column is None:
            continue

        median = pd.to_numeric(
            record.get(f"{column}_median", np.nan),
            errors="coerce",
        )
        count = pd.to_numeric(
            record.get(f"{column}_count", 0),
            errors="coerce",
        )

        count = int(count) if pd.notna(count) else 0

        if count < min_peers:
            median = np.nan

        rows.append({
            "Ratio": ratio,
            "Industry Median": median,
            "Peer Count": count,
        })

    return pd.DataFrame(rows)


# ------------------------------------------------------------
# 5. Compare company ratios against industry benchmarks
# ------------------------------------------------------------

def compare_with_industry(company_ratios, benchmark):
    """Compare company ratios with industry medians.

    Supports:
      1. Benchmark dictionary from get_industry_benchmark().
      2. DataFrame from calculate_industry_medians().

    Company ratios may be numeric values or (value, is_percent)
    tuples, as used in the Streamlit financial report.
    """
    if benchmark is None:
        return pd.DataFrame()

    if isinstance(benchmark, dict):
        benchmark_ratios = benchmark.get("ratios", {})
    elif isinstance(benchmark, pd.DataFrame):
        benchmark_ratios = {}

        for _, record in benchmark.iterrows():
            benchmark_ratios[record["Ratio"]] = {
                "median": record["Industry Median"],
                "count": record["Peer Count"],
            }
    else:
        raise TypeError(
            "benchmark must be a dictionary or DataFrame."
        )

    rows = []

    for ratio in RATIO_NAMES:
        if ratio not in company_ratios:
            continue

        raw_value = company_ratios[ratio]

        if isinstance(raw_value, (tuple, list)):
            raw_value = raw_value[0] if len(raw_value) else None

        company_value = pd.to_numeric(
            raw_value, errors="coerce"
        )

        info = benchmark_ratios.get(ratio, {})
        median = pd.to_numeric(
            info.get("median", np.nan),
            errors="coerce",
        )
        count = pd.to_numeric(
            info.get("count", 0),
            errors="coerce",
        )

        if not np.isfinite(company_value):
            company_value = np.nan

        if not np.isfinite(median):
            median = np.nan

        if pd.isna(company_value) or pd.isna(median):
            difference = np.nan
            position = "N/A"
        else:
            difference = float(company_value - median)

            if np.isclose(difference, 0, atol=1e-12):
                position = "At median"
            elif difference > 0:
                position = "Above median"
            else:
                position = "Below median"

        rows.append({
            "Ratio": ratio,
            "Company": company_value,
            "Industry Median": median,
            "Difference": difference,
            "Comparison": position,
            "Position": position,
            "Peer Count": int(count) if pd.notna(count) else 0,
            "Industry Observations": (
                int(count) if pd.notna(count) else 0
            ),
            "Unit": "pp" if ratio in PERCENT_RATIOS else "x",
        })

    return pd.DataFrame(rows)
