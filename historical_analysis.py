"""Historical financial-ratio calculations for the AC420 Streamlit dashboard.

Uses the six calculations in financial_ratios.py; does not fetch data itself.
All percentage ratios are stored as decimals (for example, 0.20 means 20%).
"""

import pandas as pd

from financial_ratios import (
    calculate_profit_margin,
    calculate_roa,
    calculate_roe,
    calculate_current_ratio,
    calculate_debt_to_equity,
    calculate_asset_turnover,
)


PERCENT_RATIOS = ["ROA", "ROE", "Profit Margin"]
MULTIPLE_RATIOS = ["Current Ratio", "Debt-to-Equity", "Asset Turnover"]
ALL_RATIOS = PERCENT_RATIOS + MULTIPLE_RATIOS


def calculate_historical_ratios(income_statement, balance_sheet):
    """Return one row per available income-statement fiscal year, oldest first.

    Columns: Fiscal Year, ROA, ROE, Profit Margin, Current Ratio,
    Debt-to-Equity, Asset Turnover. Missing inputs produce NaN. ROA, ROE,
    and asset turnover may be missing for the earliest year because they
    require beginning and ending balance-sheet values.
    """
    columns = ["Fiscal Year"] + ALL_RATIOS

    if (
        income_statement is None
        or balance_sheet is None
        or income_statement.empty
        or balance_sheet.empty
    ):
        return pd.DataFrame(columns=columns)

    rows = []

    for year_end in sorted(income_statement.columns):
        try:
            fiscal_year = pd.Timestamp(year_end).year
        except (TypeError, ValueError):
            continue

        rows.append({
            "Fiscal Year": fiscal_year,
            "ROA": calculate_roa(income_statement, balance_sheet, year=year_end),
            "ROE": calculate_roe(income_statement, balance_sheet, year=year_end),
            "Profit Margin": calculate_profit_margin(income_statement, year=year_end),
            "Current Ratio": calculate_current_ratio(balance_sheet, year=year_end),
            "Debt-to-Equity": calculate_debt_to_equity(balance_sheet, year=year_end),
            "Asset Turnover": calculate_asset_turnover(
                income_statement, balance_sheet, year=year_end
            ),
        })

    if not rows:
        return pd.DataFrame(columns=columns)

    result = pd.DataFrame(rows, columns=columns)
    result = result.sort_values("Fiscal Year").reset_index(drop=True)
    return result


def calculate_yoy_changes(historical_ratios):
    """Return changes versus the immediately preceding fiscal year.

    Profitability ratios use percentage-point (pp) changes, so a move
    from 20% to 23% gives +3.00 pp. Other ratios use changes in multiples
    (x), so a move from 1.20x to 1.35x gives +0.15x.

    A change is left missing if the prior year or either value is missing.
    """
    columns = (
        ["Fiscal Year"]
        + [f"{name} (pp)" for name in PERCENT_RATIOS]
        + [f"{name} (x)" for name in MULTIPLE_RATIOS]
    )

    if historical_ratios is None or historical_ratios.empty:
        return pd.DataFrame(columns=columns)

    history = historical_ratios.sort_values("Fiscal Year").reset_index(drop=True)
    changes = pd.DataFrame({"Fiscal Year": history["Fiscal Year"]})

    # Prevent a missing 2024 from turning 2023-to-2025 into a "YoY" change.
    is_consecutive = history["Fiscal Year"].diff().eq(1)

    for name in PERCENT_RATIOS:
        values = pd.to_numeric(history[name], errors="coerce")
        changes[f"{name} (pp)"] = (values.diff() * 100).where(is_consecutive)

    for name in MULTIPLE_RATIOS:
        values = pd.to_numeric(history[name], errors="coerce")
        changes[f"{name} (x)"] = values.diff().where(is_consecutive)

    return changes[columns]
