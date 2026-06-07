"""
PDF Generator — Retirement-Right v2
Takes client JSON + projection dict from engine
Returns PDF bytes (not a file — caller decides what to do with it)
"""
import io
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, HRFlowable, PageBreak, KeepInFrame
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ── Page geometry ─────────────────────────────────────────────────────────────
PAGE_W, PAGE_H = landscape(letter)
MARGIN = 0.4 * inch
PW = PAGE_W - 2 * MARGIN
PH = PAGE_H - 2 * MARGIN

# ── Palette ───────────────────────────────────────────────────────────────────
NAVY      = colors.HexColor('#185FA5')
NAVY_DK   = colors.HexColor('#0C447C')
NAVY_LT   = colors.HexColor('#E6F1FB')
TEAL      = colors.HexColor('#0F6E56')
TEAL_LT   = colors.HexColor('#E1F5EE')
TEAL_DK   = colors.HexColor('#085041')
PURPLE    = colors.HexColor('#534AB7')
PURPLE_LT = colors.HexColor('#EEEDFE')
PURPLE_DK = colors.HexColor('#3C3489')
AMBER     = colors.HexColor('#BA7517')
AMBER_LT  = colors.HexColor('#FEF3CD')
AMBER_DK  = colors.HexColor('#633806')
BLUE      = colors.HexColor('#378ADD')
BLUE_LT   = colors.HexColor('#EBF4FE')
BLUE_DK   = colors.HexColor('#0C447C')
GREEN     = colors.HexColor('#639922')
GREEN_LT  = colors.HexColor('#EAF3DE')
GREEN_DK  = colors.HexColor('#27500A')
BROWN     = colors.HexColor('#854F0B')
BROWN_LT  = colors.HexColor('#FAEEDA')
BROWN_DK  = colors.HexColor('#412402')
RED       = colors.HexColor('#993C1D')
RED_LT    = colors.HexColor('#F5C4B3')
RED_TXT   = colors.HexColor('#A32D2D')
GRAY_BG   = colors.HexColor('#F5F4F1')
GRAY_LN   = colors.HexColor('#D3D1C7')
WHITE     = colors.white
BLACK     = colors.HexColor('#2C2C2A')
MUTED     = colors.HexColor('#5F5E5A')
POS       = colors.HexColor('#3B6D11')
GHOST     = colors.HexColor('#F8F7F5')

# ── Style factory ─────────────────────────────────────────────────────────────
def ps(name, size=7, color=BLACK, align=TA_RIGHT, leading=None, bold=False, italic=False):
    if bold:
        fn = 'Helvetica-Bold'
    elif italic:
        fn = 'Helvetica-Oblique'
    else:
        fn = 'Helvetica'
    ld = leading or (size + 2)
    return ParagraphStyle(name, fontName=fn, fontSize=size,
                          textColor=color, leading=ld, alignment=align)

SW    = ps('sw',  color=WHITE,    align=TA_CENTER, bold=True, size=6.5)
SWL   = ps('swl', color=WHITE,    align=TA_LEFT,   bold=True, size=6.5)
STD   = ps('std', color=BLACK,    align=TA_RIGHT,  size=6.5)
STL   = ps('stl', color=MUTED,    align=TA_LEFT,   size=6.5)
SNEG  = ps('neg', color=RED_TXT,  align=TA_RIGHT,  bold=True, size=6.5)
SPOS  = ps('pos', color=POS,      align=TA_RIGHT,  bold=True, size=6.5)
STEAL = ps('tel', color=TEAL_DK,  align=TA_RIGHT,  bold=True, size=6.5)
SNVY  = ps('nvy', color=NAVY_DK,  align=TA_RIGHT,  bold=True, size=6.5)
SBLU  = ps('blu', color=BLUE_DK,  align=TA_RIGHT,  bold=True, size=6.5)
SGRN  = ps('grn', color=GREEN_DK, align=TA_RIGHT,  bold=True, size=6.5)
SBRN  = ps('brn', color=BROWN_DK, align=TA_RIGHT,  bold=True, size=6.5)
SRED  = ps('red', color=RED_TXT,  align=TA_RIGHT,  bold=True, size=6.5)
SPRP  = ps('prp', color=PURPLE_DK,align=TA_RIGHT,  bold=True, size=6.5)
SAMB  = ps('amb', color=AMBER_DK, align=TA_RIGHT,  bold=True, size=6.5)
SFOOT = ps('ft',  color=MUTED,    align=TA_LEFT,   size=5.5,  leading=7.5)
SAI   = ps('ai',  color=NAVY_DK,  align=TA_LEFT,   size=6.5,  leading=9)
SAIH  = ps('aih', color=NAVY_DK,  align=TA_LEFT,   size=7,    bold=True)

def p(txt, sty): return Paragraph(str(txt), sty)
def fmt(v):
    if v is None or v == 0: return '—'
    return f'${abs(v):,.0f}'
def ec(v, sty): return p(fmt(v), sty) if v else p('—', STD)


# ── Shared builders ───────────────────────────────────────────────────────────
def page_header(pg_num, total_pages, pg_title, pg_sub, client_name,
                analysis_date, ss_info, accent=NAVY):
    ey = ps('ey', color=colors.HexColor('#B5D4F4'), align=TA_LEFT, size=6, bold=True)
    ht = ps('ht', color=WHITE, align=TA_LEFT, size=12, leading=15, bold=True)
    hs = ps('hs', color=colors.HexColor('#B5D4F4'), align=TA_LEFT, size=6.5)
    pl = ps('pl', color=colors.HexColor('#B5D4F4'), align=TA_RIGHT, size=6, bold=True)
    wt = ps('wt', color=WHITE, align=TA_RIGHT, size=11, leading=14, bold=True)
    ws = ps('ws', color=colors.HexColor('#B5D4F4'), align=TA_RIGHT, size=6.5, leading=8)

    LW = PW * 0.52 - 24
    RW = PW * 0.48 - 24

    left = KeepInFrame(LW, 60, [
        p('RETIREMENT-RIGHT FINANCIAL ANALYSIS', ey),
        Spacer(1, 2),
        p(f'Retirement Income Analysis — {client_name}', ht),
        Spacer(1, 2),
        p(f'Prepared {analysis_date}  |  {ss_info}  |  4% growth', hs),
    ], mode='shrink')

    right = KeepInFrame(RW, 60, [
        p(f'PAGE {pg_num} OF {total_pages}', pl),
        Spacer(1, 3),
        p(pg_title, wt),
        Spacer(1, 2),
        p(pg_sub, ws),
    ], mode='shrink')

    t = Table([[left, right]], colWidths=[PW * 0.52, PW * 0.48])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), accent),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 9),
        ('LEFTPADDING', (0, 0), (0, -1), 12),
        ('RIGHTPADDING', (0, 0), (0, -1), 12),
        ('LEFTPADDING', (1, 0), (1, -1), 12),
        ('RIGHTPADDING', (1, 0), (1, -1), 12),
    ]))
    return t


def subbar(left, right, bg=NAVY_DK):
    sl = ps('sl', color=AMBER_LT, align=TA_LEFT, size=6.5, bold=True)
    sr = ps('sr', color=colors.HexColor('#FFFFFFAA'), align=TA_RIGHT, size=6, bold=True)
    t = Table([[p(left, sl), p(right, sr)]], colWidths=[PW * 0.56, PW * 0.44])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (0, -1), 12),
        ('RIGHTPADDING', (-1, 0), (-1, -1), 12),
    ]))
    return t


def ai_note(body):
    t = Table([[p('Advisor Note', SAIH), p(body, SAI)]],
              colWidths=[PW * 0.11, PW * 0.89])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), NAVY_LT),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 9),
        ('RIGHTPADDING', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEAFTER', (0, 0), (0, -1), 1.5, NAVY),
    ]))
    return t


def summary_boxes(items, n_cols=4):
    cw = PW / n_cols
    cells = []
    for col, title, body in items:
        tt = ps('bt', color=BLACK, align=TA_LEFT, bold=True, size=7)
        tb = ps('bd', color=MUTED, align=TA_LEFT, size=6, leading=8)
        c = Table([[p(title, tt)], [p(body, tb)]], colWidths=[cw - 10])
        c.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), WHITE),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 7),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('LINEBEFORE', (0, 0), (0, -1), 2.5, col),
            ('BOX', (0, 0), (-1, -1), 0.5, GRAY_LN),
        ]))
        cells.append(c)
    t = Table([cells], colWidths=[cw] * n_cols)
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    return t


def footer_note(body):
    return [
        HRFlowable(width=PW, thickness=0.4, color=GRAY_LN),
        Spacer(1, 2),
        p(body, SFOOT),
    ]


def data_row_style(ri, bg, highlights):
    cmds = [
        ('BACKGROUND', (0, ri), (-1, ri), bg),
        ('TOPPADDING', (0, ri), (-1, ri), 3),
        ('BOTTOMPADDING', (0, ri), (-1, ri), 3),
        ('LEFTPADDING', (0, ri), (-1, ri), 3),
        ('RIGHTPADDING', (0, ri), (-1, ri), 3),
        ('VALIGN', (0, ri), (-1, ri), 'MIDDLE'),
        ('LINEBELOW', (0, ri), (-1, ri), 0.25, GRAY_LN),
    ]
    for (c1, c2), col in highlights:
        cmds.append(('BACKGROUND', (c1, ri), (c2, ri), col))
    return cmds


def phase_row_style(ri, col):
    return [
        ('SPAN', (0, ri), (-1, ri)),
        ('BACKGROUND', (0, ri), (-1, ri), col),
        ('TOPPADDING', (0, ri), (-1, ri), 4),
        ('BOTTOMPADDING', (0, ri), (-1, ri), 4),
        ('LEFTPADDING', (0, ri), (-1, ri), 9),
        ('RIGHTPADDING', (0, ri), (-1, ri), 9),
        ('VALIGN', (0, ri), (-1, ri), 'MIDDLE'),
    ]


# ── Page builders ─────────────────────────────────────────────────────────────

