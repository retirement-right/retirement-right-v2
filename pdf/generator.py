"""
PDF Generator — Retirement-Right v35 (Schwab-style redesign)
Schwab/Fidelity private-wealth aesthetic.
Navy · White · Gray · Gold accent.
Large margins. Fixed-width tables. Consistent headers/footers.
"""
import io
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, HRFlowable, PageBreak, KeepInFrame, KeepTogether
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ── Page geometry ──────────────────────────────────────────────
PAGE_W, PAGE_H = letter          # 8.5 × 11 portrait
LM = RM = 0.65 * inch
TM = BM = 0.55 * inch
PW = PAGE_W - LM - RM           # ~7.2 inches printable width

# ── Palette ────────────────────────────────────────────────────
NAVY      = colors.HexColor('#0A2342')
NAVY_MD   = colors.HexColor('#1A3A5C')
NAVY_LT   = colors.HexColor('#E8EEF5')
TEAL      = colors.HexColor('#0B6B5A')
TEAL_LT   = colors.HexColor('#E0F0EC')
GOLD      = colors.HexColor('#B8963E')
GOLD_LT   = colors.HexColor('#FBF5E6')
GOLD_DK   = colors.HexColor('#7A5C1E')
AMBER     = colors.HexColor('#92400E')
AMBER_LT  = colors.HexColor('#FEF3C7')
GREEN     = colors.HexColor('#155E35')
GREEN_LT  = colors.HexColor('#DCFCE7')
RED       = colors.HexColor('#991B1B')
RED_LT    = colors.HexColor('#FEE2E2')
BLUE      = colors.HexColor('#1E3A8A')
BLUE_LT   = colors.HexColor('#DBEAFE')
PURPLE    = colors.HexColor('#4C1D95')
PURPLE_LT = colors.HexColor('#EDE9FE')
GRAY_BG   = colors.HexColor('#F7F8FA')
GRAY_LN   = colors.HexColor('#D1D5DB')
GRAY_MD   = colors.HexColor('#9CA3AF')
WHITE     = colors.white
BLACK     = colors.HexColor('#111827')
CHARCOAL  = colors.HexColor('#374151')

# ── Typography ─────────────────────────────────────────────────
def ps(name, size=8, color=BLACK, align=TA_LEFT, bold=False, leading=None):
    fn = 'Helvetica-Bold' if bold else 'Helvetica'
    ld = leading or (size + 3)
    return ParagraphStyle(name, fontName=fn, fontSize=size,
                          textColor=color, leading=ld, alignment=align)

def p(txt, sty): return Paragraph(str(txt) if txt is not None else '—', sty)

def fmt(v, zero_dash=True):
    if v is None or (zero_dash and v == 0): return '—'
    return f'${abs(v):,.0f}'

def norm_pct(v, default=0.04):
    """Normalize pct stored as 4.0 or 0.04 → always returns decimal 0.04"""
    val = v if v is not None else default
    return val / 100 if val > 1 else val

# Shared paragraph styles
H1  = ps('h1',  size=18, color=NAVY,     bold=True)
H2  = ps('h2',  size=11, color=NAVY,     bold=True)
H3  = ps('h3',  size=9,  color=NAVY_MD,  bold=True)
H4  = ps('h4',  size=8,  color=CHARCOAL, bold=True)
BDY = ps('bdy', size=8,  color=CHARCOAL, leading=13)
SML = ps('sml', size=7,  color=GRAY_MD,  leading=10)
FTR = ps('ftr', size=6,  color=GRAY_MD,  leading=8)
# Table styles
TH  = ps('th',  size=7,  color=WHITE,    align=TA_CENTER, bold=True)
THL = ps('thl', size=7,  color=WHITE,    align=TA_LEFT,   bold=True)
TD  = ps('td',  size=7,  color=CHARCOAL, align=TA_RIGHT)
TDL = ps('tdl', size=7,  color=CHARCOAL, align=TA_LEFT)
TDM = ps('tdm', size=7,  color=CHARCOAL, align=TA_CENTER)
TDB = ps('tdb', size=7,  color=BLACK,    align=TA_RIGHT,  bold=True)
TDG = ps('tdg', size=7,  color=GREEN,    align=TA_RIGHT,  bold=True)
TDR = ps('tdr', size=7,  color=RED,      align=TA_RIGHT,  bold=True)
TDN = ps('tdn', size=7,  color=NAVY,     align=TA_RIGHT,  bold=True)
TDA = ps('tda', size=7,  color=AMBER,    align=TA_RIGHT,  bold=True)
TDP = ps('tdp', size=7,  color=PURPLE,   align=TA_RIGHT,  bold=True)
TDT = ps('tdt', size=7,  color=TEAL,     align=TA_RIGHT,  bold=True)
TMT = ps('tmt', size=6.5,color=GRAY_MD,  align=TA_LEFT)


# ══════════════════════════════════════════════════════════════
# SHARED COMPONENTS
# ══════════════════════════════════════════════════════════════

def page_header(pg_num, total, right_title, right_sub, client_name, date, ss_info):
    """Consistent page header across all pages."""
    lt = ps('lht', size=6,  color=colors.HexColor('#AABDD4'), bold=True)
    lm = ps('lhm', size=10, color=WHITE, bold=True, leading=13)
    ls = ps('lhs', size=6.5,color=colors.HexColor('#AABDD4'))
    rt = ps('rht', size=6,  color=colors.HexColor('#AABDD4'), align=TA_RIGHT, bold=True)
    rm = ps('rhm', size=9,  color=WHITE, bold=True, align=TA_RIGHT, leading=12)
    rs = ps('rhs', size=6,  color=colors.HexColor('#AABDD4'), align=TA_RIGHT)

    LW = PW * 0.55
    RW = PW * 0.45

    left = KeepInFrame(LW, 55, [
        p('RETIREMENT-RIGHT  ·  CONFIDENTIAL', lt),
        Spacer(1, 2),
        p(f'Retirement Income & Legacy Blueprint — {client_name}', lm),
        Spacer(1, 2),
        p(f'Prepared {date}  ·  {ss_info}', ls),
    ], mode='shrink')

    right = KeepInFrame(RW, 55, [
        p(f'PAGE {pg_num} OF {total}', rt),
        Spacer(1, 3),
        p(right_title, rm),
        Spacer(1, 1),
        p(right_sub, rs),
    ], mode='shrink')

    t = Table([[left, right]], colWidths=[LW, RW])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), NAVY),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING',  (0,0), (0,-1), 14),
        ('RIGHTPADDING', (0,0), (0,-1), 10),
        ('LEFTPADDING',  (1,0), (1,-1), 10),
        ('RIGHTPADDING', (1,0), (1,-1), 14),
    ]))
    return t


def section_bar(left_text, right_text='', bg=NAVY_MD):
    """Thin colored bar below page header."""
    sl = ps('sbl', size=6.5, color=GOLD_LT, bold=True)
    sr = ps('sbr', size=6,   color=colors.HexColor('#FFFFFF80'), align=TA_RIGHT)
    t = Table([[p(left_text, sl), p(right_text, sr)]],
              colWidths=[PW * 0.6, PW * 0.4])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), bg),
        ('TOPPADDING',    (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING',   (0,0), (0,-1), 12),
        ('RIGHTPADDING',  (-1,0),(-1,-1), 12),
    ]))
    return t


def advisor_note(body):
    """Gold-accented advisor note box."""
    nh = ps('nh', size=7, color=GOLD_DK, bold=True)
    nb = ps('nb', size=7.5, color=CHARCOAL, leading=11)
    t = Table([[p('Advisor Note', nh), p(body, nb)]],
              colWidths=[PW * 0.13, PW * 0.87])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), GOLD_LT),
        ('TOPPADDING',    (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('LEFTPADDING',   (0,0), (-1,-1), 10),
        ('RIGHTPADDING',  (0,0), (-1,-1), 10),
        ('VALIGN',        (0,0), (-1,-1), 'TOP'),
        ('LINEAFTER',     (0,0), (0,-1), 2, GOLD),
        ('BOX',           (0,0), (-1,-1), 0.3, GOLD),
    ]))
    return t


def page_footer():
    """Consistent footer on every page."""
    return [
        Spacer(1, 4),
        HRFlowable(width=PW, thickness=0.5, color=GRAY_LN),
        Spacer(1, 2),
        p('Retirement-Right  ·  1820 E Ray Road Suite A-108  ·  Chandler, AZ 85225  ·  480-726-8805  ·  Michael J. Eberhardt, Retirement Specialist', FTR),
        Spacer(1, 1),
        p('This report is for educational and planning purposes only. It is not tax, legal, investment, or Social Security advice. Tax estimates are approximate and based on assumptions provided. Clients should consult qualified tax, legal, and financial professionals before making decisions.', FTR),
    ]


