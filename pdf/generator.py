"""
PDF Generator — Retirement-Right v42 STATIC
Every page drawn at fixed canvas coordinates. Nothing moves. Ever.
"""
import io
from datetime import date as _date
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas as rl_canvas

# ── Page geometry — FIXED ─────────────────────────────────────
PAGE_W, PAGE_H = landscape(letter)   # 792 x 612
LM = RM = 0.55 * inch               # 39.6 pt
TM = BM = 0.40 * inch               # 28.8 pt
PW = PAGE_W - LM - RM               # 712.8 pt

# ── Fixed vertical zones (Y from bottom) ─────────────────────
HDR_TOP   = PAGE_H - TM             # 583.2 — top of page header
HDR_H     = 52                      # header height
BAR_H     = 18                      # section bar height
CONTENT_Y = HDR_TOP - HDR_H - BAR_H - 6   # 507.2 — content starts here
FOOTER_Y  = BM + 30                 # 58.8  — content must stop here
CONTENT_H = CONTENT_Y - FOOTER_Y   # 448.4 — fixed content zone

ROW_H     = 16   # FIXED row height — never changes
HDR_ROW_H = 22   # table header row
NOTE_H    = 40   # advisor note box
SBOX_H    = 44   # summary boxes

def max_data_rows(has_note=False, has_sboxes=False, extra_overhead=0):
    used = HDR_ROW_H + extra_overhead
    if has_note:   used += NOTE_H + 4
    if has_sboxes: used += SBOX_H + 6
    available = CONTENT_H - used
    return max(1, int(available / ROW_H))

# ── Colors ────────────────────────────────────────────────────
NAVY     = colors.HexColor('#0A2342')
NAVY_MD  = colors.HexColor('#1A3A5C')
NAVY_LT  = colors.HexColor('#E8EEF5')
TEAL     = colors.HexColor('#0B6B5A')
TEAL_LT  = colors.HexColor('#E0F0EC')
TEAL_JMP = colors.HexColor('#C5EAE4')
GOLD     = colors.HexColor('#B8963E')
GOLD_LT  = colors.HexColor('#FBF5E6')
GOLD_DK  = colors.HexColor('#7A5C1E')
AMBER    = colors.HexColor('#92400E')
AMBER_LT = colors.HexColor('#FEF3C7')
GREEN    = colors.HexColor('#155E35')
GREEN_LT = colors.HexColor('#DCFCE7')
RED      = colors.HexColor('#991B1B')
RED_LT   = colors.HexColor('#FEE2E2')
BLUE     = colors.HexColor('#1E3A8A')
PURPLE   = colors.HexColor('#4C1D95')
GRAY_BG  = colors.HexColor('#F7F8FA')
GRAY_LN  = colors.HexColor('#D1D5DB')
GRAY_MD  = colors.HexColor('#9CA3AF')
WHITE    = colors.white
BLACK    = colors.HexColor('#111827')
CHARCOAL = colors.HexColor('#374151')

# ── Helpers ───────────────────────────────────────────────────
def fmt(v, zero_dash=True):
    if v is None or (zero_dash and v == 0): return '—'
    return f'${abs(v):,.0f}'

def norm_pct(v, default=0.04):
    val = v if v is not None else default
    return val / 100 if val > 1 else val

def age_from_dob(dob_str):
    try:
        y, m, d = map(int, dob_str.split('-'))
        today = _date.today()
        return today.year - y - ((today.month, today.day) < (m, d))
    except: return '—'

def normalize_assets(assets):
    flat = {}
    ira_t = assets.get('ira_traditional', {})
    flat['client_ira'] = (ira_t.get('client_balance',0) or 0) if isinstance(ira_t,dict) else 0
    flat['spouse_ira'] = (ira_t.get('spouse_balance',0) or 0) if isinstance(ira_t,dict) else 0
    inh = assets.get('ira_inherited')
    flat['ira_inherited'] = inh if isinstance(inh, dict) else {}
    brok = assets.get('brokerage', {})
    if isinstance(brok, dict):
        flat['brokerage'] = brok.get('total_balance', 0) or 0
        for sub in (brok.get('sub_accounts') or []):
            if 'money' in sub.get('label','').lower() or 'market' in sub.get('label','').lower():
                flat['money_market'] = sub.get('balance', 0) or 0
    elif isinstance(brok, (int, float)): flat['brokerage'] = brok
    else: flat['brokerage'] = 0
    flat.setdefault('money_market', 0)
    cash = assets.get('cash_and_savings', {})
    flat['cash'] = ((cash.get('client_balance',0) or 0)+(cash.get('spouse_balance',0) or 0)) if isinstance(cash,dict) else (cash or 0)
    flat['annuity_balance']    = assets.get('annuity_value', 0) or 0
    flat['real_estate_equity'] = assets.get('real_estate_equity', 0) or 0
    flat['home_value']         = assets.get('primary_home_value', 0) or 0
    others = assets.get('other_assets', [])
    flat['other_client'] = sum(o.get('balance',0) or 0 for o in others) if isinstance(others,list) else (assets.get('other_client',0) or 0)
    flat['other_spouse'] = assets.get('other_spouse', 0) or 0
    return flat

def normalize_ss(client_data):
    ss = client_data.get('social_security', {})
    if ss: return ss
    income = client_data.get('income', {})
    if income:
        ss_n = income.get('social_security', {})
        if ss_n:
            c = ss_n.get('client', {}) or {}
            s = ss_n.get('spouse', {}) or {}
            return {'client_status': c.get('status',''), 'client_monthly': c.get('monthly_benefit',0) or 0,
                    'client_file_age': c.get('file_age',''), 'spouse_status': s.get('status',''),
                    'spouse_monthly': s.get('monthly_benefit',0) or 0, 'spouse_file_age': s.get('file_age','')}
    return {}

def normalize_meta(client_data):
    meta = client_data.get('meta', {}); client = client_data.get('client', {})
    return (meta.get('notes','') or client.get('advisor_notes','') or '',
            meta.get('legacy_notes','') or client.get('legacy_notes','') or '')

def total_investable(a):
    keys = ['client_ira','spouse_ira','brokerage','money_market','cash',
            'annuity_balance','real_estate_equity','other_client','other_spouse']
    total = sum(a.get(k,0) or 0 for k in keys)
    inh = a.get('ira_inherited') or {}
    total += (inh.get('balance',0) or 0) if isinstance(inh,dict) else 0
    return total

def smart_collapse(rows, max_r):
    """Fit rows into max_r. Annual first, then every-5 tail."""
    if len(rows) <= max_r:
        return [(r, False) for r in rows]
    total = len(rows)
    for annual in range(min(max_r, total), -1, -1):
        remaining = total - annual
        five_count = (remaining + 4) // 5
        if annual + five_count <= max_r:
            break
    else:
        annual = max_r
    result = [(r, False) for r in rows[:annual]]
    for i, r in enumerate(rows[annual:]):
        if i % 5 == 0:
            result.append((r, True))
    return result

# ── Canvas drawing primitives ─────────────────────────────────

def draw_header(c, pg, total, right_title, right_sub, client_name, date, ss_info):
    y_top = HDR_TOP
    c.setFillColor(NAVY)
    c.rect(LM, y_top - HDR_H, PW, HDR_H, fill=1, stroke=0)
    # Left
    c.setFillColor(colors.HexColor('#AABDD4')); c.setFont('Helvetica-Bold', 6.5)
    c.drawString(LM+12, y_top-13, 'RETIREMENT-RIGHT  ·  CONFIDENTIAL')
    c.setFillColor(WHITE); c.setFont('Helvetica-Bold', 10)
    c.drawString(LM+12, y_top-27, f'Retirement Income & Legacy Blueprint — {client_name}'[:75])
    c.setFillColor(colors.HexColor('#AABDD4')); c.setFont('Helvetica', 6.5)
    c.drawString(LM+12, y_top-41, f'Prepared {date}  ·  {ss_info}'[:90])
    # Right
    c.setFillColor(colors.HexColor('#AABDD4')); c.setFont('Helvetica-Bold', 6.5)
    c.drawRightString(PAGE_W-RM-12, y_top-13, f'PAGE {pg} OF {total}')
    c.setFillColor(WHITE); c.setFont('Helvetica-Bold', 9)
    c.drawRightString(PAGE_W-RM-12, y_top-27, right_title[:55])
    c.setFillColor(colors.HexColor('#AABDD4')); c.setFont('Helvetica', 6.5)
    c.drawRightString(PAGE_W-RM-12, y_top-41, right_sub[:65])

def draw_bar(c, left, right='', bg=None):
    if bg is None: bg = NAVY_MD
    y = HDR_TOP - HDR_H - BAR_H
    c.setFillColor(bg); c.rect(LM, y, PW, BAR_H, fill=1, stroke=0)
    c.setFillColor(colors.HexColor('#F0E6C8')); c.setFont('Helvetica-Bold', 7)
    c.drawString(LM+12, y+5, left[:92])
    if right:
        c.setFillColor(colors.HexColor('#FFFFFF90')); c.setFont('Helvetica', 6.5)
        c.drawRightString(PAGE_W-RM-12, y+5, right[:65])

