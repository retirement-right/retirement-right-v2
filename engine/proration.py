"""
Module 2 — Income Proration Engine
Calculates prorated salary, 401k contributions, and employer match
for each person for each projection year, applying:
  - Partial-year proration (first year from analysis date, final year to retirement)
  - Annual raises (applied each Jan 1 on full-year salary)
  - IRS contribution limits (employee + catch-up)
  - Employer match with cap
  - Final-year 401k total flagged for IRA opening balance rollup

Contribution input supports two formats (backward compatible):
  Method A — Retirement-Right preferred (fixed dollar amounts):
    annual_contribution_trad  e.g. 23000
    annual_contribution_roth  e.g. 0
  Method B — Legacy (percentage of salary):
    contrib_401k_pct          e.g. 0.2447
    contrib_roth_401k_pct     e.g. 0.0
  Resolution order: Method A takes priority if present; Method B is fallback.
"""
from datetime import date
from typing import Optional

# ── IRS limits by tax year ────────────────────────────────────────────────────
# Format: {year: {"employee": limit, "catchup": additional_catchup, "total": combined_limit}}
IRS_LIMITS = {
    2023: {"employee": 22500,  "catchup": 7500,  "total": 66000},
    2024: {"employee": 23000,  "catchup": 7500,  "total": 69000},
    2025: {"employee": 23500,  "catchup": 7500,  "total": 70000},
    2026: {"employee": 23500,  "catchup": 7500,  "total": 71000},
}
IRS_CATCHUP_AGE = 50
IRS_RMD_START_AGE = 73

def get_irs_limits(tax_year: int) -> dict:
    """Return IRS limits for year, using most recent known year if future."""
    years = sorted(IRS_LIMITS.keys())
    yr = tax_year if tax_year in IRS_LIMITS else years[-1]
    return IRS_LIMITS[yr]


# ── Per-person per-year employment income ─────────────────────────────────────

def calc_employment_year(
    year: int,
    months_working: int,
    annual_salary_base: float,
    years_since_base: int,
    raise_pct: float,
    # --- Method A: fixed dollar amounts (None = not provided) ---
    annual_contribution_trad: Optional[float],
    annual_contribution_roth: Optional[float],
    # --- Method B: percentage of salary (fallback) ---
    contrib_401k_pct: float,
    contrib_roth_pct: float,
    # --- Employer match (unchanged) ---
    employer_match_pct: float,
    employer_match_cap_pct: float,
    apply_catchup: bool,
    age_this_year: int,
    tax_year: int,
) -> dict:
    """
    Calculate all employment-related figures for one person for one year.

    Contribution resolution:
      If annual_contribution_trad is not None → prorate by (months_working / 12)
      Else → prorated_salary * contrib_401k_pct
      Same logic for Roth.

    Returns dict with:
      prorated_salary, annual_salary (full-year),
      contrib_traditional, contrib_roth, employer_match,
      total_401k_to_ira (contrib + match),
      is_partial_year
    """
    if months_working == 0:
        return {
            "prorated_salary":       0.0,
            "annual_salary":         0.0,
            "contrib_traditional":   0.0,
            "contrib_roth":          0.0,
            "employer_match":        0.0,
            "total_401k_to_ira":     0.0,
            "is_final_working_year": False,
            "is_partial_year":       False,
        }

    # Apply raises: salary grows each full Jan 1
    annual_salary = annual_salary_base * ((1 + raise_pct) ** years_since_base)

    # Prorated salary for this year
    proration_factor = months_working / 12
    prorated_salary  = round(annual_salary * proration_factor, 2)

    # IRS limits
    limits    = get_irs_limits(tax_year)
    emp_limit = limits["employee"]
    if apply_catchup and age_this_year >= IRS_CATCHUP_AGE:
        emp_limit += limits["catchup"]
    # Prorate IRS limit for partial years
    prorated_limit = round(emp_limit * proration_factor, 2)

    # ── Contribution resolution ───────────────────────────────────────────
    # Method A (dollar amount) takes priority over Method B (percentage).
    # Both are then subject to IRS cap enforcement below.

    if annual_contribution_trad is not None:
        # Method A — prorate fixed annual dollar amount
        raw_trad = round(annual_contribution_trad * proration_factor, 2)
    else:
        # Method B — percentage of prorated salary
        raw_trad = round(prorated_salary * contrib_401k_pct, 2)

    if annual_contribution_roth is not None:
        # Method A — prorate fixed annual dollar amount
        raw_roth = round(annual_contribution_roth * proration_factor, 2)
    else:
        # Method B — percentage of prorated salary
        raw_roth = round(prorated_salary * contrib_roth_pct, 2)

    raw_total = raw_trad + raw_roth

    # ── IRS cap enforcement (traditional + Roth share same annual limit) ──
    if raw_total > prorated_limit:
        scale     = prorated_limit / raw_total
        raw_trad  = round(raw_trad * scale, 2)
        raw_roth  = round(raw_roth * scale, 2)
        raw_total = prorated_limit

    contrib_trad = raw_trad
    contrib_roth = raw_roth

    # ── Employer match ────────────────────────────────────────────────────
    # Match is applied on prorated salary up to match cap
    matchable_salary  = prorated_salary * employer_match_cap_pct
    matchable_contrib = min(raw_total, matchable_salary)
    employer_match    = round(matchable_contrib * employer_match_pct, 2)

    # ── Total flowing to traditional IRA/401k ────────────────────────────
    # Roth tracked separately in portfolio engine
    total_to_ira = round(contrib_trad + employer_match, 2)

    is_partial = (months_working < 12)

    return {
        "prorated_salary":       round(prorated_salary, 2),
        "annual_salary":         round(annual_salary, 2),
        "contrib_traditional":   contrib_trad,
        "contrib_roth":          contrib_roth,
        "employer_match":        employer_match,
        "total_401k_to_ira":     total_to_ira,
        "is_partial_year":       is_partial,
    }


