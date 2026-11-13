"""Compustat annual industry benchmarks for the AC420 Streamlit project.

Input: one CSV exported from WRDS Compustat North America Fundamentals Annual
with gvkey, fyear, sic or sich, ni, sale, at, seq, act, lct, dlc, dltt.

Important: Include at least one preceding fiscal year per firm when you want
ROA, ROE, or asset turnover, since those use average opening/closing balances.
All percent ratios are stored as DECIMALS, matching financial_ratios.py.
"""

import math

import pandas as pd

from historical_analysis import ALL_RATIOS, PERCENT_RATIOS

REQUIRED_COLUMNS = {
    "gvkey", "fyear", "ni", "sale", "at", "seq",
    "act", "lct", "dlc", "dltt",
}
NUMERIC_COLUMNS = ["ni", "sale", "at", "seq", "act", "lct", "dlc", "dltt"]


def _standardize_sic(value):
    """Convert values like 7372, '7372', or '7372.0' into '7372'."""
    if pd.isna(value):
        return ""
    value = str(value).strip()
    if value.endswith(".0"):
        value = value[:-2]
    return value.zfill(4) if value.isdigit() else value


def _divide(numerator, denominator):
    """Return NaN when a denominator is missing or nonpositive."""
    return numerator.div(denominator.where(denominator > 0))


def calculate_industry_medians(compustat_data, sic_code, fiscal_year, min_peers=5):
    """Calculate cross-sectional medians for the six project ratios.

    Args:
        compustat_data: Raw Compustat Fundamentals Annual DataFrame.
        sic_code: Exact four-digit SIC; e.g., '7372'.
        fiscal_year: Fiscal year to compare (e.g., 2025).
        min_peers: Minimum NONMISSING firm observations needed per ratio.

    Returns:
        DataFrame with columns Ratio, Industry Median, Peer Count, from
        ALL_RATIOS. If the group has too few valid firms for a ratio, that
        median is left NaN rather than reporting a fragile benchmark.
    """
    if compustat_data is None or compustat_data.empty:
        raise ValueError("Compustat CSV is empty.")

    df = compustat_data.copy()
    df.columns = df.columns.astype(str).str.strip().str.lower()
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError("Compustat CSV is missing columns: " + ", ".join(sorted(missing)))
    if "sich" not in df.columns and "sic" not in df.columns:
        raise ValueError("Compustat CSV needs an 'sich' or 'sic' industry column.")
    if min_peers < 1:
        raise ValueError("min_peers must be 1 or greater.")

    df["gvkey"] = df["gvkey"].astype("string").str.strip()
    df["fyear"] = pd.to_numeric(df["fyear"], errors="coerce")
    df = df.dropna(subset=["gvkey", "fyear"])
    df = df[df["gvkey"] != ""]
    df["fyear"] = df["fyear"].astype(int)

    if "sich" in df.columns and "sic" in df.columns:
        sic = df["sich"].combine_first(df["sic"])
    elif "sich" in df.columns:
        sic = df["sich"]
    else:
        sic = df["sic"]
    df["industry_sic"] = sic.map(_standardize_sic)

    for name in NUMERIC_COLUMNS:
        df[name] = pd.to_numeric(df[name], errors="coerce")

    # Standard WRDS filters should be applied during export. If a file still
    # contains repeated company-year records, retain the latest datadate.
    sort_columns = ["gvkey", "fyear"]
    if "datadate" in df.columns:
        df["datadate"] = pd.to_datetime(df["datadate"], errors="coerce")
        sort_columns.append("datadate")
    df = df.sort_values(sort_columns)
    df = df.drop_duplicates(["gvkey", "fyear"], keep="last")

    groups = df.groupby("gvkey", sort=False)
    previous_year = groups["fyear"].shift(1)
    consecutive = df["fyear"].sub(previous_year).eq(1)

    # Average balance denominators, consistent with financial_ratios.py.
    prior_assets = groups["at"].shift(1).where(consecutive)
    prior_equity = groups["seq"].shift(1).where(consecutive)
    average_assets = (df["at"] + prior_assets) / 2
    average_equity = (df["seq"] + prior_equity) / 2

    df["ROA"] = _divide(df["ni"], average_assets)
    df["ROE"] = _divide(df["ni"], average_equity)
    df["Profit Margin"] = _divide(df["ni"], df["sale"])
    df["Current Ratio"] = _divide(df["act"], df["lct"])

    # Require both debt components, rather than quietly treating missing as 0.
    debt = df["dlc"] + df["dltt"]
    df["Debt-to-Equity"] = _divide(debt, df["seq"])
    df["Asset Turnover"] = _divide(df["sale"], average_assets)

    code = _standardize_sic(sic_code)
    if len(code) != 4 or not code.isdigit():
        raise ValueError("Please provide an exact four-digit SIC code, such as 7372.")
    peers = df.loc[
        (df["industry_sic"] == code) & (df["fyear"] == int(fiscal_year))
    ]

    if peers.empty:
        raise ValueError(
            f"No Compustat companies found for SIC {code}, FY{fiscal_year}. "
            "Check the file's SIC column and fiscal-year coverage."
        )

    rows = []
    for ratio in ALL_RATIOS:
        observations = pd.to_numeric(peers[ratio], errors="coerce")
        observations = observations[observations.map(math.isfinite)]
        count = len(observations)
        median = float(observations.median()) if count >= min_peers else float("nan")
        rows.append({
            "Ratio": ratio,
            "Industry Median": median,
            "Peer Count": count,
        })

    return pd.DataFrame(rows)


def compare_with_industry(company_ratios, medians):
    """Combine report['ratios'] and medians; direction is descriptive only.

    company_ratios is a dictionary of {ratio: (value, is_percent)}.
    The Difference column is decimal points for percent ratios and a numeric
    multiple for other ratios; convert to pp or x in the Streamlit UI.
    """
    median_by_ratio = medians.set_index("Ratio")
    rows = []
    for ratio in ALL_RATIOS:
        company_value = company_ratios.get(ratio, (None, False))[0]
        company_value = pd.to_numeric(company_value, errors="coerce")
        median = median_by_ratio.at[ratio, "Industry Median"]
        count = int(median_by_ratio.at[ratio, "Peer Count"])
        if not pd.notna(company_value) or not pd.notna(median):
            difference = float("nan")
            direction = "N/A"
        else:
            difference = float(company_value - median)
            direction = (
                "Above median" if difference > 1e-12
                else "Below median" if difference < -1e-12
                else "At median"
            )
        rows.append({
            "Ratio": ratio,
            "Company": company_value,
            "Industry Median": median,
            "Difference": difference,
            "Comparison": direction,
            "Peer Count": count,
            "Unit": "pp" if ratio in PERCENT_RATIOS else "x",
        })
    return pd.DataFrame(rows)