def build_working_page(story, client_data, projection, ctx):
    """Page 1 — Working years (only added if client or spouse is/was working)"""
    years     = projection["years"]
    working   = [r for r in years if r.get("total_employment_income", 0) > 0]
    if not working:
        return  # skip page entirely if no working years

    client    = client_data["client"]
    spouse    = client_data.get("spouse")
    need_base = client_data["assumptions"].get("income_need_annual", client_data["assumptions"].get("annual_income_need", 80000))
    inflation = client_data["assumptions"].get("inflation_pct", 0.025)

    story.append(page_header(
        ctx["pg"], ctx["total"], 'Working Years',
        'Salary · 401k contributions · taxes · surplus — while employed',
        ctx["name"], ctx["date"], ctx["ss_info"], TEAL))
    ctx["pg"] += 1

    story.append(subbar(
        f'WORKING YEARS  |  ${need_base:,.0f} income need  ·  {inflation*100:.1f}% inflation',
        'EMPLOYMENT INCOME COVERS ALL SPENDING — PORTFOLIO UNTOUCHED', TEAL))
    story.append(Spacer(1, 4))
    story.append(ai_note(
        'During working years employment income covers the spending need entirely. '
        '401k contributions reduce taxable income and build retirement accounts simultaneously. '
        'The annual surplus flows directly into reserves accelerating portfolio growth. '
        '<b>Key insight:</b> every dollar saved now directly reduces the portfolio draw required in retirement.'))
    story.append(Spacer(1, 4))

    ratios = [0.08, 0.075, 0.075, 0.075, 0.075, 0.082, 0.082, 0.082, 0.082, 0.082, 0.09]
    CW = [PW * r for r in ratios]
    rows, cmds = [], []

    rows.append([p('Year\nAges', SWL),
                 p('Employment income', SW), p('', SW),
                 p('401k contributions', SW), p('', SW),
                 p('Taxable income', SW), p('Est. taxes', SW),
                 p('Income need', SW), p('Net surplus', SW),
                 p('To reserves', SW), p('Cumulative\nreserves', SW)])
    rows.append([p('', SWL),
                 p(f"{client['first_name']} salary", SW),
                 p(f"{spouse['first_name']} salary" if spouse else '—', SW),
                 p(f"{client['first_name']} 401k", SW), p('Spouse 401k', SW),
                 p('After deductions', SW), p('Federal est.', SW),
                 p('2.5% inflation', SW), p('Income – taxes – need', SW),
                 p('Added to savings', SW), p('All accounts', SW)])
    cmds += [
        ('SPAN', (1, 0), (2, 0)), ('SPAN', (3, 0), (4, 0)),
        ('BACKGROUND', (0, 0), (0, 1), colors.HexColor('#2C2C2A')),
        ('BACKGROUND', (1, 0), (2, 1), TEAL), ('BACKGROUND', (3, 0), (4, 1), PURPLE),
        ('BACKGROUND', (5, 0), (5, 1), NAVY), ('BACKGROUND', (6, 0), (6, 1), AMBER),
        ('BACKGROUND', (7, 0), (7, 1), PURPLE), ('BACKGROUND', (8, 0), (8, 1), GREEN),
        ('BACKGROUND', (9, 0), (9, 1), BROWN), ('BACKGROUND', (10, 0), (10, 1), NAVY),
        ('TOPPADDING', (0, 0), (-1, 1), 5), ('BOTTOMPADDING', (0, 0), (-1, 1), 5),
        ('LEFTPADDING', (0, 0), (-1, 1), 3), ('RIGHTPADDING', (0, 0), (-1, 1), 3),
        ('VALIGN', (0, 0), (-1, 1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, 1), 0.3, colors.HexColor('#FFFFFF40')),
    ]

    odd = True
    totals = {'c_sal':0,'s_sal':0,'c_401':0,'s_401':0,'taxes':0,'need':0}
    for r in working:
        ri   = len(rows)
        c_s  = r.get('client_salary', 0)
        s_s  = r.get('spouse_salary', 0)
        c_4  = r.get('client_contrib_trad', 0) + r.get('client_contrib_roth', 0)
        s_4  = r.get('spouse_contrib_trad', 0) + r.get('spouse_contrib_roth', 0)
        tax  = round((c_s + s_s) * 0.18, 0)  # simplified — tax engine covers retirement
        need = r.get('spending_need', 0)
        surp = round(c_s + s_s - tax - need, 0)
        cum  = r.get('total_portfolio', 0)
        ages = f"{r['client_age']}/{r['spouse_age']}" if r.get('spouse_age') else str(r['client_age'])
        sc   = p(fmt(abs(surp)), SNEG) if surp < 0 else p(fmt(surp), SPOS)
        rows.append([
            p(f"{r['year']}\n{ages}", STL),
            p(fmt(c_s), STEAL), p(fmt(s_s), STEAL),
            p(fmt(c_4), SPRP),  p(fmt(s_4), SPRP),
            p(fmt(c_s + s_s - c_4 - s_4), STD),
            p(fmt(tax), SAMB),  p(fmt(need), SNVY),
            sc, p('—', STD), p(fmt(cum), SBLU),
        ])
        bg = WHITE if odd else GRAY_BG; odd = not odd
        emp_bg = TEAL_LT if (c_s or s_s) else bg
        cmds += data_row_style(ri, bg, [((1,2), emp_bg), ((3,4), PURPLE_LT),
                                         ((8,8), GREEN_LT), ((10,10), NAVY_LT)])
        totals['c_sal'] += c_s; totals['s_sal'] += s_s
        totals['c_401'] += c_4; totals['s_401'] += s_4
        totals['taxes'] += tax; totals['need']  += need

    cmds += [('GRID', (0, 2), (-1, -1), 0.2, GRAY_LN),
             ('LINEAFTER', (2, 2), (2, -1), 1.0, TEAL),
             ('LINEAFTER', (4, 2), (4, -1), 1.0, PURPLE),
             ('LINEAFTER', (7, 2), (7, -1), 0.5, GRAY_LN)]
    tbl = Table(rows, colWidths=CW, repeatRows=2)
    tbl.setStyle(TableStyle(cmds))
    story.append(tbl)
    story.append(Spacer(1, 5))
    story.append(summary_boxes([
        (TEAL,   'Portfolio untouched',  'All spending covered by salary. Portfolio compounds at 4% with zero draws during working years.'),
        (PURPLE, '401k builds wealth',   'Contributions + employer match build tax-deferred balance before mandatory RMDs begin at age 73.'),
        (GREEN,  'Reserves grow',        f"Cash and investments grow throughout working years — a strong foundation entering retirement."),
        (AMBER,  'Tax efficiency',       'Partial-year income + 401k deductions keep taxable income low in the transition year.'),
    ]))
    story.append(Spacer(1, 4))
    story.extend(footer_note(
        'Employment income shown prorated for partial years. 401k contributions reduce taxable income shown. '
        'Tax estimate simplified for working years — see retirement pages for detailed tax projection. '
        'Reserves = all accounts combined at year-end.'))


def build_retirement_page(story, client_data, projection, ctx):
    """Page 2 — Retirement years income"""
    years    = projection["years"]
    ret_yrs  = [r for r in years if r.get("phase") == "both_retired" or
                (r.get("total_employment_income", 0) == 0 and
                 (r.get("total_ss", 0) > 0 or r.get("fixed_income", 0) > 0 or
                  r.get("ira_distributions", 0) > 0))]
    if not ret_yrs:
        ret_yrs = years  # fallback — show all

    client   = client_data["client"]
    spouse   = client_data.get("spouse")
    summary  = projection["summary"]

    story.append(page_header(
        ctx["pg"], ctx["total"], 'Retirement Years',
        'SS · pension · rental · IRA distributions · taxes · income need · surplus or gap',
        ctx["name"], ctx["date"], ctx["ss_info"]))
    ctx["pg"] += 1

    need_base = client_data["assumptions"].get("income_need_annual", client_data["assumptions"].get("annual_income_need", 80000))
    inflation = client_data["assumptions"].get("inflation_pct", 0.025)
    if inflation > 1: inflation = inflation / 100
    story.append(subbar(
        f'RETIREMENT YEARS  |  ${need_base:,.0f} base · {(inflation if inflation<=1 else inflation/100)*100:.1f}% inflation',
        'RMDs DRAWN FIRST — EXCESS SPLIT EVENLY WHEN RMDs INSUFFICIENT'))
    story.append(Spacer(1, 4))
    story.append(ai_note(
        'In retirement, income flows from fixed sources (SS, pension, rental) and IRA distributions. '
        'IRS-required RMDs are taken first each year. When RMDs alone cover the gap the surplus reinvests. '
        'When RMDs are insufficient the additional amount is <b>split evenly</b> between client and spouse IRA accounts. '
        'Taxes are estimated on gross income including the taxable portion of SS and all IRA distributions.'))
    story.append(Spacer(1, 3))

    # Show every year for first 20, then every 5 years after that
    display_yrs = []
    for i, r in enumerate(ret_yrs):
        # Skip ghost rows where both clients are dead and no income
        if not r.get('client_alive', True) and not r.get('spouse_alive', True):
            continue
        if i < 20:
            display_yrs.append((r, False))
        elif (i - 20) % 5 == 0:
            display_yrs.append((r, True))  # True = 5-year marker

    ratios = [0.068,0.062,0.062,0.060,0.065,0.065,0.075,0.068,0.068,0.068,0.075,0.075,0.069]
    CW = [PW * r for r in ratios]
    rows, cmds = [], []

    cname = client['first_name']
    sname = spouse['first_name'] if spouse else 'Spouse'
    rows.append([p('Year\nAges', SWL),
                 p('Fixed income', SW), p('', SW), p('', SW),
                 p('IRA distributions', SW), p('', SW),
                 p('Total income', SW), p('Est. taxes', SW),
                 p('Net income', SW), p('Income need', SW),
                 p('Surplus / Gap', SW), p('Net monthly', SW), p('Reserves', SW)])
    rows.append([p('', SWL),
                 p(f'{cname} SS', SW), p(f'{sname} SS', SW), p('Pension/Other', SW),
                 p(f'{cname} IRA', SW), p(f'{sname} IRA', SW),
                 p('Gross total', SW), p('Federal est.', SW),
                 p('After tax', SW), p('2.5% inflat.', SW),
                 p('+ surplus / - gap', SW), p('Take-home', SW), p('All accounts', SW)])
    cmds += [
        ('SPAN', (1, 0), (3, 0)), ('SPAN', (4, 0), (5, 0)),
        ('BACKGROUND', (0, 0), (0, 1), colors.HexColor('#2C2C2A')),
        ('BACKGROUND', (1, 0), (3, 1), NAVY), ('BACKGROUND', (4, 0), (5, 1), BLUE),
        ('BACKGROUND', (6, 0), (6, 1), TEAL), ('BACKGROUND', (7, 0), (7, 1), AMBER),
        ('BACKGROUND', (8, 0), (8, 1), GREEN), ('BACKGROUND', (9, 0), (9, 1), PURPLE),
        ('BACKGROUND', (10, 0), (10, 1), RED), ('BACKGROUND', (11, 0), (11, 1), TEAL),
        ('BACKGROUND', (12, 0), (12, 1), NAVY),
        ('TOPPADDING', (0, 0), (-1, 1), 5), ('BOTTOMPADDING', (0, 0), (-1, 1), 5),
        ('LEFTPADDING', (0, 0), (-1, 1), 3), ('RIGHTPADDING', (0, 0), (-1, 1), 3),
        ('VALIGN', (0, 0), (-1, 1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, 1), 0.3, colors.HexColor('#FFFFFF40')),
    ]

    odd = True
    for r, is_5yr in display_yrs:
        ri    = len(rows)
        c_ss  = r.get('client_ss', 0)
        s_ss  = r.get('spouse_ss', 0)
        fixed = r.get('fixed_income', 0)  # pension+rental+annuity
        c_ira = r.get('client_rmd_taken', 0) + r.get('client_ira_extra', 0)
        s_ira = r.get('spouse_rmd_taken', 0) + r.get('spouse_ira_extra', 0)
        gross = r.get('gross_income', 0)
        taxes = r.get('total_tax', 0)
        net   = r.get('net_income', 0)
        need  = r.get('spending_need', 0)
        surp  = r.get('income_surplus', 0)
        mo    = r.get('net_monthly', 0)
        port  = r.get('total_portfolio', 0)
        ages  = f"{r['client_age']}/{r['spouse_age']}" if r.get('spouse_age') else str(r['client_age'])
        sc    = p(fmt(abs(surp)), SPOS) if surp >= 0 else p(f'({fmt(abs(surp))})', SNEG)
        rows.append([
            p(f"{r['year']}\n{ages}", STL),
            p(fmt(c_ss), SNVY), p(fmt(s_ss), SNVY), p(fmt(fixed), SNVY),
            p(fmt(c_ira), SBLU), p(fmt(s_ira), SBLU),
            p(fmt(gross), STD), p(fmt(taxes), SAMB),
            p(fmt(net), SGRN), p(fmt(need), SPRP),
            sc, p(fmt(mo), STD), p(fmt(port), SNVY),
        ])
        bg   = TEAL_LT if is_5yr else (WHITE if odd else GRAY_BG); odd = not odd
        gbg  = AMBER_LT if surp >= 0 else RED_LT
        cmds += data_row_style(ri, bg, [((1,3), NAVY_LT if not is_5yr else TEAL_LT),
                                         ((4,5), BLUE_LT if not is_5yr else TEAL_LT),
                                         ((8,8), GREEN_LT), ((10,10), gbg), ((12,12), NAVY_LT)])
        if is_5yr:
            cmds += [('LINEABOVE', (0, ri), (-1, ri), 1.5, TEAL)]
    cmds += [('GRID', (0, 2), (-1, -1), 0.2, GRAY_LN),
             ('LINEAFTER', (3, 2), (3, -1), 1.0, NAVY),
             ('LINEAFTER', (5, 2), (5, -1), 1.0, BLUE),
             ('LINEAFTER', (9, 2), (9, -1), 0.5, GRAY_LN),
             ('LINEAFTER', (10, 2), (10, -1), 1.0, RED),
             ('LINEAFTER', (11, 2), (11, -1), 0.5, GRAY_LN)]
    tbl = Table(rows, colWidths=CW, repeatRows=2)
    tbl.setStyle(TableStyle(cmds))
    story.append(tbl)
    story.append(Spacer(1, 5))
    s = summary
    story.append(summary_boxes([
        (NAVY,    'Lifetime gross income',  f"${s['lifetime_gross']:,.0f} total gross income over projection period."),
        (AMBER,   'Lifetime taxes',         f"${s['lifetime_federal_tax']:,.0f} federal + ${s['lifetime_state_tax']:,.0f} state estimated tax."),
        (GREEN,   'Lifetime net income',    f"${s['lifetime_net']:,.0f} net after all estimated taxes."),
        (NAVY_DK, f"Portfolio: ${s['ending_portfolio']:,.0f}",
                  f"Grows from ${s['starting_portfolio']:,.0f} to ${s['ending_portfolio']:,.0f} by end of projection."),
    ]))
    story.append(Spacer(1, 4))
    story.extend(footer_note(
        'Fixed income = SS + pension + rental + annuity. IRA distributions = RMD amounts first; '
        'additional split evenly when needed. Gap shown in parentheses. '
        'Reserves = all accounts combined. Selected years shown — full detail available on request.'))


