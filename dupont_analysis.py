
from financial_ratios import (
    _average_balance,
    _resolve_year,
    calculate_asset_turnover,
    calculate_profit_margin,
    calculate_roe,
)


def calculate_dupont(
    income_statement,
    balance_sheet,
    year=None
):

    fiscal_year_end = _resolve_year(
        income_statement, year
    )

    if fiscal_year_end is None:
        return None

    profit_margin = calculate_profit_margin(
        income_statement,
        year=fiscal_year_end
    )

    asset_turnover = calculate_asset_turnover(
        income_statement,
        balance_sheet,
        year=fiscal_year_end
    )

    average_assets = _average_balance(
        balance_sheet,
        "TotalAssets",
        fiscal_year_end
    )

    average_equity = _average_balance(
        balance_sheet,
        "StockholdersEquity",
        fiscal_year_end
    )

    if (
        profit_margin is None
        or asset_turnover is None
        or average_assets is None
        or average_equity is None
        or average_assets <= 0
        or average_equity <= 0
    ):
        return None

    equity_multiplier = (
        average_assets / average_equity
    )

    dupont_roe = (
        profit_margin
        * asset_turnover
        * equity_multiplier
    )

    return {
        "fiscal_year_end": fiscal_year_end,
        "profit_margin": profit_margin,
        "asset_turnover": asset_turnover,
        "equity_multiplier": equity_multiplier,
        "dupont_roe": dupont_roe,

        "calculated_roe": calculate_roe(
            income_statement,
            balance_sheet,
            year=fiscal_year_end
        ),
    }