def kpi_row(items):
    """
    Row of KPI boxes. items = [(label, value, color_accent), ...]
    """
    cells = []
    n = len(items)
    for label, value, accent in items:
        lbl_s = ps('kl', size=6.5, color=GRAY_MD, align=TA_CENTER, bold=True)
        val_s = ps('kv', size=14,  color=NAVY,    align=TA_CENTER, bold=True)
        c = Table([[p(label, lbl_s)], [p(value, val_s)]], colWidths=[PW/n - 6])
        c.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,-1), WHITE),
            ('TOPPADDING',    (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('LEFTPADDING',   (0,0), (-1,-1), 6),
            ('RIGHTPADDING',  (0,0), (-1,-1), 6),
            ('LINEBELOW',     (0,-1),(-1,-1), 3, accent),
            ('BOX',           (0,0), (-1,-1), 0.5, GRAY_LN),
        ]))
        cells.append(c)
    t = Table([cells], colWidths=[PW/n] * n)
    t.setStyle(TableStyle([
        ('VALIGN',        (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING',   (0,0), (-1,-1), 0),
        ('RIGHTPADDING',  (0,0), (-1,-1), 4),
        ('TOPPADDING',    (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    return t


def info_row(label, value, bold_val=False):
    ls = ps('il', size=7.5, color=GRAY_MD, align=TA_LEFT)
    vs = ps('iv', size=7.5, color=BLACK,   align=TA_RIGHT, bold=bold_val)
    return [p(label, ls), p(value, vs)]


def two_col_info_table(rows, w1=None, w2=None):
    w1 = w1 or PW * 0.55
    w2 = w2 or PW * 0.45
    t = Table(rows, colWidths=[w1, w2])
    cmds = [
        ('GRID',          (0,0), (-1,-1), 0.3, GRAY_LN),
        ('TOPPADDING',    (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING',   (0,0), (-1,-1), 8),
        ('RIGHTPADDING',  (0,0), (-1,-1), 8),
    ]
    for i in range(len(rows)):
        bg = WHITE if i % 2 == 0 else GRAY_BG
        cmds.append(('BACKGROUND', (0,i), (-1,i), bg))
    t.setStyle(TableStyle(cmds))
    return t


def phase_divider(text, n_cols):
    style = ps('pd', size=6.5, color=WHITE, bold=True, align=TA_LEFT)
    return [p(f'— {text} —', style)] + [p('', style)] * (n_cols - 1)



def normalize_assets(assets):
    """Flatten nested asset schema into flat dict for display."""
    flat = {}
    ira_t = assets.get('ira_traditional', {})
    if isinstance(ira_t, dict):
        flat['client_ira'] = ira_t.get('client_balance', 0) or 0
        flat['spouse_ira'] = ira_t.get('spouse_balance', 0) or 0
    else:
        flat['client_ira'] = 0
        flat['spouse_ira'] = 0

    ira_r = assets.get('ira_roth', {})
    flat['client_roth'] = (ira_r.get('client_balance',0) or 0) if isinstance(ira_r,dict) else 0
    flat['spouse_roth']  = (ira_r.get('spouse_balance',0) or 0) if isinstance(ira_r,dict) else 0

    inh = assets.get('ira_inherited')
    flat['ira_inherited'] = inh if isinstance(inh, dict) else {}

    brok = assets.get('brokerage', {})
    if isinstance(brok, dict):
        flat['brokerage'] = brok.get('total_balance', 0) or 0
        subs = brok.get('sub_accounts') or []
        for sub in subs:
            lbl = sub.get('label','').lower()
            if 'money' in lbl or 'market' in lbl:
                flat['money_market'] = sub.get('balance',0) or 0
    elif isinstance(brok, (int,float)):
        flat['brokerage'] = brok
    else:
        flat['brokerage'] = 0
    flat.setdefault('money_market', 0)

    cash = assets.get('cash_and_savings', {})
    if isinstance(cash, dict):
        flat['cash'] = (cash.get('client_balance',0) or 0) + (cash.get('spouse_balance',0) or 0)
    else:
        flat['cash'] = cash or 0

    flat['annuity_balance']   = assets.get('annuity_value', 0) or 0
    flat['real_estate_equity']= assets.get('real_estate_equity', 0) or 0
    flat['home_value']        = assets.get('primary_home_value', 0) or 0

    others = assets.get('other_assets', [])
    if isinstance(others, list):
        flat['other_client'] = sum(o.get('balance',0) or 0 for o in others)
    else:
        flat['other_client'] = assets.get('other_client', 0) or 0
    flat['other_spouse'] = assets.get('other_spouse', 0) or 0

    return flat

# ══════════════════════════════════════════════════════════════
# PAGE 1 — COVER PAGE
# ══════════════════════════════════════════════════════════════
def build_cover_page(story, client_data, projection):
    client  = client_data['client']
    spouse  = client_data.get('spouse')
    summary = projection['summary']
    assets  = normalize_assets(client_data.get('assets', {}))
    assump  = client_data.get('assumptions', {})

    cname = f"{client.get('first_name','')} {client.get('last_name','')}"
    sname = f"{spouse.get('first_name','')} {spouse.get('last_name','')}" if spouse else ''
    prepared_for = f'{cname} & {sname}' if sname else cname

    total_inv = 0
    for k in ['client_ira','spouse_ira','brokerage','money_market','cash',
              'annuity_balance','real_estate_equity','other_client','other_spouse']:
        v = assets.get(k, 0)
        total_inv += v if isinstance(v, (int, float)) else 0
    if 'ira_inherited' in assets and isinstance(assets['ira_inherited'], dict):
        total_inv += assets['ira_inherited'].get('balance', 0)

    spend = assump.get('income_need_annual', assump.get('annual_income_need', 0))
    ror   = norm_pct(assump.get('rate_of_return', 0.04))

    # Cover banner
    banner = Table([[p('RETIREMENT-RIGHT', ps('cb', size=9, color=GOLD, bold=True, align=TA_CENTER))]],
                   colWidths=[PW])
    banner.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), NAVY),
        ('TOPPADDING',    (0,0), (-1,-1), 22),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING',   (0,0), (-1,-1), 0),
    ]))
    story.append(banner)

    title_blk = Table([[p('Retirement Income\n& Legacy Blueprint',
                           ps('ct', size=26, color=WHITE, bold=True, align=TA_CENTER, leading=32))]],
                      colWidths=[PW])
    title_blk.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), NAVY),
        ('TOPPADDING',    (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(title_blk)

    conf_blk = Table([[p('CONFIDENTIAL  ·  PREPARED EXCLUSIVELY FOR',
                          ps('cc', size=7, color=colors.HexColor('#AABDD4'), align=TA_CENTER, bold=True))]],
                     colWidths=[PW])
    conf_blk.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), NAVY),
        ('TOPPADDING',    (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(conf_blk)

    client_blk = Table([[p(prepared_for,
                            ps('cpf', size=20, color=WHITE, bold=True, align=TA_CENTER, leading=25))]],
                       colWidths=[PW])
    client_blk.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), NAVY),
        ('TOPPADDING',    (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 18),
    ]))
    story.append(client_blk)

    story.append(Spacer(1, 16))

    # KPI boxes
    kpis = [
        ('Total Investable Assets', f'${total_inv:,.0f}',   NAVY),
        ('Annual Income Goal',      f'${spend:,.0f}',       TEAL),
        ('Lifetime SS (Est.)',      f'${summary.get("lifetime_ss",0):,.0f}', GOLD),
        ('Estimated Lifetime Tax',  f'${summary.get("lifetime_federal_tax",0):,.0f}', AMBER),
        ('Ending Portfolio',        f'${summary.get("ending_portfolio",0):,.0f}', GREEN),
        ('Projection Years',        str(summary.get("projection_years", 0)), BLUE),
    ]
    story.append(kpi_row(kpis))
    story.append(Spacer(1, 18))

    # Prepared by
    by_s  = ps('by',  size=8,  color=GRAY_MD, align=TA_CENTER)
    by2_s = ps('by2', size=10, color=NAVY,    align=TA_CENTER, bold=True)
    by3_s = ps('by3', size=7.5,color=CHARCOAL,align=TA_CENTER)

    story.append(p('Prepared by', by_s))
    story.append(Spacer(1, 3))
    story.append(p('Michael J. Eberhardt', by2_s))
    story.append(p('Retirement Specialist  ·  Retirement-Right', by3_s))
    story.append(p('1820 E Ray Road Suite A-108  ·  Chandler, AZ 85225', by3_s))
    story.append(Spacer(1, 16))

    HRFlowable(width=PW * 0.5, thickness=1, color=GOLD, spaceAfter=0)
    story.append(HRFlowable(width=PW * 0.4, thickness=1, color=GRAY_LN))
    story.append(Spacer(1, 8))
    story.append(p(
        f'Analysis prepared {projection.get("report_date","2026")}  ·  Rate of return assumed: {ror*100:.1f}%  ·  Planning horizon: {summary.get("projection_years",0)} years',
        ps('disc', size=6.5, color=GRAY_MD, align=TA_CENTER)))
    story.append(Spacer(1, 4))
    story.append(p(
        'This report is for educational and planning purposes only. It is not tax, legal, investment, or Social Security advice.',
        ps('disc2', size=6, color=GRAY_MD, align=TA_CENTER)))
    story.append(PageBreak())


# ══════════════════════════════════════════════════════════════
# PAGE 2 — EXECUTIVE SUMMARY
# ══════════════════════════════════════════════════════════════
def build_executive_summary(story, client_data, projection, ctx):
    client  = client_data['client']
    spouse  = client_data.get('spouse')
    summary = projection['summary']
    assump  = client_data.get('assumptions', {})
    assets  = normalize_assets(client_data.get('assets', {}))

    spend   = assump.get('income_need_annual', assump.get('annual_income_need', 0))
    ror     = norm_pct(assump.get('rate_of_return', 0.04))
    inf     = norm_pct(assump.get('inflation_pct', 0.025))

    total_inv = sum(assets.get(k, 0) or 0 for k in [
        'client_ira','spouse_ira','brokerage','money_market','cash',
        'annuity_balance','real_estate_equity','other_client','other_spouse'])
    inh_a = assets.get('ira_inherited') or {}
    total_inv += inh_a.get('balance', 0) or 0

    end_port = summary.get('ending_portfolio', 0)
    lt_ss    = summary.get('lifetime_ss', 0)
    lt_tax   = summary.get('lifetime_federal_tax', 0) + summary.get('lifetime_state_tax', 0)
    lt_net   = summary.get('lifetime_net', 0)
    proj_yrs = summary.get('projection_years', 0)

    story.append(page_header(ctx['pg'], ctx['total'],
        'Executive Summary', 'Key findings · planning opportunities · retirement numbers',
        ctx['name'], ctx['date'], ctx['ss_info']))
    ctx['pg'] += 1
    story.append(section_bar('RETIREMENT INCOME & LEGACY ANALYSIS — AT A GLANCE', f'{proj_yrs}-YEAR PROJECTION'))
    story.append(Spacer(1, 10))

    # Three callout sections
    sec_h = ps('esh', size=9, color=WHITE, bold=True)
    sec_b = ps('esb', size=8, color=CHARCOAL, leading=13)
    blt   = ps('ebl', size=8, color=CHARCOAL, leading=13)

    def exec_section(title, bg, items):
        hdr = Table([[p(title, sec_h)]], colWidths=[PW])
        hdr.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,-1), bg),
            ('TOPPADDING',    (0,0), (-1,-1), 7),
            ('BOTTOMPADDING', (0,0), (-1,-1), 7),
            ('LEFTPADDING',   (0,0), (-1,-1), 14),
        ]))
        bdy_items = [hdr]
        for item in items:
            bdy_items.append(p(f'  ✓  {item}', blt))
        bdy_tbl = Table([[i] for i in bdy_items[1:]], colWidths=[PW])
        bdy_tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,-1), WHITE),
            ('TOPPADDING',    (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING',   (0,0), (-1,-1), 14),
            ('RIGHTPADDING',  (0,0), (-1,-1), 14),
            ('BOX',           (0,0), (-1,-1), 0.4, GRAY_LN),
        ]))
        return [hdr, bdy_tbl, Spacer(1, 8)]

    # What you're doing well — contextual
    doing_well = [
        f'Your portfolio of ${total_inv:,.0f} provides a strong foundation entering retirement.',
        f'Estimated lifetime Social Security of ${lt_ss:,.0f} reduces portfolio dependency significantly.',
        'Your waterfall strategy preserves investment accounts by drawing fixed income first.',
    ]
    if end_port > total_inv:
        doing_well.append(f'Your ending portfolio of ${end_port:,.0f} exceeds your starting assets — the plan is structurally sustainable.')

    for item in exec_section('What You Are Doing Well', GREEN, doing_well):
        story.append(item)

    # Opportunities
    opps = [
        'Review tax bracket positioning each year — strategic Roth conversions may reduce lifetime tax burden.',
        f'With {inf*100:.1f}% inflation, your income need grows to an estimated ${spend*(1+inf)**proj_yrs:,.0f} by end of projection.',
        'Inherited IRA 10-year rule requires careful annual distribution planning to avoid bracket spikes.',
        'Annual portfolio rebalancing ensures the assumed rate of return remains achievable.',
    ]
    for item in exec_section('Planning Opportunities', NAVY, opps):
        story.append(item)

    # Key numbers
    story.append(Spacer(1, 6))
    ks = ps('ksh', size=9, color=NAVY, bold=True)
    story.append(p('Key Retirement Numbers', ks))
    story.append(Spacer(1, 5))

    num_rows = [
        ['Total Investable Assets',   f'${total_inv:,.0f}'],
        ['Annual Income Goal',         f'${spend:,.0f}'],
        ['Lifetime Social Security',   f'${lt_ss:,.0f}'],
        ['Lifetime Taxes (Est.)',       f'${lt_tax:,.0f}'],
        ['Lifetime Net Income',         f'${lt_net:,.0f}'],
        ['Starting Portfolio',         f'${summary.get("starting_portfolio",0):,.0f}'],
        ['Ending Portfolio',           f'${end_port:,.0f}'],
        ['Projection Years',           str(proj_yrs)],
        ['Assumed Rate of Return',     f'{ror*100:.1f}%'],
        ['Inflation Rate',             f'{inf*100:.1f}%'],
    ]
    tbl_rows = []
    for i, (lbl, val) in enumerate(num_rows):
        bg = WHITE if i % 2 == 0 else GRAY_BG
        ls = ps(f'nl{i}', size=8, color=CHARCOAL)
        vs = ps(f'nv{i}', size=8, color=NAVY, bold=True, align=TA_RIGHT)
        tbl_rows.append([p(lbl, ls), p(val, vs)])
    nt = Table(tbl_rows, colWidths=[PW * 0.6, PW * 0.4])
    cmds = [('GRID',(0,0),(-1,-1),0.3,GRAY_LN),
            ('TOPPADDING',(0,0),(-1,-1),5), ('BOTTOMPADDING',(0,0),(-1,-1),5),
            ('LEFTPADDING',(0,0),(-1,-1),10), ('RIGHTPADDING',(0,0),(-1,-1),10)]
    for i in range(len(tbl_rows)):
        cmds.append(('BACKGROUND',(0,i),(-1,i), WHITE if i%2==0 else GRAY_BG))
    nt.setStyle(TableStyle(cmds))
    story.append(nt)
    story.extend(page_footer())
    story.append(PageBreak())