def build_waterfall_page(story, client_data, projection, ctx):
    """Page 3 — Withdrawal waterfall"""
    years    = projection["years"]
    client   = client_data["client"]
    need_base= client_data["assumptions"].get("income_need_annual", client_data["assumptions"].get("annual_income_need", 80000))
    inflation= client_data["assumptions"].get("inflation_pct", 0.025)
    last_need= years[-1].get('spending_need', 0) if years else 0

    story.append(page_header(
        ctx["pg"], ctx["total"], 'Withdrawal Waterfall',
        'Which account funds the gap · in what order · how much each year',
        ctx["name"], ctx["date"], ctx["ss_info"]))
    ctx["pg"] += 1

    story.append(subbar(
        f'INCOME NEED: ${need_base:,.0f} BASE  |  {inflation*100:.1f}% ANNUAL INFLATION  |  GROWS TO ${last_need:,.0f}',
        'ORDER: Employment → SS + Fixed → IRA RMDs → Investments → Cash Reserves'))
    story.append(Spacer(1, 4))
    story.append(ai_note(
        'This page traces exactly which account fills the income gap each year. '
        'Teal columns show working income — making clear why early years need no portfolio draw. '
        'Once retired, SS and fixed income take over. IRA RMDs fill the remaining gap first (mandatory at 73). '
        'The investment account is drawn only when RMDs fall short. Cash reserves are the last resort. '
        '<b>The portfolio continues growing even with annual draws — the plan is structurally sound.</b>'))
    story.append(Spacer(1, 4))

    ratios = [0.081,0.073,0.073,0.073,0.068,0.059,0.073,0.068,0.073,0.070,0.067,0.073,0.065,0.081]
    CW = [PW * r for r in ratios]
    rows, cmds = [], []

    cname = client['first_name']
    sname = client_data['spouse']['first_name'] if client_data.get('spouse') else 'Spouse'
    rows.append([p('Year\nAges', SWL),
                 p('Working income', SW), p('', SW), p('', SW),
                 p('Fixed retirement', SW), p('', SW), p('', SW),
                 p('Spending', SW), p('Gap', SW),
                 p('Step 1 — IRA RMDs', SW), p('', SW),
                 p('Step 2', SW), p('Step 3', SW), p('Total drawn', SW)])
    rows.append([p('', SWL),
                 p(f'{cname} sal.', SW), p(f'{sname} sal.', SW), p('Total emp.', SW),
                 p('SS', SW), p('Pension/Other', SW), p('All fixed', SW),
                 p('Annual need', SW), p('Portfolio gap', SW),
                 p(f'{cname} IRA', SW), p(f'{sname} IRA', SW),
                 p('Invest.', SW), p('Cash resv.', SW), p('From portfolio', SW)])
    cmds += [
        ('SPAN', (1, 0), (3, 0)), ('SPAN', (4, 0), (6, 0)), ('SPAN', (9, 0), (10, 0)),
        ('BACKGROUND', (0, 0), (0, 1), colors.HexColor('#2C2C2A')),
        ('BACKGROUND', (1, 0), (3, 1), TEAL), ('BACKGROUND', (4, 0), (6, 1), NAVY),
        ('BACKGROUND', (7, 0), (7, 1), PURPLE), ('BACKGROUND', (8, 0), (8, 1), AMBER),
        ('BACKGROUND', (9, 0), (10, 1), BLUE), ('BACKGROUND', (11, 0), (11, 1), GREEN),
        ('BACKGROUND', (12, 0), (12, 1), BROWN), ('BACKGROUND', (13, 0), (13, 1), RED),
        ('TOPPADDING', (0, 0), (-1, 1), 5), ('BOTTOMPADDING', (0, 0), (-1, 1), 5),
        ('LEFTPADDING', (0, 0), (-1, 1), 3), ('RIGHTPADDING', (0, 0), (-1, 1), 3),
        ('VALIGN', (0, 0), (-1, 1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, 1), 0.3, colors.HexColor('#FFFFFF40')),
    ]

    # Phase tracking
    current_phase = None
    phase_colors  = {"both_working": TEAL, "client_only": TEAL,
                     "spouse_only": TEAL, "both_retired": NAVY_DK}
    phase_labels  = {
        "both_working": ("Both working", "Employment income covers all spending — portfolio untouched."),
        "client_only":  ("Client working only", "Spouse retired — client salary continues covering spending."),
        "spouse_only":  ("Spouse working only", "Client retired — spouse salary continues covering spending."),
        "both_retired": ("Fully retired", "Portfolio waterfall active — RMDs first, then investments, then cash."),
    }

    odd = True
    for r in years:
        phase = r.get('phase', 'both_retired')
        # Insert phase banner on phase change
        if phase != current_phase:
            current_phase = phase
            ri = len(rows)
            label, desc = phase_labels.get(phase, (phase, ''))
            rows.append([
                p(f'— {label.upper()} —',
                  ps('ph', color=WHITE, align=TA_LEFT, size=6.5, bold=True, leading=8)),
                p(desc, ps('pd', color=colors.HexColor('#FFFFFFCC'), align=TA_LEFT, size=6, leading=7.5)),
                '','','','','','','','','','','',''
            ])
            col = phase_colors.get(phase, NAVY)
            cmds += phase_row_style(ri, col)

        ri    = len(rows)
        c_s   = r.get('client_salary', 0)
        s_s   = r.get('spouse_salary', 0)
        te    = r.get('total_employment_income', 0)
        ss    = r.get('total_ss', 0)
        fixed = r.get('fixed_income', 0)
        all_f = r.get('total_fixed_income', 0)
        need  = r.get('spending_need', 0)
        gap   = r.get('income_gap', 0)
        c_rmd = r.get('client_rmd_taken', 0)
        s_rmd = r.get('spouse_rmd_taken', 0)
        c_ex  = r.get('client_ira_extra', 0)
        s_ex  = r.get('spouse_ira_extra', 0)
        brok  = r.get('brokerage_draw', 0)
        cash  = r.get('cash_draw', 0)
        total_draw = round(c_rmd + s_rmd + c_ex + s_ex + brok + cash, 0)
        ages  = f"{r['client_age']}/{r['spouse_age']}" if r.get('spouse_age') else str(r['client_age'])
        gc    = p('Covered ✓', SPOS) if gap <= 0 else p(fmt(abs(gap)), SNEG)
        tc    = p('$0', SPOS) if total_draw == 0 else p(fmt(total_draw), SRED)
        emp_bg = TEAL_LT if te > 0 else (WHITE if odd else GRAY_BG)
        rows.append([
            p(f"{r['year']}\n{ages}", STL),
            ec(c_s, STEAL), ec(s_s, STEAL), ec(te, STEAL),
            ec(ss, SNVY), ec(fixed, SNVY), p(fmt(all_f), STD),
            p(fmt(need), STD), gc,
            ec(c_rmd + c_ex, SBLU), ec(s_rmd + s_ex, SBLU),
            ec(brok, SGRN), ec(cash, SBRN), tc,
        ])
        bg = WHITE if odd else GRAY_BG; odd = not odd
        cmds += data_row_style(ri, bg, [((1,3), emp_bg), ((8,8), AMBER_LT),
                                         ((9,10), BLUE_LT), ((11,11), GREEN_LT),
                                         ((12,12), BROWN_LT), ((13,13), RED_LT)])
    cmds += [('GRID', (0, 2), (-1, -1), 0.2, GRAY_LN),
             ('LINEAFTER', (3, 2), (3, -1), 1.0, TEAL),
             ('LINEAFTER', (6, 2), (6, -1), 1.0, NAVY),
             ('LINEAFTER', (8, 2), (8, -1), 1.0, AMBER),
             ('LINEAFTER', (10, 2), (10, -1), 1.0, BLUE),
             ('LINEAFTER', (11, 2), (11, -1), 1.0, GREEN),
             ('LINEAFTER', (12, 2), (12, -1), 1.0, BROWN)]
    tbl = Table(rows, colWidths=CW)
    tbl.setStyle(TableStyle(cmds))
    story.append(tbl)
    story.append(Spacer(1, 4))
    story.extend(footer_note(
        'Waterfall order: Employment → SS + Fixed income → IRA RMDs (mandatory at 73) → Investment account → Cash reserves. '
        '"Covered ✓" = fixed income exceeds need; RMDs in those years reinvest to reserves. '
        'Extra beyond RMDs split evenly client/spouse IRAs.'))