def draw_footer(c):
    fy = BM + 14
    c.setStrokeColor(GRAY_LN); c.setLineWidth(0.5)
    c.line(LM, fy+10, PAGE_W-RM, fy+10)
    c.setFillColor(NAVY_MD); c.setFont('Helvetica-Bold', 7.5)
    c.drawString(LM, fy+2, 'Retirement-Right  ·  1820 E Ray Road Suite A-108  ·  Chandler, AZ 85225  ·  480-726-8805  ·  Michael J. Eberhardt, Retirement Specialist')
    c.setFillColor(GRAY_MD); c.setFont('Helvetica', 6.5)
    c.drawString(LM, fy-8, 'Educational and planning purposes only. Not tax, legal, investment, or Social Security advice. Tax estimates are approximate. Consult qualified professionals.')

def draw_note(c, y, text):
    """Draw advisor note. Returns y after note."""
    c.setFillColor(GOLD_LT); c.rect(LM, y-NOTE_H, PW, NOTE_H, fill=1, stroke=0)
    c.setFillColor(GOLD); c.rect(LM, y-NOTE_H, 3, NOTE_H, fill=1, stroke=0)
    c.setStrokeColor(GOLD); c.setLineWidth(0.3); c.rect(LM, y-NOTE_H, PW, NOTE_H, fill=0, stroke=1)
    c.setFillColor(GOLD_DK); c.setFont('Helvetica-Bold', 7.5); c.drawString(LM+10, y-13, 'Advisor Note')
    c.setFillColor(CHARCOAL); c.setFont('Helvetica', 7.5)
    # simple 2-line wrap
    words = text.split(); l1 = ''; l2 = ''
    nw = PW - 118
    for w in words:
        t = (l1+' '+w).strip()
        if c.stringWidth(t,'Helvetica',7.5) < nw: l1 = t
        elif not l2: l2 = w
        else:
            t2 = (l2+' '+w).strip()
            if c.stringWidth(t2,'Helvetica',7.5) < nw: l2 = t2
    c.drawString(LM+108, y-14, l1); 
    if l2: c.drawString(LM+108, y-26, l2)
    return y - NOTE_H - 4

def draw_kpi_row(c, y, items):
    """Draw KPI box row. Returns y after boxes."""
    n = len(items); bw = PW/n; bh = 52
    for i,(label,value,accent) in enumerate(items):
        x = LM + i*bw + 2
        c.setFillColor(WHITE); c.setStrokeColor(GRAY_LN); c.setLineWidth(0.5)
        c.rect(x, y-bh, bw-4, bh, fill=1, stroke=1)
        c.setFillColor(accent); c.rect(x, y-bh, bw-4, 3, fill=1, stroke=0)
        c.setFillColor(GRAY_MD); c.setFont('Helvetica-Bold', 7)
        c.drawCentredString(x+bw/2-2, y-15, label)
        c.setFillColor(NAVY); c.setFont('Helvetica-Bold', 15)
        c.drawCentredString(x+bw/2-2, y-36, value)
    return y - bh - 6

def draw_sboxes(c, y, items):
    """Draw summary boxes. Returns y after boxes."""
    n = len(items); bw = PW/n; bh = SBOX_H
    for i,(accent,title,body) in enumerate(items):
        x = LM + i*bw + 2
        c.setFillColor(WHITE); c.setStrokeColor(GRAY_LN); c.setLineWidth(0.4)
        c.rect(x, y-bh, bw-4, bh, fill=1, stroke=1)
        c.setFillColor(accent); c.rect(x, y-bh, 3, bh, fill=1, stroke=0)
        c.setFillColor(accent); c.setFont('Helvetica-Bold', 8)
        c.drawString(x+8, y-15, title[:32])
        c.setFillColor(CHARCOAL); c.setFont('Helvetica', 7)
        words = body.split(); l1=''; l2=''
        nw = bw-18
        for w in words:
            t=(l1+' '+w).strip()
            if c.stringWidth(t,'Helvetica',7)<nw: l1=t
            elif not l2: l2=w
            else:
                t2=(l2+' '+w).strip()
                if c.stringWidth(t2,'Helvetica',7)<nw: l2=t2
        c.drawString(x+8, y-27, l1)
        if l2: c.drawString(x+8, y-37, l2)
    return y - bh - 4

def draw_info_rows(c, x, y, rows, w1, w2, title=None):
    """Draw 2-col info table. Returns y after table."""
    rh = 18
    if title:
        c.setFillColor(NAVY); c.setFont('Helvetica-Bold', 8.5)
        c.drawString(x, y, title); y -= 14
    for i,(lbl,val) in enumerate(rows):
        bg = WHITE if i%2==0 else GRAY_BG
        c.setFillColor(bg); c.rect(x, y-rh, w1+w2, rh, fill=1, stroke=0)
        c.setStrokeColor(GRAY_LN); c.setLineWidth(0.3)
        c.rect(x, y-rh, w1+w2, rh, fill=0, stroke=1)
        c.setFillColor(GRAY_MD); c.setFont('Helvetica', 8); c.drawString(x+6, y-rh+5, str(lbl))
        c.setFillColor(BLACK); c.drawRightString(x+w1+w2-6, y-rh+5, str(val))
        y -= rh
    return y

def draw_table(c, start_y, col_widths, col_aligns, headers, data_rows):
    """
    Draw fixed data table. Returns y after last row.
    headers: list of str
    data_rows: list of (cells, bg_color, top_line_color_or_None)
      cells: list of (text, fg_color, bold) or just str
    """
    xs = [LM]
    for w in col_widths[:-1]: xs.append(xs[-1]+w)

    def cell(cx, cy, w, h, text, align, fg, bold, text_size=7.5):
        fn = 'Helvetica-Bold' if bold else 'Helvetica'
        c.setFont(fn, text_size); c.setFillColor(fg)
        pad = 4; s = str(text)[:22]
        if align=='L': c.drawString(cx+pad, cy-h+4, s)
        elif align=='C': c.drawCentredString(cx+w/2, cy-h+4, s)
        else: c.drawRightString(cx+w-pad, cy-h+4, s)

    # Header
    y = start_y
    for i,(hdr,cx,w) in enumerate(zip(headers,xs,col_widths)):
        c.setFillColor(NAVY); c.rect(cx, y-HDR_ROW_H, w, HDR_ROW_H, fill=1, stroke=0)
        align = col_aligns[i] if i<len(col_aligns) else 'R'
        cell(cx, y, w, HDR_ROW_H, hdr, align, WHITE, True)
    c.setStrokeColor(colors.HexColor('#FFFFFF30')); c.setLineWidth(0.3)
    for cx,w in zip(xs,col_widths): c.rect(cx, y-HDR_ROW_H, w, HDR_ROW_H, fill=0, stroke=1)
    y -= HDR_ROW_H

    # Data
    for row_data in data_rows:
        if len(row_data)==3: cells, bg, top_line = row_data
        else: cells, bg = row_data; top_line = None
        if top_line:
            c.setStrokeColor(top_line); c.setLineWidth(2)
            c.line(LM, y, LM+PW, y); c.setLineWidth(0.3)
        c.setFillColor(bg); c.rect(LM, y-ROW_H, PW, ROW_H, fill=1, stroke=0)
        c.setStrokeColor(GRAY_LN); c.setLineWidth(0.2); c.line(LM, y-ROW_H, LM+PW, y-ROW_H)
        for i,(ct,cx,w) in enumerate(zip(cells,xs,col_widths)):
            if isinstance(ct, tuple): txt,fg,bold = ct
            else: txt,fg,bold = str(ct),BLACK,False
            align = col_aligns[i] if i<len(col_aligns) else 'R'
            cell(cx, y, w, ROW_H, txt, align, fg, bold)
        y -= ROW_H

    # Border and col dividers
    c.setStrokeColor(GRAY_LN); c.setLineWidth(0.4)
    c.rect(LM, y, PW, start_y-y, fill=0, stroke=1)
    c.setLineWidth(0.2)
    for cx in xs[1:]: c.line(cx, start_y, cx, y)
    return y

# ── Page builders ─────────────────────────────────────────────