# ══════════════════════════════════════════════════════════════
# PAGE 3 — ADVISOR OBSERVATIONS
# ══════════════════════════════════════════════════════════════
def build_advisor_observations(story, client_data, projection, ctx):
    client  = client_data['client']
    summary = projection['summary']
    assump  = client_data.get('assumptions', {})
    assets  = normalize_assets(client_data.get('assets', {}))
    ss      = client_data.get('social_security', {})
    income  = client_data.get('income_streams', {})

    spend   = assump.get('income_need_annual', assump.get('annual_income_need', 0))
    ror     = norm_pct(assump.get('rate_of_return', 0.04))
    inf     = norm_pct(assump.get('inflation_pct', 0.025))
    end_p   = summary.get('ending_portfolio', 0)
    start_p = summary.get('starting_portfolio', 0)
    lt_tax  = summary.get('lifetime_federal_tax', 0)
    proj_y  = summary.get('projection_years', 0)
    inh     = assets.get('ira_inherited') or {}
    notes   = client.get('advisor_notes', '')
    legacy  = client.get('legacy_notes', '')

    story.append(page_header(ctx['pg'], ctx['total'],
        'Advisor Observations', 'Income sustainability · tax planning · legacy considerations',
        ctx['name'], ctx['date'], ctx['ss_info']))
    ctx['pg'] += 1
    story.append(section_bar('PERSONALIZED PLANNING CONSIDERATIONS — PREPARED BY MICHAEL J. EBERHARDT'))
    story.append(Spacer(1, 10))

    obs_h = ps('obh', size=8.5, color=NAVY, bold=True)
    obs_b = ps('obb', size=8,   color=CHARCOAL, leading=13)

    def obs_block(title, body_text):
        items = [
            KeepTogether([
                p(title, obs_h),
                Spacer(1, 3),
                p(body_text, obs_b),
                Spacer(1, 10),
            ])
        ]
        return items

    # Income Sustainability
    sustainability = (
        f'Based on a {ror*100:.1f}% annual return assumption with {inf*100:.1f}% inflation, '
        f'your portfolio is projected to grow from ${start_p:,.0f} to ${end_p:,.0f} over {proj_y} years. '
        f'Your income strategy draws from fixed sources first — Social Security and fixed income — '
        f'before touching investment accounts. This sequencing extends portfolio longevity significantly. '
        f'The plan is designed to cover your ${spend:,.0f} base income need, adjusted annually for inflation.'
    )
    story.extend(obs_block('Income Sustainability', sustainability))

    # Tax Planning
    tax_obs = (
        f'Your estimated lifetime federal tax burden is ${lt_tax:,.0f}. '
        'Tax-efficient withdrawal sequencing — drawing taxable IRA funds during lower-income years — '
        'can meaningfully reduce this figure. Consideration should be given to Roth conversions in '
        'years where income falls below the top of the 22% bracket. '
        'Social Security taxation (85% inclusion assumed) is factored into all projections. '
        'Consult your CPA annually to optimize the timing and source of retirement distributions.'
    )
    story.extend(obs_block('Tax Planning Observations', tax_obs))

    # Inherited IRA
    if inh and inh.get('balance', 0):
        bal  = inh.get('balance', 0)
        yr   = inh.get('year_inherited', 2020)
        dead = yr + 10
        strat = inh.get('distribution_strategy', 'even').replace('_', ' ').title()
        inh_obs = (
            f'You hold an inherited IRA with a current balance of ${bal:,.0f}, inherited in {yr}. '
            f'Under the IRS 10-Year Rule, this account must be fully distributed by December 31, {dead}. '
            f'The current strategy is {strat} distribution, which spreads the tax impact across years '
            f'to avoid bracket spikes. All inherited IRA distributions are included in taxable income. '
            'We recommend revisiting this strategy annually with your tax advisor.'
        )
        story.extend(obs_block('Inherited IRA — 10-Year Rule Planning', inh_obs))

    # Legacy
    legacy_obs = (
        f'Your projected ending portfolio of ${end_p:,.0f} represents your legacy position at the end '
        f'of the {proj_y}-year projection. This figure grows with the portfolio rate of return '
        'even as annual distributions are made, reflecting the structural sustainability of your plan. '
        'If legacy is a priority, we recommend reviewing your estate plan, beneficiary designations, '
        'and any trust structures annually to ensure they reflect your current wishes.'
    )
    if legacy:
        legacy_obs += f' Client note: {legacy}'
    story.extend(obs_block('Legacy & Estate Planning', legacy_obs))

    # Risk Management
    risk_obs = (
        f'The {ror*100:.1f}% return assumption is conservative relative to long-term market averages. '
        'Sequence-of-returns risk is the primary threat to retirement income plans — a significant '
        'market decline in the first 5 years of retirement can permanently impair a portfolio even '
        'if markets recover. Your waterfall strategy mitigates this by maintaining a cash buffer '
        'and drawing from stable fixed income sources before liquidating investments.'
    )
    story.extend(obs_block('Risk Management', risk_obs))

    # Next steps
    next_s = (
        '1. Schedule annual income review to confirm actual vs. projected portfolio performance.\n'
        '2. Review inherited IRA distribution timing with CPA before each tax year end.\n'
        '3. Confirm Social Security claiming strategy has not changed.\n'
        '4. Update estate documents and beneficiary designations.\n'
        '5. Review investment allocation to confirm return assumption remains appropriate.'
    )
    story.extend(obs_block('Recommended Next Steps', next_s))

    if notes:
        story.append(advisor_note(notes))

    story.extend(page_footer())
    story.append(PageBreak())