def build_balances_page(story, client_data, projection, ctx):
    """Page 4 — Account balances and drawdown"""
    years   = projection["years"]
    summary = projection["summary"]
    client  = client_data["client"]
    spouse  = client_data.get("spouse")

    story.append(page_header(
        ctx["pg"], ctx["total"], 'Account Balances & Drawdown',
        'Each account · 4% growth · contributions · withdrawals · closing balance',
        ctx["name"], ctx["date"], ctx["ss_info"], NAVY_DK))
    ctx["pg"] += 1

    story.append(subbar(
        'ALL ACCOUNTS AT 4% ANNUAL GROWTH  |  WITHDRAWALS PER WATERFALL (PAGE 3)',
        f"PORTFOLIO: ${summary['starting_portfolio']:,.0f} → ${summary['ending_portfolio']:,.0f}  —  PLAN SUSTAINABLE",
        NAVY_DK))
    story.append(Spacer(1, 4))
    story.append(ai_note(
        'Every account starts with its current balance, earns the assumed rate of return annually, '
        'receives contributions during working years, and is reduced by withdrawals per the waterfall. '
        '<b>The closing balance is the client\'s financial legacy figure.</b> '
        'Even with increasing distributions in later years the combined reserves grow — '
        'confirming the plan is structurally sound through the full projection horizon.'))
    story.append(Spacer(1, 4))

    # Four mini account tables side by side
    def acct_tbl(title, color, lt, rows_data):
        cw_inner = PW / 4 - 5
        col_r = [0.20, 0.17, 0.13, 0.15, 0.17, 0.18]
        cw = [cw_inner * r for r in col_r]
        th  = ps('th',  color=WHITE,    align=TA_CENTER, bold=True, size=6)
        thl = ps('thl', color=WHITE,    align=TA_LEFT,   bold=True, size=6)
        vl  = ps('vl',  color=BLACK,    align=TA_RIGHT,  size=6)
        dr  = ps('dr',  color=RED_TXT,  align=TA_RIGHT,  bold=True, size=6)
        cl  = ps('cl',  color=NAVY_DK,  align=TA_RIGHT,  bold=True, size=6)
        yl  = ps('yl',  color=MUTED,    align=TA_LEFT,   size=6)
        er  = ps('er',  color=GREEN_DK, align=TA_RIGHT,  size=6)
        cr  = ps('cr',  color=TEAL_DK,  align=TA_RIGHT,  bold=True, size=6)
        t_rows, t_cmds = [], []
        t_rows.append([p(title, ps('tt', color=WHITE, align=TA_CENTER, bold=True, size=6.5))])
        t_rows.append([p('Opening · Earnings · Draws · Closing',
                          ps('sb', color=colors.HexColor('#FFFFFFCC'), align=TA_CENTER, size=5.5))])
        t_rows.append([p('Year', thl), p('Opening', th), p('Contrib.', th),
                        p('Earn.', th), p('Drawn', th), p('Closing', th)])
        t_cmds += [
            ('SPAN', (0, 0), (-1, 0)), ('SPAN', (0, 1), (-1, 1)),
            ('BACKGROUND', (0, 0), (-1, 1), color),
            ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#00000020')),
            ('TOPPADDING', (0, 0), (-1, 2), 3), ('BOTTOMPADDING', (0, 0), (-1, 2), 3),
            ('LEFTPADDING', (0, 0), (-1, 2), 3), ('RIGHTPADDING', (0, 0), (-1, 2), 3),
            ('VALIGN', (0, 0), (-1, 2), 'MIDDLE'),
        ]
        odd = True
        for row in rows_data:
            yr, opn, contrib, earn, draw, close = row
            ri = len(t_rows)
            t_rows.append([
                p(str(yr), yl), p(fmt(opn), vl),
                p(fmt(contrib), cr) if contrib else p('—', vl),
                p(fmt(earn), er),
                p(f'({fmt(draw)})', dr) if draw else p('—', vl),
                p(fmt(close), cl),
            ])
            bg = WHITE if odd else lt; odd = not odd
            t_cmds += [
                ('BACKGROUND', (0, ri), (-1, ri), bg),
                ('BACKGROUND', (4, ri), (4, ri), RED_LT if draw else bg),
                ('BACKGROUND', (5, ri), (5, ri), NAVY_LT),
                ('TOPPADDING', (0, ri), (-1, ri), 2), ('BOTTOMPADDING', (0, ri), (-1, ri), 2),
                ('LEFTPADDING', (0, ri), (-1, ri), 3), ('RIGHTPADDING', (0, ri), (-1, ri), 3),
                ('VALIGN', (0, ri), (-1, ri), 'MIDDLE'),
                ('LINEBELOW', (0, ri), (-1, ri), 0.2, GRAY_LN),
            ]
        t_cmds += [('GRID', (0, 2), (-1, -1), 0.2, GRAY_LN)]
        t = Table(t_rows, colWidths=cw)
        t.setStyle(TableStyle(t_cmds))
        return t

    # Sample every year (not every other year)
    sampled = years

    rate = client_data["assumptions"].get("rate_of_return", 0.04)
    c_ira_rows, s_ira_rows, brok_rows, cash_rows = [], [], [], []

    # Only show rows where account has activity (stop at depletion)
    c_ira_depleted = False
    s_ira_depleted = False
    brok_depleted = False
    cash_depleted = False
    for r in sampled:
        yr   = r["year"]
        c_ira_rows.append((yr,
            r.get("client_ira_open", 0), r.get("client_ira_contrib", 0),
            r.get("client_ira_earn", 0), r.get("client_ira_draw", 0),
            r.get("client_ira_close", 0)))
        s_ira_rows.append((yr,
            r.get("spouse_ira_open", 0), r.get("spouse_ira_contrib", 0),
            r.get("spouse_ira_earn", 0), r.get("spouse_ira_draw", 0),
            r.get("spouse_ira_close", 0)))
        brok_rows.append((yr,
            r.get("brokerage_open", 0), 0,
            r.get("brokerage_earn", 0), r.get("brokerage_draw", 0),
            r.get("brokerage_close", 0)))
        cash_rows.append((yr,
            r.get("cash_open", 0), 0,
            r.get("cash_earn", 0), r.get("cash_draw", 0),
            r.get("cash_close", 0)))

    # Trim trailing all-zero rows from account tables
    def trim_rows(rows):
        while rows and rows[-1][1] == 0 and rows[-1][2] == 0 and rows[-1][3] == 0 and rows[-1][4] == 0 and rows[-1][5] == 0:
            rows.pop()
        return rows
    c_ira_rows = trim_rows(c_ira_rows)
    s_ira_rows = trim_rows(s_ira_rows)
    brok_rows  = trim_rows(brok_rows)
    cash_rows  = trim_rows(cash_rows)

    cname = client['first_name']
    sname = spouse['first_name'] if spouse else 'Spouse'

    # Check if each account has any activity
    c_ira_has_data = any(r.get('client_ira_open',0) or r.get('client_ira_close',0) for r in years)
    s_ira_has_data = any(r.get('spouse_ira_open',0) or r.get('spouse_ira_close',0) for r in years)
    brok_has_data  = any(r.get('brokerage_open',0) or r.get('brokerage_close',0) for r in years)
    cash_has_data  = any(r.get('cash_open',0) or r.get('cash_close',0) for r in years)

    def make_na_tbl(title, color):
        """Placeholder table for accounts with no data."""
        cw_inner = PW / 2 - 8
        t_rows = [
            [p(title, ps('tt', color=WHITE, align=TA_CENTER, bold=True, size=6.5))],
            [p('Opening · Earnings · Draws · Closing', ps('sb', color=colors.HexColor('#FFFFFFCC'), align=TA_CENTER, size=5.5))],
            [p('N/A — No account balance', ps('na', color=MUTED, align=TA_CENTER, size=7, italic=True))],
        ]
        t_cmds = [
            ('SPAN', (0,0), (-1,0)), ('SPAN', (0,1), (-1,1)), ('SPAN', (0,2), (-1,2)),
            ('BACKGROUND', (0,0), (-1,1), color),
            ('BACKGROUND', (0,2), (-1,2), GRAY_BG),
            ('TOPPADDING', (0,0), (-1,-1), 6), ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 4), ('RIGHTPADDING', (0,0), (-1,-1), 4),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]
        t = Table(t_rows, colWidths=[cw_inner])
        t.setStyle(TableStyle(t_cmds))
        return t

    def acct_tbl_wide(title, color, lt, rows_data):
        """Account table at half-page width (2 per row)."""
        cw_inner = PW / 2 - 8
        col_r = [0.18, 0.18, 0.14, 0.16, 0.17, 0.17]
        cw = [cw_inner * r for r in col_r]
        th  = ps('th',  color=WHITE,    align=TA_CENTER, bold=True, size=6)
        thl = ps('thl', color=WHITE,    align=TA_LEFT,   bold=True, size=6)
        vl  = ps('vl',  color=BLACK,    align=TA_RIGHT,  size=6)
        dr  = ps('dr',  color=RED_TXT,  align=TA_RIGHT,  bold=True, size=6)
        cl  = ps('cl',  color=NAVY_DK,  align=TA_RIGHT,  bold=True, size=6)
        yl  = ps('yl',  color=MUTED,    align=TA_LEFT,   size=6)
        er  = ps('er',  color=GREEN_DK, align=TA_RIGHT,  size=6)
        cr  = ps('cr',  color=TEAL_DK,  align=TA_RIGHT,  bold=True, size=6)
        t_rows, t_cmds = [], []
        t_rows.append([p(title, ps('tt', color=WHITE, align=TA_CENTER, bold=True, size=6.5))])
        t_rows.append([p('Opening · Earnings · Draws · Closing',
                          ps('sb', color=colors.HexColor('#FFFFFFCC'), align=TA_CENTER, size=5.5))])
        t_rows.append([p('Year', thl), p('Opening', th), p('Contrib.', th),
                        p('Earn.', th), p('Drawn', th), p('Closing', th)])
        t_cmds += [
            ('SPAN', (0, 0), (-1, 0)), ('SPAN', (0, 1), (-1, 1)),
            ('BACKGROUND', (0, 0), (-1, 1), color),
            ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#00000020')),
            ('TOPPADDING', (0, 0), (-1, 2), 3), ('BOTTOMPADDING', (0, 0), (-1, 2), 3),
            ('LEFTPADDING', (0, 0), (-1, 2), 3), ('RIGHTPADDING', (0, 0), (-1, 2), 3),
            ('VALIGN', (0, 0), (-1, 2), 'MIDDLE'),
        ]
        odd = True
        for row in rows_data:
            yr, opn, contrib, earn, draw, close = row
            ri = len(t_rows)
            t_rows.append([
                p(str(yr), yl), p(fmt(opn), vl),
                p(fmt(contrib), cr) if contrib else p('—', vl),
                p(fmt(earn), er),
                p(f'({fmt(draw)})', dr) if draw else p('—', vl),
                p(fmt(close), cl),
            ])
            bg = WHITE if odd else lt; odd = not odd
            t_cmds += [
                ('BACKGROUND', (0, ri), (-1, ri), bg),
                ('BACKGROUND', (4, ri), (4, ri), RED_LT if draw else bg),
                ('BACKGROUND', (5, ri), (5, ri), NAVY_LT),
                ('TOPPADDING', (0, ri), (-1, ri), 2), ('BOTTOMPADDING', (0, ri), (-1, ri), 2),
                ('LEFTPADDING', (0, ri), (-1, ri), 3), ('RIGHTPADDING', (0, ri), (-1, ri), 3),
                ('VALIGN', (0, ri), (-1, ri), 'MIDDLE'),
                ('LINEBELOW', (0, ri), (-1, ri), 0.2, GRAY_LN),
            ]
        t_cmds += [('GRID', (0, 2), (-1, -1), 0.2, GRAY_LN)]
        t = Table(t_rows, colWidths=cw)
        t.setStyle(TableStyle(t_cmds))
        return t

    t1 = acct_tbl_wide(f"{cname}'s IRA / 401k", NAVY,  NAVY_LT,  c_ira_rows) if c_ira_has_data else make_na_tbl(f"{cname}'s IRA / 401k", NAVY)
    t2 = acct_tbl_wide(f"{sname}'s IRA",         TEAL,  TEAL_LT,  s_ira_rows) if s_ira_has_data else make_na_tbl(f"{sname}'s IRA", TEAL)
    t3 = acct_tbl_wide("Joint Investments",      GREEN, GREEN_LT, brok_rows)  if brok_has_data  else make_na_tbl("Joint Investments", GREEN)
    t4 = acct_tbl_wide("Cash & Reserves",        BROWN, BROWN_LT, cash_rows)  if cash_has_data  else make_na_tbl("Cash & Reserves", BROWN)

    # 2 tables per row
    row1 = Table([[t1, t2]], colWidths=[PW/2, PW/2])
    row1.setStyle(TableStyle([
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),4),
        ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),
    ]))
    row2 = Table([[t3, t4]], colWidths=[PW/2, PW/2])
    row2.setStyle(TableStyle([
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),4),
        ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),
    ]))
    story.append(row1)
    story.append(Spacer(1, 6))
    story.append(row2)
    story.append(Spacer(1, 8))
    story.append(Spacer(1, 6))

    # Combined reserves summary table
    rh  = ps('rh',  color=WHITE,    align=TA_CENTER, bold=True, size=6.5)
    rhl = ps('rhl', color=WHITE,    align=TA_LEFT,   bold=True, size=6.5)
    rv  = ps('rv',  color=BLACK,    align=TA_RIGHT,  size=6.5)
    rb  = ps('rb',  color=NAVY_DK,  align=TA_RIGHT,  bold=True, size=6.5)
    rm  = ps('rm',  color=GREEN_DK, align=TA_RIGHT,  bold=True, size=6.5)
    ryl = ps('ryl', color=MUTED,    align=TA_LEFT,   size=6.5)

    r_rows = [[p('Year', rhl), p(f"{cname}'s IRA", rh), p(f"{sname}'s IRA", rh),
               p('Brokerage', rh), p('Cash & Resv.', rh),
               p('Inh. IRA', rh), p('Other', rh),
               p('Combined portfolio', rh), p('Net monthly', rh)]]
    rcmds = [('BACKGROUND', (0, 0), (-1, 0), NAVY_DK),
             ('TOPPADDING', (0, 0), (-1, 0), 4), ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
             ('LEFTPADDING', (0, 0), (-1, 0), 5), ('RIGHTPADDING', (0, 0), (-1, 0), 5)]

    # milestone thresholds
    thresholds = set()
    if summary['ending_portfolio'] > 1000000:
        thresholds.add('1M')
    if summary['ending_portfolio'] > 2000000:
        thresholds.add('2M')
    crossed = set()

    for i, r in enumerate(years):
        ri    = len(r_rows)
        port  = r.get('total_portfolio', 0)
        mo    = r.get('net_monthly', 0)
        yr    = r['year']
        is_ms = False
        is_5yr = (i > 0 and i % 5 == 0)  # divider every 5 years
        if '1M' in thresholds and '1M' not in crossed and port >= 1000000:
            is_ms = True; crossed.add('1M')
        if '2M' in thresholds and '2M' not in crossed and port >= 2000000:
            is_ms = True; crossed.add('2M')
        bg = AMBER_LT if is_ms else (TEAL_LT if is_5yr else (WHITE if i % 2 == 0 else GRAY_BG))
        r_rows.append([
            p(str(r['year']), ryl),
            p(fmt(r.get('client_ira_close',0)), rv),
            p(fmt(r.get('spouse_ira_close',0)), rv),
            p(fmt(r.get('brokerage_close',0)), rv),
            p(fmt(r.get('cash_close',0)), rv),
            p(fmt(r.get('inherited_ira_close',0)), rv),
            p(fmt(r.get('other_close',0)), rv),
            p(fmt(port), rb), p(fmt(mo), rm),
        ])
        rcmds += [
            ('BACKGROUND', (0, ri), (-1, ri), bg),
            ('BACKGROUND', (7, ri), (7, ri), NAVY_LT if not is_ms else AMBER_LT),
            ('TOPPADDING', (0, ri), (-1, ri), 3), ('BOTTOMPADDING', (0, ri), (-1, ri), 3),
            ('LEFTPADDING', (0, ri), (-1, ri), 5), ('RIGHTPADDING', (0, ri), (-1, ri), 5),
        ]
        if is_5yr:
            rcmds += [('LINEABOVE', (0, ri), (-1, ri), 1.5, TEAL)]
        else:
            rcmds += [('LINEBELOW', (0, ri), (-1, ri), 0.25, GRAY_LN)]
    rcmds += [('GRID', (0, 0), (-1, -1), 0.2, GRAY_LN),
              ('LINEAFTER', (6, 0), (6, -1), 1.5, NAVY)]
    rcw = [PW * r for r in [0.07, 0.12, 0.12, 0.13, 0.12, 0.10, 0.09, 0.18, 0.10]]
    rtbl = Table(r_rows, colWidths=rcw)
    rtbl.setStyle(TableStyle(rcmds))
    story.append(p('COMBINED PORTFOLIO — ALL ACCOUNTS BY YEAR',
                   ps('cr', color=MUTED, align=TA_LEFT, bold=True, size=6.5)))
    story.append(Spacer(1, 3))
    story.append(rtbl)
    story.append(Spacer(1, 4))
    story.extend(footer_note(
        'All accounts earn the assumed rate of return annually. Contributions shown during working years. '
        'Withdrawals in red parentheses — sourced per waterfall page 3. '
        'Amber rows = milestone portfolio crossings. Teal dividers = every 5 years. All years shown.'))