def build_cover(c, client_data, projection):
    client = client_data['client']; spouse = client_data.get('spouse')
    summary = projection['summary']; assets = normalize_assets(client_data.get('assets',{}))
    assump = client_data.get('assumptions',{})
    cname = f"{client.get('first_name','')} {client.get('last_name','')}"
    sname = f"{spouse.get('first_name','')} {spouse.get('last_name','')}" if spouse else ''
    prepared_for = f'{cname} & {sname}' if sname else cname
    total_inv = total_investable(assets); home = assets.get('home_value',0) or 0
    total_net = total_inv + home
    spend = assump.get('income_need_annual', assump.get('annual_income_need',0))
    ror   = norm_pct(assump.get('rate_of_return',0.04))
    lt_ss = summary.get('lifetime_ss',0); lt_tax = summary.get('lifetime_federal_tax',0)
    end_p = summary.get('ending_portfolio',0); proj_y = summary.get('projection_years',0)
    rdate = projection.get('report_date','') or _date.today().strftime('%B %d, %Y')

    # Navy banner
    c.setFillColor(NAVY); c.rect(0, PAGE_H-130, PAGE_W, 130, fill=1, stroke=0)
    c.setFillColor(GOLD); c.setFont('Helvetica-Bold',10); c.drawCentredString(PAGE_W/2, PAGE_H-22, 'RETIREMENT-RIGHT')
    c.setFillColor(colors.HexColor('#AABDD4')); c.setFont('Helvetica',8)
    c.drawCentredString(PAGE_W/2, PAGE_H-36, 'Confidential Retirement Planning Report')
    c.setFillColor(WHITE); c.setFont('Helvetica-Bold',24)
    c.drawCentredString(PAGE_W/2, PAGE_H-68, 'Retirement Income & Legacy Blueprint')
    c.setFillColor(colors.HexColor('#AABDD4')); c.setFont('Helvetica-Bold',7)
    c.drawCentredString(PAGE_W/2, PAGE_H-90, 'PREPARED EXCLUSIVELY FOR')
    c.setFillColor(WHITE); c.setFont('Helvetica-Bold',20)
    c.drawCentredString(PAGE_W/2, PAGE_H-112, prepared_for)

    # Centerpiece
    cp_y = PAGE_H - 168
    c.setFillColor(WHITE); c.setStrokeColor(GOLD); c.setLineWidth(2)
    c.rect(LM+PW*0.1, cp_y-68, PW*0.8, 68, fill=1, stroke=1)
    c.setFillColor(GRAY_MD); c.setFont('Helvetica-Bold',9); c.drawCentredString(PAGE_W/2, cp_y-15, 'TOTAL NET ASSETS')
    c.setFillColor(NAVY); c.setFont('Helvetica-Bold',28); c.drawCentredString(PAGE_W/2, cp_y-44, f'${total_net:,.0f}')
    c.setFillColor(GRAY_MD); c.setFont('Helvetica',8); c.drawCentredString(PAGE_W/2, cp_y-60, f'Investable: ${total_inv:,.0f}   ·   Home: ${home:,.0f}')

    # 4 KPI boxes at fixed Y
    draw_kpi_row(c, cp_y-80, [
        ('Annual Income Goal', f'${spend:,.0f}', TEAL),
        ('Lifetime Social Security', f'${lt_ss:,.0f}', GOLD),
        ('Estimated Lifetime Tax', f'${lt_tax:,.0f}', AMBER),
        ('Ending Portfolio', f'${end_p:,.0f}', GREEN),
    ])

    # Prepared by at fixed Y
    by_y = 170
    c.setStrokeColor(GOLD); c.setLineWidth(1); c.line(LM+PW*0.3, by_y+4, LM+PW*0.7, by_y+4)
    c.setFillColor(NAVY); c.setFont('Helvetica-Bold',11); c.drawCentredString(PAGE_W/2, by_y-10, 'Michael J. Eberhardt')
    c.setFillColor(CHARCOAL); c.setFont('Helvetica',8)
    c.drawCentredString(PAGE_W/2, by_y-22, 'Retirement Specialist  ·  Retirement-Right')
    c.drawCentredString(PAGE_W/2, by_y-34, '1820 E Ray Road Suite A-108  ·  Chandler, AZ 85225  ·  480-726-8805')
    c.setStrokeColor(GRAY_LN); c.setLineWidth(0.5); c.line(LM+PW*0.3, by_y-44, LM+PW*0.7, by_y-44)
    c.setFillColor(GRAY_MD); c.setFont('Helvetica',7)
    c.drawCentredString(PAGE_W/2, by_y-56, f'Report Date: {rdate}  ·  Rate of Return: {ror*100:.1f}%  ·  Projection: {proj_y} years')
    c.drawCentredString(PAGE_W/2, by_y-68, 'For educational and planning purposes only. Not tax, legal, investment, or Social Security advice.')


def build_exec_summary(c, pg, total_pg, client_data, projection, ctx):
    client = client_data['client']; summary = projection['summary']
    assump = client_data.get('assumptions',{}); assets = normalize_assets(client_data.get('assets',{}))
    spend = assump.get('income_need_annual', assump.get('annual_income_need',0))
    ror = norm_pct(assump.get('rate_of_return',0.04)); inf = norm_pct(assump.get('inflation_pct',0.025))
    total_inv = total_investable(assets); end_p = summary.get('ending_portfolio',0)
    lt_ss = summary.get('lifetime_ss',0); lt_tax = summary.get('lifetime_federal_tax',0)+summary.get('lifetime_state_tax',0)
    lt_net = summary.get('lifetime_net',0); start_p = summary.get('starting_portfolio',0); proj_y = summary.get('projection_years',0)

    draw_header(c, pg, total_pg, 'Executive Summary', 'Key findings · planning opportunities · numbers', ctx['name'], ctx['date'], ctx['ss_info'])
    draw_bar(c, 'RETIREMENT INCOME & LEGACY ANALYSIS — AT A GLANCE', f'{proj_y}-YEAR PROJECTION')
    draw_footer(c)

    y = CONTENT_Y

    def section_block(title, items, bg):
        nonlocal y
        sh = 18
        c.setFillColor(bg); c.rect(LM, y-sh, PW, sh, fill=1, stroke=0)
        c.setFillColor(WHITE); c.setFont('Helvetica-Bold',8.5); c.drawString(LM+12, y-sh+5, title)
        y -= sh
        ih = len(items)*15+6
        c.setFillColor(WHITE); c.rect(LM, y-ih, PW, ih, fill=1, stroke=0)
        c.setStrokeColor(GRAY_LN); c.setLineWidth(0.3); c.rect(LM, y-ih, PW, ih, fill=0, stroke=1)
        for item in items:
            y -= 15; c.setFillColor(CHARCOAL); c.setFont('Helvetica',8.5)
            c.drawString(LM+12, y-1, f'  ✓  {item}'[:95])
        y -= 6

    doing = [f'Portfolio of ${total_inv:,.0f} provides a strong foundation entering retirement.',
             f'Estimated lifetime Social Security of ${lt_ss:,.0f} significantly reduces portfolio dependency.',
             'Waterfall strategy preserves investments by drawing fixed income first.']
    if end_p > start_p: doing.append(f'Ending portfolio of ${end_p:,.0f} exceeds starting assets — structurally sustainable.')
    section_block('What You Are Doing Well', doing, GREEN)
    y -= 4

    opps = [f'With {inf*100:.1f}% inflation, income need grows to ~${spend*(1+inf)**proj_y:,.0f} by end of projection.',
            'Review tax brackets annually — Roth conversions may reduce lifetime tax burden.',
            'Inherited IRA 10-year rule requires careful annual planning to avoid bracket spikes.',
            'Annual portfolio rebalancing ensures assumed rate of return remains achievable.']
    section_block('Planning Opportunities', opps, NAVY)
    y -= 8

    # Key numbers 2-col grid
    c.setFillColor(NAVY); c.setFont('Helvetica-Bold',9); c.drawString(LM, y, 'Key Retirement Numbers'); y -= 14
    num_data = [
        ('Total Investable Assets', f'${total_inv:,.0f}', 'Starting Portfolio', f'${start_p:,.0f}'),
        ('Annual Income Goal', f'${spend:,.0f}', 'Ending Portfolio', f'${end_p:,.0f}'),
        ('Lifetime Social Security', f'${lt_ss:,.0f}', 'Projection Years', str(proj_y)),
        ('Lifetime Taxes (Est.)', f'${lt_tax:,.0f}', 'Rate of Return', f'{ror*100:.1f}%'),
        ('Lifetime Net Income', f'${lt_net:,.0f}', 'Inflation Rate', f'{inf*100:.1f}%'),
    ]
    cw1 = PW*0.28; cw2 = PW*0.22
    for i,(l1,v1,l2,v2) in enumerate(num_data):
        bg = WHITE if i%2==0 else GRAY_BG; rh = 18
        c.setFillColor(bg); c.rect(LM, y-rh, PW, rh, fill=1, stroke=0)
        c.setStrokeColor(GRAY_LN); c.setLineWidth(0.3); c.rect(LM, y-rh, PW, rh, fill=0, stroke=1)
        c.setFillColor(GRAY_MD); c.setFont('Helvetica',8.5); c.drawString(LM+6, y-rh+5, l1)
        c.setFillColor(NAVY); c.setFont('Helvetica-Bold',8.5); c.drawRightString(LM+cw1+cw2-6, y-rh+5, v1)
        c.setFillColor(GRAY_MD); c.setFont('Helvetica',8.5); c.drawString(LM+cw1+cw2+6, y-rh+5, l2)
        c.setFillColor(NAVY); c.setFont('Helvetica-Bold',8.5); c.drawRightString(LM+PW-6, y-rh+5, v2)
        y -= rh


