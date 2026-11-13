
import math
import pandas as pd

from historical_analysis import (
    ALL_RATIOS,
    PERCENT_RATIOS
)

REQUIRED_COLUMNS = {
    "gvkey", "fyear", "ni", "sale",
    "at", "seq", "act", "lct",
    "dlc", "dltt"
}

NUMERIC_COLUMNS = [
    "ni", "sale", "at", "seq",
    "act", "lct", "dlc", "dltt"
]


def _standardize_sic(value):
    if pd.isna(value):
        return ""

    value = str(value).strip()

    if value.endswith(".0"):
        value = value[:-2]

    if value.isdigit():
        return value.zfill(4)

    return value


def _divide(numerator, denominator):
    return numerator.div(
        denominator.where(denominator > 0)
    )


def calculate_industry_medians(
    compustat_data,
    sic_code,
    fiscal_year,
    min_peers=5
):

    if compustat_data is None or compustat_data.empty:
        raise ValueError("Compustat CSV is empty.")

    df = compustat_data.copy()

    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
    )

    missing = REQUIRED_COLUMNS - set(df.columns)

    if missing:
        raise ValueError(
            "Missing columns: " + ", ".join(sorted(missing))
        )

    if "sich" not in df.columns and "sic" not in df.columns:
        raise ValueError(
            "Compustat CSV needs 'sich' or 'sic'."
        )

    if min_peers < 1:
        raise ValueError(
            "min_peers must be at least 1."
        )

    df["gvkey"] = (
        df["gvkey"].astype("string").str.strip()
    )

    df["fyear"] = pd.to_numeric(
        df["fyear"], errors="coerce"
    )

    df = df.dropna(
        subset=["gvkey", "fyear"]
    )

    df = df[df["gvkey"] != ""]

    df["fyear"] = df["fyear"].astype(int)

    if "sich" in df.columns and "sic" in df.columns:
        sic = df["sich"].combine_first(df["sic"])

    elif "sich" in df.columns:
        sic = df["sich"]

    else:
        sic = df["sic"]

    df["industry_sic"] = sic.map(
        _standardize_sic
    )

    for name in NUMERIC_COLUMNS:
        df[name] = pd.to_numeric(
            df[name], errors="coerce"
        )

    sort_columns = ["gvkey", "fyear"]

    if "datadate" in df.columns:
        df["datadate"] = pd.to_datetime(
            df["datadate"], errors="coerce"
        )
        sort_columns.append("datadate")

    df = df.sort_values(sort_columns)

    df = df.drop_duplicates(
        ["gvkey", "fyear"],
        keep="last"
    )

    groups = df.groupby("gvkey", sort=False)

    previous_year = groups["fyear"].shift(1)

    consecutive = (
        df["fyear"].sub(previous_year).eq(1)
    )

    prior_assets = (
        groups["at"].shift(1).where(consecutive)
    )

    prior_equity = (
        groups["seq"].shift(1).where(consecutive)
    )

    average_assets = (
        df["at"] + prior_assets
    ) / 2

    average_equity = (
        df["seq"] + prior_equity
    ) / 2

    # Calculate all six ratios

    df["ROA"] = _divide(
        df["ni"], average_assets
    )

    df["ROE"] = _divide(
        df["ni"], average_equity
    )

    df["Profit Margin"] = _divide(
        df["ni"], df["sale"]
    )

    df["Current Ratio"] = _divide(
        df["act"], df["lct"]
    )

    debt = df["dlc"] + df["dltt"]

    df["Debt-to-Equity"] = _divide(
        debt, df["seq"]
    )

    df["Asset Turnover"] = _divide(
        df["sale"], average_assets
    )

    code = _standardize_sic(sic_code)

    if len(code) != 4 or not code.isdigit():
        raise ValueError(
            "Provide an exact four-digit SIC code."
        )

    peers = df.loc[
        (df["industry_sic"] == code)
        & (df["fyear"] == int(fiscal_year))
    ]

    if peers.empty:
        raise ValueError(
            f"No Compustat companies found "
            f"for SIC {code}, FY{fiscal_year}."
        )

    rows = []

    for ratio in ALL_RATIOS:

        observations = pd.to_numeric(
            peers[ratio],
            errors="coerce"
        )

        observations = observations[
            observations.map(math.isfinite)
        ]

        count = len(observations)

        if count >= min_peers:
            median = float(observations.median())
        else:
            median = float("nan")

        rows.append({
            "Ratio": ratio,
            "Industry Median": median,
            "Peer Count": count
        })

    return pd.DataFrame(rows)


def compare_with_industry(
    company_ratios,
    medians
):

    median_by_ratio = medians.set_index("Ratio")

    rows = []

    for ratio in ALL_RATIOS:

        company_value = company_ratios.get(
            ratio, (None, False)
        )[0]

        company_value = pd.to_numeric(
            company_value, errors="coerce"
        )

        median = median_by_ratio.at[
            ratio, "Industry Median"
        ]

        count = int(
            median_by_ratio.at[ratio, "Peer Count"]
        )

        if (
            not pd.notna(company_value)
            or not pd.notna(median)
        ):
            difference = float("nan")
            direction = "N/A"

        else:
            difference = float(
                company_value - median
            )

            if difference > 1e-12:
                direction = "Above median"
            elif difference < -1e-12:
                direction = "Below median"
            else:
                direction = "At median"

        rows.append({
            "Ratio": ratio,
            "Company": company_value,
            "Industry Median": median,
            "Difference": difference,
            "Comparison": direction,
            "Peer Count": count,
            "Unit": (
                "pp" if ratio in PERCENT_RATIOS else "x"
            )
        })

    return pd.DataFrame(rows)
