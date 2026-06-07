"""
Orchestrator — Retirement-Right v2 Engine
Runs all 8 modules in dependency order and returns the complete
year-by-year projection as a list of dicts.

Usage:
    from engine.orchestrator import run_projection
    result = run_projection(client_json)
    result["years"]       → list of year dicts
    result["summary"]     → lifetime totals
    result["client_name"] → display name
"""
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from engine.dates         import build_phase_table, parse_date
from engine.proration     import build_employment_table
from engine.social_security import build_ss_table
from engine.fixed_income  import build_fixed_income_table
from engine.rmd           import build_rmd_table
from engine.waterfall     import build_waterfall_table
from engine.taxes         import build_tax_table, estimate_taxes
from engine.portfolio     import build_portfolio_table


def merge_tables(*tables: list[dict]) -> list[dict]:
    """Merge multiple per-year tables by year key."""
    if not tables:
        return []
    base = {r["year"]: dict(r) for r in tables[0]}
    for tbl in tables[1:]:
        for row in tbl:
            yr = row["year"]
            if yr in base:
                base[yr].update(row)
            else:
                base[yr] = dict(row)
    return [base[y] for y in sorted(base.keys())]


def run_projection(client_data: dict) -> dict:
    """
    Main entry point. Takes v2 JSON dict, returns full projection.
    """
    meta   = client_data["meta"]
    client = client_data["client"]
    spouse = client_data.get("spouse")

    # Normalize assumptions — convert percentage values to decimals if needed
    client_data = dict(client_data)
    client_data["assumptions"] = normalize_assumptions(client_data["assumptions"])

    # ── Step 1: Date engine — phase boundaries for all years ─────────────
    phase_table = build_phase_table(client_data)

    # ── Step 2: Employment income + 401k proration ───────────────────────
    employment_table = build_employment_table(client_data, phase_table)

    # ── Step 3: Social Security ───────────────────────────────────────────
    ss_table = build_ss_table(client_data, phase_table)

    # ── Step 4: Fixed income (pension, rental, annuity, other) ───────────
    fixed_table = build_fixed_income_table(client_data, phase_table)

    # ── Step 5: RMD calculations (requires prior-year balances) ──────────
    # First pass with empty portfolio table to bootstrap
    empty_portfolio = [{**r, "client_ira_close": 0, "spouse_ira_close": 0}
                       for r in phase_table]
    rmd_table = build_rmd_table(client_data, phase_table, empty_portfolio)

    # ── Step 6: Waterfall — income gap + draw amounts ─────────────────────
    assets = client_data.get("assets", {})
    ira_trad = assets.get("ira_traditional") or {}
    initial_balances = {
        "c_ira": ira_trad.get("client_balance", 0),
        "s_ira": ira_trad.get("spouse_balance", 0),
        "brok":  (assets.get("brokerage") or {}).get("total_balance", 0),
        "cash":  ((assets.get("cash_and_savings") or {}).get("client_balance", 0) or 0) +
                 ((assets.get("cash_and_savings") or {}).get("spouse_balance", 0) or 0),
    }
    waterfall_table = build_waterfall_table(
        client_data, phase_table,
        employment_table, ss_table, fixed_table, rmd_table,
        initial_balances,
    )

    # ── Step 7: Portfolio — apply draws to get closing balances ───────────
    portfolio_table = build_portfolio_table(
        client_data, phase_table,
        employment_table, waterfall_table, rmd_table,
    )

    # ── Step 8: RMD recalculation with real prior-year balances ──────────
    rmd_table = build_rmd_table(client_data, phase_table, portfolio_table)

    # ── Step 9: Tax estimates using gross income from waterfall ───────────
    # Build combined income table for tax engine
    combined = merge_tables(waterfall_table, ss_table, fixed_table)
    # Add ira_distributions key for tax engine
    for row in combined:
        row["ira_distributions"] = row.get("ira_distributions", 0)

    tax_table = build_tax_table(client_data, phase_table, combined)

    # ── Step 10: Merge all tables into final year-by-year projection ──────
    final = merge_tables(
        phase_table,
        employment_table,
        ss_table,
        fixed_table,
        rmd_table,
        waterfall_table,
        portfolio_table,
        tax_table,
    )

    # ── Add net income to each year ────────────────────────────────────────
    for row in final:
        row["net_income"]    = round(row.get("gross_income", 0) - row.get("total_tax", 0), 2)
        row["net_monthly"]   = round(row["net_income"] / 12, 2)

    # ── Summary totals ─────────────────────────────────────────────────────
    summary = {
        "lifetime_gross":       round(sum(r.get("gross_income", 0)  for r in final), 2),
        "lifetime_ss":          round(sum(r.get("total_ss", 0)       for r in final), 2),
        "lifetime_federal_tax": round(sum(r.get("federal_tax", 0)    for r in final), 2),
        "lifetime_state_tax":   round(sum(r.get("state_tax", 0)      for r in final), 2),
        "lifetime_net":         round(sum(r.get("net_income", 0)      for r in final), 2),
        "starting_portfolio":   final[0].get("total_portfolio", 0) if final else 0,
        "ending_portfolio":     final[-1].get("total_portfolio", 0) if final else 0,
        "projection_years":     len(final),
        "first_year":           final[0]["year"] if final else None,
        "last_year":            final[-1]["year"] if final else None,
    }

    # ── Display names ──────────────────────────────────────────────────────
    client_name = f"{client['first_name']} {client['last_name']}"
    spouse_name = f"{spouse['first_name']} {spouse['last_name']}" if spouse else None
    display_name = f"{client_name} & {spouse_name}" if spouse_name else client_name

    return {
        "client_name":   display_name,
        "analysis_date": meta["analysis_date"],
        "years":         final,
        "summary":       summary,
    }


