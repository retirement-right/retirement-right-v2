"""
Module 6 — Tax Estimator
Estimates federal and state income tax for each projection year.
Uses 2024 brackets by default (configurable via tax_year).
Handles MFJ and single filers, SS taxable portion, standard deduction.

These are planning estimates — not a substitute for a tax professional.
"""

# ── Federal tax brackets ──────────────────────────────────────────────────────
# Format: {year: {"mfj": [(rate, limit), ...], "single": [(rate, limit), ...]}}
# limit = upper bound of bracket; last entry limit = None (top bracket)
FEDERAL_BRACKETS = {
    2024: {
        "married_filing_jointly": [
            (0.10,  23200),
            (0.12,  94300),
            (0.22,  201050),
            (0.24,  383900),
            (0.32,  487450),
            (0.35,  731200),
            (0.37,  None),
        ],
        "single": [
            (0.10,  11600),
            (0.12,  47150),
            (0.22,  100525),
            (0.24,  191950),
            (0.32,  243725),
            (0.35,  609350),
            (0.37,  None),
        ],
        "standard_deduction": {
            "married_filing_jointly": 29200,
            "single":                 14600,
            "head_of_household":      21900,
            "married_filing_separately": 14600,
        },
    }
}

# Arizona flat rate (example; extendable to other states)
STATE_RATES = {
    "AZ": 0.025,
    "TX": 0.0,
    "FL": 0.0,
    "NV": 0.0,
    "WA": 0.0,
}


def get_brackets(filing_status: str, tax_year: int) -> list:
    year_data = FEDERAL_BRACKETS.get(tax_year, FEDERAL_BRACKETS[2024])
    # Normalize filing status to bracket key
    key = filing_status if filing_status in year_data else "married_filing_jointly"
    return year_data[key]


def get_standard_deduction(filing_status: str, tax_year: int) -> float:
    year_data = FEDERAL_BRACKETS.get(tax_year, FEDERAL_BRACKETS[2024])
    deductions = year_data.get("standard_deduction", {})
    return deductions.get(filing_status, deductions.get("married_filing_jointly", 29200))


def calc_federal_tax(taxable_income: float, filing_status: str, tax_year: int) -> float:
    """
    Calculate federal income tax using progressive brackets.
    taxable_income = gross income - standard deduction (already applied by caller).
    """
    if taxable_income <= 0:
        return 0.0

    brackets = get_brackets(filing_status, tax_year)
    tax = 0.0
    prev_limit = 0.0

    for rate, limit in brackets:
        if limit is None:
            # Top bracket — tax everything remaining
            tax += (taxable_income - prev_limit) * rate
            break
        bracket_income = min(taxable_income, limit) - prev_limit
        if bracket_income <= 0:
            break
        tax += bracket_income * rate
        prev_limit = limit

    return round(tax, 2)


def calc_state_tax(gross_income: float, ss_income: float, state: str | None) -> float:
    """
    Estimate state income tax.
    Many states exempt SS from state tax — subtract SS before applying rate.
    """
    if not state:
        return 0.0
    rate = STATE_RATES.get(state.upper(), 0.0)
    if rate == 0.0:
        return 0.0
    # Most states don't tax SS
    taxable_state = max(gross_income - ss_income, 0)
    return round(taxable_state * rate, 2)