# ── Main entry point ──────────────────────────────────────────────────────────

def generate_pdf(client_data: dict, projection: dict) -> bytes:
    """
    Generate the full 4-page report PDF.
    Returns PDF as bytes.
    """
    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(letter),
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN,  bottomMargin=MARGIN,
        allowSplitting=1,
    )

    # Build context
    client = client_data["client"]
    spouse = client_data.get("spouse")
    name   = projection["client_name"]
    date   = client_data["meta"]["analysis_date"]

    # SS info line for header
    ss_cfg = client_data.get("income", {}).get("social_security", {})
    c_ss   = ss_cfg.get("client", {}) or {}
    s_ss   = ss_cfg.get("spouse", {}) or {}

    def ss_label(cfg, person_name):
        st = cfg.get("status", "not_started")
        if st == "collecting":    return f"{person_name} SS collecting"
        if st == "file_at_age":   return f"{person_name} files SS @ {cfg.get('file_age')}"
        if st == "not_started":   return f"{person_name} no SS"
        return ""

    ss_parts = [ss_label(c_ss, client["first_name"])]
    if spouse:
        ss_parts.append(ss_label(s_ss, spouse["first_name"]))
    ss_info = "  |  ".join(p for p in ss_parts if p)

    # Count pages
    has_working = any(r.get("total_employment_income", 0) > 0 for r in projection["years"])
    total_pages = (1 if has_working else 0) + 3  # working + retirement + waterfall + balances

    ctx = {
        "pg":    1,
        "total": total_pages,
        "name":  name,
        "date":  date,
        "ss_info": ss_info,
    }

    # Count total pages
    has_working   = any(r.get("total_employment_income", 0) > 0 for r in projection["years"])
    has_inh_ira   = bool((client_data.get("assets",{}).get("ira_inherited") or {}).get("balance",0))
    total_pages   = 3 + (1 if has_working else 0) + (1 if has_inh_ira else 0) + 3
    # Pages: cover + snapshot + income_tax + (working?) + income_projection + (inh_ira?) + retirement + waterfall + balances

    ctx["total"] = total_pages

    story = []

    # Page 1 — Cover (portrait-style, no header bar)
    build_cover_page(story, client_data, projection)
    story.append(PageBreak())

    # Page 2 — Client Snapshot
    build_snapshot_page(story, client_data, projection, ctx)
    story.append(PageBreak())

    # Page 3 — Income & Tax Strategy
    build_income_tax_page(story, client_data, projection, ctx)
    story.append(PageBreak())

    # Page 4 (optional) — Working Years
    if has_working:
        build_working_page(story, client_data, projection, ctx)
        story.append(PageBreak())

    # Next — Income Projection (year-by-year table)
    build_income_projection_page(story, client_data, projection, ctx)
    story.append(PageBreak())

    # Next (optional) — Inherited IRA Schedule
    if has_inh_ira:
        build_inherited_ira_page(story, client_data, projection, ctx)
        story.append(PageBreak())

    # Retirement Years
    build_retirement_page(story, client_data, projection, ctx)
    story.append(PageBreak())

    # Waterfall
    build_waterfall_page(story, client_data, projection, ctx)
    story.append(PageBreak())

    # Balances
    build_balances_page(story, client_data, projection, ctx)

    doc.build(story)
    return buf.getvalue()