def build_advisor_obs(c, pg, total_pg, client_data, projection, ctx):
    client = client_data['client']; summary = projection['summary']
    assump = client_data.get('assumptions',{}); assets = normalize_assets(client_data.get('assets',{}))
    ror = norm_pct(assump.get('rate_of_return',0.04)); inf = norm_pct(assump.get('inflation_pct',0.025))
    end_p = summary.get('ending_portfolio',0); start_p = summary.get('starting_portfolio',0)
    lt_tax = summary.get('lifetime_federal_tax',0); proj_y = summary.get('projection_years',0)
    spend = assump.get('income_need_annual', assump.get('annual_income_need',0))
    inh = assets.get('ira_inherited') or {}; notes, legacy = normalize_meta(client_data)

    draw_header(c, pg, total_pg, 'Advisor Observations', 'Income sustainability · tax planning · legacy', ctx['name'], ctx['date'], ctx['ss_info'])
    draw_bar(c, 'PERSONALIZED PLANNING CONSIDERATIONS — PREPARED BY MICHAEL J. EBERHARDT')
    draw_footer(c)

    y = CONTENT_Y
    def obs(title, text):
        nonlocal y
        c.setFillColor(NAVY); c.setFont('Helvetica-Bold',9); c.drawString(LM, y, title); y -= 3
        words = text.split(); line = ''; lines = []
        max_w = PW - 20
        for w in words:
            t = (line+' '+w).strip()
            if c.stringWidth(t,'Helvetica',8.5) < max_w: line = t
            else:
                if line: lines.append(line)
                line = w
        if line: lines.append(line)
        c.setFillColor(CHARCOAL); c.setFont('Helvetica',8.5)
        for ln in lines[:3]:
            y -= 13; c.drawString(LM, y, ln)
        y -= 10

    obs('Income Sustainability',
        f'Based on {ror*100:.1f}% annual return with {inf*100:.1f}% inflation, your portfolio is projected to grow from ${start_p:,.0f} to ${end_p:,.0f} over {proj_y} years. Your strategy draws fixed sources first — Social Security and fixed income — before touching investment accounts, significantly extending portfolio longevity.')
    obs('Tax Planning Observations',
        f'Estimated lifetime federal tax is ${lt_tax:,.0f}. Tax-efficient withdrawal sequencing — drawing taxable IRA funds during lower-income years — can meaningfully reduce this figure. Roth conversions in years where income falls below the 22% bracket deserve annual review. All projections assume 85% of Social Security is federally taxable.')
    if inh and isinstance(inh,dict) and inh.get('balance',0):
        bal=inh.get('balance',0); yr=inh.get('year_inherited',2020); dead=yr+10
        strat=inh.get('distribution_strategy','even').replace('_',' ').title()
        obs('Inherited IRA — 10-Year Rule Planning',
            f'You hold an inherited IRA with a current balance of ${bal:,.0f}, inherited in {yr}. Under the IRS 10-Year Rule, this account must be fully distributed by December 31, {dead}. Current strategy: {strat} distribution to spread tax impact. All distributions are included in taxable income. Review annually with your tax advisor.')
    obs('Legacy & Estate Planning',
        f'Your projected ending portfolio of ${end_p:,.0f} represents your legacy position at the end of the {proj_y}-year projection. Review estate plan, beneficiary designations, and trust structures annually to ensure they reflect your current wishes.' + (f' Client note: {legacy}' if legacy else ''))
    obs('Risk Management',
        f'The {ror*100:.1f}% return assumption is conservative relative to long-term market averages. Sequence-of-returns risk is the primary threat — a significant market decline in the first 5 years of retirement can permanently impair a portfolio even if markets recover. Your waterfall strategy mitigates this by drawing from stable fixed income sources first.')
    obs('Recommended Next Steps',
        '1. Schedule annual income review to confirm actual vs. projected performance.  2. Review inherited IRA distribution timing with CPA before each tax year end.  3. Confirm Social Security claiming strategy has not changed.  4. Update estate documents and beneficiary designations.  5. Review investment allocation annually.')
    if notes:
        y -= 4; c.setFillColor(GOLD_LT); c.rect(LM, y-30, PW, 30, fill=1, stroke=0)
        c.setFillColor(GOLD); c.rect(LM, y-30, 3, 30, fill=1, stroke=0)
        c.setFillColor(GOLD_DK); c.setFont('Helvetica-Bold',7.5); c.drawString(LM+10, y-12, 'Advisor Notes:')
        c.setFillColor(CHARCOAL); c.setFont('Helvetica',7.5); c.drawString(LM+100, y-12, notes[:120])


def build_snapshot(c, pg, total_pg, client_data, projection, ctx):
    client = client_data['client']; spouse = client_data.get('spouse')
    assump = client_data.get('assumptions',{}); assets = normalize_assets(client_data.get('assets',{}))
    emp_ret = (client_data.get('client',{}).get('retirement') or {}); retire_age = emp_ret.get('retirement_age','—')
    ror = norm_pct(assump.get('rate_of_return',0.04)); inf = norm_pct(assump.get('inflation_pct',0.025))
    spend = assump.get('income_need_annual', assump.get('annual_income_need',0))

    draw_header(c, pg, total_pg, 'Retirement Snapshot', 'Identity · asset inventory · planning horizons', ctx['name'], ctx['date'], ctx['ss_info'])
    draw_bar(c, 'CLIENT SNAPSHOT — AS OF ANALYSIS DATE', 'All values in today\'s dollars')
    draw_footer(c)

    y = CONTENT_Y; half = PW/2 - 10

    # Client info
    c.setFillColor(NAVY); c.setFont('Helvetica-Bold',8.5); c.drawString(LM, y, 'Client Information'); y -= 14
    ci_rows = [('Name', f"{client.get('first_name','')} {client.get('last_name','')}")
                ,('Date of Birth', f"{client.get('dob','')} (age {age_from_dob(client.get('dob',''))})")]
    if spouse:
        ci_rows += [('Spouse', f"{spouse.get('first_name','')} {spouse.get('last_name','')}"),
                    ('Spouse DOB', f"{spouse.get('dob','')} (age {age_from_dob(spouse.get('dob',''))})")]
    ci_rows += [('Filing Status', client.get('filing_status','').replace('_',' ').title()),
                ('State', client.get('state','—')),
                ('Target Retire Age', str(retire_age)),
                ('Annual Spending Need', f'${spend:,.0f}'),
                ('Rate of Return', f'{ror*100:.1f}%'),
                ('Inflation Rate', f'{inf*100:.1f}%')]
    y_ci = y
    for i,(lbl,val) in enumerate(ci_rows):
        bg = WHITE if i%2==0 else GRAY_BG; rh=17
        c.setFillColor(bg); c.rect(LM, y_ci-rh, half, rh, fill=1, stroke=0)
        c.setStrokeColor(GRAY_LN); c.setLineWidth(0.3); c.rect(LM, y_ci-rh, half, rh, fill=0, stroke=1)
        c.setFillColor(GRAY_MD); c.setFont('Helvetica',8); c.drawString(LM+6, y_ci-rh+4, lbl)
        c.setFillColor(BLACK); c.drawRightString(LM+half-6, y_ci-rh+4, str(val)[:30])
        y_ci -= rh

    # Asset inventory on right
    ax = LM + half + 10
    aw = half - 8
    c.setFillColor(NAVY); c.setFont('Helvetica-Bold',8.5); c.drawString(ax, y, 'Asset Inventory'); 
    y_ai = y - 14
    ai_rows = []
    inh = assets.get('ira_inherited') or {}
    if isinstance(inh,dict) and inh.get('balance',0): ai_rows.append(('Inherited IRA', f"${inh['balance']:,.0f}"))
    for k,lbl in [('client_ira','Client IRA/401k'),('spouse_ira','Spouse IRA/401k'),('brokerage','Taxable Brokerage'),('money_market','Money Market'),('cash','Cash & Savings'),('annuity_balance','Annuity'),('real_estate_equity','Real Estate Equity'),('other_client','Other Assets')]:
        v = assets.get(k,0) or 0
        if v > 0: ai_rows.append((lbl, f'${v:,.0f}'))
    total_inv = total_investable(assets); home = assets.get('home_value',0) or 0
    ai_rows.append(('Total Investable', f'${total_inv:,.0f}'))
    if home: ai_rows += [('Home (non-investable)', f'${home:,.0f}'),('Total Net Assets', f'${total_inv+home:,.0f}')]
    for i,(lbl,val) in enumerate(ai_rows):
        bg = WHITE if i%2==0 else GRAY_BG
        is_total = 'Total' in lbl; rh = 18
        c.setFillColor(bg); c.rect(ax, y_ai-rh, aw, rh, fill=1, stroke=0)
        if is_total:
            c.setStrokeColor(NAVY); c.setLineWidth(1); c.line(ax, y_ai, ax+aw, y_ai); c.setLineWidth(0.3)
        c.setStrokeColor(GRAY_LN); c.setLineWidth(0.3); c.rect(ax, y_ai-rh, aw, rh, fill=0, stroke=1)
        fn = 'Helvetica-Bold' if is_total else 'Helvetica'
        fc = NAVY if is_total else GRAY_MD
        c.setFillColor(fc); c.setFont(fn, 8); c.drawString(ax+6, y_ai-rh+4, lbl)
        c.setFillColor(NAVY if is_total else BLACK); c.setFont('Helvetica-Bold' if is_total else 'Helvetica', 8)
        c.drawRightString(ax+aw-6, y_ai-rh+4, val)
        y_ai -= rh