# ══════════════════════════════════════════════════════════════
# PAGE 4 — RETIREMENT SNAPSHOT (Client Info + Assets)
# ══════════════════════════════════════════════════════════════
def build_snapshot_page(story, client_data, projection, ctx):
    client  = client_data['client']
    spouse  = client_data.get('spouse')
    assump  = client_data.get('assumptions', {})
    assets  = normalize_assets(client_data.get('assets', {}))
    emp     = client_data.get('employment', {})
    summary = projection['summary']

    from datetime import date
    def age_from_dob(dob_str):
        try:
            y, m, d = map(int, dob_str.split('-'))
            today = date.today()
            return today.year - y - ((today.month, today.day) < (m, d))
        except:
            return '—'

    ror = norm_pct(assump.get('rate_of_return', 0.04))
    inf = norm_pct(assump.get('inflation_pct', 0.025))
    spend = assump.get('income_need_annual', assump.get('annual_income_need', 0))
    retire_age = emp.get('client_retire_age') or client.get('target_retirement_age', '—')

    story.append(page_header(ctx['pg'], ctx['total'],
        'Retirement Snapshot', 'Identity · asset inventory · planning horizons',
        ctx['name'], ctx['date'], ctx['ss_info']))
    ctx['pg'] += 1
    story.append(section_bar('CLIENT SNAPSHOT — AS OF ANALYSIS DATE', 'All values in today\'s dollars'))
    story.append(Spacer(1, 10))

    # Client info table
    c_dob = client.get('dob','')
    c_age = age_from_dob(c_dob)
    client_rows = [
        info_row('Name', f"{client.get('first_name','')} {client.get('last_name','')}"),
        info_row('Date of Birth', f"{c_dob} (age {c_age})"),
    ]
    if spouse:
        s_dob = spouse.get('dob','')
        s_age = age_from_dob(s_dob)
        client_rows += [
            info_row('Spouse', f"{spouse.get('first_name','')} {spouse.get('last_name','')}"),
            info_row('Spouse DOB', f"{s_dob} (age {s_age})"),
        ]
    client_rows += [
        info_row('Filing Status', client.get('filing_status','').replace('_',' ').title()),
        info_row('State', client.get('state','—')),
        info_row('Target Retirement Age', str(retire_age)),
        info_row('Annual Spending Need', f'${spend:,.0f}'),
        info_row('Rate of Return', f'{ror*100:.1f}%'),
        info_row('Inflation Rate', f'{inf*100:.1f}%'),
    ]

    ci_t = Table(client_rows, colWidths=[PW*0.25, PW*0.25])
    cmds = [('GRID',(0,0),(-1,-1),0.3,GRAY_LN),
            ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
            ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8)]
    for i in range(len(client_rows)):
        cmds.append(('BACKGROUND',(0,i),(-1,i), WHITE if i%2==0 else GRAY_BG))
    ci_t.setStyle(TableStyle(cmds))

    # Asset inventory
    asset_items = []
    ira_c = assets.get('client_ira', 0)
    ira_s = assets.get('spouse_ira', 0)
    ira_total = ira_c + ira_s
    if ira_total:
        asset_items.append(('Pre-Tax (IRA/401k)', ira_total, NAVY))
        if ira_c: asset_items.append((f'  ■ {client.get("first_name","")} IRA', ira_c, NAVY_LT))
        if ira_s and spouse: asset_items.append((f'  ■ {spouse.get("first_name","")} IRA', ira_s, NAVY_LT))
    inh = assets.get('ira_inherited') or {}
    if inh.get('balance',0): asset_items.append(('Inherited IRA', inh['balance'], AMBER))
    brok = assets.get('brokerage',0)
    mm   = assets.get('money_market',0)
    if brok+mm: asset_items.append(('Taxable Brokerage', brok+mm, TEAL))
    if brok and mm:
        if brok: asset_items.append(('  ■ Managed Brokerage', brok, TEAL_LT))
        if mm:   asset_items.append(('  ■ Money Market', mm, TEAL_LT))
    if assets.get('cash',0): asset_items.append(('Cash & Savings', assets['cash'], GREEN))
    if assets.get('annuity_balance',0): asset_items.append(('Annuity', assets['annuity_balance'], GOLD))
    if assets.get('real_estate_equity',0): asset_items.append(('Real Estate Equity', assets['real_estate_equity'], PURPLE))
    oc = assets.get('other_client',0)
    os_ = assets.get('other_spouse',0)
    if oc+os_: asset_items.append(('Other Assets', oc+os_, GRAY_MD))

    total_inv = sum([assets.get(k,0) or 0 for k in ['client_ira','spouse_ira','brokerage','money_market',
                    'cash','annuity_balance','real_estate_equity','other_client','other_spouse']])
    inh_flat = assets.get('ira_inherited') or {}
    if isinstance(inh_flat, dict): total_inv += inh_flat.get('balance',0) or 0

    ai_rows = []
    for label, val, accent in asset_items:
        is_sub = label.startswith('  ■')
        ls = ps(f'al{label}', size=7 if not is_sub else 6.5,
                color=CHARCOAL if not is_sub else GRAY_MD)
        vs = ps(f'av{label}', size=7 if not is_sub else 6.5,
                color=NAVY if not is_sub else GRAY_MD,
                bold=not is_sub, align=TA_RIGHT)
        ai_rows.append([p(label, ls), p(fmt(val, zero_dash=False), vs)])

    # Total line
    ai_rows.append([p('Total Investable', ps('ait', size=8, color=NAVY, bold=True)),
                    p(f'${total_inv:,.0f}', ps('aiv', size=8, color=NAVY, bold=True, align=TA_RIGHT))])
    home = assets.get('home_value',0)
    if home:
        ai_rows.append([p('Home (non-investable)', ps('ahn',size=7,color=GRAY_MD)),
                        p(f'${home:,.0f}', ps('ahv',size=7,color=GRAY_MD,align=TA_RIGHT))])
        ai_rows.append([p('Total Net Assets', ps('ant',size=8,color=NAVY,bold=True)),
                        p(f'${total_inv+home:,.0f}', ps('anv',size=8,color=NAVY,bold=True,align=TA_RIGHT))])

    ai_t = Table(ai_rows, colWidths=[PW*0.3, PW*0.2])
    ai_cmds = [('GRID',(0,0),(-1,-1),0.3,GRAY_LN),
               ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
               ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8)]
    for i in range(len(ai_rows)):
        ai_cmds.append(('BACKGROUND',(0,i),(-1,i), WHITE if i%2==0 else GRAY_BG))
    # Bold separator before totals
    total_idx = len(ai_rows) - (3 if home else 1)
    ai_cmds.append(('LINEABOVE',(0,total_idx),(-1,total_idx),1,NAVY))
    ai_t.setStyle(TableStyle(ai_cmds))

    # Two-column layout
    lh = ps('lhd', size=8.5, color=NAVY, bold=True)
    left_col  = Table([[p('Client Information', lh)], [Spacer(1,4)], [ci_t]], colWidths=[PW*0.5-6])
    right_col = Table([[p('Asset Inventory', lh)], [Spacer(1,4)], [ai_t]], colWidths=[PW*0.5-6])
    grid = Table([[left_col, right_col]], colWidths=[PW*0.5, PW*0.5])
    grid.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),
                              ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),6),
                              ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0)]))
    story.append(grid)
    story.extend(page_footer())
    story.append(PageBreak())


# ══════════════════════════════════════════════════════════════
# PAGE 5 — INCOME & TAX STRATEGY
# ══════════════════════════════════════════════════════════════
def build_income_tax_page(story, client_data, projection, ctx):
    client  = client_data['client']
    spouse  = client_data.get('spouse')
    ss_data = client_data.get('social_security', {})
    summary = projection['summary']

    cname = client.get('first_name','Client')
    sname = spouse.get('first_name','Spouse') if spouse else 'Spouse'

    story.append(page_header(ctx['pg'], ctx['total'],
        'Income & Tax Strategy', 'Social Security · pension · tax positioning · lifetime summary',
        ctx['name'], ctx['date'], ctx['ss_info']))
    ctx['pg'] += 1
    story.append(section_bar('LIFETIME INCOME & TAX ANALYSIS'))
    story.append(Spacer(1, 10))

    # SS rows
    c_status  = ss_data.get('client_status','—').replace('_',' ').title()
    c_monthly = ss_data.get('client_monthly', 0)
    c_age     = ss_data.get('client_file_age','')
    s_status  = ss_data.get('spouse_status','—').replace('_',' ').title()
    s_monthly = ss_data.get('spouse_monthly', 0)
    s_age     = ss_data.get('spouse_file_age','')

    def row(lbl, val): return info_row(lbl, str(val))

    ss_rows = [
        row(f'{cname} Status', c_status),
        row(f'{cname} Monthly Benefit', f'${c_monthly:,.0f} /mo' if c_monthly else '—'),
    ]
    if c_age: ss_rows.append(row(f'{cname} File Age', str(c_age)))
    if spouse:
        ss_rows += [
            row(f'{sname} Status', s_status),
            row(f'{sname} Monthly Benefit', f'${s_monthly:,.0f} /mo' if s_monthly else '—'),
        ]
        if s_age: ss_rows.append(row(f'{sname} File Age', str(s_age)))
    combined = (c_monthly + s_monthly)
    ss_rows.append(row('Combined Monthly SS', f'${combined:,.0f} /mo'))
    ss_rows.append(row('Lifetime SS (est.)', f'${summary.get("lifetime_ss",0):,.0f}'))

    ss_t = two_col_info_table(ss_rows, PW*0.22, PW*0.14)

    # Tax summary rows
    tax_rows = [
        row('Lifetime Gross', f'${summary.get("lifetime_gross",0):,.0f}'),
        row('Lifetime Federal Tax', f'${summary.get("lifetime_federal_tax",0):,.0f}'),
        row('Lifetime State Tax', f'${summary.get("lifetime_state_tax",0):,.0f}'),
        row('Lifetime Net', f'${summary.get("lifetime_net",0):,.0f}'),
    ]
    tax_t = two_col_info_table(tax_rows, PW*0.18, PW*0.12)

    # Portfolio summary rows
    port_rows = [
        row('Starting Portfolio', f'${summary.get("starting_portfolio",0):,.0f}'),
        row('Ending Portfolio', f'${summary.get("ending_portfolio",0):,.0f}'),
        row('Projection Years', str(summary.get('projection_years',0))),
    ]
    port_t = two_col_info_table(port_rows, PW*0.20, PW*0.14)

    # Section labels
    sh = ps('ssh', size=8, color=NAVY, bold=True)
    three = Table([[
        Table([[p('Social Security Plan', sh)],[Spacer(1,4)],[ss_t]],   colWidths=[PW*0.36]),
        Table([[p('Lifetime Tax Summary', sh)],[Spacer(1,4)],[tax_t]],  colWidths=[PW*0.30]),
        Table([[p('Portfolio Summary', sh)],[Spacer(1,4)],[port_t]],    colWidths=[PW*0.34]),
    ]], colWidths=[PW*0.36, PW*0.30, PW*0.34])
    three.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),
                               ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),8),
                               ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0)]))
    story.append(three)
    story.append(Spacer(1, 10))

    notes  = client.get('advisor_notes','')
    legacy = client.get('legacy_notes','')
    if notes or legacy:
        note_rows = []
        lh2 = ps('alh', size=7, color=GOLD_DK, bold=True)
        lb2 = ps('alb', size=7.5, color=CHARCOAL, leading=11)
        if notes:  note_rows.append([p('Advisor Notes:', lh2), p(notes,  lb2)])
        if legacy: note_rows.append([p('Legacy & Estate:', lh2), p(legacy, lb2)])
        nt = Table(note_rows, colWidths=[PW*0.15, PW*0.85])
        nt.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,-1), GOLD_LT),
            ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
            ('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),
            ('VALIGN',(0,0),(-1,-1),'TOP'),
            ('LINEAFTER',(0,0),(0,-1),2,GOLD),
            ('BOX',(0,0),(-1,-1),0.3,GOLD),
        ]))
        story.append(nt)

    story.extend(page_footer())
    story.append(PageBreak())