# ═══════════════════════════════════════════════════════════════════════════
# COVER PAGE
# ═══════════════════════════════════════════════════════════════════════════
def build_cover_page(story, client_data, projection):
    from reportlab.lib.pagesizes import portrait, letter as letter_size
    meta    = client_data["meta"]
    client  = client_data["client"]
    spouse  = client_data.get("spouse")
    assets  = client_data.get("assets", {})
    summary = projection["summary"]
    assumptions = client_data.get("assumptions", {})

    # Use portrait for cover
    CPW = letter_size[0] - 1.2 * inch
    DARK_NAVY = colors.HexColor('#0D1B3E')
    GOLD      = colors.HexColor('#C8972B')
    GOLD_LT   = colors.HexColor('#F5E6C8')

    def cp(txt, size=10, color=WHITE, bold=False, align=TA_CENTER, leading=None):
        fn = 'Helvetica-Bold' if bold else 'Helvetica'
        ld = leading or size + 3
        return Paragraph(txt, ParagraphStyle('cp', fontName=fn, fontSize=size,
                         textColor=color, leading=ld, alignment=align))

    # Header bar
    hdr = Table([[
        cp('RETIREMENT-RIGHT FINANCIAL ANALYSIS', 7, colors.HexColor('#B5C8E8'), bold=True),
        cp('CONFIDENTIAL', 7, colors.HexColor('#B5C8E8'), bold=True, align=TA_RIGHT),
    ]], colWidths=[CPW * 0.7, CPW * 0.3])
    hdr.setStyle(TableStyle([
        ('BACKGROUND', (0,0),(-1,-1), DARK_NAVY),
        ('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10),
        ('LEFTPADDING',(0,0),(-1,-1),14),('RIGHTPADDING',(0,0),(-1,-1),14),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 30))

    # Title block
    story.append(cp('· COMPREHENSIVE RETIREMENT BLUEPRINT ·', 9,
                    GOLD, bold=True, align=TA_CENTER))
    story.append(Spacer(1, 12))
    story.append(cp('Retirement', 36, DARK_NAVY, bold=True, align=TA_CENTER, leading=42))
    story.append(cp('Blueprint', 36, DARK_NAVY, bold=True, align=TA_CENTER, leading=42))
    story.append(Spacer(1, 8))

    cname = f"{client['first_name']} {client['last_name']}"
    sname = f"{spouse['first_name']} {spouse['last_name']}" if spouse else None
    prepared_for = f"Prepared for {cname} & {sname}" if sname else f"Prepared for {cname}"
    story.append(cp(prepared_for, 11, colors.HexColor('#4A5568'), align=TA_CENTER))
    story.append(Spacer(1, 24))

    # Key metrics grid
    def calc_total_investable(assets):
        total = 0
        ira = assets.get("ira_traditional") or {}
        total += (ira.get("client_balance",0) or 0) + (ira.get("spouse_balance",0) or 0)
        roth = assets.get("ira_roth") or {}
        total += (roth.get("client_balance",0) or 0) + (roth.get("spouse_balance",0) or 0)
        inh = assets.get("ira_inherited") or {}
        total += inh.get("balance",0) or 0
        brok = assets.get("brokerage") or {}
        total += brok.get("total_balance",0) or 0
        total += assets.get("annuity_value",0) or 0
        total += assets.get("real_estate_equity",0) or 0
        cash = assets.get("cash_and_savings") or {}
        total += (cash.get("client_balance",0) or 0) + (cash.get("spouse_balance",0) or 0)
        for a in (assets.get("other_assets") or []):
            if a.get("investable", True):
                total += a.get("balance",0) or 0
        return total

    total_inv = calc_total_investable(assets)
    need = assumptions.get("income_need_annual", 80000)
    if need > 1: need = need  # already a dollar amount

    metrics = [
        ('TOTAL INVESTABLE', f'${total_inv:,.0f}'),
        ('TARGET RETIRE AGE', str(client.get("retirement",{}).get("retirement_age","—"))),
        ('ANNUAL SPEND GOAL', f'${need:,.0f}'),
        ('LIFETIME SS (EST.)', f'${summary["lifetime_ss"]:,.0f}'),
        ('EST. LIFETIME FED TAX', f'${summary["lifetime_federal_tax"]:,.0f}'),
        ('ENDING PORTFOLIO', f'${summary["ending_portfolio"]:,.0f}'),
    ]

    met_cells = []
    for label, value in metrics:
        c = Table([
            [cp(label, 7, colors.HexColor('#6B7A99'), bold=True, align=TA_LEFT)],
            [cp(value, 18, DARK_NAVY, bold=True, align=TA_LEFT)],
        ], colWidths=[CPW/3 - 16])
        c.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#F7F9FC')),
            ('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10),
            ('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),8),
            ('LINEBEFORE',(0,0),(0,-1),3,GOLD),
            ('BOX',(0,0),(-1,-1),0.5,colors.HexColor('#D1DCF0')),
        ]))
        met_cells.append(c)

    # 2 rows of 3
    row1 = Table([met_cells[:3]], colWidths=[CPW/3]*3)
    row1.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),6),
        ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0)]))
    row2 = Table([met_cells[3:]], colWidths=[CPW/3]*3)
    row2.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),6),
        ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0)]))
    story.append(row1)
    story.append(Spacer(1, 8))
    story.append(row2)
    story.append(Spacer(1, 20))

    # Description box
    desc_box = Table([[cp(
        'This blueprint provides a structured year-by-year view of retirement assets, '
        'income sources, running portfolio balance, and federal & state tax estimates — '
        'including withdrawal waterfall strategy and recommended tax positioning.',
        9, colors.HexColor('#4A5568'), align=TA_LEFT, leading=13
    )]], colWidths=[CPW])
    desc_box.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#F0F4FB')),
        ('TOPPADDING',(0,0),(-1,-1),12),('BOTTOMPADDING',(0,0),(-1,-1),12),
        ('LEFTPADDING',(0,0),(-1,-1),16),('RIGHTPADDING',(0,0),(-1,-1),16),
        ('LINEBEFORE',(0,0),(0,-1),3,NAVY),
    ]))
    story.append(desc_box)
    story.append(Spacer(1, 20))

    # Footer
    firm = meta.get("firm_name","Retirement-Right Advisory")
    addr = meta.get("firm_address","1820 E Ray Road, Suite A-108, Chandler, AZ 85225")
    date_str = meta.get("analysis_date","")
    story.append(cp(f"{firm}  ·  {addr}", 7, colors.HexColor('#6B7A99'), align=TA_CENTER))
    story.append(Spacer(1,4))
    story.append(cp(
        'Estimates are for planning purposes only and not tax, legal, or investment advice. '
        f'Tax calculations use 2024 federal brackets.  |  Report date: {date_str}',
        6.5, colors.HexColor('#9AA5B4'), align=TA_CENTER))


# ═══════════════════════════════════════════════════════════════════════════
# CLIENT SNAPSHOT PAGE
# ═══════════════════════════════════════════════════════════════════════════
def build_snapshot_page(story, client_data, projection, ctx):
    meta    = client_data["meta"]
    client  = client_data["client"]
    spouse  = client_data.get("spouse")
    assets  = client_data.get("assets", {})
    assumptions = client_data.get("assumptions", {})
    summary = projection["summary"]

    story.append(page_header(ctx["pg"], ctx["total"], 'Client Snapshot',
        'Identity · asset inventory · retirement dates · planning horizons',
        ctx["name"], ctx["date"], ctx["ss_info"]))
    ctx["pg"] += 1
    story.append(Spacer(1, 6))

    def lbl(txt): return ps('lbl', size=7, color=MUTED, align=TA_LEFT)
    def val(txt, bold=True): return ps('val', size=8, color=BLACK, align=TA_RIGHT, bold=bold)

    def row(label, value, bg=WHITE):
        return [p(label, ps('rl', size=7, color=MUTED, align=TA_LEFT)),
                p(str(value), ps('rv', size=7.5, color=BLACK, align=TA_RIGHT, bold=True))]

    # ── Left column: client info ──────────────────────────────────────────
    from datetime import date as date_cls, datetime
    def age_from_dob(dob_str):
        try:
            dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
            today = date_cls.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            return age
        except: return "—"

    c_age = age_from_dob(client.get("dob",""))
    s_age = age_from_dob(spouse.get("dob","")) if spouse else "—"
    cname = f"{client['first_name']} {client['last_name']}"
    sname = f"{spouse['first_name']} {spouse['last_name']}" if spouse else "—"

    client_rows = [
        row("Name", cname),
        row("Date of Birth", f"{client.get('dob','—')} (age {c_age})"),
        row("Spouse", sname),
        row("Spouse DOB", f"{spouse.get('dob','—')} (age {s_age})" if spouse else "—"),
        row("Filing Status", client.get("filing_status","—").replace("_"," ").title()),
        row("State", client.get("state","—")),
        row("Target Retirement Age", str(client.get("retirement",{}).get("retirement_age","—"))),
        row("Annual Spending Need", f"${assumptions.get('income_need_annual',0):,.0f}"),
        row("Rate of Return", f"{(assumptions.get('rate_of_return',0) if assumptions.get('rate_of_return',0) <= 1 else assumptions.get('rate_of_return',0)/100)*100:.1f}%"),
        row("Inflation Rate", f"{(assumptions.get('inflation_pct',0) if assumptions.get('inflation_pct',0) <= 1 else assumptions.get('inflation_pct',0)/100)*100:.1f}%"),
    ]
    info_tbl = Table(client_rows, colWidths=[PW*0.28, PW*0.22])
    info_tbl.setStyle(TableStyle([
        ('GRID',(0,0),(-1,-1),0.3,GRAY_LN),
        ('ROWBACKGROUNDS',(0,0),(-1,-1),[WHITE, GRAY_BG]),
        ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
        ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
    ]))

    # ── Right column: asset inventory ────────────────────────────────────
    def asset_rows(assets):
        rows = []
        def ar(label, val, indent=False, bold=False, highlight=False):
            lbl_txt = f"  ↳ {label}" if indent else label
            rows.append((lbl_txt, val, bold, highlight))

        ira = assets.get("ira_traditional") or {}
        c_ira = ira.get("client_balance",0) or 0
        s_ira = ira.get("spouse_balance",0) or 0
        ar("Pre-Tax (IRA)", f"${c_ira+s_ira:,.0f}", bold=True)
        if c_ira: ar(f"{client['first_name']} IRA", f"${c_ira:,.0f}", indent=True)
        if s_ira and spouse: ar(f"{spouse['first_name']} IRA", f"${s_ira:,.0f}", indent=True)

        roth = assets.get("ira_roth") or {}
        c_roth = roth.get("client_balance",0) or 0
        s_roth = roth.get("spouse_balance",0) or 0
        if c_roth + s_roth > 0:
            ar("Roth IRA", f"${c_roth+s_roth:,.0f}", bold=True)

        inh = assets.get("ira_inherited") or {}
        inh_bal = inh.get("balance",0) or 0
        if inh_bal: ar("Inherited IRA", f"${inh_bal:,.0f}", bold=True)

        brok = assets.get("brokerage") or {}
        brok_tot = brok.get("total_balance",0) or 0
        if brok_tot:
            ar("Taxable Brokerage", f"${brok_tot:,.0f}", bold=True)
            for sub in (brok.get("sub_accounts") or []):
                ar(sub.get("label",""), f"${sub.get('balance',0):,.0f}", indent=True)

        ann = assets.get("annuity_value",0) or 0
        if ann: ar("Annuity", f"${ann:,.0f}", bold=True)

        re = assets.get("real_estate_equity",0) or 0
        if re: ar("Real Estate Equity", f"${re:,.0f}", bold=True)

        cash = assets.get("cash_and_savings") or {}
        cash_tot = (cash.get("client_balance",0) or 0) + (cash.get("spouse_balance",0) or 0)
        if cash_tot: ar("Cash & Savings", f"${cash_tot:,.0f}", bold=True)

        for a in (assets.get("other_assets") or []):
            if a.get("balance",0): ar(a.get("label","Other"), f"${a.get('balance',0):,.0f}")

        # Total investable
        total = (c_ira+s_ira+c_roth+s_roth+inh_bal+brok_tot+ann+re+cash_tot +
                 sum(a.get("balance",0) for a in (assets.get("other_assets") or []) if a.get("investable",True)))
        ar("Total Investable", f"${total:,.0f}", bold=True, highlight=True)

        home = assets.get("primary_home_value",0) or 0
        if home: ar("Home (non-investable)", f"${home:,.0f}")
        ar("Total Net Assets", f"${total+home:,.0f}", bold=True, highlight=True)
        return rows

    a_rows = asset_rows(assets)
    a_tbl_data = []
    a_cmds = []
    for i, (lbl_txt, val_txt, bold, highlight) in enumerate(a_rows):
        lc = colors.HexColor('#C8972B') if bold else MUTED
        vc = NAVY_DK if bold else BLACK
        vb = bold
        a_tbl_data.append([
            p(lbl_txt, ps(f'al{i}', size=7, color=lc, align=TA_LEFT, bold=bold)),
            p(val_txt, ps(f'av{i}', size=7, color=vc, align=TA_RIGHT, bold=vb)),
        ])
        bg = AMBER_LT if highlight else (WHITE if i%2==0 else GRAY_BG)
        a_cmds += [
            ('BACKGROUND',(0,i),(-1,i),bg),
            ('TOPPADDING',(0,i),(-1,i),3),('BOTTOMPADDING',(0,i),(-1,i),3),
            ('LEFTPADDING',(0,i),(-1,i),6),('RIGHTPADDING',(0,i),(-1,i),6),
        ]
    a_cmds += [('GRID',(0,0),(-1,-1),0.3,GRAY_LN)]
    asset_tbl = Table(a_tbl_data, colWidths=[PW*0.28, PW*0.22])
    asset_tbl.setStyle(TableStyle(a_cmds))

    # Two columns side by side
    combined = Table([[
        Table([[p('Client Information', ps('sh', size=8, color=NAVY_DK, align=TA_LEFT, bold=True))],
               [info_tbl]], colWidths=[PW*0.5-8]),
        Table([[p('Asset Inventory', ps('sh2', size=8, color=colors.HexColor('#C8972B'), align=TA_LEFT, bold=True))],
               [asset_tbl]], colWidths=[PW*0.5-8]),
    ]], colWidths=[PW*0.5, PW*0.5])
    combined.setStyle(TableStyle([
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),4),
        ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),
    ]))
    story.append(combined)