# ── Build full employment table for both people ───────────────────────────────

def build_employment_table(client_data: dict, phase_table: list[dict]) -> list[dict]:
    """
    For each year in phase_table, compute employment income for client and spouse.
    Returns list of dicts, one per year, merged with phase info.
    """
    meta        = client_data["meta"]
    client      = client_data["client"]
    spouse      = client_data.get("spouse")
    assumptions = client_data["assumptions"]
    tax_year    = assumptions.get("tax_year", 2024)

    analysis_year = int(meta["analysis_date"][:4])

    def get_emp(person):
        """
        Extract employment config from person dict.
        Supports both Method A (dollar amounts) and Method B (percentages).
        Returns None for dollar fields if not present, triggering fallback to pct.
        """
        emp = person.get("employment") or {}
        return {
            "annual_salary":          emp.get("annual_salary", 0),
            "annual_raise_pct":       emp.get("annual_raise_pct", 0),
            # Method A — dollar amounts (None if absent → fallback to pct)
            "annual_contribution_trad": emp.get("annual_contribution_trad"),
            "annual_contribution_roth": emp.get("annual_contribution_roth"),
            # Method B — percentages (fallback if dollar amounts absent)
            "contrib_401k_pct":       emp.get("contrib_401k_pct", 0),
            "contrib_roth_401k_pct":  emp.get("contrib_roth_401k_pct", 0),
            # Employer match (same for both methods)
            "employer_match_pct":     emp.get("employer_match_pct", 0),
            "employer_match_cap_pct": emp.get("employer_match_cap_pct", 0),
            "apply_catchup":          emp.get("apply_catchup", True),
        }

    c_emp = get_emp(client)
    s_emp = get_emp(spouse) if spouse else get_emp({})

    results = []
    for row in phase_table:
        year     = row["year"]
        yrs_since = year - analysis_year

        # Client
        c_result = calc_employment_year(
            year                     = year,
            months_working           = row["client_months_working"],
            annual_salary_base       = c_emp["annual_salary"],
            years_since_base         = yrs_since,
            raise_pct                = c_emp["annual_raise_pct"],
            annual_contribution_trad = c_emp["annual_contribution_trad"],
            annual_contribution_roth = c_emp["annual_contribution_roth"],
            contrib_401k_pct         = c_emp["contrib_401k_pct"],
            contrib_roth_pct         = c_emp["contrib_roth_401k_pct"],
            employer_match_pct       = c_emp["employer_match_pct"],
            employer_match_cap_pct   = c_emp["employer_match_cap_pct"],
            apply_catchup            = c_emp["apply_catchup"],
            age_this_year            = row["client_age"],
            tax_year                 = tax_year,
        )

        # Spouse
        s_result = calc_employment_year(
            year                     = year,
            months_working           = row["spouse_months_working"],
            annual_salary_base       = s_emp["annual_salary"],
            years_since_base         = yrs_since,
            raise_pct                = s_emp["annual_raise_pct"],
            annual_contribution_trad = s_emp["annual_contribution_trad"],
            annual_contribution_roth = s_emp["annual_contribution_roth"],
            contrib_401k_pct         = s_emp["contrib_401k_pct"],
            contrib_roth_pct         = s_emp["contrib_roth_401k_pct"],
            employer_match_pct       = s_emp["employer_match_pct"],
            employer_match_cap_pct   = s_emp["employer_match_cap_pct"],
            apply_catchup            = s_emp["apply_catchup"],
            age_this_year            = row["spouse_age"] or 0,
            tax_year                 = tax_year,
        )

        results.append({
            **row,
            "client_salary":            c_result["prorated_salary"],
            "client_contrib_trad":      c_result["contrib_traditional"],
            "client_contrib_roth":      c_result["contrib_roth"],
            "client_match":             c_result["employer_match"],
            "client_401k_to_ira":       c_result["total_401k_to_ira"],
            "spouse_salary":            s_result["prorated_salary"],
            "spouse_contrib_trad":      s_result["contrib_traditional"],
            "spouse_contrib_roth":      s_result["contrib_roth"],
            "spouse_match":             s_result["employer_match"],
            "spouse_401k_to_ira":       s_result["total_401k_to_ira"],
            "total_employment_income":  round(
                c_result["prorated_salary"] + s_result["prorated_salary"], 2),
            "total_401k_contributions": round(
                c_result["contrib_traditional"] + c_result["contrib_roth"] +
                s_result["contrib_traditional"] + s_result["contrib_roth"], 2),
        })

    return results