# ══════════════════════════════════════════════════════════════
# PAGE 6 — INCOME PROJECTION
# ══════════════════════════════════════════════════════════════
def build_income_projection_page(story, client_data, projection, ctx):
    client  = client_data['client']
    spouse  = client_data.get('spouse')
    years   = projection['years']
    summary = projection['summary']
    assump  = client_data.get('assumptions', {})

    cname = client.get('first_name','Client')
    sname = spouse.get('first_name','Spouse') if spouse else 'Spouse'

    ror = norm_pct(assump.get('rate_of_return', 0.04))
    inf = norm_pct(assump.get('inflation_pct', 0.025))

    story.append(page_header(ctx['pg'], ctx['total'],
        'Income Projection', 'Year-by-year SS · IRA · portfolio income vs spending need',
        ctx['name'], ctx['date'], ctx['ss_info']))
    ctx['pg'] += 1
    story.append(section_bar(
        f'PROJECTED ANNUAL INCOME — ALL SOURCES  |  {len(years)} YEAR PROJECTION',
        f'LIFETIME GROSS ${summary["lifetime_gross"]:,.0f}  |  LIFETIME NET ${summary["lifetime_net"]:,.0f}'))
    story.append(Spacer(1, 5))

    # Column widths
    CW = [PW*r for r in [0.08, 0.07, 0.07, 0.07, 0.07, 0.07, 0.09, 0.085, 0.085, 0.085, 0.095, 0.095]]

    rows, cmds = [], []
    rows.append([
        p('Year', THL), p(f'{cname}\nSS', TH), p(f'{sname}\nSS', TH),
        p('Pension/\nOther', TH), p('IRA/RMD\nDist.', TH), p('Asset\nDraw', TH),
        p('Gross\nIncome', TH), p('Est.\nTaxes', TH), p('Net\nIncome', TH),
        p('Need', TH), p('Surplus/\nGap', TH), p('Reserves', TH),
    ])
    cmds += [
        ('BACKGROUND',(0,0),(-1,0), NAVY),
        ('TOPPADDING',(0,0),(-1,0),5),('BOTTOMPADDING',(0,0),(-1,0),5),
        ('LEFTPADDING',(0,0),(-1,0),4),('RIGHTPADDING',(0,0),(-1,0),4),
        ('VALIGN',(0,0),(-1,0),'MIDDLE'),
        ('GRID',(0,0),(-1,0),0.3,colors.HexColor('#FFFFFF30')),
    ]

    odd = True
    for r in years:
        if not r.get('client_alive',True) and not r.get('spouse_alive',True) and r.get('gross_income',0)==0:
            continue
        ri     = len(rows)
        c_ss   = r.get('client_ss',0)
        s_ss   = r.get('spouse_ss',0)
        fixed  = r.get('fixed_income',0)
        ira_d  = r.get('ira_distributions',0)
        adraw  = r.get('brokerage_draw',0)+r.get('cash_draw',0)+r.get('real_estate_draw',0)
        gross  = r.get('gross_income',0)
        taxes  = r.get('total_tax',0)
        net    = r.get('net_income',0)
        need   = r.get('spending_need',0)
        surp   = r.get('income_surplus',0) or 0
        port   = r.get('total_portfolio',0)
        ages   = f"{r['client_age']}/{r.get('spouse_age','')}" if r.get('spouse_age') else str(r['client_age'])

        sc = p(fmt(surp), TDG) if surp >= 0 else p(f'({fmt(abs(surp))})', TDR)
        bg = WHITE if odd else GRAY_BG; odd = not odd

        rows.append([
            p(f"{r['year']}\n{ages}", TMT),
            p(fmt(c_ss), TDN), p(fmt(s_ss), TDN),
            p(fmt(fixed), TDN), p(fmt(ira_d), ps('ird',size=7,color=BLUE,align=TA_RIGHT,bold=True)),
            p(fmt(adraw), TDT) if adraw else p('—', TD),
            p(fmt(gross), TD), p(fmt(taxes), TDA),
            p(fmt(net), TDG), p(fmt(need), TDP),
            sc, p(fmt(port), TDN),
        ])
        surp_bg = GREEN_LT if surp >= 0 else RED_LT
        cmds += [
            ('BACKGROUND',(0,ri),(-1,ri), bg),
            ('BACKGROUND',(10,ri),(10,ri), surp_bg),
            ('TOPPADDING',(0,ri),(-1,ri),3),('BOTTOMPADDING',(0,ri),(-1,ri),3),
            ('LEFTPADDING',(0,ri),(-1,ri),4),('RIGHTPADDING',(0,ri),(-1,ri),4),
            ('VALIGN',(0,ri),(-1,ri),'MIDDLE'),
            ('LINEBELOW',(0,ri),(-1,ri),0.2,GRAY_LN),
        ]

    # Totals row
    ri = len(rows)
    rows.append([
        p('Totals', ps('tot',size=7,color=BLACK,bold=True,align=TA_LEFT)),
        p(fmt(summary['lifetime_ss']), TDN), p('', TD),
        p('', TD), p('', TD), p('', TD),
        p(fmt(summary['lifetime_gross']), TDB),
        p(fmt(summary['lifetime_federal_tax']+summary['lifetime_state_tax']), TDA),
        p(fmt(summary['lifetime_net']), TDG),
        p('', TD), p('', TD),
        p(fmt(summary['ending_portfolio']), TDN),
    ])
    cmds += [
        ('BACKGROUND',(0,ri),(-1,ri), GRAY_BG),
        ('TOPPADDING',(0,ri),(-1,ri),4),('BOTTOMPADDING',(0,ri),(-1,ri),4),
        ('LEFTPADDING',(0,ri),(-1,ri),4),('RIGHTPADDING',(0,ri),(-1,ri),4),
        ('LINEABOVE',(0,ri),(-1,ri),0.75,GRAY_LN),
    ]
    cmds += [('GRID',(0,1),(-1,-1),0.2,GRAY_LN)]

    tbl = Table(rows, colWidths=CW, repeatRows=1)
    tbl.setStyle(TableStyle(cmds))
    story.append(tbl)
    story.append(Spacer(1,5))
    story.extend(page_footer())
    story.append(p(
        f'Assumptions: {ror*100:.1f}% growth, {inf*100:.1f}% inflation on spending, '
        f'SS COLA applied annually, RMDs at age 73 using IRS Uniform Lifetime Table, '
        f'85% of SS treated as federally taxable, 2024 federal brackets.', FTR))
    story.append(PageBreak())


# ══════════════════════════════════════════════════════════════
# PAGE 7 — INHERITED IRA SCHEDULE
# ══════════════════════════════════════════════════════════════
def build_inherited_ira_page(story, client_data, projection, ctx):
    assets = normalize_assets(client_data.get('assets', {}))
    inh    = assets.get('ira_inherited') or {}
    if not inh or not inh.get('balance', 0):
        return

    start_bal      = inh.get('balance', 0)
    year_inherited = inh.get('year_inherited', 2020)
    must_dist_by   = inh.get('must_distribute_by') or (year_inherited + 10)
    strategy       = inh.get('distribution_strategy', 'even')

    story.append(page_header(ctx['pg'], ctx['total'],
        'Inherited IRA · 10-Year Rule', 'Distribution schedule · remaining balance · tax impact',
        ctx['name'], ctx['date'], ctx['ss_info']))
    ctx['pg'] += 1
    story.append(section_bar('INHERITED IRA MANDATORY DISTRIBUTION SCHEDULE'))
    story.append(Spacer(1, 8))

    # KPI cards
    cards = [
        ('Starting Balance', f'${start_bal:,.0f}', NAVY),
        ('Year Inherited', str(year_inherited), AMBER),
        ('Must Distribute By', str(must_dist_by), RED),
        ('Strategy', strategy.replace('_',' ').title(), TEAL),
    ]
    story.append(kpi_row(cards))
    story.append(Spacer(1, 10))

    # Distribution table
    years_data = projection['years']
    inh_rows_data = [
        (r['year'], r.get('client_age',''), r.get('inherited_ira_dist',0), r.get('inherited_ira_balance',0))
        for r in years_data
        if r.get('inherited_ira_dist',0) > 0 or r.get('inherited_ira_balance',0) > 0
    ]

    CW = [PW*r for r in [0.12, 0.12, 0.28, 0.26, 0.22]]
    rows, cmds = [], []
    rows.append([p('Year', THL), p('Age', TH), p('Distribution', TH),
                 p('Remaining Balance', TH), p('Cumulative Dist.', TH)])
    cmds += [('BACKGROUND',(0,0),(-1,0), AMBER),
             ('TOPPADDING',(0,0),(-1,0),5),('BOTTOMPADDING',(0,0),(-1,0),5),
             ('LEFTPADDING',(0,0),(-1,0),6),('RIGHTPADDING',(0,0),(-1,0),6),
             ('VALIGN',(0,0),(-1,0),'MIDDLE')]

    cumulative = 0
    odd = True
    for yr, age, dist, bal in inh_rows_data:
        ri = len(rows)
        cumulative += dist
        bg = WHITE if odd else GRAY_BG; odd = not odd
        rows.append([
            p(str(yr), TDL), p(str(age), TDM),
            p(fmt(dist), TDA), p(fmt(bal), TDN), p(fmt(cumulative), TD),
        ])
        cmds += [
            ('BACKGROUND',(0,ri),(-1,ri), bg),
            ('BACKGROUND',(2,ri),(2,ri), AMBER_LT),
            ('TOPPADDING',(0,ri),(-1,ri),4),('BOTTOMPADDING',(0,ri),(-1,ri),4),
            ('LEFTPADDING',(0,ri),(-1,ri),6),('RIGHTPADDING',(0,ri),(-1,ri),6),
            ('LINEBELOW',(0,ri),(-1,ri),0.2,GRAY_LN),
        ]
    cmds += [('GRID',(0,0),(-1,-1),0.2,GRAY_LN)]
    tbl = Table(rows, colWidths=CW, repeatRows=1)
    tbl.setStyle(TableStyle(cmds))

    rule_text = (
        '<b>10-Year Rule:</b> Non-spouse beneficiaries who inherited IRAs after Jan 1, 2020 '
        'must fully distribute the account by Dec 31 of the 10th year after the original '
        'owner\'s death. Distributions are taxed as ordinary income.\n\n'
        f'<b>Strategy:</b> {strategy.replace("_"," ").title()} distribution spreads withdrawals '
        'to minimize annual tax impact and avoid large lump-sum distributions that could '
        'push income into higher tax brackets.\n\n'
        '<b>Tax Impact:</b> All inherited IRA distributions are included in gross income '
        'for federal and state tax calculations throughout this report.'
    )
    rule_box = Table([[p(rule_text, ps('rt',size=7.5,color=NAVY_MD,align=TA_LEFT,leading=12))]],
                     colWidths=[PW*0.38])
    rule_box.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1), NAVY_LT),
        ('TOPPADDING',(0,0),(-1,-1),12),('BOTTOMPADDING',(0,0),(-1,-1),12),
        ('LEFTPADDING',(0,0),(-1,-1),14),('RIGHTPADDING',(0,0),(-1,-1),14),
        ('LINEBEFORE',(0,0),(0,-1),3, NAVY),
    ]))

    two = Table([[tbl, rule_box]], colWidths=[PW*0.58, PW*0.42])
    two.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),
                              ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),6),
                              ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0)]))
    story.append(two)
    story.extend(page_footer())
    story.append(PageBreak())