def build_income_tax(c, pg, total_pg, client_data, projection, ctx):
    client = client_data['client']; spouse = client_data.get('spouse')
    ss_data = normalize_ss(client_data); summary = projection['summary']
    cname = client.get('first_name','Client'); sname = spouse.get('first_name','Spouse') if spouse else 'Spouse'

    draw_header(c, pg, total_pg, 'Income & Tax Strategy', 'Social Security · pension · tax · lifetime summary', ctx['name'], ctx['date'], ctx['ss_info'])
    draw_bar(c, 'LIFETIME INCOME & TAX ANALYSIS')
    draw_footer(c)

    y = CONTENT_Y

    def status_lbl(st):
        return {'collecting':'Currently Collecting','will_file':'Will File at Age','not_started':'Not Started','none':'Not Applicable'}.get(st, st.replace('_',' ').title() if st else '—')

    c_st = ss_data.get('client_status',''); c_mo = ss_data.get('client_monthly',0) or 0; c_age = ss_data.get('client_file_age','')
    s_st = ss_data.get('spouse_status',''); s_mo = ss_data.get('spouse_monthly',0) or 0; s_age = ss_data.get('spouse_file_age','')
    lt_ss = summary.get('lifetime_ss',0)

    ss_rows = []
    if c_st and c_st!='none':
        ss_rows.append((f'{cname} Status', status_lbl(c_st)))
        if c_mo > 0: ss_rows.append((f'{cname} Monthly Benefit', f'${c_mo:,.0f} /mo'))
        if c_age: ss_rows.append((f'{cname} File Age', str(c_age)))
    if spouse and s_st and s_st!='none':
        ss_rows.append((f'{sname} Status', status_lbl(s_st)))
        if s_mo > 0: ss_rows.append((f'{sname} Monthly Benefit', f'${s_mo:,.0f} /mo'))
        if s_age: ss_rows.append((f'{sname} File Age', str(s_age)))
    comb = c_mo + s_mo
    if comb > 0: ss_rows.append(('Combined Monthly SS', f'${comb:,.0f} /mo'))
    ss_rows.append(('Lifetime SS (est.)', f'${lt_ss:,.0f}'))
    if not ss_rows: ss_rows = [('Social Security','Not applicable')]

    tax_rows = [('Lifetime Gross', f"${summary.get('lifetime_gross',0):,.0f}"),
                ('Lifetime Federal Tax', f"${summary.get('lifetime_federal_tax',0):,.0f}"),
                ('Lifetime State Tax', f"${summary.get('lifetime_state_tax',0):,.0f}"),
                ('Lifetime Net', f"${summary.get('lifetime_net',0):,.0f}")]
    port_rows = [('Starting Portfolio', f"${summary.get('starting_portfolio',0):,.0f}"),
                 ('Ending Portfolio', f"${summary.get('ending_portfolio',0):,.0f}"),
                 ('Projection Years', str(summary.get('projection_years',0)))]

    col1 = PW*0.34; col2 = PW*0.31; col3 = PW*0.35
    w1a = col1*0.62; w1b = col1*0.38; w2a = col2*0.62; w2b = col2*0.38; w3a = col3*0.58; w3b = col3*0.42

    y = draw_info_rows(c, LM, y, ss_rows, w1a, w1b, 'Social Security Plan')
    y_tax = CONTENT_Y; draw_info_rows(c, LM+col1, y_tax, tax_rows, w2a, w2b, 'Lifetime Tax Summary')
    draw_info_rows(c, LM+col1+col2, y_tax, port_rows, w3a, w3b, 'Portfolio Summary')

    notes, legacy = normalize_meta(client_data)
    if notes or legacy:
        min_y = min(y, CONTENT_Y - len(ss_rows)*18 - 14, CONTENT_Y - len(tax_rows)*18 - 14) - 10
        c.setFillColor(GOLD_LT); c.rect(LM, min_y-36, PW, 36, fill=1, stroke=0)
        c.setFillColor(GOLD); c.rect(LM, min_y-36, 3, 36, fill=1, stroke=0)
        c.setStrokeColor(GOLD); c.setLineWidth(0.3); c.rect(LM, min_y-36, PW, 36, fill=0, stroke=1)
        ly = min_y - 12
        if notes:
            c.setFillColor(GOLD_DK); c.setFont('Helvetica-Bold',7.5); c.drawString(LM+10, ly, 'Advisor Notes:')
            c.setFillColor(CHARCOAL); c.setFont('Helvetica',7.5); c.drawString(LM+100, ly, notes[:120]); ly -= 14
        if legacy:
            c.setFillColor(GOLD_DK); c.setFont('Helvetica-Bold',7.5); c.drawString(LM+10, ly, 'Legacy & Estate:')
            c.setFillColor(CHARCOAL); c.setFont('Helvetica',7.5); c.drawString(LM+100, ly, legacy[:120])


def build_income_projection(c, pg, total_pg, client_data, projection, ctx):
    client = client_data['client']; spouse = client_data.get('spouse')
    years = projection['years']; summary = projection['summary']; assump = client_data.get('assumptions',{})
    cname = client.get('first_name','Client'); sname = spouse.get('first_name','Spouse') if spouse else 'Spouse'
    ror = norm_pct(assump.get('rate_of_return',0.04)); inf = norm_pct(assump.get('inflation_pct',0.025))

    draw_header(c, pg, total_pg, 'Income Projection', 'Year-by-year SS · IRA · asset draw · spending need', ctx['name'], ctx['date'], ctx['ss_info'])
    display = [r for r in years if not(not r.get('client_alive',True) and not r.get('spouse_alive',True) and r.get('gross_income',0)==0)]
    draw_bar(c, f'PROJECTED ANNUAL INCOME — {len(display)} YEAR PROJECTION', f'LIFETIME GROSS ${summary['lifetime_gross']:,.0f}  |  NET ${summary['lifetime_net']:,.0f}')
    draw_footer(c)

    # Column layout
    cw = [w*PW for w in [0.075, 0.07, 0.07, 0.065, 0.07, 0.07, 0.09, 0.08, 0.085, 0.085, 0.10, 0.09]]
    aligns = ['L','R','R','R','R','R','R','R','R','R','R','R']
    headers = ['Year', f'{cname}\nSS', f'{sname}\nSS', 'Pension/\nOther', 'IRA/RMD\nDist.', 'Asset\nDraw', 'Gross\nIncome', 'Est.\nTaxes', 'Net\nIncome', 'Need', 'Surplus/\nGap', 'Reserves']
    # Use flat headers for canvas
    hdr_flat = ['Year', f'{cname} SS', f'{sname} SS', 'Pension/Other', 'IRA/RMD', 'Asset Draw', 'Gross Income', 'Est. Taxes', 'Net Income', 'Need', 'Surplus/Gap', 'Reserves']

    max_r = max_data_rows(has_note=False, extra_overhead=16)  # extra for footnote
    collapsed = smart_collapse(display, max_r)

    rows = []
    odd = True
    for r, is_jump in collapsed:
        c_ss = r.get('client_ss',0); s_ss = r.get('spouse_ss',0)
        fixed = r.get('fixed_income',0); ira_d = r.get('ira_distributions',0)
        adraw = r.get('brokerage_draw',0)+r.get('cash_draw',0)+r.get('real_estate_draw',0)
        gross = r.get('gross_income',0); taxes = r.get('total_tax',0)
        net   = r.get('net_income',0);  need  = r.get('spending_need',0)
        surp  = r.get('income_surplus',0) or 0; port = r.get('total_portfolio',0)
        ages  = f"{r['client_age']}/{r.get('spouse_age','')}" if r.get('spouse_age') else str(r['client_age'])
        bg = TEAL_JMP if is_jump else (WHITE if odd else GRAY_BG)
        surp_bg = GREEN_LT if surp>=0 else RED_LT
        surp_txt = fmt(surp) if surp>=0 else f'({fmt(abs(surp))})'
        surp_fg = GREEN if surp>=0 else RED
        cells = [
            (f"{r['year']}\n{ages}", GRAY_MD, False),
            (fmt(c_ss), NAVY, True), (fmt(s_ss), NAVY, True),
            (fmt(fixed), NAVY, True), (fmt(ira_d), BLUE, True),
            (fmt(adraw) if adraw else '—', TEAL, True),
            (fmt(gross), BLACK, False), (fmt(taxes), AMBER, True),
            (fmt(net), GREEN, True), (fmt(need), PURPLE, True),
            (surp_txt, surp_fg, True), (fmt(port), NAVY, True)
        ]
        top = TEAL if is_jump else None
        rows.append((cells, bg, top))
        odd = not odd

    # Add totals row
    rows.append(([
        ('Totals', BLACK, True),
        (fmt(summary['lifetime_ss']), NAVY, True), ('',BLACK,False),
        ('',BLACK,False), ('',BLACK,False), ('',BLACK,False),
        (fmt(summary['lifetime_gross']), BLACK, True),
        (fmt(summary['lifetime_federal_tax']+summary['lifetime_state_tax']), AMBER, True),
        (fmt(summary['lifetime_net']), GREEN, True),
        ('',BLACK,False), ('',BLACK,False),
        (fmt(summary['ending_portfolio']), NAVY, True)
    ], GRAY_BG, GRAY_LN))

    end_y = draw_table(c, CONTENT_Y, cw, aligns, hdr_flat, rows)

    # Footnote
    c.setFillColor(GRAY_MD); c.setFont('Helvetica',6.5)
    note = f'Assumptions: {ror*100:.1f}% growth, {inf*100:.1f}% inflation, SS COLA annually, RMDs at age 73, 85% SS taxable, 2024 brackets.'
    if any(j for _,_,j in rows[:-1] if j is not None and j!=GRAY_LN): note += ' Teal rows = 5-year interval summary.'
    c.drawString(LM, end_y-8, note)


