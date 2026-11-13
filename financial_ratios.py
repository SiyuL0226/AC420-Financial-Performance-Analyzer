"""Financial ratio calculations based on annual Yahoo Finance statements.

All calculations accept an optional `year` (a statement column, usually a
pandas Timestamp). Omitting `year` preserves the original behavior: use the
latest fiscal year. For average balance calculations, the most recent earlier
balance-sheet column is used as the beginning balance.

The debt-to-equity formula uses interest-bearing TotalDebt divided by ending
StockholdersEquity, consistent with the existing project definition.
"""

import pandas as pd


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def _latest_year(statement):
    """Find the latest available fiscal year in a statement."""
    if statement is None or statement.empty:
        return None
    return max(statement.columns)


def _resolve_year(statement, year=None):
    """Return a valid statement column, defaulting to the latest year.

    Accepts an exact column (e.g., Timestamp('2025-06-30')) or a four-digit
    fiscal year (e.g., 2025). Matching uses the statement's fiscal end date.
    """
    if statement is None or statement.empty:
        return None

    if year is None:
        return _latest_year(statement)

    if year in statement.columns:
        return year

    if isinstance(year, (int, str)) and str(year).isdigit() and len(str(year)) == 4:
        matches = [
            col for col in statement.columns
            if hasattr(col, "year") and col.year == int(year)
        ]
        return max(matches) if matches else None

    return None


def _get_value(statement, row_name, year):
    """Retrieve an accounting value safely."""
    if (
        statement is None
        or statement.empty
        or year is None
        or row_name not in statement.index
        or year not in statement.columns
    ):
        return None

    value = statement.loc[row_name, year]

    # Prevent passing ambiguous data if a statement repeats a row label.
    if not pd.api.types.is_scalar(value) or pd.isna(value):
        return None

    try:
        return float(value)
    except (TypeError, ValueError, OverflowError):
        return None


def _average_balance(balance_sheet, row_name, current_year):
    """Average the current balance and the latest preceding balance."""
    if current_year is None or balance_sheet is None or balance_sheet.empty:
        return None

    prior_years = [
        year for year in balance_sheet.columns if year < current_year
    ]
    if not prior_years:
        return None

    previous_year = max(prior_years)
    current = _get_value(balance_sheet, row_name, current_year)
    previous = _get_value(balance_sheet, row_name, previous_year)

    if current is None or previous is None:
        return None

    return (current + previous) / 2


# ==========================================
# 1. PROFITABILITY RATIOS