# ══════════════════════════════════════════════════════════════
# PAGE 8 — RETIREMENT YEARS
# ══════════════════════════════════════════════════════════════
def build_retirement_years_page(story, client_data, projection, ctx):
    client  = client_data['client']
    spouse  = client_data.get('spouse')
    years   = projection['years']
    summary = projection['summary']
    assump  = client_data.get('assumptions', {})

    cname   = client.get('first_name','Client')
    sname   = spouse.get('first_name','Spouse') if spouse else 'Spouse'
    need_base = assump.get('income_need_annual', assump.get('annual_income_need', 80000))
    inf       = norm_pct(assump.get('inflation_pct', 0.025))

    ret_yrs = [r for r in years if r.get('phase','') not in ('working','transitioning')
               and not (not r.get('client_alive',True) and not r.get('spouse_alive',True) and r.get('gross_income',0)==0)]

    story.append(page_header(ctx['pg'], ctx['total'],
        'Retirement Years', 'SS · pension · IRA distributions · taxes · income need · surplus or gap',
        ctx['name'], ctx['date'], ctx['ss_info']))
    ctx['pg'] += 1
    story.append(section_bar(
        f'RETIREMENT YEARS  |  ${need_base:,.0f} base · {inf*100:.1f}% inflation',
        'RMDs DRAWN FIRST — EXCESS SPLIT EVENLY WHEN RMDs INSUFFICIENT'))
    story.append(Spacer(1, 5))
    story.append(advisor_note(
        'In retirement, income flows from fixed sources (SS, pension, rental) and IRA distributions. '
        'IRS-required RMDs are taken first each year. When RMDs alone cover the gap the surplus reinvests. '
        'When RMDs are insufficient the additional amount is <b>split evenly</b> between client and spouse IRA accounts. '
        'Taxes are estimated on gross income including the taxable portion of SS and all IRA distributions.'))
    story.append(Spacer(1, 5))

    # Show every year for first 20, every 5 after that
    display_yrs = []
    for i, r in enumerate(ret_yrs):
        if i < 20:
            display_yrs.append((r, False))
        elif (i - 20) % 5 == 0:
            display_yrs.append((r, True))

    CW = [PW*r for r in [0.08, 0.07, 0.07, 0.06, 0.07, 0.07, 0.07, 0.065, 0.065, 0.08, 0.075, 0.07, 0.09]]

    rows, cmds = [], []
    rows.append([
        p('Year\nAges', THL),
        p(f'{cname}\nSS', TH), p(f'{sname}\nSS', TH), p('Pension/\nOther', TH),
        p(f'{cname}\nIRA', TH), p(f'{sname}\nIRA', TH),
        p('Gross\nTotal', TH), p('Federal\nEst.', TH), p('After\nTax', TH),
        p(f'Income Need\n{inf*100:.1f}% inflat.', TH),
        p('+ surplus\n/ -gap', TH), p('Net\nMonthly', TH), p('All\nAccounts', TH),
    ])
    cmds += [('BACKGROUND',(0,0),(-1,0), NAVY),
             ('TOPPADDING',(0,0),(-1,0),5),('BOTTOMPADDING',(0,0),(-1,0),5),
             ('LEFTPADDING',(0,0),(-1,0),3),('RIGHTPADDING',(0,0),(-1,0),3),
             ('VALIGN',(0,0),(-1,0),'MIDDLE'),
             ('GRID',(0,0),(-1,0),0.3,colors.HexColor('#FFFFFF30'))]

    odd = True
    for r, is_5yr in display_yrs:
        ri  = len(rows)
        c_ss = r.get('client_ss', 0)
        s_ss = r.get('spouse_ss', 0)
        fixed = r.get('fixed_income', 0)
        c_ira = r.get('client_rmd_taken',0) + r.get('client_ira_extra',0)
        s_ira = r.get('spouse_rmd_taken',0) + r.get('spouse_ira_extra',0)
        gross = r.get('gross_income', 0)
        taxes = r.get('total_tax', 0)
        net   = r.get('net_income', 0)
        need  = r.get('spending_need', 0)
        surp  = r.get('income_surplus', 0) or 0
        mo    = r.get('net_monthly', 0)
        port  = r.get('total_portfolio', 0)
        ages  = f"{r['client_age']}/{r.get('spouse_age','')}" if r.get('spouse_age') else str(r['client_age'])

        sc    = p(fmt(surp), TDG) if surp >= 0 else p(f'({fmt(abs(surp))})', TDR)
        bg    = TEAL_LT if is_5yr else (WHITE if odd else GRAY_BG); odd = not odd

        rows.append([
            p(f"{r['year']}\n{ages}", TMT),
            p(fmt(c_ss), TDN), p(fmt(s_ss), TDN), p(fmt(fixed), TDN),
            p(fmt(c_ira), ps('ci',size=7,color=BLUE,align=TA_RIGHT,bold=True)),
            p(fmt(s_ira), ps('si',size=7,color=BLUE,align=TA_RIGHT,bold=True)),
            p(fmt(gross), TD), p(fmt(taxes), TDA),
            p(fmt(net), TDG), p(fmt(need), TDP),
            sc, p(fmt(mo), TD), p(fmt(port), TDN),
        ])
        surp_bg = GREEN_LT if surp >= 0 else RED_LT
        cmds += [
            ('BACKGROUND',(0,ri),(-1,ri), bg),
            ('BACKGROUND',(10,ri),(10,ri), surp_bg),
            ('TOPPADDING',(0,ri),(-1,ri),3),('BOTTOMPADDING',(0,ri),(-1,ri),3),
            ('LEFTPADDING',(0,ri),(-1,ri),3),('RIGHTPADDING',(0,ri),(-1,ri),3),
            ('VALIGN',(0,ri),(-1,ri),'MIDDLE'),
            ('LINEBELOW',(0,ri),(-1,ri),0.2,GRAY_LN),
        ]
        if is_5yr:
            cmds += [('LINEABOVE',(0,ri),(-1,ri),1.5,TEAL)]

    cmds += [('GRID',(0,1),(-1,-1),0.2,GRAY_LN)]
    tbl = Table(rows, colWidths=CW, repeatRows=1)
    tbl.setStyle(TableStyle(cmds))
    story.append(tbl)
    story.append(Spacer(1, 8))

    # Summary boxes
    boxes = [
        (NAVY,  'Lifetime Gross Income', f'${summary.get("lifetime_gross",0):,.0f} total gross income over projection period.'),
        (AMBER, 'Lifetime Taxes',        f'${summary.get("lifetime_federal_tax",0):,.0f} federal + ${summary.get("lifetime_state_tax",0):,.0f} state estimated tax.'),
        (GREEN, 'Lifetime Net Income',   f'${summary.get("lifetime_net",0):,.0f} net after all estimated taxes.'),
        (TEAL,  f'Portfolio: ${summary.get("ending_portfolio",0):,.0f}', f'Grows from ${summary.get("starting_portfolio",0):,.0f} to ${summary.get("ending_portfolio",0):,.0f} by end of projection.'),
    ]
    cells = []
    for accent, title, body in boxes:
        ts = ps('bt', size=7.5, color=accent, bold=True)
        bs = ps('bb', size=7,   color=CHARCOAL, leading=10)
        c  = Table([[p(title, ts)],[p(body, bs)]], colWidths=[PW/4-6])
        c.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),WHITE),
                               ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
                               ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),6),
                               ('LINEBEFORE',(0,0),(0,-1),3,accent),
                               ('BOX',(0,0),(-1,-1),0.4,GRAY_LN)]))
        cells.append(c)
    bt = Table([cells], colWidths=[PW/4]*4)
    bt.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),
                             ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),4),
                             ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0)]))
    story.append(bt)
    story.extend(page_footer())
    story.append(PageBreak())


# ══════════════════════════════════════════════════════════════
# PAGE 9 — WITHDRAWAL WATERFALL
# ══════════════════════════════════════════════════════════════
def build_waterfall_page(story, client_data, projection, ctx):
    client  = client_data['client']
    spouse  = client_data.get('spouse')
    years   = projection['years']
    assump  = client_data.get('assumptions', {})

    cname     = client.get('first_name','Client')
    sname     = spouse.get('first_name','Spouse') if spouse else 'Spouse'
    need_base = assump.get('income_need_annual', assump.get('annual_income_need', 80000))
    inf       = norm_pct(assump.get('inflation_pct', 0.025))

    last_need = max((r.get('spending_need',0) for r in years), default=0)

    story.append(page_header(ctx['pg'], ctx['total'],
        'Withdrawal Waterfall', 'Which account funds the gap · in what order · how much each year',
        ctx['name'], ctx['date'], ctx['ss_info']))
    ctx['pg'] += 1
    story.append(section_bar(
        f'INCOME NEED: ${need_base:,.0f} BASE  |  {inf*100:.1f}% ANNUAL INFLATION  |  GROWS TO ${last_need:,.0f}',
        'ORDER: Employment → SS + Fixed → IRA RMDs → Investments → Cash Reserves'))
    story.append(Spacer(1, 5))
    story.append(advisor_note(
        'This page traces exactly which account fills the income gap each year. '
        'Once retired, SS and fixed income take over. IRA RMDs fill the remaining gap first (mandatory at 73). '
        'The investment account is drawn only when RMDs fall short. Cash reserves are the last resort. '
        '<b>The portfolio continues growing even with annual draws — the plan is structurally sound.</b>'))
    story.append(Spacer(1, 5))

    CW = [PW*r for r in [0.07, 0.065, 0.065, 0.065, 0.065, 0.065, 0.07, 0.07, 0.07, 0.065, 0.065, 0.07, 0.065, 0.075]]

    rows, cmds = [], []
    rows.append([
        p('Year\nAges', THL),
        p(f'{cname}\nsal.', TH), p(f'{sname}\nsal.', TH), p('Total\nemp.', TH),
        p('SS', TH), p('Pension/\nOther', TH), p('All\nfixed', TH),
        p('Annual\nneed', TH), p('Portfolio\ngap', TH),
        p(f'{cname}\nIRA', TH), p(f'{sname}\nIRA', TH),
        p('Invest.', TH), p('Cash\nresv.', TH), p('From\nportfolio', TH),
    ])
    cmds += [('BACKGROUND',(0,0),(-1,0), NAVY),
             ('TOPPADDING',(0,0),(-1,0),5),('BOTTOMPADDING',(0,0),(-1,0),5),
             ('LEFTPADDING',(0,0),(-1,0),3),('RIGHTPADDING',(0,0),(-1,0),3),
             ('VALIGN',(0,0),(-1,0),'MIDDLE'),
             ('GRID',(0,0),(-1,0),0.3,colors.HexColor('#FFFFFF30'))]

    last_phase = None
    odd = True
    for r in years:
        if not r.get('client_alive',True) and not r.get('spouse_alive',True) and r.get('gross_income',0)==0:
            continue
        phase = r.get('phase','')
        if phase != last_phase:
            last_phase = phase
            ri = len(rows)
            label = {'working':'— BOTH WORKING —','transitioning':'— TRANSITIONING —'}.get(phase,'— FULLY RETIRED —')
            rows.append(phase_divider(label, 14))
            cmds += [('SPAN',(0,ri),(-1,ri)),
                     ('BACKGROUND',(0,ri),(-1,ri), TEAL if 'RETIRED' in label else NAVY_MD),
                     ('TOPPADDING',(0,ri),(-1,ri),3),('BOTTOMPADDING',(0,ri),(-1,ri),3),
                     ('LEFTPADDING',(0,ri),(-1,ri),8)]

        ri     = len(rows)
        c_sal  = r.get('client_salary',0)
        s_sal  = r.get('spouse_salary',0)
        tot_e  = c_sal + s_sal
        ss     = r.get('client_ss',0) + r.get('spouse_ss',0)
        fixed  = r.get('fixed_income',0)
        all_f  = ss + fixed
        need   = r.get('spending_need',0)
        gap    = r.get('income_surplus',0) or 0
        c_ira  = r.get('client_rmd_taken',0) + r.get('client_ira_extra',0)
        s_ira  = r.get('spouse_rmd_taken',0) + r.get('spouse_ira_extra',0)
        invest = r.get('brokerage_draw',0)
        cash   = r.get('cash_draw',0)
        total_drawn = c_ira + s_ira + invest + cash
        ages   = f"{r['client_age']}/{r.get('spouse_age','')}" if r.get('spouse_age') else str(r['client_age'])

        covered = gap >= 0 and total_drawn == 0
        gap_cell = p('Covered ✓', TDG) if covered else p(fmt(abs(gap)), TDR)
        bg = WHITE if odd else GRAY_BG; odd = not odd

        rows.append([
            p(f"{r['year']}\n{ages}", TMT),
            p(fmt(c_sal), TDT), p(fmt(s_sal), TDT), p(fmt(tot_e), TDT),
            p(fmt(ss), TDN), p(fmt(fixed), TDN), p(fmt(all_f), TDB),
            p(fmt(need), TDP), gap_cell,
            p(fmt(c_ira), ps('wci',size=7,color=BLUE,align=TA_RIGHT,bold=True)),
            p(fmt(s_ira), ps('wsi',size=7,color=BLUE,align=TA_RIGHT,bold=True)),
            p(fmt(invest), TDG), p(fmt(cash), TDG),
            p(fmt(total_drawn), TDB),
        ])
        gap_bg = GREEN_LT if covered else RED_LT
        cmds += [
            ('BACKGROUND',(0,ri),(-1,ri), bg),
            ('BACKGROUND',(8,ri),(8,ri), gap_bg),
            ('TOPPADDING',(0,ri),(-1,ri),3),('BOTTOMPADDING',(0,ri),(-1,ri),3),
            ('LEFTPADDING',(0,ri),(-1,ri),3),('RIGHTPADDING',(0,ri),(-1,ri),3),
            ('VALIGN',(0,ri),(-1,ri),'MIDDLE'),
            ('LINEBELOW',(0,ri),(-1,ri),0.2,GRAY_LN),
        ]
    cmds += [('GRID',(0,1),(-1,-1),0.2,GRAY_LN)]
    tbl = Table(rows, colWidths=CW, repeatRows=1)
    tbl.setStyle(TableStyle(cmds))
    story.append(tbl)
    story.extend(page_footer())
    story.append(PageBreak())