def build_inherited_ira(c, pg, total_pg, client_data, projection, ctx):
    assets = normalize_assets(client_data.get('assets',{}))
    inh = assets.get('ira_inherited') or {}
    if not inh or not isinstance(inh,dict) or not inh.get('balance',0): return False

    start_bal = inh.get('balance',0); year_inh = inh.get('year_inherited',2020)
    must_by   = inh.get('must_distribute_by') or (year_inh+10)
    strategy  = inh.get('distribution_strategy','even')

    draw_header(c, pg, total_pg, 'Inherited IRA · 10-Year Rule', 'Distribution schedule · remaining balance · tax impact', ctx['name'], ctx['date'], ctx['ss_info'])
    draw_bar(c, 'INHERITED IRA MANDATORY DISTRIBUTION SCHEDULE')
    draw_footer(c)

    y = CONTENT_Y
    draw_kpi_row(c, y, [('Starting Balance',f'${start_bal:,.0f}',NAVY),('Year Inherited',str(year_inh),AMBER),('Must Distribute By',str(must_by),RED),('Strategy',strategy.replace('_',' ').title(),TEAL)])
    y -= 62

    ydata = [(r['year'],r.get('client_age',''),r.get('inherited_ira_dist',0),r.get('inherited_ira_balance',0))
             for r in projection['years'] if r.get('inherited_ira_dist',0)>0 or r.get('inherited_ira_balance',0)>0]
    cw_t = [PW*0.58*r for r in [0.16,0.14,0.32,0.24,0.14]]
    cw_r = [PW*0.42]
    hdrs = ['Year','Age','Distribution','Remaining Balance','Cumulative Dist.']
    alns = ['L','C','R','R','R']
    cum = 0; rows = []
    for yr,age,dist,bal in ydata:
        cum += dist; odd_bg = WHITE if len(rows)%2==0 else GRAY_BG
        rows.append(([(str(yr),CHARCOAL,False),(str(age),CHARCOAL,False),(fmt(dist),AMBER,True),(fmt(bal),NAVY,True),(fmt(cum),BLACK,False)],odd_bg,None))
    draw_table(c, y, cw_t, alns, hdrs, rows)

    # Rule box on right
    rx = LM + PW*0.60; ry = y; rw = PW*0.38; rh = len(rows)*ROW_H + HDR_ROW_H + 10
    c.setFillColor(NAVY_LT); c.rect(rx, ry-rh, rw, rh, fill=1, stroke=0)
    c.setFillColor(NAVY); c.rect(rx, ry-rh, 3, rh, fill=1, stroke=0)
    rule_txt = ['10-Year Rule: Non-spouse beneficiaries who inherited IRAs after','Jan 1, 2020 must fully distribute by Dec 31 of the 10th year.','Distributions are taxed as ordinary income.','',f'Strategy: {strategy.replace("_"," ").title()} distribution spreads','withdrawals to minimize annual tax impact.','','Tax Impact: All distributions included in gross income for','federal and state tax calculations throughout this report.']
    c.setFillColor(NAVY_MD); c.setFont('Helvetica',7.5)
    for i,line in enumerate(rule_txt):
        c.drawString(rx+10, ry-14-i*12, line)
    return True

NAVY_MD = colors.HexColor('#1A3A5C')
NAVY_LT = colors.HexColor('#E8EEF5')

def build_retirement_years(c, pg, total_pg, client_data, projection, ctx):
    client = client_data['client']; spouse = client_data.get('spouse')
    years  = projection['years']; summary = projection['summary']; assump = client_data.get('assumptions',{})
    cname = client.get('first_name','Client'); sname = spouse.get('first_name','Spouse') if spouse else 'Spouse'
    need_base = assump.get('income_need_annual', assump.get('annual_income_need',80000))
    inf = norm_pct(assump.get('inflation_pct',0.025))

    draw_header(c, pg, total_pg, 'Retirement Years', 'SS · pension · IRA · taxes · need · surplus or gap', ctx['name'], ctx['date'], ctx['ss_info'])
    draw_bar(c, f'RETIREMENT YEARS  |  ${need_base:,.0f} base · {inf*100:.1f}% inflation', 'RMDs DRAWN FIRST — EXCESS SPLIT EVENLY')
    draw_footer(c)

    note_txt = 'In retirement, income flows from fixed sources and IRA distributions. RMDs are taken first (mandatory at 73). Gap filled by splitting evenly between client and spouse IRA. Taxes estimated on gross income including taxable SS and IRA distributions.'
    y = draw_note(c, CONTENT_Y, note_txt)
    y -= 4

    ret = [r for r in years if r.get('phase','') not in ('working','transitioning')
           and not(not r.get('client_alive',True) and not r.get('spouse_alive',True) and r.get('gross_income',0)==0)]
    # first 20 annual + every 5 after
    disp0 = [(r,False) for r in ret[:20]] + [(r,True) for i,r in enumerate(ret[20:]) if i%5==0]
    disp0_rows = [r for r,_ in disp0]
    max_r = max_data_rows(has_note=True, has_sboxes=True, extra_overhead=12)
    collapsed = smart_collapse(disp0_rows, max_r)
    # merge is_5 flags
    is5_map = {id(r): f for r,f in disp0}
    final = [(r, is5_map.get(id(r),False) or is_j) for r,is_j in collapsed]

    cw = [w*PW for w in [0.075,0.065,0.065,0.055,0.065,0.065,0.065,0.065,0.065,0.08,0.075,0.065,0.09]]
    aligns = ['L','R','R','R','R','R','R','R','R','R','R','R','R']
    hdr_flat = ['Year/Ages',f'{cname} SS',f'{sname} SS','Pension/Other',f'{cname} IRA',f'{sname} IRA','Gross','Fed Tax','After Tax',f'Need {inf*100:.1f}%','+surp/-gap','Net Mo.','All Accts']

    rows = []; odd = True
    for r,is_teal in final:
        c_ss=r.get('client_ss',0); s_ss=r.get('spouse_ss',0); fixed=r.get('fixed_income',0)
        c_ira=r.get('client_rmd_taken',0)+r.get('client_ira_extra',0)
        s_ira=r.get('spouse_rmd_taken',0)+r.get('spouse_ira_extra',0)
        gross=r.get('gross_income',0); taxes=r.get('total_tax',0); net=r.get('net_income',0)
        need=r.get('spending_need',0); surp=r.get('income_surplus',0) or 0
        mo=r.get('net_monthly',0); port=r.get('total_portfolio',0)
        ages=f"{r['client_age']}/{r.get('spouse_age','')}" if r.get('spouse_age') else str(r['client_age'])
        surp_txt = fmt(surp) if surp>=0 else f'({fmt(abs(surp))})'
        surp_fg = GREEN if surp>=0 else RED
        bg = TEAL_JMP if is_teal else (WHITE if odd else GRAY_BG)
        top = TEAL if is_teal else None
        rows.append(([
            (f"{r['year']}\n{ages}",GRAY_MD,False),
            (fmt(c_ss),NAVY,True),(fmt(s_ss),NAVY,True),(fmt(fixed),NAVY,True),
            (fmt(c_ira),BLUE,True),(fmt(s_ira),BLUE,True),
            (fmt(gross),BLACK,False),(fmt(taxes),AMBER,True),(fmt(net),GREEN,True),
            (fmt(need),PURPLE,True),(surp_txt,surp_fg,True),(fmt(mo),BLACK,False),(fmt(port),NAVY,True)
        ], bg, top))
        odd = not odd

    end_y = draw_table(c, y, cw, aligns, hdr_flat, rows)
    draw_sboxes(c, end_y-6, [
        (NAVY,'Lifetime Gross',f"${summary.get('lifetime_gross',0):,.0f} total gross income."),
        (AMBER,'Lifetime Taxes',f"${summary.get('lifetime_federal_tax',0):,.0f} fed + ${summary.get('lifetime_state_tax',0):,.0f} state."),
        (GREEN,'Lifetime Net',f"${summary.get('lifetime_net',0):,.0f} net after all taxes."),
        (TEAL,f"Portfolio: ${summary.get('ending_portfolio',0):,.0f}",f"${summary.get('starting_portfolio',0):,.0f} → ${summary.get('ending_portfolio',0):,.0f}."),
    ])