def estimate_taxes(
    year: int,
    gross_income: float,
    ss_income: float,
    ss_taxable_pct: float,
    ira_distributions: float,
    filing_status: str,
    state: str | None,
    tax_year: int,
    inflation_pct: float,
    analysis_year: int,
) -> dict:
    """
    Estimate total taxes for one year.

    Taxable income =
      (gross - ss_income)              ← wages, IRA dist, pension, rental
      + ss_income * ss_taxable_pct     ← taxable SS portion
      - standard_deduction             ← inflation-adjusted estimate

    Returns: {"federal": float, "state": float, "total": float, "marginal_bracket": float}
    """
    # SS taxable portion
    ss_taxable = ss_income * ss_taxable_pct

    # Non-SS income (already taxable in full)
    non_ss_income = gross_income - ss_income

    # Gross taxable before deduction
    gross_taxable = non_ss_income + ss_taxable

    # Standard deduction — inflate from tax_year to current year
    base_deduction = get_standard_deduction(filing_status, tax_year)
    years_inflated = year - analysis_year
    # Deduction grows with inflation as a proxy for future adjustments
    std_deduction = round(base_deduction * ((1 + inflation_pct) ** years_inflated), 0)

    taxable_income = max(gross_taxable - std_deduction, 0)

    federal = calc_federal_tax(taxable_income, filing_status, tax_year)
    state_t = calc_state_tax(gross_income, ss_income, state)
    total   = round(federal + state_t, 2)

    # Find marginal bracket
    brackets = get_brackets(filing_status, tax_year)
    marginal = brackets[-1][0]
    prev = 0.0
    for rate, limit in brackets:
        if limit is None or taxable_income <= limit:
            marginal = rate
            break
        prev = limit

    return {
        "federal_tax":      federal,
        "state_tax":        state_t,
        "total_tax":        total,
        "taxable_income":   round(taxable_income, 2),
        "std_deduction":    std_deduction,
        "marginal_bracket": marginal,
    }


def build_tax_table(
    client_data: dict,
    phase_table: list[dict],
    income_table: list[dict],  # merged employment + SS + fixed income
) -> list[dict]:
    """
    For each year, estimate taxes based on total gross income.
    income_table must have: gross_income, total_ss, ira_distributions keys.
    """
    meta        = client_data["meta"]
    client      = client_data["client"]
    assumptions = client_data["assumptions"]

    filing_status  = client.get("filing_status", "married_filing_jointly")
    state          = client.get("state")
    tax_year       = assumptions.get("tax_year", 2024)
    ss_taxable_pct = assumptions.get("ss_taxable_pct", 0.85)
    inflation_pct  = assumptions.get("inflation_pct", 0.025)
    analysis_year  = int(meta["analysis_date"][:4])
    has_spouse     = client_data.get("spouse") is not None

    # Build income lookup
    income_by_year = {r["year"]: r for r in income_table}
    # alive flags come from income_table (merged from ss engine)
    alive_by_year  = income_by_year

    results = []
    for row in phase_table:
        year = row["year"]
        inc  = income_by_year.get(year, {})
        alv  = alive_by_year.get(year, {})

        # ── Filing status switches to single after first spouse dies ──────
        client_alive = alv.get("client_alive", True)
        spouse_alive = alv.get("spouse_alive", True)

        if not has_spouse:
            year_filing_status = "single"
        elif client_alive and spouse_alive:
            year_filing_status = filing_status      # MFJ while both alive
        elif client_alive and not spouse_alive:
            year_filing_status = "single"           # Client widowed
        elif not client_alive and spouse_alive:
            year_filing_status = "single"           # Spouse widowed
        else:
            year_filing_status = "single"           # Both deceased

        # Use gross_income_for_tax which includes brokerage draws + non-IRA earnings
        # Falls back to gross_income for backwards compatibility
        gross     = inc.get("gross_income_for_tax", inc.get("gross_income", 0))
        ss_income = inc.get("total_ss", 0)
        ira_dists = inc.get("ira_distributions", 0)

        tax_result = estimate_taxes(
            year              = year,
            gross_income      = gross,
            ss_income         = ss_income,
            ss_taxable_pct    = ss_taxable_pct,
            ira_distributions = ira_dists,
            filing_status     = year_filing_status,
            state             = state,
            tax_year          = tax_year,
            inflation_pct     = inflation_pct,
            analysis_year     = analysis_year,
        )

        results.append({
            **row,
            **tax_result,
            "filing_status_used":        year_filing_status,
            "gross_income_for_tax":      inc.get("gross_income_for_tax", inc.get("gross_income", 0)),
            "taxable_brokerage_income":  inc.get("taxable_brokerage_income", 0),
        })

    return results
