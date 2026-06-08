"""
Module 8 — Waterfall Engine
The core income gap calculator. For each year:
  1. Sum all income sources
  2. Calculate spending need (inflation-adjusted)
  3. Determine gap = need - income
  4. Fund gap in waterfall order:
       Employment income (working years)
       → SS + Fixed income (pension, rental, annuity)
       → IRA RMDs (mandatory — taken regardless, surplus reinvests)
       → Brokerage / investments
       → Cash & savings (last resort)
  5. When RMDs exceed gap → surplus RMDs reinvest to brokerage
  6. When RMDs insufficient → extra split evenly between client/spouse IRA
  7. Returns per-source draw amounts for portfolio engine to apply
"""


def build_waterfall_table(
    client_data: dict,
    phase_table: list[dict],
    employment_table: list[dict],
    ss_table: list[dict],
    fixed_income_table: list[dict],
    rmd_table: list[dict],
    portfolio_balances: dict,  # current balances by account name
) -> list[dict]:
    """
    For each year, calculate income waterfall and return draw amounts.

    portfolio_balances: running balances passed in from portfolio engine.
    This is a two-pass system:
      Pass 1 (this module): determine draws needed
      Pass 2 (portfolio.py): apply draws to get closing balances

    Since they're interdependent, the orchestrator runs an iterative approach:
    waterfall uses *opening* balances to determine draws, portfolio applies them.
    """
    meta        = client_data["meta"]
    assumptions = client_data["assumptions"]
    assets      = client_data.get("assets", {})

    inflation     = assumptions.get("inflation_pct", 0.025)
    base_need     = assumptions.get("income_need_annual", 80000)
    rate          = assumptions.get("rate_of_return", 0.04)
    analysis_year = int(meta["analysis_date"][:4])

    # Build lookups
    emp_by_year = {r["year"]: r for r in employment_table}
    ss_by_year  = {r["year"]: r for r in ss_table}
    fix_by_year = {r["year"]: r for r in fixed_income_table}
    rmd_by_year = {r["year"]: r for r in rmd_table}

    # Running portfolio balances (updated each year)
    ira_trad   = assets.get("ira_traditional") or {}
    c_ira_bal  = ira_trad.get("client_balance", 0)
    s_ira_bal  = ira_trad.get("spouse_balance", 0)
    brok_bal   = (assets.get("brokerage") or {}).get("total_balance", 0)
    ann_bal    = assets.get("annuity_value") or 0
    cash_sav   = assets.get("cash_and_savings") or {}
    cash_bal   = (cash_sav.get("client_balance", 0) or 0) + \
                 (cash_sav.get("spouse_balance", 0) or 0)
    re_bal     = assets.get("real_estate_equity") or 0
    other_bal  = sum(a.get("balance", 0) for a in (assets.get("other_assets") or [])
                     if a.get("investable", True))

    results = []

    for row in phase_table:
        year   = row["year"]
        emp    = emp_by_year.get(year, {})
        ss     = ss_by_year.get(year, {})
        fix    = fix_by_year.get(year, {})
        rmd    = rmd_by_year.get(year, {})

        # ── Income sources ────────────────────────────────────────────────
        employment_income = emp.get("total_employment_income", 0)
        ss_income         = ss.get("total_ss", 0)
        fixed_income      = fix.get("total_fixed_non_ss", 0)
        inh_dist          = rmd.get("inherited_ira_dist", 0)
        c_rmd             = rmd.get("client_rmd", 0)
        s_rmd             = rmd.get("spouse_rmd", 0)
        total_rmd         = c_rmd + s_rmd

        # ── Inflation-adjusted spending need ──────────────────────────────
        years_elapsed = year - analysis_year
        need = round(base_need * ((1 + inflation) ** years_elapsed), 2)

        # ── Fixed income total (employment + SS + other fixed) ────────────
        total_fixed = round(employment_income + ss_income + fixed_income + inh_dist, 2)

        # ── Gap = need - fixed income ─────────────────────────────────────
        gap = round(need - total_fixed, 2)

        # Initialize draw amounts
        c_rmd_taken = 0.0
        s_rmd_taken = 0.0
        c_ira_extra = 0.0
        s_ira_extra = 0.0
        brok_draw   = 0.0
        cash_draw   = 0.0
        surplus_to_brok = 0.0

        if gap <= 0:
            # Fixed income already covers need.
            # RMDs are MANDATORY — must still be taken and reported as taxable income.
            # The excess (RMDs + fixed surplus) reinvests into brokerage.
            c_rmd_taken = c_rmd
            s_rmd_taken = s_rmd
            surplus_to_brok = round(abs(gap) + total_rmd, 2)

        else:
            # Gap exists — fund it from waterfall
            remaining_gap = gap

            # Step 1: RMDs — IRS MANDATORY. Always taken in FULL.
            # If RMD > remaining_gap, excess reinvests to brokerage.
            c_rmd_taken = c_rmd          # always take the full RMD
            s_rmd_taken = s_rmd          # always take the full RMD
            remaining_gap -= (c_rmd_taken + s_rmd_taken)

            if remaining_gap <= 0:
                # RMDs alone covered the gap — reinvest the RMD surplus
                surplus_to_brok = round(abs(remaining_gap), 2)
                remaining_gap = 0

            # Step 2: Extra IRA draws — split evenly between client and spouse
            if remaining_gap > 0:
                half = round(remaining_gap / 2, 2)
                # Client IRA extra (from available balance)
                c_avail     = max(c_ira_bal * (1 + rate) - c_rmd_taken, 0)
                c_ira_extra = min(half, c_avail)
                # Spouse IRA extra
                s_avail     = max(s_ira_bal * (1 + rate) - s_rmd_taken, 0)
                s_ira_extra = min(remaining_gap - c_ira_extra, s_avail)
                remaining_gap = round(remaining_gap - c_ira_extra - s_ira_extra, 2)

            # Step 3: Brokerage
            if remaining_gap > 0:
                brok_draw   = min(remaining_gap, brok_bal * (1 + rate))
                remaining_gap = round(remaining_gap - brok_draw, 2)

            # Step 4: Cash & savings (last resort)
            if remaining_gap > 0:
                cash_draw   = min(remaining_gap, cash_bal * (1 + rate))
                remaining_gap = round(remaining_gap - cash_draw, 2)

        # ── Gross income for tax calculation ──────────────────────────────
        ira_distributions = round(c_rmd_taken + s_rmd_taken + c_ira_extra + s_ira_extra + inh_dist, 2)
        gross_income = round(total_fixed + ira_distributions, 2)

        # ── Net income (before applying to need) ──────────────────────────
        # Tax estimated separately in tax engine; net shown for reference
        surplus = round(gross_income - need, 2)  # positive = excess, negative = shortfall

        # ── Update running balances (simplified — portfolio.py does full calc) ──
        c_ira_bal = max(round(c_ira_bal * (1 + rate) + emp.get("client_401k_to_ira", 0)
                              - c_rmd_taken - c_ira_extra, 2), 0)
        s_ira_bal = max(round(s_ira_bal * (1 + rate) + emp.get("spouse_401k_to_ira", 0)
                              - s_rmd_taken - s_ira_extra, 2), 0)
        brok_bal  = max(round(brok_bal * (1 + rate) + surplus_to_brok - brok_draw, 2), 0)
        cash_bal  = max(round(cash_bal * (1 + rate) - cash_draw, 2), 0)

        results.append({
            **row,
            # Income sources
            "employment_income":   round(employment_income, 2),
            "ss_income":           round(ss_income, 2),
            "fixed_income":        round(fixed_income, 2),
            "inherited_ira_dist":  round(inh_dist, 2),
            "total_fixed_income":  total_fixed,
            # Gap
            "spending_need":       need,
            "income_gap":          round(gap, 2),
            # Draws
            "client_rmd_taken":    round(c_rmd_taken, 2),
            "spouse_rmd_taken":    round(s_rmd_taken, 2),
            "client_ira_extra":    round(c_ira_extra, 2),
            "spouse_ira_extra":    round(s_ira_extra, 2),
            "ira_distributions":   ira_distributions,
            "brokerage_draw":      round(brok_draw, 2),
            "surplus_to_brokerage":round(surplus_to_brok, 2),
            "cash_draw":           round(cash_draw, 2),
            "client_ira_extra":    round(c_ira_extra, 2),
            "spouse_ira_extra":    round(s_ira_extra, 2),
            # Income summary
            "gross_income":        gross_income,
            "income_surplus":      surplus,
            # Pass-throughs for portfolio engine
            "client_roth_draw":    0.0,
            "spouse_roth_draw":    0.0,
            "annuity_draw":        0.0,
            "real_estate_draw":    0.0,
            "surplus_to_cash":     0.0,
        })

    return results