def build_waterfall(c, pg, total_pg, client_data, projection, ctx):
    client = client_data['client']; spouse = client_data.get('spouse')
    years = projection['years']; assump = client_data.get('assumptions',{})
    cname = client.get('first_name','Client'); sname = spouse.get('first_name','Spouse') if spouse else 'Spouse'
    need_base = assump.get('income_need_annual', assump.get('annual_income_need',80000))
    inf = norm_pct(assump.get('inflation_pct',0.025))
    last_need = max((r.get('spending_need',0) for r in years), default=0)

    draw_header(c, pg, total_pg, 'Withdrawal Waterfall', 'Which account funds the gap · in what order · how much', ctx['name'], ctx['date'], ctx['ss_info'])
    draw_bar(c, f'INCOME NEED: ${need_base:,.0f} BASE  |  {inf*100:.1f}% INFLATION  |  GROWS TO ${last_need:,.0f}', 'Employment → SS+Fixed → IRA RMDs → Investments → Cash')
    draw_footer(c)

    note_txt = 'Traces which account fills the income gap each year. SS and fixed income take over at retirement. IRA RMDs fill gap first (mandatory at 73). Investment account drawn only when RMDs fall short. Portfolio continues growing even with annual draws.'
    y = draw_note(c, CONTENT_Y, note_txt)
    y -= 4

    # Build display rows — all live years
    live = [r for r in years if not(not r.get('client_alive',True) and not r.get('spouse_alive',True) and r.get('gross_income',0)==0)]
    max_r = max_data_rows(has_note=True, has_sboxes=True, extra_overhead=12)
    # add phase rows count to overhead
    phases = set(); phase_count = 0
    for r in live:
        if r.get('phase','') not in phases: phases.add(r.get('phase','')); phase_count += 1
    max_r = max(1, max_r - phase_count)
    collapsed = smart_collapse(live, max_r)

    cw = [w*PW for w in [0.07,0.055,0.055,0.055,0.065,0.065,0.065,0.065,0.065,0.065,0.065,0.065,0.065,0.07]]
    aligns = ['L','R','R','R','R','R','R','R','R','R','R','R','R','R']
    hdr_flat = ['Year/Ages',f'{cname} sal.',f'{sname} sal.','Total emp.','SS','Pension','All fixed','Annual need','Port. gap',f'{cname} IRA',f'{sname} IRA','Invest.','Cash','From portfolio']

    rows = []; last_phase = None; odd = True
    for r, is_jump in collapsed:
        phase = r.get('phase','')
        if phase != last_phase:
            last_phase = phase
            label = {'working':'BOTH WORKING','transitioning':'TRANSITIONING'}.get(phase,'FULLY RETIRED')
            ph_bg = TEAL if 'RETIRED' in label else NAVY_MD
            rows.append(([
                (f'— {label} —',WHITE,True)] + [('',WHITE,False)]*13,
                ph_bg, None))
        c_sal=r.get('client_salary',0); s_sal=r.get('spouse_salary',0)
        ss=r.get('client_ss',0)+r.get('spouse_ss',0); fixed=r.get('fixed_income',0); all_f=ss+fixed
        need=r.get('spending_need',0); surp=r.get('income_surplus',0) or 0
        c_ira=r.get('client_rmd_taken',0)+r.get('client_ira_extra',0)
        s_ira=r.get('spouse_rmd_taken',0)+r.get('spouse_ira_extra',0)
        invest=r.get('brokerage_draw',0); cash=r.get('cash_draw',0)
        total_drawn=c_ira+s_ira+invest+cash; covered=surp>=0 and total_drawn==0
        gap_txt = 'Covered ✓' if covered else fmt(abs(surp)); gap_fg = GREEN if covered else RED
        ages=f"{r['client_age']}/{r.get('spouse_age','')}" if r.get('spouse_age') else str(r['client_age'])
        bg = TEAL_JMP if is_jump else (WHITE if odd else GRAY_BG)
        top = TEAL if is_jump else None
        rows.append(([
            (f"{r['year']}\n{ages}",GRAY_MD,False),
            (fmt(c_sal),TEAL,True),(fmt(s_sal),TEAL,True),(fmt(c_sal+s_sal),TEAL,True),
            (fmt(ss),NAVY,True),(fmt(fixed),NAVY,True),(fmt(all_f),BLACK,True),
            (fmt(need),PURPLE,True),(gap_txt,gap_fg,True),
            (fmt(c_ira),BLUE,True),(fmt(s_ira),BLUE,True),
            (fmt(invest),GREEN,True),(fmt(cash),GREEN,True),(fmt(total_drawn),BLACK,True)
        ], bg, top))
        odd = not odd

    end_y = draw_table(c, y, cw, aligns, hdr_flat, rows)

    # Growth summary
    sp = projection['summary'].get('starting_portfolio',0); ep = projection['summary'].get('ending_portfolio',0)
    draw_sboxes(c, end_y-6, [
        (NAVY,'Starting Portfolio',f'${sp:,.0f}'),
        (GREEN,'Ending Portfolio',f'${ep:,.0f}'),
        (TEAL,'Total Growth',f'${ep-sp:,.0f}'),
        (GOLD,'Growth %',f'{(ep-sp)/sp*100:.1f}%' if sp else '—'),
    ])


def build_working_years(c, pg, total_pg, client_data, projection, ctx):
    years = projection['years']; working = [r for r in years if r.get('client_salary',0)+r.get('spouse_salary',0)>0]
    if not working: return False
    client=client_data['client']; spouse=client_data.get('spouse'); assump=client_data.get('assumptions',{})
    need_base=assump.get('income_need_annual',assump.get('annual_income_need',80000))
    inf=norm_pct(assump.get('inflation_pct',0.025))
    cname=client.get('first_name','Client'); sname=spouse.get('first_name','Spouse') if spouse else 'Spouse'

    draw_header(c, pg, total_pg, 'Working Years', 'Salary · 401k · taxes · surplus — while employed', ctx['name'], ctx['date'], ctx['ss_info'])
    draw_bar(c, f'WORKING YEARS  |  ${need_base:,.0f} income need · {inf*100:.1f}% inflation', 'EMPLOYMENT INCOME COVERS ALL SPENDING — PORTFOLIO UNTOUCHED', bg=TEAL)
    draw_footer(c)

    note_txt = 'During working years employment income covers the spending need entirely. 401k contributions reduce taxable income and build retirement accounts. Every dollar saved now directly reduces the portfolio draw required in retirement.'
    y = draw_note(c, CONTENT_Y, note_txt); y -= 4

    cw = [w*PW for w in [0.09,0.09,0.09,0.09,0.09,0.09,0.09,0.09,0.09,0.09,0.10]]
    aligns = ['L','R','R','R','R','R','R','R','R','R','R']
    hdr_flat = ['Year/Ages',f'{cname} Salary',f'{sname} Salary',f'{cname} 401k',f'{sname} 401k','Taxable Income','Est. Taxes','Income Need','Net Surplus','To Reserves','Cumul. Reserves']

    max_r = max_data_rows(has_note=True)
    collapsed = smart_collapse(working, max_r)
    rows = []; odd = True
    for r, is_jump in collapsed:
        c_s=r.get('client_salary',0); s_s=r.get('spouse_salary',0)
        c_4=r.get('client_contrib_trad',0)+r.get('client_contrib_roth',0)
        s_4=r.get('spouse_contrib_trad',0)+r.get('spouse_contrib_roth',0)
        tax=r.get('total_tax',round((c_s+s_s)*0.18,0)); need=r.get('spending_need',0)
        surp=c_s+s_s-tax-need; cum=r.get('total_portfolio',0)
        ages=f"{r['client_age']}/{r.get('spouse_age','')}" if r.get('spouse_age') else str(r['client_age'])
        bg = TEAL_JMP if is_jump else (WHITE if odd else GRAY_BG)
        rows.append(([
            (f"{r['year']}\n{ages}",GRAY_MD,False),
            (fmt(c_s),TEAL,True),(fmt(s_s),TEAL,True),(fmt(c_4),PURPLE,True),(fmt(s_4),PURPLE,True),
            (fmt(c_s+s_s-c_4-s_4),BLACK,False),(fmt(tax),AMBER,True),(fmt(need),PURPLE,True),
            (fmt(surp),GREEN if surp>=0 else RED,True),(fmt(surp) if surp>0 else '—',GREEN,False),(fmt(cum),NAVY,True)
        ], bg, TEAL if is_jump else None))
        odd = not odd

    draw_table(c, y, cw, aligns, hdr_flat, rows)
    return True


def build_account_balances(c, pg, total_pg, client_data, projection, ctx):
    """Draws IRA accounts pair page. Returns next pg."""
    client=client_data['client']; spouse=client_data.get('spouse'); years=projection['years']
    summary=projection['summary']; cname=client.get('first_name','Client'); sname=spouse.get('first_name','Spouse') if spouse else 'Spouse'
    sp=summary.get('starting_portfolio',0); ep=summary.get('ending_portfolio',0)

    def get_acct(open_k,earn_k,draw_k,close_k,contrib_k=None):
        data = []
        for r in years:
            if not r.get('client_alive',True) and not r.get('spouse_alive',True): continue
            o=r.get(open_k,0) or 0; e=r.get(earn_k,0) or 0; d=r.get(draw_k,0) or 0; cl=r.get(close_k,0) or 0
            cb=r.get(contrib_k,0) or 0 if contrib_k else 0
            if o or e or d or cl or cb: data.append((r['year'],o,cb,e,d,cl))
        while data and all(v==0 for v in data[-1][1:]): data.pop()
        return data

    c_ira = get_acct('client_ira_open','client_ira_earn','client_ira_draw','client_ira_close','client_ira_contrib')
    s_ira = get_acct('spouse_ira_open','spouse_ira_earn','spouse_ira_draw','spouse_ira_close','spouse_ira_contrib')
    brok  = get_acct('brokerage_open','brokerage_earn','brokerage_draw','brokerage_close')
    cash  = get_acct('cash_open','cash_earn','cash_draw','cash_close')

    MAX_R = max_data_rows(has_note=False, extra_overhead=50)  # 50 for two mini-table headers

    def mini_table(c, start_x, start_y, title, color, data, half_w):
        cw = [half_w*r for r in [0.17,0.17,0.14,0.17,0.17,0.18]]
        aligns = ['L','R','R','R','R','R']
        hdrs = ['Year','Opening','Contrib.','Earn.','Drawn','Closing']
        # Title bar
        c.setFillColor(color); c.rect(start_x, start_y-16, half_w, 16, fill=1, stroke=0)
        c.setFillColor(WHITE); c.setFont('Helvetica-Bold',8); c.drawString(start_x+6, start_y-12, title)
        if not data:
            c.setFillColor(GRAY_BG); c.rect(start_x, start_y-16-24, half_w, 24, fill=1, stroke=0)
            c.setStrokeColor(GRAY_LN); c.setLineWidth(0.3); c.rect(start_x, start_y-40, half_w, 40, fill=0, stroke=1)
            c.setFillColor(GRAY_MD); c.setFont('Helvetica',8); c.drawCentredString(start_x+half_w/2, start_y-32, 'No balance reported for this account.')
            return start_y - 40
        # Header row
        xs = [start_x]
        for w in cw[:-1]: xs.append(xs[-1]+w)
        ty = start_y - 16
        for i,(hdr,x,w) in enumerate(zip(hdrs,xs,cw)):
            c.setFillColor(colors.HexColor('#00000020')); c.rect(x, ty-HDR_ROW_H, w, HDR_ROW_H, fill=1, stroke=0)
            c.setFillColor(WHITE); c.setFont('Helvetica-Bold',7); c.drawCentredString(x+w/2, ty-HDR_ROW_H+5, hdr)
        ty -= HDR_ROW_H
        # Data rows — limit to MAX_R
        for i,(yr,opn,contrib,earn,draw,cl) in enumerate(data[:MAX_R]):
            bg = WHITE if i%2==0 else GRAY_BG; rh = ROW_H
            c.setFillColor(bg); c.rect(start_x, ty-rh, half_w, rh, fill=1, stroke=0)
            c.setStrokeColor(GRAY_LN); c.setLineWidth(0.2); c.line(start_x, ty-rh, start_x+half_w, ty-rh)
            vals = [(str(yr),GRAY_MD,False),(fmt(opn,False),CHARCOAL,False),(fmt(contrib,False) if contrib else '—',TEAL,True),(fmt(earn,False),GREEN,False),(f'({fmt(draw,False)})' if draw else '—',RED,True),(fmt(cl,False),NAVY,True)]
            for (txt,fg,bold),(x,w) in zip(vals,zip(xs,cw)):
                fn='Helvetica-Bold' if bold else 'Helvetica'; c.setFont(fn,7.5); c.setFillColor(fg)
                if vals.index((txt,fg,bold))==0: c.drawString(x+4, ty-rh+4, txt[:8])
                else: c.drawRightString(x+w-3, ty-rh+4, txt[:12])
            ty -= rh
        c.setStrokeColor(GRAY_LN); c.setLineWidth(0.3); c.rect(start_x, ty, half_w, start_y-16-ty, fill=0, stroke=1)
        return ty

    half = PW/2 - 4

    # Page 1: IRA accounts
    draw_header(c, pg, total_pg, 'Account Balances & Drawdown', 'IRA Accounts — growth · contributions · withdrawals', ctx['name'], ctx['date'], ctx['ss_info'])
    draw_bar(c, f'IRA ACCOUNTS  |  ALL ACCOUNTS AT ASSUMED RATE OF RETURN', f'PORTFOLIO: ${sp:,.0f} → ${ep:,.0f}')
    draw_footer(c)
    mini_table(c, LM, CONTENT_Y, f"{cname}'s IRA / 401k", NAVY, c_ira, half)
    mini_table(c, LM+half+8, CONTENT_Y, f"{sname}'s IRA", TEAL, s_ira, half)

    c.showPage(); pg += 1

    # Page 2: Investment accounts
    draw_header(c, pg, total_pg, 'Account Balances & Drawdown', 'Investment & Cash Accounts — growth · withdrawals', ctx['name'], ctx['date'], ctx['ss_info'])
    draw_bar(c, f'INVESTMENT & CASH ACCOUNTS  |  ASSUMED RATE OF RETURN', f'PORTFOLIO: ${sp:,.0f} → ${ep:,.0f}')
    draw_footer(c)
    mini_table(c, LM, CONTENT_Y, 'Joint Investments', GREEN, brok, half)
    mini_table(c, LM+half+8, CONTENT_Y, 'Cash & Reserves', AMBER, cash, half)

    c.showPage(); pg += 1
    return pg