# ══════════════════════════════════════════════════════════════
# PAGE 10 — WORKING YEARS (conditional)
# ══════════════════════════════════════════════════════════════
def build_working_page(story, client_data, projection, ctx):
    years   = projection['years']
    working = [r for r in years if r.get('total_employment_income',0) > 0
               or r.get('client_salary',0) > 0 or r.get('spouse_salary',0) > 0]
    if not working:
        return

    client  = client_data['client']
    spouse  = client_data.get('spouse')
    assump  = client_data.get('assumptions', {})
    need_base = assump.get('income_need_annual', assump.get('annual_income_need', 80000))
    inf       = norm_pct(assump.get('inflation_pct', 0.025))

    cname = client.get('first_name','Client')
    sname = spouse.get('first_name','Spouse') if spouse else 'Spouse'

    story.append(page_header(ctx['pg'], ctx['total'],
        'Working Years', 'Salary · 401k contributions · taxes · surplus — while employed',
        ctx['name'], ctx['date'], ctx['ss_info']))
    ctx['pg'] += 1
    story.append(section_bar(
        f'WORKING YEARS  |  ${need_base:,.0f} income need  ·  {inf*100:.1f}% inflation',
        'EMPLOYMENT INCOME COVERS ALL SPENDING — PORTFOLIO UNTOUCHED', TEAL))
    story.append(Spacer(1, 5))
    story.append(advisor_note(
        'During working years employment income covers the spending need entirely. '
        '401k contributions reduce taxable income and build retirement accounts simultaneously. '
        'The annual surplus flows directly into reserves accelerating portfolio growth. '
        '<b>Key insight:</b> every dollar saved now directly reduces the portfolio draw required in retirement.'))
    story.append(Spacer(1, 5))

    CW = [PW*r for r in [0.09, 0.09, 0.09, 0.09, 0.09, 0.09, 0.09, 0.09, 0.09, 0.09, 0.10]]
    rows, cmds = [], []
    rows.append([p('Year\nAges', THL),
                 p(f'{cname}\nSalary', TH), p(f'{sname}\nSalary', TH),
                 p(f'{cname}\n401k', TH), p(f'{sname}\n401k', TH),
                 p('Taxable\nIncome', TH), p('Est.\nTaxes', TH),
                 p('Income\nNeed', TH), p('Net\nSurplus', TH),
                 p('To\nReserves', TH), p('Cumulative\nReserves', TH)])
    cmds += [('BACKGROUND',(0,0),(-1,0), TEAL),
             ('TOPPADDING',(0,0),(-1,0),5),('BOTTOMPADDING',(0,0),(-1,0),5),
             ('LEFTPADDING',(0,0),(-1,0),3),('RIGHTPADDING',(0,0),(-1,0),3),
             ('VALIGN',(0,0),(-1,0),'MIDDLE')]

    odd = True
    for r in working:
        ri   = len(rows)
        c_s  = r.get('client_salary',0)
        s_s  = r.get('spouse_salary',0)
        c_4  = r.get('client_contrib_trad',0)+r.get('client_contrib_roth',0)
        s_4  = r.get('spouse_contrib_trad',0)+r.get('spouse_contrib_roth',0)
        tax  = r.get('total_tax', round((c_s+s_s)*0.18,0))
        need = r.get('spending_need',0)
        surp = c_s+s_s-tax-need
        cum  = r.get('total_portfolio',0)
        ages = f"{r['client_age']}/{r.get('spouse_age','')}" if r.get('spouse_age') else str(r['client_age'])
        bg   = WHITE if odd else GRAY_BG; odd = not odd

        rows.append([
            p(f"{r['year']}\n{ages}", TMT),
            p(fmt(c_s), TDT), p(fmt(s_s), TDT),
            p(fmt(c_4), TDP), p(fmt(s_4), TDP),
            p(fmt(c_s+s_s-c_4-s_4), TD), p(fmt(tax), TDA),
            p(fmt(need), TDP), p(fmt(surp), TDG if surp>=0 else TDR),
            p(fmt(surp) if surp>0 else '—', TDG),
            p(fmt(cum), TDN),
        ])
        cmds += [
            ('BACKGROUND',(0,ri),(-1,ri), bg),
            ('TOPPADDING',(0,ri),(-1,ri),3),('BOTTOMPADDING',(0,ri),(-1,ri),3),
            ('LEFTPADDING',(0,ri),(-1,ri),3),('RIGHTPADDING',(0,ri),(-1,ri),3),
            ('VALIGN',(0,ri),(-1,ri),'MIDDLE'),
            ('LINEBELOW',(0,ri),(-1,ri),0.2,GRAY_LN),
        ]
    cmds += [('GRID',(0,0),(-1,-1),0.2,GRAY_LN)]
    tbl = Table(rows, colWidths=CW, repeatRows=1)
    tbl.setStyle(TableStyle(cmds))
    story.append(tbl)
    story.extend(page_footer())
    story.append(PageBreak())


