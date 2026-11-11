
import pandas as pd


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def _latest_year(statement):
    """Find the latest available fiscal year."""
    if statement is None or statement.empty:
        return None

    return statement.columns.max()


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

    if pd.isna(value):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _average_balance(balance_sheet, row_name, current_year):
    """Calculate average beginning and ending balance."""

    if current_year is None or balance_sheet is None or balance_sheet.empty:
        return None

    prior_years = [
        year for year in balance_sheet.columns
        if year < current_year
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
# ==========================================

def calculate_profit_margin(income_statement):
    """
    Profit Margin = Net Income / Total Revenue
    """

    year = _latest_year(income_statement)

    net_income = _get_value(
        income_statement, "NetIncome", year
    )

    revenue = _get_value(
        income_statement, "TotalRevenue", year
    )

    if net_income is None or revenue is None or revenue == 0:
        return None

    return net_income / revenue


def calculate_roa(income_statement, balance_sheet):
    """
    ROA = Net Income / Average Total Assets
    """

    year = _latest_year(income_statement)

    net_income = _get_value(
        income_statement, "NetIncome", year
    )

    average_assets = _average_balance(
        balance_sheet, "TotalAssets", year
    )

    if (
        net_income is None
        or average_assets is None
        or average_assets <= 0
    ):
        return None

    return net_income / average_assets


def calculate_roe(income_statement, balance_sheet):
    """
    ROE = Net Income / Average Stockholders' Equity
    """

    year = _latest_year(income_statement)

    net_income = _get_value(
        income_statement, "NetIncome", year
    )

    average_equity = _average_balance(
        balance_sheet, "StockholdersEquity", year
    )

    if (
        net_income is None
        or average_equity is None
        or average_equity <= 0
    ):
        return None

    return net_income / average_equity


# ==========================================
# 2. LIQUIDITY RATIO
# ==========================================

def calculate_current_ratio(balance_sheet):
    """
    Current Ratio = Current Assets / Current Liabilities
    """

    year = _latest_year(balance_sheet)

    current_assets = _get_value(
        balance_sheet, "CurrentAssets", year
    )

    current_liabilities = _get_value(
        balance_sheet, "CurrentLiabilities", year
    )

    if (
        current_assets is None
        or current_liabilities is None
        or current_liabilities <= 0
    ):
        return None

    return current_assets / current_liabilities


# ==========================================
# 3. LEVERAGE RATIO
# ==========================================

def calculate_debt_to_equity(balance_sheet):
    """
    Debt-to-Equity = Total Interest-Bearing Debt /
                     Stockholders' Equity
    """

    year = _latest_year(balance_sheet)

    total_debt = _get_value(
        balance_sheet, "TotalDebt", year
    )

    equity = _get_value(
        balance_sheet, "StockholdersEquity", year
    )

    if (
        total_debt is None
        or equity is None
        or equity <= 0
    ):
        return None

    return total_debt / equity


# ==========================================
# 4. EFFICIENCY RATIO
# ==========================================

def calculate_asset_turnover(income_statement, balance_sheet):
    """
    Asset Turnover = Total Revenue / Average Total Assets
    """

    year = _latest_year(income_statement)

    revenue = _get_value(
        income_statement, "TotalRevenue", year
    )

    average_assets = _average_balance(
        balance_sheet, "TotalAssets", year
    )

    if (
        revenue is None
        or average_assets is None
        or average_assets <= 0
    ):
        return None

    return revenue / average_assets