# ── CLI runner for testing ─────────────────────────────────────────────────────
if __name__ == "__main__":
    fixture = sys.argv[1] if len(sys.argv) > 1 else "fixtures/abel.json"
    with open(fixture) as f:
        data = json.load(f)

    result = run_projection(data)
    print(f"\n{'='*70}")
    print(f"  {result['client_name']}  |  Analysis: {result['analysis_date']}")
    print(f"{'='*70}")
    print(f"  {'Year':<6} {'Ages':<10} {'Employment':>12} {'SS':>10} "
          f"{'Fixed':>10} {'IRA Dist':>10} {'Gross':>12} {'Taxes':>9} "
          f"{'Net':>12} {'Portfolio':>14}")
    print(f"  {'-'*6} {'-'*10} {'-'*12} {'-'*10} {'-'*10} "
          f"{'-'*10} {'-'*12} {'-'*9} {'-'*12} {'-'*14}")

    for r in result["years"]:
        c_age = r.get("client_age","")
        s_age = r.get("spouse_age","")
        ages  = f"{c_age}/{s_age}" if s_age else str(c_age)
        print(
            f"  {r['year']:<6} {ages:<10} "
            f"${r.get('employment_income',0):>11,.0f} "
            f"${r.get('total_ss',0):>9,.0f} "
            f"${r.get('fixed_income',0):>9,.0f} "
            f"${r.get('ira_distributions',0):>9,.0f} "
            f"${r.get('gross_income',0):>11,.0f} "
            f"${r.get('total_tax',0):>8,.0f} "
            f"${r.get('net_income',0):>11,.0f} "
            f"${r.get('total_portfolio',0):>13,.0f}"
        )

    s = result["summary"]
    print(f"\n{'─'*70}")
    print(f"  Lifetime gross:     ${s['lifetime_gross']:>14,.0f}")
    print(f"  Lifetime SS:        ${s['lifetime_ss']:>14,.0f}")
    print(f"  Lifetime fed tax:   ${s['lifetime_federal_tax']:>14,.0f}")
    print(f"  Lifetime state tax: ${s['lifetime_state_tax']:>14,.0f}")
    print(f"  Lifetime net:       ${s['lifetime_net']:>14,.0f}")
    print(f"  Starting portfolio: ${s['starting_portfolio']:>14,.0f}")
    print(f"  Ending portfolio:   ${s['ending_portfolio']:>14,.0f}")
    print(f"{'='*70}\n")


def normalize_assumptions(assumptions: dict) -> dict:
    """
    Normalize assumption values that may come in as percentages (e.g. 2.5)
    instead of decimals (e.g. 0.025). Converts any value > 1 for rate fields.
    """
    a = dict(assumptions)
    for key in ["inflation_pct", "rate_of_return", "ss_taxable_pct"]:
        if key in a and a[key] is not None:
            val = float(a[key])
            if val > 1:  # came in as percentage — convert to decimal
                a[key] = round(val / 100, 6)
    return a