# ══════════════════════════════════════════════════════════════
# PAGE 11 — ACCOUNT BALANCES & DRAWDOWN
# ══════════════════════════════════════════════════════════════
def build_balances_page(story, client_data, projection, ctx):
    client  = client_data['client']
    spouse  = client_data.get('spouse')
    years   = projection['years']

    cname = client.get('first_name','Client')
    sname = spouse.get('first_name','Spouse') if spouse else 'Spouse'

    story.append(page_header(ctx['pg'], ctx['total'],
        'Account Balances & Drawdown', 'Each account · growth · contributions · withdrawals · closing balance',
        ctx['name'], ctx['date'], ctx['ss_info']))
    ctx['pg'] += 1
    start_p = projection['summary'].get('starting_portfolio',0)
    end_p   = projection['summary'].get('ending_portfolio',0)
    story.append(section_bar(
        f'ALL ACCOUNTS AT ASSUMED RATE OF RETURN  |  WITHDRAWALS PER WATERFALL',
        f'PORTFOLIO: ${start_p:,.0f} → ${end_p:,.0f} — PLAN SUSTAINABLE'))
    story.append(Spacer(1, 6))

    # Build per-account row data
    def acct_rows(open_k, earn_k, draw_k, close_k, contrib_k=None):
        data = []
        for r in years:
            o = r.get(open_k, 0) or 0
            e = r.get(earn_k, 0) or 0
            d = r.get(draw_k, 0) or 0
            c = r.get(close_k, 0) or 0
            cb = r.get(contrib_k, 0) or 0 if contrib_k else 0
            if o or e or d or c or cb:
                data.append((r['year'], o, cb, e, d, c))
        # Trim trailing all-zero rows
        while data and all(v==0 for v in data[-1][1:]):
            data.pop()
        return data

    c_ira_rows  = acct_rows('client_ira_open','client_ira_earn','client_ira_draw','client_ira_close','client_ira_contrib')
    s_ira_rows  = acct_rows('spouse_ira_open','spouse_ira_earn','spouse_ira_draw','spouse_ira_close','spouse_ira_contrib')
    brok_rows   = acct_rows('brokerage_open','brokerage_earn','brokerage_draw','brokerage_close')
    cash_rows   = acct_rows('cash_open','cash_earn','cash_draw','cash_close')

    c_ira_has  = bool(c_ira_rows)
    s_ira_has  = bool(s_ira_rows)
    brok_has   = bool(brok_rows)
    cash_has   = bool(cash_rows)

    def acct_tbl(title, color, rows_data, has_data):
        cw = PW/2 - 10
        col_r = [0.18, 0.18, 0.14, 0.16, 0.17, 0.17]
        cws   = [cw*r for r in col_r]
        if not has_data:
            na = Table([[p(title, ps('nat',size=7.5,color=WHITE,bold=True,align=TA_CENTER))],
                        [p('No balance reported for this account.', ps('nab',size=7,color=GRAY_MD,align=TA_CENTER,leading=10))]],
                       colWidths=[cw])
            na.setStyle(TableStyle([
                ('BACKGROUND',(0,0),(-1,0), color),
                ('BACKGROUND',(0,1),(-1,1), GRAY_BG),
                ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
                ('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),
                ('BOX',(0,0),(-1,-1),0.3,GRAY_LN),
            ]))
            return na

        th = ps('ath', size=6.5, color=WHITE, align=TA_CENTER, bold=True)
        thl = ps('athl', size=6.5, color=WHITE, align=TA_LEFT, bold=True)
        tr = [
            [p(title, ps('att',size=7,color=WHITE,bold=True,align=TA_CENTER))],
            [p('Opening · Earnings · Draws · Closing',
               ps('ats',size=6,color=colors.HexColor('#FFFFFFAA'),align=TA_CENTER))],
            [Table([[p('Year',thl),p('Opening',th),p('Contrib.',th),
                     p('Earn.',th),p('Drawn',th),p('Closing',th)]],
                   colWidths=cws)],
        ]
        tc = [
            ('SPAN',(0,0),(-1,0)),('SPAN',(0,1),(-1,1)),
            ('BACKGROUND',(0,0),(-1,1), color),
            ('BACKGROUND',(0,2),(-1,2), colors.HexColor('#00000018')),
            ('TOPPADDING',(0,0),(-1,2),3),('BOTTOMPADDING',(0,0),(-1,2),3),
            ('LEFTPADDING',(0,0),(-1,2),4),('RIGHTPADDING',(0,0),(-1,2),4),
            ('VALIGN',(0,0),(-1,2),'MIDDLE'),
        ]
        odd = True
        for yr, opn, contrib, earn, draw, close in rows_data:
            ri = len(tr)
            vl = ps(f'v{ri}', size=6.5, color=CHARCOAL, align=TA_RIGHT)
            dr = ps(f'd{ri}', size=6.5, color=RED, align=TA_RIGHT, bold=True)
            cl = ps(f'c{ri}', size=6.5, color=NAVY, align=TA_RIGHT, bold=True)
            er = ps(f'e{ri}', size=6.5, color=GREEN, align=TA_RIGHT)
            yl = ps(f'y{ri}', size=6.5, color=GRAY_MD, align=TA_LEFT)
            cr = ps(f'cr{ri}',size=6.5, color=TEAL, align=TA_RIGHT, bold=True)
            data_row = Table([[
                p(str(yr), yl),
                p(fmt(opn,False), vl),
                p(fmt(contrib,False), cr) if contrib else p('—', vl),
                p(fmt(earn,False), er),
                p(f'({fmt(draw,False)})', dr) if draw else p('—', vl),
                p(fmt(close,False), cl),
            ]], colWidths=cws)
            data_row.setStyle(TableStyle([
                ('BACKGROUND',(0,0),(-1,-1), WHITE if odd else GRAY_BG),
                ('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2),
                ('LEFTPADDING',(0,0),(-1,-1),3),('RIGHTPADDING',(0,0),(-1,-1),3),
                ('LINEBELOW',(0,0),(-1,-1),0.2,GRAY_LN),
            ]))
            odd = not odd
            tr.append([data_row])
            tc += [('TOPPADDING',(0,ri),(-1,ri),0),('BOTTOMPADDING',(0,ri),(-1,ri),0),
                   ('LEFTPADDING',(0,ri),(-1,ri),0),('RIGHTPADDING',(0,ri),(-1,ri),0)]

        tc += [('BOX',(0,0),(-1,-1),0.3,GRAY_LN)]
        t = Table(tr, colWidths=[cw])
        t.setStyle(TableStyle(tc))
        return t

    t1 = acct_tbl(f"{cname}'s IRA / 401k", NAVY,  c_ira_rows, c_ira_has)
    t2 = acct_tbl(f"{sname}'s IRA",         TEAL,  s_ira_rows, s_ira_has)
    t3 = acct_tbl("Joint Investments",       GREEN, brok_rows,  brok_has)
    t4 = acct_tbl("Cash & Reserves",         AMBER, cash_rows,  cash_has)

    row1 = Table([[t1, t2]], colWidths=[PW/2, PW/2])
    row1.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),
                               ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),4),
                               ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0)]))
    row2 = Table([[t3, t4]], colWidths=[PW/2, PW/2])
    row2.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),
                               ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),4),
                               ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0)]))
    story.append(row1)
    story.append(Spacer(1, 8))
    story.append(row2)
    story.append(Spacer(1, 10))

    # Combined portfolio table
    ch = ps('cph', size=8.5, color=NAVY, bold=True)
    story.append(p('Combined Portfolio — All Accounts by Year', ch))
    story.append(Spacer(1, 5))

    rCW = [PW*r for r in [0.07, 0.09, 0.09, 0.1, 0.09, 0.09, 0.08, 0.13, 0.1]]
    r_rows, r_cmds = [], []
    r_rows.append([p('Year',THL), p(f"{cname}'s IRA",TH), p(f"{sname}'s IRA",TH),
                   p('Brokerage',TH), p('Cash & Resv.',TH), p('Inh. IRA',TH),
                   p('Other',TH), p('Combined Portfolio',TH), p('Net Monthly',TH)])
    r_cmds += [('BACKGROUND',(0,0),(-1,0),NAVY),
               ('TOPPADDING',(0,0),(-1,0),5),('BOTTOMPADDING',(0,0),(-1,0),5),
               ('LEFTPADDING',(0,0),(-1,0),4),('RIGHTPADDING',(0,0),(-1,0),4),
               ('VALIGN',(0,0),(-1,0),'MIDDLE')]

    crossed = set()
    for i, r in enumerate(years):
        if not r.get('client_alive',True) and not r.get('spouse_alive',True):
            continue
        ri   = len(r_rows)
        port = r.get('total_portfolio',0)
        mo   = r.get('net_monthly',0)
        is_5 = (i > 0 and i % 5 == 0)
        is_ms = False
        for thresh, label in [(1000000,'1M'),(2000000,'2M'),(3000000,'3M'),(5000000,'5M')]:
            if label not in crossed and port >= thresh:
                is_ms = True; crossed.add(label)
        bg = GOLD_LT if is_ms else (TEAL_LT if is_5 else (WHITE if i%2==0 else GRAY_BG))

        r_rows.append([
            p(str(r['year']), TDL),
            p(fmt(r.get('client_ira_close',0)), TD),
            p(fmt(r.get('spouse_ira_close',0)), TD),
            p(fmt(r.get('brokerage_close',0)), TD),
            p(fmt(r.get('cash_close',0)), TD),
            p(fmt(r.get('inherited_ira_close',0) or r.get('inherited_ira_balance',0)), TD),
            p(fmt(r.get('other_close',0)), TD),
            p(fmt(port), TDB),
            p(fmt(mo), TD),
        ])
        r_cmds += [
            ('BACKGROUND',(0,ri),(-1,ri), bg),
            ('BACKGROUND',(7,ri),(7,ri), NAVY_LT if not is_ms else GOLD_LT),
            ('TOPPADDING',(0,ri),(-1,ri),3),('BOTTOMPADDING',(0,ri),(-1,ri),3),
            ('LEFTPADDING',(0,ri),(-1,ri),4),('RIGHTPADDING',(0,ri),(-1,ri),4),
            ('VALIGN',(0,ri),(-1,ri),'MIDDLE'),
        ]
        if is_5:
            r_cmds += [('LINEABOVE',(0,ri),(-1,ri),1.5,TEAL)]
        else:
            r_cmds += [('LINEBELOW',(0,ri),(-1,ri),0.2,GRAY_LN)]

    r_cmds += [('GRID',(0,0),(-1,-1),0.2,GRAY_LN)]
    rt = Table(r_rows, colWidths=rCW, repeatRows=1)
    rt.setStyle(TableStyle(r_cmds))
    story.append(rt)
    story.extend(page_footer())
    story.append(p(
        'All accounts earn the assumed rate of return annually. '
        'Withdrawals in red parentheses — sourced per waterfall. '
        'Gold rows = portfolio milestone crossings. Teal dividers = every 5 years. All years shown.',
        FTR))


# ══════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════
def generate_pdf(client_data: dict, projection: dict) -> bytes:
    """Generate the full Retirement-Right PDF report. Returns PDF bytes."""
    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=LM, rightMargin=RM,
        topMargin=TM,  bottomMargin=BM,
        allowSplitting=1,
    )

    client = client_data['client']
    spouse = client_data.get('spouse')
    years  = projection['years']

    cname = f"{client.get('first_name','')} {client.get('last_name','')}"
    sname = f"& {spouse.get('first_name','')} {spouse.get('last_name','')}" if spouse else ''
    full_name = f'{cname} {sname}'.strip()

    ss_data = client_data.get('social_security', {})
    c_st  = ss_data.get('client_status','')
    c_fa  = ss_data.get('client_file_age','')
    s_st  = ss_data.get('spouse_status','')
    s_fa  = ss_data.get('spouse_file_age','')
    ror   = norm_pct(client_data.get('assumptions',{}).get('rate_of_return',0.04))

    def ss_label(status, name, fa):
        if status == 'collecting': return f'{name} SS collecting'
        if status == 'will_file' and fa: return f'{name} files SS @ {fa}'
        if status == 'none': return f'{name} no SS'
        return f'{name} SS {status}'

    ss_info = ss_label(c_st, client.get('first_name','Client'), c_fa)
    if spouse: ss_info += '  |  ' + ss_label(s_st, spouse.get('first_name','Spouse'), s_fa)

    report_date = projection.get('report_date', '')
    if not report_date:
        from datetime import date
        report_date = date.today().strftime('%Y-%m-%d')

    # Count total pages
    has_working = any(r.get('client_salary',0)+r.get('spouse_salary',0) > 0 for r in years)
    has_inh_ira = bool((client_data.get('assets',{}).get('ira_inherited') or {}).get('balance',0))
    total_pages = 9 + (1 if has_working else 0) + (1 if has_inh_ira else 0)

    ctx = {
        'pg': 2, 'total': total_pages,
        'name': full_name, 'date': report_date,
        'ss_info': ss_info, 'ror': ror,
    }

    story = []

    # Page 1 — Cover
    build_cover_page(story, client_data, projection)

    # Page 2 — Executive Summary
    build_executive_summary(story, client_data, projection, ctx)

    # Page 3 — Advisor Observations
    build_advisor_observations(story, client_data, projection, ctx)

    # Page 4 — Retirement Snapshot
    build_snapshot_page(story, client_data, projection, ctx)

    # Page 5 — Income & Tax Strategy
    build_income_tax_page(story, client_data, projection, ctx)

    # Page 6 — Income Projection
    build_income_projection_page(story, client_data, projection, ctx)

    # Page 7 — Inherited IRA (conditional)
    build_inherited_ira_page(story, client_data, projection, ctx)

    # Page 8 — Retirement Years
    build_retirement_years_page(story, client_data, projection, ctx)

    # Page 9 — Withdrawal Waterfall
    build_waterfall_page(story, client_data, projection, ctx)

    # Page 10 — Working Years (conditional)
    build_working_page(story, client_data, projection, ctx)

    # Page 11 — Account Balances & Drawdown
    build_balances_page(story, client_data, projection, ctx)

    doc.build(story)
    return buf.getvalue()