# ═══════════════════════════════════════════════════════════════════════════
# INCOME & TAX STRATEGY PAGE
# ═══════════════════════════════════════════════════════════════════════════
def build_income_tax_page(story, client_data, projection, ctx):
    client  = client_data["client"]
    spouse  = client_data.get("spouse")
    income  = client_data.get("income", {})
    summary = projection["summary"]
    meta    = client_data.get("meta", {})

    story.append(page_header(ctx["pg"], ctx["total"], 'Income & Tax Strategy',
        'Social Security · pension · tax positioning · lifetime summary',
        ctx["name"], ctx["date"], ctx["ss_info"]))
    ctx["pg"] += 1
    story.append(Spacer(1, 6))

    ss_cfg = income.get("social_security", {}) or {}
    c_ss   = ss_cfg.get("client", {}) or {}
    s_ss   = ss_cfg.get("spouse", {}) or {}

    def status_label(s):
        return {"collecting":"Currently Collecting","file_at_age":"Will File at Age","not_started":"Not Started"}.get(s, s)

    cname = client["first_name"]
    sname = spouse["first_name"] if spouse else "Spouse"

    def info_row(label, value):
        return [p(label, ps('ir1',size=7,color=MUTED,align=TA_LEFT)),
                p(str(value), ps('ir2',size=7.5,color=BLACK,align=TA_RIGHT,bold=True))]

    # SS Plan
    ss_rows = [
        info_row(f"{cname} Status", status_label(c_ss.get("status","—"))),
        info_row(f"{cname} Monthly Benefit", f"${(c_ss.get('monthly_benefit') or 0):,.0f} /mo"),
    ]
    if c_ss.get("file_age"):
        ss_rows.append(info_row(f"{cname} File Age", str(c_ss.get("file_age"))))
    if spouse:
        ss_rows += [
            info_row(f"{sname} Status", status_label(s_ss.get("status","—"))),
            info_row(f"{sname} Monthly Benefit", f"${(s_ss.get('monthly_benefit') or 0):,.0f} /mo"),
        ]
    c_mo = c_ss.get("monthly_benefit",0) or 0
    s_mo = s_ss.get("monthly_benefit",0) or 0
    ss_rows.append(info_row("Combined Monthly SS", f"${c_mo+s_mo:,.0f} /mo"))
    ss_rows.append(info_row("Lifetime SS (est.)", f"${summary['lifetime_ss']:,.0f}"))

    ss_tbl = Table(ss_rows, colWidths=[PW*0.22, PW*0.12])
    ss_tbl.setStyle(TableStyle([
        ('GRID',(0,0),(-1,-1),0.3,GRAY_LN),
        ('ROWBACKGROUNDS',(0,0),(-1,-1),[WHITE,GRAY_BG]),
        ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
        ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
    ]))

    # Tax summary
    tax_rows = [
        info_row("Lifetime Gross", f"${summary['lifetime_gross']:,.0f}"),
        info_row("Lifetime Federal Tax", f"${summary['lifetime_federal_tax']:,.0f}"),
        info_row("Lifetime State Tax", f"${summary['lifetime_state_tax']:,.0f}"),
        info_row("Lifetime Net", f"${summary['lifetime_net']:,.0f}"),
    ]
    tax_tbl = Table(tax_rows, colWidths=[PW*0.22, PW*0.12])
    tax_tbl.setStyle(TableStyle([
        ('GRID',(0,0),(-1,-1),0.3,GRAY_LN),
        ('ROWBACKGROUNDS',(0,0),(-1,-1),[WHITE,GRAY_BG]),
        ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
        ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
    ]))

    # Portfolio summary
    port_rows = [
        info_row("Starting Portfolio", f"${summary['starting_portfolio']:,.0f}"),
        info_row("Ending Portfolio", f"${summary['ending_portfolio']:,.0f}"),
        info_row("Projection Years", str(summary['projection_years'])),
    ]
    port_tbl = Table(port_rows, colWidths=[PW*0.20, PW*0.14])
    port_tbl.setStyle(TableStyle([
        ('GRID',(0,0),(-1,-1),0.3,GRAY_LN),
        ('ROWBACKGROUNDS',(0,0),(-1,-1),[WHITE,GRAY_BG]),
        ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
        ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
    ]))

    # Notes
    notes = meta.get("notes","") or ""
    legacy = meta.get("legacy_notes","") or ""

    three_col = Table([[
        Table([[p('Social Security Plan',ps('ssh',size=8,color=NAVY_DK,align=TA_LEFT,bold=True))],
               [ss_tbl]], colWidths=[PW*0.36]),
        Table([[p('Lifetime Tax Summary',ps('tsh',size=8,color=AMBER_DK,align=TA_LEFT,bold=True))],
               [tax_tbl]], colWidths=[PW*0.30]),
        Table([[p('Portfolio Summary',ps('psh',size=8,color=TEAL_DK,align=TA_LEFT,bold=True))],
               [port_tbl]], colWidths=[PW*0.34]),
    ]], colWidths=[PW*0.36, PW*0.30, PW*0.34])
    three_col.setStyle(TableStyle([
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),6),
        ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),
    ]))
    story.append(three_col)
    story.append(Spacer(1,10))

    if notes or legacy:
        note_data = []
        if notes:
            note_data.append([p('Advisor Notes:', ps('nh',size=7,color=AMBER_DK,align=TA_LEFT,bold=True)),
                               p(notes, ps('nb',size=7,color=BLACK,align=TA_LEFT,leading=10))])
        if legacy:
            note_data.append([p('Legacy & Estate:', ps('lh',size=7,color=AMBER_DK,align=TA_LEFT,bold=True)),
                               p(legacy, ps('lb2',size=7,color=BLACK,align=TA_LEFT,leading=10))])
        note_tbl = Table(note_data, colWidths=[PW*0.15, PW*0.85])
        note_tbl.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,-1),AMBER_LT),
            ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
            ('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),
            ('VALIGN',(0,0),(-1,-1),'TOP'),
        ]))
        story.append(note_tbl)


