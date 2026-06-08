"""
Module 4 — Fixed Income Engine
Calculates pension, rental, annuity, and other recurring income
for each projection year. All grow by their respective COLA/growth rates.
"""
from engine.dates import parse_date, age_at_year_end


def cola_amount(base: float, cola_pct: float, years: int) -> float:
    """Apply COLA for N years to a base amount."""
    return round(base * ((1 + cola_pct) ** years), 2)


def build_fixed_income_table(client_data: dict, phase_table: list[dict]) -> list[dict]:
    """
    For each year, calculate all fixed income sources:
      pension (client + spouse), rental, annuity, other_income items.

    Returns list of dicts with fixed income fields added.

    Supports two JSON shapes for pension:
      Flat (v2 standard):  pension.client_monthly, pension.client_start_age,
                           pension.client_cola, pension.client_include_in_projection
      Nested (legacy):     pension.client.monthly_amount, pension.client.start_age,
                           pension.client.cola_pct

    Supports two JSON shapes for rental:
      New:    rental.annual_net  (preferred)
      Legacy: rental.annual_amount
    """
    meta        = client_data["meta"]
    income      = client_data.get("income", {})
    client      = client_data["client"]
    spouse      = client_data.get("spouse")

    analysis_year = int(meta["analysis_date"][:4])
    client_dob    = parse_date(client["dob"])
    spouse_dob    = parse_date(spouse["dob"]) if spouse else None

    pension_cfg = income.get("pension") or {}
    rental_cfg  = income.get("rental") or {}
    annuity_cfg = income.get("annuity") or {}
    other_list  = income.get("other_income") or []

    # ── Resolve pension config — flat v2 shape vs legacy nested shape ────
    # Flat v2 shape: keys live directly on pension_cfg
    # Legacy shape:  pension_cfg.client and pension_cfg.spouse sub-objects
    if "client_monthly" in pension_cfg or "client_start_age" in pension_cfg:
        # Flat v2 shape
        c_pension_monthly    = pension_cfg.get("client_monthly", 0) or 0
        c_pension_start_age  = pension_cfg.get("client_start_age", 0) or 0
        c_pension_cola       = pension_cfg.get("client_cola", False)
        c_pension_cola_pct   = 0.0  # cola=False means no increase
        c_pension_include    = pension_cfg.get("client_include_in_projection", True)
        c_pension_base       = c_pension_monthly * 12

        s_pension_monthly    = pension_cfg.get("spouse_monthly", 0) or 0
        s_pension_start_age  = pension_cfg.get("spouse_start_age") or 0
        s_pension_cola_pct   = 0.0
        s_pension_include    = pension_cfg.get("spouse_include_in_projection", True)
        s_pension_base       = s_pension_monthly * 12
    else:
        # Legacy nested shape
        c_pen = pension_cfg.get("client") or {}
        s_pen = pension_cfg.get("spouse") or {}
        c_pension_base       = (c_pen.get("monthly_amount", 0) or 0) * 12
        c_pension_start_age  = c_pen.get("start_age", 0) or 0
        c_pension_cola_pct   = c_pen.get("cola_pct", 0) or 0
        c_pension_include    = True
        s_pension_base       = (s_pen.get("monthly_amount", 0) or 0) * 12
        s_pension_start_age  = s_pen.get("start_age", 0) or 0
        s_pension_cola_pct   = s_pen.get("cola_pct", 0) or 0
        s_pension_include    = True

    # ── Resolve rental config — new annual_net vs legacy annual_amount ───
    # New shape has annual_net; legacy has annual_amount
    if "annual_net" in rental_cfg:
        rental_base    = rental_cfg.get("annual_net", 0) or 0
        rental_include = rental_cfg.get("include_in_projection", True)
        rental_cola    = rental_cfg.get("cola_pct", 0) or 0
    elif "annual_amount" in rental_cfg:
        rental_base    = rental_cfg.get("annual_amount", 0) or 0
        rental_include = True
        rental_cola    = rental_cfg.get("cola_pct", 0.015) or 0.015
    else:
        rental_base    = 0
        rental_include = False
        rental_cola    = 0

    results = []
    for row in phase_table:
        year   = row["year"]
        c_age  = row["client_age"]
        s_age  = row.get("spouse_age", 0) or 0
        years_elapsed = year - analysis_year

        # ── Pension — client ──────────────────────────────────────────────
        c_pension_annual = 0.0
        if c_pension_include and c_pension_base > 0 and c_age >= c_pension_start_age:
            years_on = year - (client_dob.year + c_pension_start_age)
            c_pension_annual = cola_amount(c_pension_base, c_pension_cola_pct, max(years_on, 0))

        # ── Pension — spouse ──────────────────────────────────────────────
        s_pension_annual = 0.0
        if s_pension_include and s_pension_base > 0 and spouse_dob and s_age >= s_pension_start_age:
            years_on = year - (spouse_dob.year + s_pension_start_age)
            s_pension_annual = cola_amount(s_pension_base, s_pension_cola_pct, max(years_on, 0))

        # ── Rental income ─────────────────────────────────────────────────
        rental_annual = 0.0
        if rental_include and rental_base > 0:
            rental_annual = cola_amount(rental_base, rental_cola, years_elapsed)

        # ── Annuity income ────────────────────────────────────────────────
        annuity_annual = 0.0
        if annuity_cfg:
            start_age  = annuity_cfg.get("start_age", 0)
            base       = annuity_cfg.get("annual_income", 0) or 0
            cola       = annuity_cfg.get("cola_pct", 0)
            if c_age >= start_age and base > 0:
                years_on = year - (client_dob.year + start_age)
                annuity_annual = cola_amount(base, cola, max(years_on, 0))

        # ── Other income items ────────────────────────────────────────────
        other_annual = 0.0
        other_breakdown = []
        for item in other_list:
            start_age = item.get("start_age", 0)
            end_age   = item.get("end_age")
            base      = item.get("annual_amount", 0) or 0
            cola      = item.get("cola_pct", 0)
            if c_age >= start_age and (end_age is None or c_age <= end_age):
                years_on = year - (client_dob.year + start_age)
                amt = cola_amount(base, cola, max(years_on, 0))
                other_annual += amt
                other_breakdown.append({"label": item.get("label",""), "amount": amt})

        total_fixed = round(
            c_pension_annual + s_pension_annual +
            rental_annual + annuity_annual + other_annual, 2
        )

        results.append({
            **row,
            "client_pension":       round(c_pension_annual, 2),
            "spouse_pension":       round(s_pension_annual, 2),
            "rental":               round(rental_annual, 2),
            "annuity_income":       round(annuity_annual, 2),
            "other_income":         round(other_annual, 2),
            "other_breakdown":      other_breakdown,
            "total_fixed_non_ss":   total_fixed,
        })

    return results