def build_portfolio_summary(c, pg, total_pg, client_data, projection, ctx):
    years = projection['years']; summary = projection['summary']
    client=client_data['client']; spouse=client_data.get('spouse')
    cname=client.get('first_name','Client'); sname=spouse.get('first_name','Spouse') if spouse else 'Spouse'
    sp=summary.get('starting_portfolio',0); ep=summary.get('ending_portfolio',0)

    draw_header(c, pg, total_pg, 'Combined Portfolio Summary', 'All accounts by year — annual then 5-year intervals', ctx['name'], ctx['date'], ctx['ss_info'])
    draw_bar(c, 'COMBINED PORTFOLIO — ALL ACCOUNTS BY YEAR', f'PORTFOLIO: ${sp:,.0f} → ${ep:,.0f}')
    draw_footer(c)

    live = [r for r in years if r.get('client_alive',True) or r.get('spouse_alive',True)]
    max_r = max_data_rows(has_note=False, extra_overhead=14)
    collapsed = smart_collapse(live, max_r)

    cw = [w*PW for w in [0.07,0.09,0.09,0.10,0.09,0.09,0.08,0.14,0.10]]
    aligns = ['L','R','R','R','R','R','R','R','R']
    hdr_flat = ['Year',f'{cname}\'s IRA',f'{sname}\'s IRA','Brokerage','Cash & Resv.','Inh. IRA','Other','Combined Portfolio','Net Monthly']

    rows = []; odd = True; crossed = set()
    for r, is_jump in collapsed:
        port = r.get('total_portfolio',0); mo = r.get('net_monthly',0)
        is_ms = False
        for thresh,lbl in [(1e6,'1M'),(2e6,'2M'),(3e6,'3M'),(5e6,'5M')]:
            if lbl not in crossed and port>=thresh: is_ms=True; crossed.add(lbl)
        bg = TEAL_JMP if is_jump else (GOLD_LT if is_ms else (WHITE if odd else GRAY_BG))
        top = TEAL if is_jump else None
        rows.append(([
            (str(r['year']),CHARCOAL,False),
            (fmt(r.get('client_ira_close',0)),BLACK,False),
            (fmt(r.get('spouse_ira_close',0)),BLACK,False),
            (fmt(r.get('brokerage_close',0)),BLACK,False),
            (fmt(r.get('cash_close',0)),BLACK,False),
            (fmt(r.get('inherited_ira_close',0) or r.get('inherited_ira_balance',0)),BLACK,False),
            (fmt(r.get('other_close',0)),BLACK,False),
            (fmt(port),NAVY,True),(fmt(mo),BLACK,False)
        ], bg, top))
        odd = not odd

    end_y = draw_table(c, CONTENT_Y, cw, aligns, hdr_flat, rows)
    c.setFillColor(GRAY_MD); c.setFont('Helvetica',6.5)
    note = 'Annual detail shown first. Teal rows = 5-year interval summary. Gold rows = portfolio milestone crossings.' if any(is_jump for _,_,top in rows if top is not None and top==TEAL) else 'All years shown. Gold rows = portfolio milestone crossings.'
    c.drawString(LM, end_y-8, note)


# ══════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════
def generate_pdf(client_data: dict, projection: dict) -> bytes:
    """Generate complete static-page PDF. Returns bytes."""
    buf = io.BytesIO()

    client = client_data['client']; spouse = client_data.get('spouse')
    years  = projection['years']

    cname = f"{client.get('first_name','')} {client.get('last_name','')}"
    sname = f"& {spouse.get('first_name','')} {spouse.get('last_name','')}" if spouse else ''
    full_name = f'{cname} {sname}'.strip()

    ss_data = normalize_ss(client_data)
    c_st = ss_data.get('client_status',''); c_fa = ss_data.get('client_file_age','')
    s_st = ss_data.get('spouse_status',''); s_fa = ss_data.get('spouse_file_age','')

    def ss_lbl(status, name, fa):
        if status=='collecting': return f'{name} SS collecting'
        if status=='will_file' and fa: return f'{name} files SS @ {fa}'
        if status=='none': return f'{name} no SS'
        return f'{name} SS {status}'

    ss_info = ss_lbl(c_st, client.get('first_name','Client'), c_fa)
    if spouse: ss_info += '  |  ' + ss_lbl(s_st, spouse.get('first_name','Spouse'), s_fa)

    report_date = projection.get('report_date','') or _date.today().strftime('%Y-%m-%d')

    assets_norm = normalize_assets(client_data.get('assets',{}))
    inh_check   = assets_norm.get('ira_inherited') or {}
    has_inh_ira = bool(isinstance(inh_check,dict) and inh_check.get('balance',0))
    has_working = any(r.get('client_salary',0)+r.get('spouse_salary',0)>0 for r in years)

    # Fixed page count: cover + 4 text pages + 6 data pages + 0/1 inh + 0/1 working
    total_pages = 12 + (1 if has_inh_ira else 0) + (1 if has_working else 0)

    ctx = {'name': full_name, 'date': report_date, 'ss_info': ss_info}

    c = rl_canvas.Canvas(buf, pagesize=landscape(letter))

    # Page 1 — Cover
    build_cover(c, client_data, projection)
    c.showPage()

    pg = 2

    # Page 2 — Executive Summary
    build_exec_summary(c, pg, total_pages, client_data, projection, ctx); pg += 1; c.showPage()

    # Page 3 — Advisor Observations
    build_advisor_obs(c, pg, total_pages, client_data, projection, ctx); pg += 1; c.showPage()

    # Page 4 — Retirement Snapshot
    build_snapshot(c, pg, total_pages, client_data, projection, ctx); pg += 1; c.showPage()

    # Page 5 — Income & Tax Strategy
    build_income_tax(c, pg, total_pages, client_data, projection, ctx); pg += 1; c.showPage()

    # Page 6 — Income Projection
    build_income_projection(c, pg, total_pages, client_data, projection, ctx); pg += 1; c.showPage()

    # Page 7 (optional) — Inherited IRA
    if has_inh_ira:
        build_inherited_ira(c, pg, total_pages, client_data, projection, ctx); pg += 1; c.showPage()

    # Page 7/8 — Retirement Years
    build_retirement_years(c, pg, total_pages, client_data, projection, ctx); pg += 1; c.showPage()

    # Page 8/9 — Waterfall
    build_waterfall(c, pg, total_pages, client_data, projection, ctx); pg += 1; c.showPage()

    # Page 9/10 (optional) — Working Years
    if has_working:
        build_working_years(c, pg, total_pages, client_data, projection, ctx); pg += 1; c.showPage()

    # Page 10/11 + 11/12 — Account Balances (2 pages)
    pg = build_account_balances(c, pg, total_pages, client_data, projection, ctx)

    # Page 12/13 — Combined Portfolio
    build_portfolio_summary(c, pg, total_pages, client_data, projection, ctx); c.showPage()

    c.save()
    return buf.getvalue()