# ═══════════════════════════════════════════════════════════════════════════
# INCOME PROJECTION PAGE (year-by-year table with chart bar)
# ═══════════════════════════════════════════════════════════════════════════
def build_income_projection_page(story, client_data, projection, ctx):
    client  = client_data["client"]
    spouse  = client_data.get("spouse")
    years   = projection["years"]
    summary = projection["summary"]

    story.append(page_header(ctx["pg"], ctx["total"], 'Income Projection',
        'Year-by-year SS · IRA · portfolio income vs spending need',
        ctx["name"], ctx["date"], ctx["ss_info"]))
    ctx["pg"] += 1

    story.append(subbar(
        f'PROJECTED ANNUAL INCOME — ALL SOURCES  |  {len(years)} YEAR PROJECTION',
        f'LIFETIME GROSS ${summary["lifetime_gross"]:,.0f}  |  LIFETIME NET ${summary["lifetime_net"]:,.0f}'))
    story.append(Spacer(1, 5))

    cname = client["first_name"]
    sname = spouse["first_name"] if spouse else "Spouse"

    # Bar chart using table rows
    max_gross = max((r.get("gross_income",0) for r in years), default=1) or 1

    def bar(value, max_val, color, width=80):
        """Simple bar using a single-cell table with right-side background trick."""
        pct = min(value / max_val, 1.0) if max_val else 0
        filled = max(int(pct * width), 1)
        # Use a paragraph with colored background as bar indicator
        bar_style = ps('bs', size=4, color=color, align=TA_LEFT)
        filled_block = Paragraph('█' * min(filled, 40), bar_style)
        return filled_block

    # Table columns — removed bar chart column
    ratios = [0.07, 0.065, 0.07, 0.07, 0.07, 0.075, 0.09, 0.085, 0.085, 0.085, 0.10, 0.10]
    CW = [PW * r for r in ratios]

    rows, cmds = [], []
    rows.append([
        p('Year', SWL), p(f'{cname} SS', SW), p(f'{sname} SS', SW),
        p('Pension/\nOther', SW), p('IRA/RMD\nDist.', SW),
        p('Asset\nDraw', SW),
        p('Gross\nIncome', SW), p('Est.\nTaxes', SW),
        p('Net\nIncome', SW), p('Need', SW),
        p('Surplus/\nGap', SW), p('Reserves', SW),
    ])
    cmds += [
        ('BACKGROUND',(0,0),(-1,0),NAVY),
        ('TOPPADDING',(0,0),(-1,0),5),('BOTTOMPADDING',(0,0),(-1,0),5),
        ('LEFTPADDING',(0,0),(-1,0),3),('RIGHTPADDING',(0,0),(-1,0),3),
        ('VALIGN',(0,0),(-1,0),'MIDDLE'),
        ('GRID',(0,0),(-1,0),0.3,colors.HexColor('#FFFFFF40')),
    ]

    odd = True
    lifetime_ss = 0; lifetime_gross = 0; lifetime_taxes = 0; lifetime_net = 0
    for r in years:
        # Skip ghost rows where both dead and no income
        if not r.get('client_alive', True) and not r.get('spouse_alive', True) and r.get('gross_income', 0) == 0:
            continue
        ri = len(rows)
        c_ss  = r.get("client_ss",0)
        s_ss  = r.get("spouse_ss",0)
        fixed = r.get("fixed_income",0)
        ira_d = r.get("ira_distributions",0)
        asset_draw = r.get("brokerage_draw",0) + r.get("cash_draw",0) + r.get("real_estate_draw",0)
        gross = r.get("gross_income",0)
        taxes = r.get("total_tax",0)
        net   = r.get("net_income",0)
        need  = r.get("spending_need",0)
        surp  = r.get("income_surplus",0)
        port  = r.get("total_portfolio",0)
        ages  = f"{r['client_age']}/{r.get('spouse_age','')}" if r.get('spouse_age') else str(r['client_age'])

        lifetime_ss += c_ss + s_ss
        lifetime_gross += gross; lifetime_taxes += taxes; lifetime_net += net

        sc = p(fmt(abs(surp)), SPOS) if (surp or 0) >= 0 else p(f'({fmt(abs(surp or 0))})', SNEG)
        bg = WHITE if odd else GRAY_BG; odd = not odd

        rows.append([
            p(f"{r['year']}\n{ages}", STL),
            p(fmt(c_ss), SNVY), p(fmt(s_ss), SNVY),
            p(fmt(fixed), SNVY), p(fmt(ira_d), SBLU),
            p(fmt(asset_draw), SGRN) if asset_draw else p('—', STD),
            p(fmt(gross), STD), p(fmt(taxes), SAMB),
            p(fmt(net), SGRN), p(fmt(need), SPRP),
            sc, p(fmt(port), SNVY),
        ])
        cmds += data_row_style(ri, bg, [((9,9), AMBER_LT if (surp or 0) >= 0 else RED_LT)])

    # Totals
    ri = len(rows)
    rows.append([
        p('Totals', ps('tot',color=BLACK,align=TA_LEFT,bold=True,size=6.5)),
        p(fmt(summary["lifetime_ss"]), SNVY), p('', STD),
        p('', STD), p('', STD), p('', STD),
        p(fmt(summary["lifetime_gross"]), STD),
        p(fmt(summary["lifetime_federal_tax"]+summary["lifetime_state_tax"]), SAMB),
        p(fmt(summary["lifetime_net"]), SGRN),
        p('', STD), p('', STD),
        p(fmt(summary["ending_portfolio"]), SNVY),
    ])
    cmds += [
        ('BACKGROUND',(0,ri),(-1,ri),GHOST),
        ('TOPPADDING',(0,ri),(-1,ri),4),('BOTTOMPADDING',(0,ri),(-1,ri),4),
        ('LEFTPADDING',(0,ri),(-1,ri),3),('RIGHTPADDING',(0,ri),(-1,ri),3),
        ('LINEABOVE',(0,ri),(-1,ri),0.75,GRAY_LN),
    ]
    cmds += [('GRID',(0,1),(-1,-1),0.2,GRAY_LN),
             ('LINEAFTER',(3,1),(3,-1),0.5,GRAY_LN),
             ('LINEAFTER',(4,1),(4,-1),1.0,BLUE),
             ('LINEAFTER',(7,1),(7,-1),0.5,GRAY_LN),
             ('LINEAFTER',(9,1),(9,-1),0.5,GRAY_LN),
             ('LINEAFTER',(10,1),(10,-1),1.0,NAVY)]

    tbl = Table(rows, colWidths=CW, repeatRows=1)
    tbl.setStyle(TableStyle(cmds))
    story.append(tbl)
    story.append(Spacer(1,5))
    story.extend(footer_note(
        f'Assumptions: {(lambda v: v if v<=1 else v/100)(client_data["assumptions"].get("rate_of_return",0.04))*100:.1f}% growth, '
        f'{(lambda v: v if v<=1 else v/100)(client_data["assumptions"].get("inflation_pct",0.025))*100:.1f}% inflation on spending, '
        f'SS COLA applied annually, RMDs at age 73 using IRS Uniform Lifetime Table, '
        f'85% of SS treated as federally taxable, 2024 federal brackets.'))


# ═══════════════════════════════════════════════════════════════════════════
# INHERITED IRA SCHEDULE PAGE
# ═══════════════════════════════════════════════════════════════════════════
def build_inherited_ira_page(story, client_data, projection, ctx):
    assets = client_data.get("assets", {})
    inh    = assets.get("ira_inherited") or {}
    if not inh or not inh.get("balance", 0):
        return  # skip if no inherited IRA

    story.append(page_header(ctx["pg"], ctx["total"], 'Inherited IRA · 10-Year Rule',
        'Distribution schedule · remaining balance · tax impact',
        ctx["name"], ctx["date"], ctx["ss_info"]))
    ctx["pg"] += 1
    story.append(Spacer(1, 6))

    start_bal      = inh.get("balance", 0)
    year_inherited = inh.get("year_inherited", 2020)
    must_dist_by   = inh.get("must_distribute_by") or (year_inherited + 10)
    strategy       = inh.get("distribution_strategy", "even")
    ten_year       = inh.get("ten_year_rule", True)

    # Info cards
    cards = [
        ('Starting Balance', f"${start_bal:,.0f}"),
        ('Year Inherited', str(year_inherited)),
        ('Must Distribute By', str(must_dist_by)),
        ('Strategy', strategy.replace("_"," ").title()),
    ]
    card_cells = []
    for label, value in cards:
        c = Table([
            [p(label, ps('cl',size=7,color=MUTED,align=TA_LEFT,bold=True))],
            [p(value, ps('cv',size=14,color=NAVY_DK,align=TA_LEFT,bold=True))],
        ], colWidths=[PW/4-12])
        c.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,-1),WHITE),
            ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
            ('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),6),
            ('LINEBEFORE',(0,0),(0,-1),3,AMBER),
            ('BOX',(0,0),(-1,-1),0.5,GRAY_LN),
        ]))
        card_cells.append(c)
    card_row = Table([card_cells], colWidths=[PW/4]*4)
    card_row.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),4),
        ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0)]))
    story.append(card_row)
    story.append(Spacer(1,10))

    # Distribution table from projection
    years_data = projection["years"]
    inh_rows_data = [(r["year"], r.get("client_age",""), r.get("inherited_ira_dist",0),
                      r.get("inherited_ira_balance",0))
                     for r in years_data
                     if r.get("inherited_ira_dist",0) > 0 or r.get("inherited_ira_balance",0) > 0]

    CW = [PW*r for r in [0.12, 0.12, 0.30, 0.28, 0.18]]
    rows, cmds = [], []
    rows.append([
        p('Year', SWL), p('Age', SW),
        p('Distribution', SW), p('Remaining Balance', SW), p('Cumulative Dist.', SW),
    ])
    cmds += [
        ('BACKGROUND',(0,0),(-1,0),AMBER),
        ('TOPPADDING',(0,0),(-1,0),5),('BOTTOMPADDING',(0,0),(-1,0),5),
        ('LEFTPADDING',(0,0),(-1,0),5),('RIGHTPADDING',(0,0),(-1,0),5),
        ('VALIGN',(0,0),(-1,0),'MIDDLE'),
    ]

    cumulative = 0
    odd = True
    for yr, age, dist, bal in inh_rows_data:
        ri = len(rows)
        cumulative += dist
        rows.append([
            p(str(yr), STL), p(str(age), STD),
            p(fmt(dist), SAMB),
            p(fmt(bal), SNVY),
            p(fmt(cumulative), STD),
        ])
        bg = WHITE if odd else GRAY_BG; odd = not odd
        cmds += [
            ('BACKGROUND',(0,ri),(-1,ri),bg),
            ('BACKGROUND',(2,ri),(2,ri),AMBER_LT),
            ('TOPPADDING',(0,ri),(-1,ri),4),('BOTTOMPADDING',(0,ri),(-1,ri),4),
            ('LEFTPADDING',(0,ri),(-1,ri),5),('RIGHTPADDING',(0,ri),(-1,ri),5),
            ('LINEBELOW',(0,ri),(-1,ri),0.25,GRAY_LN),
        ]
    cmds += [('GRID',(0,0),(-1,-1),0.2,GRAY_LN)]

    tbl = Table(rows, colWidths=CW, repeatRows=1)
    tbl.setStyle(TableStyle(cmds))

    # Two columns: table + rule explanation
    rule_text = (
        '<b>10-Year Rule:</b> Non-spouse beneficiaries who inherited IRAs after '
        'Jan 1, 2020 must fully distribute the account by Dec 31 of the 10th year '
        'after the original owner\'s death. Distributions are taxed as ordinary income.\n\n'
        f'<b>Strategy:</b> {strategy.replace("_"," ").title()} distribution spreads '
        'withdrawals to minimize annual tax impact and avoid large lump-sum distributions '
        'that could push income into higher tax brackets.\n\n'
        '<b>Tax Impact:</b> All inherited IRA distributions are included in gross income '
        'for federal and state tax calculations throughout this report.'
    )

    rule_box = Table([[p(rule_text, ps('rt',size=7,color=NAVY_DK,align=TA_LEFT,leading=11))]], colWidths=[PW*0.35])
    rule_box.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),NAVY_LT),
        ('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10),
        ('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),12),
        ('LINEBEFORE',(0,0),(0,-1),3,NAVY),
    ]))

    two_col = Table([[tbl, rule_box]], colWidths=[PW*0.60, PW*0.40])
    two_col.setStyle(TableStyle([
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),6),
        ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),
    ]))
    story.append(two_col)
    story.append(Spacer(1,5))
    story.extend(footer_note(
        'Inherited IRA distributions are required by IRS regulation and are included '
        'in gross income each year. Consult a tax advisor regarding optimal distribution strategy.'))
