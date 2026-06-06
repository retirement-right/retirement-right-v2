"""
Module 5 — RMD Engine
Calculates Required Minimum Distributions using the IRS Uniform Lifetime Table.
Handles:
  - Traditional IRA / 401k RMDs starting at age 73
  - Inherited IRA 10-year rule (post-SECURE Act)
  - Per-account balance tracking for RMD base (prior year Dec 31 balance)
"""

# IRS Uniform Lifetime Table (age → distribution period)
UNIFORM_LIFETIME_TABLE = {
    72: 27.4, 73: 26.5, 74: 25.5, 75: 24.6, 76: 23.7, 77: 22.9,
    78: 22.0, 79: 21.1, 80: 20.2, 81: 19.4, 82: 18.5, 83: 17.7,
    84: 16.8, 85: 16.0, 86: 15.2, 87: 14.4, 88: 13.7, 89: 12.9,
    90: 12.2, 91: 11.5, 92: 10.8, 93: 10.1, 94:  9.5, 95:  8.9,
    96:  8.4, 97:  7.8, 98:  7.3, 99:  6.8, 100: 6.4,
}
RMD_START_AGE = 73


def rmd_amount(prior_year_balance: float, age: int) -> float:
    """
    Calculate RMD for current year based on prior Dec 31 balance and age.
    Returns 0 if age < RMD_START_AGE or balance is zero.
    """
    if age < RMD_START_AGE or prior_year_balance <= 0:
        return 0.0
    period = UNIFORM_LIFETIME_TABLE.get(age, UNIFORM_LIFETIME_TABLE[100])
    return round(prior_year_balance / period, 2)


def inherited_ira_distribution(
    balance: float,
    year: int,
    year_inherited: int,
    must_distribute_by: int,
    strategy: str,
    growth_rate: float,
    start_balance: float,
) -> float:
    """
    Calculate inherited IRA distribution for a given year.

    strategy:
      'even'      — equal annual draws over 10 years
      'end_loaded'— take minimum until final year, then remainder
      'rmd_table' — use RMD table for beneficiary (simplified: uniform table)
    """
    if balance <= 0:
        return 0.0

    years_remaining = must_distribute_by - year + 1
    if years_remaining <= 0:
        return balance  # final year — distribute everything

    if strategy == "even":
        # Simple: starting_balance / 10, grown by rate each year
        # More accurate: distribute proportionally so balance zeros at year 10
        return round(balance / years_remaining, 2)

    if strategy == "end_loaded":
        if years_remaining > 1:
            return 0.0  # hold until final year
        return round(balance, 2)

    if strategy == "rmd_table":
        # Use remaining years as distribution period
        return round(balance / years_remaining, 2)

    return round(balance / years_remaining, 2)


def build_rmd_table(
    client_data: dict,
    phase_table: list[dict],
    portfolio_table: list[dict],  # needs prior-year balances
) -> list[dict]:
    """
    For each year, calculate:
      - client_rmd: RMD from client traditional IRA
      - spouse_rmd: RMD from spouse traditional IRA
      - inherited_ira_dist: required distribution from inherited IRA
      - total_required_dist: sum of all required distributions

    NOTE: This module calculates the RMD *requirement*.
    The waterfall engine decides how much is actually taken vs. reinvested.
    """
    meta       = client_data["meta"]
    client     = client_data["client"]
    spouse     = client_data.get("spouse")
    assets     = client_data.get("assets", {})
    assumptions= client_data["assumptions"]
    rate       = assumptions.get("rate_of_return", 0.04)

    inh_cfg = assets.get("ira_inherited") or {}
    inh_start_bal = inh_cfg.get("balance", 0)
    year_inherited = inh_cfg.get("year_inherited")
    must_dist_by   = inh_cfg.get("must_distribute_by") or (
        (year_inherited + 10) if year_inherited else None
    )
    inh_strategy   = inh_cfg.get("distribution_strategy", "even")
    ten_year_rule  = inh_cfg.get("ten_year_rule", False)

    # Build a lookup from portfolio_table for prior-year IRA balances
    port_by_year = {p["year"]: p for p in portfolio_table}

    results = []
    inh_balance = inh_start_bal  # track running inherited IRA balance

    for i, row in enumerate(phase_table):
        year      = row["year"]
        c_age     = row["client_age"]
        s_age     = row.get("spouse_age", 0) or 0

        # Prior-year IRA balances (use opening balance for year = prior year closing)
        if i == 0:
            c_ira_prior = assets.get("ira_traditional", {}).get("client_balance", 0)
            s_ira_prior = assets.get("ira_traditional", {}).get("spouse_balance", 0)
        else:
            prev = port_by_year.get(year - 1, {})
            c_ira_prior = prev.get("client_ira_close", 0)
            s_ira_prior = prev.get("spouse_ira_close", 0)

        # RMDs — use prior year Dec 31 balance (simplified: prior year closing)
        c_rmd = rmd_amount(c_ira_prior, c_age)
        s_rmd = rmd_amount(s_ira_prior, s_age)

        # Inherited IRA distribution
        inh_dist = 0.0
        if inh_start_bal > 0 and ten_year_rule and must_dist_by:
            analysis_year = int(meta["analysis_date"][:4])
            if year >= analysis_year and year <= must_dist_by:
                inh_dist = inherited_ira_distribution(
                    balance          = inh_balance,
                    year             = year,
                    year_inherited   = year_inherited,
                    must_distribute_by = must_dist_by,
                    strategy         = inh_strategy,
                    growth_rate      = rate,
                    start_balance    = inh_start_bal,
                )
                # Grow remaining balance for next year
                inh_balance = round((inh_balance - inh_dist) * (1 + rate), 2)
                inh_balance = max(inh_balance, 0)
            elif year > must_dist_by:
                inh_dist    = 0.0
                inh_balance = 0.0

        results.append({
            **row,
            "client_rmd":        c_rmd,
            "spouse_rmd":        s_rmd,
            "inherited_ira_dist": round(inh_dist, 2),
            "inherited_ira_balance": round(inh_balance, 2),
            "total_required_dist": round(c_rmd + s_rmd + inh_dist, 2),
        })

    return results
