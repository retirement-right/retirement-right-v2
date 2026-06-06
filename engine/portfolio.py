"""
Module 7 — Portfolio Engine
Tracks each account balance year by year:
  - Client traditional IRA / 401k
  - Spouse traditional IRA / 401k
  - Client Roth IRA
  - Spouse Roth IRA
  - Inherited IRA (balance tracked in rmd.py, mirrored here)
  - Brokerage / taxable investments
  - Annuity (asset value)
  - Real estate equity
  - Cash & savings
  - Other assets

Each account: opening_balance + contributions + earnings - withdrawals = closing_balance
Withdrawals come from the waterfall engine (passed in).
This module grows accounts and applies draws.
"""


def grow(balance: float, rate: float) -> float:
    """Apply one year of growth."""
    return round(balance * (1 + rate), 2)


def build_portfolio_table(
    client_data: dict,
    phase_table: list[dict],
    employment_table: list[dict],
    waterfall_table: list[dict],
    rmd_table: list[dict],
) -> list[dict]:
    """
    For each year, track all account balances.
    employment_table provides 401k contributions.
    waterfall_table provides withdrawals per account.
    rmd_table provides inherited IRA distributions (already computed).
    """
    assets      = client_data.get("assets", {})
    assumptions = client_data.get("assumptions", {})
    rate        = assumptions.get("rate_of_return", 0.04)

    # Opening balances
    ira_trad    = assets.get("ira_traditional") or {}
    ira_roth    = assets.get("ira_roth") or {}
    inh_cfg     = assets.get("ira_inherited") or {}
    brokerage   = assets.get("brokerage") or {}
    cash_sav    = assets.get("cash_and_savings") or {}
    other_list  = assets.get("other_assets") or []

    c_ira_bal  = ira_trad.get("client_balance", 0)
    s_ira_bal  = ira_trad.get("spouse_balance", 0)
    c_roth_bal = ira_roth.get("client_balance", 0)
    s_roth_bal = ira_roth.get("spouse_balance", 0)
    inh_bal    = inh_cfg.get("balance", 0)
    brok_bal   = brokerage.get("total_balance", 0)
    ann_bal    = assets.get("annuity_value") or 0
    re_bal     = assets.get("real_estate_equity") or 0
    cash_bal   = (cash_sav.get("client_balance", 0) or 0) + \
                 (cash_sav.get("spouse_balance", 0) or 0)
    other_bal  = sum(a.get("balance", 0) for a in other_list if a.get("investable", True))

    # Build lookups
    emp_by_year  = {r["year"]: r for r in employment_table}
    wf_by_year   = {r["year"]: r for r in waterfall_table}
    rmd_by_year  = {r["year"]: r for r in rmd_table}

    results = []

    for row in phase_table:
        year = row["year"]
        emp  = emp_by_year.get(year, {})
        wf   = wf_by_year.get(year, {})
        rmd  = rmd_by_year.get(year, {})

        # ── CLIENT TRADITIONAL IRA ────────────────────────────────────────
        c_ira_open   = c_ira_bal
        c_contrib    = emp.get("client_401k_to_ira", 0)
        c_earn       = round(c_ira_open * rate, 2)
        c_rmd_req    = rmd.get("client_rmd", 0)
        c_extra_draw = wf.get("client_ira_extra", 0)   # extra beyond RMD if needed
        c_ira_draw   = round(c_rmd_req + c_extra_draw, 2)
        c_ira_close  = max(round(c_ira_open + c_contrib + c_earn - c_ira_draw, 2), 0)
        c_ira_bal    = c_ira_close

        # ── SPOUSE TRADITIONAL IRA ────────────────────────────────────────
        s_ira_open   = s_ira_bal
        s_contrib    = emp.get("spouse_401k_to_ira", 0)
        s_earn       = round(s_ira_open * rate, 2)
        s_rmd_req    = rmd.get("spouse_rmd", 0)
        s_extra_draw = wf.get("spouse_ira_extra", 0)
        s_ira_draw   = round(s_rmd_req + s_extra_draw, 2)
        s_ira_close  = max(round(s_ira_open + s_contrib + s_earn - s_ira_draw, 2), 0)
        s_ira_bal    = s_ira_close

        # ── ROTH IRAs ────────────────────────────────────────────────────
        c_roth_contrib = emp.get("client_contrib_roth", 0)
        c_roth_earn    = round(c_roth_bal * rate, 2)
        c_roth_draw    = wf.get("client_roth_draw", 0)
        c_roth_close   = max(round(c_roth_bal + c_roth_contrib + c_roth_earn - c_roth_draw, 2), 0)
        c_roth_bal     = c_roth_close

        s_roth_contrib = emp.get("spouse_contrib_roth", 0)
        s_roth_earn    = round(s_roth_bal * rate, 2)
        s_roth_draw    = wf.get("spouse_roth_draw", 0)
        s_roth_close   = max(round(s_roth_bal + s_roth_contrib + s_roth_earn - s_roth_draw, 2), 0)
        s_roth_bal     = s_roth_close

        # ── INHERITED IRA ─────────────────────────────────────────────────
        # Balance tracked in rmd.py; mirror it here for portfolio totals
        inh_close = rmd.get("inherited_ira_balance", inh_bal)
        inh_dist  = rmd.get("inherited_ira_dist", 0)
        inh_bal   = inh_close

        # ── BROKERAGE ────────────────────────────────────────────────────
        brok_open    = brok_bal
        brok_earn    = round(brok_open * rate, 2)
        brok_draw    = wf.get("brokerage_draw", 0)
        # Excess income (surplus after expenses) deposited to brokerage
        brok_deposit = wf.get("surplus_to_brokerage", 0)
        brok_close   = max(round(brok_open + brok_earn + brok_deposit - brok_draw, 2), 0)
        brok_bal     = brok_close

        # ── ANNUITY VALUE ────────────────────────────────────────────────
        ann_open  = ann_bal
        ann_earn  = round(ann_open * rate, 2)
        ann_draw  = wf.get("annuity_draw", 0)
        ann_close = max(round(ann_open + ann_earn - ann_draw, 2), 0)
        ann_bal   = ann_close

        # ── REAL ESTATE ──────────────────────────────────────────────────
        re_open  = re_bal
        re_earn  = round(re_open * rate, 2)
        re_draw  = wf.get("real_estate_draw", 0)
        re_close = max(round(re_open + re_earn - re_draw, 2), 0)
        re_bal   = re_close

        # ── CASH & SAVINGS ────────────────────────────────────────────────
        cash_open    = cash_bal
        cash_earn    = round(cash_open * rate, 2)
        cash_draw    = wf.get("cash_draw", 0)
        cash_deposit = wf.get("surplus_to_cash", 0)
        cash_close   = max(round(cash_open + cash_earn + cash_deposit - cash_draw, 2), 0)
        cash_bal     = cash_close

        # ── OTHER ASSETS ─────────────────────────────────────────────────
        other_close = round(other_bal * (1 + rate), 2)
        other_bal   = other_close

        # ── TOTALS ────────────────────────────────────────────────────────
        total_ira    = round(c_ira_close + s_ira_close, 2)
        total_roth   = round(c_roth_close + s_roth_close, 2)
        total_port   = round(
            c_ira_close + s_ira_close +
            c_roth_close + s_roth_close +
            inh_close + brok_close +
            ann_close + re_close +
            cash_close + other_close, 2
        )

        results.append({
            **row,
            # Client IRA
            "client_ira_open":    c_ira_open,
            "client_ira_contrib": c_contrib,
            "client_ira_earn":    c_earn,
            "client_ira_draw":    c_ira_draw,
            "client_ira_close":   c_ira_close,
            # Spouse IRA
            "spouse_ira_open":    s_ira_open,
            "spouse_ira_contrib": s_contrib,
            "spouse_ira_earn":    s_earn,
            "spouse_ira_draw":    s_ira_draw,
            "spouse_ira_close":   s_ira_close,
            # Roth
            "client_roth_close":  c_roth_close,
            "spouse_roth_close":  s_roth_close,
            # Inherited IRA
            "inherited_ira_close": inh_close,
            "inherited_ira_dist":  inh_dist,
            # Brokerage
            "brokerage_open":    brok_open,
            "brokerage_earn":    brok_earn,
            "brokerage_draw":    brok_draw,
            "brokerage_close":   brok_close,
            # Annuity
            "annuity_close":     ann_close,
            # Real estate
            "real_estate_close": re_close,
            # Cash
            "cash_open":         cash_open,
            "cash_earn":         cash_earn,
            "cash_draw":         cash_draw,
            "cash_close":        cash_close,
            # Other
            "other_close":       other_close,
            # Summary
            "total_ira":         total_ira,
            "total_roth":        total_roth,
            "total_portfolio":   total_port,
        })

    return results
