"""
PDF Report Generation Service — Clavra ProdPilot™
Generates branded, professional PDF reports for each data domain.
"""
from __future__ import annotations

import io
import os
from datetime import datetime
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table,
                                 TableStyle)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import Inventory
from app.models.production import ProductionOrder
from app.models.production_line import ProductionLine
from app.models.quality import QualityReport
from app.models.shipment import Shipment

# ── Font registration ──────────────────────────────────────────────────────────
_FONTS_OK = False

def _init_fonts():
    global _FONTS_OK
    if _FONTS_OK:
        return
    try:
        fd = r"C:\Windows\Fonts"
        pdfmetrics.registerFont(TTFont("Ar",  os.path.join(fd, "arial.ttf")))
        pdfmetrics.registerFont(TTFont("ArB", os.path.join(fd, "arialbd.ttf")))
        pdfmetrics.registerFont(TTFont("ArI", os.path.join(fd, "ariali.ttf")))
        pdfmetrics.registerFont(TTFont("CrN", os.path.join(fd, "cour.ttf")))
        pdfmetrics.registerFontFamily("Ar", normal="Ar", bold="ArB", italic="ArI")
        _FONTS_OK = True
    except Exception:
        pass  # falls back to built-in Helvetica

_init_fonts()

def _f(bold: bool = False) -> str:
    if _FONTS_OK:
        return "ArB" if bold else "Ar"
    return "Helvetica-Bold" if bold else "Helvetica"

# ── Color palette ──────────────────────────────────────────────────────────────
NAVY  = colors.HexColor("#1B3A6B")
TEAL  = colors.HexColor("#0D7377")
LGREY = colors.HexColor("#CCCCCC")
DGREY = colors.HexColor("#444444")
MGREY = colors.HexColor("#888888")
ROW2  = colors.HexColor("#F5F7FA")
LNY   = colors.HexColor("#D6E4F0")
WHITE = colors.white
BLACK = colors.black

# Status → colour mapping for text cells
_SC = {
    "Pending":      colors.HexColor("#888888"),
    "Cutting":      colors.HexColor("#3B82F6"),
    "Sewing":       colors.HexColor("#8B5CF6"),
    "Finishing":    colors.HexColor("#F59E0B"),
    "QC":           colors.HexColor("#EC4899"),
    "Packed":       colors.HexColor("#10B981"),
    "Shipped":      colors.HexColor("#0D7377"),
    "Completed":    colors.HexColor("#10B981"),
    "Cancelled":    colors.HexColor("#EF4444"),
    "In Transit":   colors.HexColor("#3B82F6"),
    "Delivered":    colors.HexColor("#10B981"),
    "Delayed":      colors.HexColor("#EF4444"),
    "In Stock":     colors.HexColor("#10B981"),
    "Low Stock":    colors.HexColor("#F59E0B"),
    "Out of Stock": colors.HexColor("#EF4444"),
    "Active":       colors.HexColor("#10B981"),
    "Running":      colors.HexColor("#10B981"),
    "Idle":         colors.HexColor("#888888"),
    "Maintenance":  colors.HexColor("#F59E0B"),
    "critical":     colors.HexColor("#EF4444"),
    "major":        colors.HexColor("#F59E0B"),
    "minor":        colors.HexColor("#3B82F6"),
}

# ── Paragraph style helpers ────────────────────────────────────────────────────
PW, PH = A4
MG = 1.5 * cm
CW = PW - 2 * MG  # ≈ 510 pts

def _s(name, **kw) -> ParagraphStyle:
    return ParagraphStyle(name, **kw)

def _p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(str(text), style)

def _sp(h: float = 0.3) -> Spacer:
    return Spacer(1, h * cm)

_REP_TITLE  = _s("rt",  fontName=_f(True),  fontSize=18, textColor=NAVY,  spaceAfter=2)
_REP_SUB    = _s("rs",  fontName=_f(False), fontSize=8.5,textColor=MGREY, spaceAfter=10)
_TH         = _s("th",  fontName=_f(True),  fontSize=9,  textColor=WHITE, leading=12)
_TD         = _s("td",  fontName=_f(False), fontSize=8.5,textColor=BLACK, leading=12)
_KPI_LBL    = _s("kl",  fontName=_f(False), fontSize=8,  textColor=MGREY, alignment=TA_CENTER)
_KPI_VAL    = _s("kv",  fontName=_f(True),  fontSize=18, textColor=NAVY,  alignment=TA_CENTER)
_KPI_SUB    = _s("ks",  fontName=_f(False), fontSize=7.5,textColor=MGREY, alignment=TA_CENTER)
_SEC_HDR    = _s("sh",  fontName=_f(True),  fontSize=10, textColor=TEAL,  spaceBefore=10, spaceAfter=4)

BASE_TS = [
    ("GRID",          (0, 0), (-1, -1), 0.4, LGREY),
    ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ("LEFTPADDING",   (0, 0), (-1, -1), 6),
    ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
    ("TOPPADDING",    (0, 0), (-1,  0), 6),
    ("BOTTOMPADDING", (0, 0), (-1,  0), 6),
    ("TOPPADDING",    (0, 1), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
    ("BACKGROUND",    (0, 0), (-1,  0), NAVY),
    ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, ROW2]),
]

def _status_cell(text: str) -> Paragraph:
    c = _SC.get(str(text), BLACK)
    st = _s(f"sc_{text}", fontName=_f(True), fontSize=8.5, textColor=c, leading=12)
    return Paragraph(str(text), st)

def _pct_bar(pct: int) -> str:
    pct = min(max(int(pct or 0), 0), 100)
    return f"{pct}%"

# ── Header / Footer canvas callback ───────────────────────────────────────────
def _page_deco(canvas, doc, title: str, generated: str):
    canvas.saveState()
    # Top rule + header text
    canvas.setStrokeColor(NAVY)
    canvas.setLineWidth(1.5)
    canvas.line(MG, PH - MG + 2, PW - MG, PH - MG + 2)
    canvas.setFont(_f(True), 8)
    canvas.setFillColor(NAVY)
    canvas.drawString(MG, PH - MG + 6, f"Clavra ProdPilot™  |  {title}")
    canvas.setFont(_f(False), 7.5)
    canvas.setFillColor(MGREY)
    canvas.drawRightString(PW - MG, PH - MG + 6, generated)
    # Bottom rule + footer text
    canvas.setStrokeColor(LGREY)
    canvas.setLineWidth(0.5)
    canvas.line(MG, MG - 4, PW - MG, MG - 4)
    canvas.setFont(_f(False), 7.5)
    canvas.setFillColor(MGREY)
    canvas.drawString(MG, MG - 14, "Clavra ProdPilot™  |  Confidential — For Internal Use Only")
    canvas.drawRightString(PW - MG, MG - 14, f"Page {doc.page}")
    canvas.restoreState()

# ── KPI summary table ──────────────────────────────────────────────────────────
def _kpi_table(kpis: list[tuple[str, str, str]]) -> Table:
    """kpis = [(label, value, subtitle), ...]  — renders as coloured KPI cards."""
    n = len(kpis)
    gap = 4
    cw = (CW - gap * (n - 1)) / n
    row = [[
        Table(
            [[_p(lbl, _KPI_LBL)], [_p(val, _KPI_VAL)], [_p(sub, _KPI_SUB)]],
            colWidths=[cw],
            style=TableStyle([
                ("BACKGROUND", (0,0), (-1,-1), LNY),
                ("LEFTPADDING",  (0,0), (-1,-1), 6),
                ("RIGHTPADDING", (0,0), (-1,-1), 6),
                ("TOPPADDING",   (0,0), (-1,-1), 6),
                ("BOTTOMPADDING",(0,0), (-1,-1), 6),
                ("BOX",          (0,0), (-1,-1), 0.5, NAVY),
            ])
        )
        for lbl, val, sub in kpis
    ]]
    return Table(row, colWidths=[cw + (gap if i < n-1 else 0) for i in range(n)],
                 style=TableStyle([("LEFTPADDING",(0,0),(-1,-1),0),
                                   ("RIGHTPADDING",(0,0),(-1,-1),0)]))

# ── Data table builder ────────────────────────────────────────────────────────
def _dt(headers, rows, cws, status_col: int = -1) -> Table:
    data = [[_p(h, _TH) for h in headers]]
    for row in rows:
        cells = []
        for j, cell in enumerate(row):
            if j == status_col and cell:
                cells.append(_status_cell(str(cell)))
            else:
                cells.append(_p(str(cell) if cell is not None else "–", _TD))
        data.append(cells)
    return Table(data, colWidths=cws, style=TableStyle(BASE_TS),
                 hAlign="LEFT", repeatRows=1)

# ── PDF builder core ──────────────────────────────────────────────────────────
def _build_pdf(story: list, title: str, subtitle: str) -> bytes:
    buf = io.BytesIO()
    generated = f"Generated: {datetime.now().strftime('%d %b %Y  %H:%M')}"
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=MG, rightMargin=MG,
        topMargin=MG + 1*cm, bottomMargin=MG + 0.8*cm,
        title=title, author="Clavra ProdPilot™",
    )
    cb = lambda c, d: _page_deco(c, d, title, generated)
    doc.build(story, onFirstPage=cb, onLaterPages=cb)
    return buf.getvalue()

def _report_header(title: str, subtitle: str) -> list:
    return [
        _p(title, _REP_TITLE),
        _p(subtitle, _REP_SUB),
    ]

def _fmt_date(dt) -> str:
    if not dt:
        return "–"
    if isinstance(dt, str):
        return dt[:10]
    return dt.strftime("%d %b %Y")

# ══════════════════════════════════════════════════════════════════════════════
# 1. PRODUCTION ORDERS REPORT
# ══════════════════════════════════════════════════════════════════════════════
async def generate_orders_pdf(
    db: AsyncSession, org_id: int,
    status: Optional[str] = None,
    buyer: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> bytes:
    q = select(ProductionOrder)
    if org_id is not None:
        q = q.where(ProductionOrder.org_id == org_id)
    if status:
        q = q.where(ProductionOrder.status == status)
    if buyer:
        q = q.where(ProductionOrder.buyer.ilike(f"%{buyer}%"))
    if from_date:
        q = q.where(ProductionOrder.delivery_date >= from_date)
    if to_date:
        q = q.where(ProductionOrder.delivery_date <= to_date)
    q = q.order_by(ProductionOrder.id.desc())
    result = await db.execute(q)
    orders = result.scalars().all()

    # KPIs
    total = len(orders)
    active = sum(1 for o in orders if o.status not in ("Completed", "Cancelled", "Shipped"))
    completed = sum(1 for o in orders if o.status in ("Completed", "Shipped"))
    avg_pct = round(sum((o.produced_qty or 0) / max(o.quantity, 1) * 100 for o in orders) / max(total, 1))
    total_defects = sum(o.defect_qty or 0 for o in orders)

    # Filters description
    parts = []
    if status:  parts.append(f"Status: {status}")
    if buyer:   parts.append(f"Buyer: {buyer}")
    if from_date: parts.append(f"From: {from_date}")
    if to_date:   parts.append(f"To: {to_date}")
    filt = "  |  Filters: " + ", ".join(parts) if parts else ""

    story = _report_header(
        "Production Orders Report",
        f"All production orders for your organisation{filt}"
    )
    story.append(_kpi_table([
        ("Total Orders",  str(total),     "all statuses"),
        ("Active",        str(active),    "in progress"),
        ("Completed",     str(completed), "shipped / done"),
        ("Avg Progress",  f"{avg_pct}%",  f"{total_defects} defects"),
    ]))
    story.append(_sp(0.5))

    # Table
    headers = ["Order No", "Buyer", "Style", "Qty", "Produced", "Defects", "Progress", "Status", "Delivery"]
    cws = [65, 70, 75, 40, 50, 50, 50, 65, 60]  # = 525 → trim to fit CW
    # Normalise to CW
    scale = CW / sum(cws)
    cws = [c * scale for c in cws]

    rows = []
    for o in orders:
        pct = round((o.produced_qty or 0) / max(o.quantity, 1) * 100)
        rows.append([
            o.order_no, o.buyer or "–", o.style or "–",
            str(o.quantity), str(o.produced_qty or 0),
            str(o.defect_qty or 0), f"{pct}%",
            o.status, _fmt_date(o.delivery_date),
        ])
    story.append(_dt(headers, rows, cws, status_col=7))
    return _build_pdf(story, "Production Orders Report",
                      datetime.now().strftime("%d %b %Y %H:%M"))


# ══════════════════════════════════════════════════════════════════════════════
# 2. SHIPMENTS REPORT
# ══════════════════════════════════════════════════════════════════════════════
async def generate_shipments_pdf(
    db: AsyncSession, org_id: int,
    status: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> bytes:
    q = select(Shipment)
    if org_id is not None:
        q = q.where(Shipment.org_id == org_id)
    if status:
        q = q.where(Shipment.status == status)
    if from_date:
        q = q.where(Shipment.eta >= from_date)
    if to_date:
        q = q.where(Shipment.eta <= to_date)
    q = q.order_by(Shipment.id.desc())
    result = await db.execute(q)
    ships = result.scalars().all()

    total = len(ships)
    in_transit = sum(1 for s in ships if s.status == "In Transit")
    delivered = sum(1 for s in ships if s.status == "Delivered")
    delayed = sum(1 for s in ships if s.status == "Delayed")

    parts = []
    if status:    parts.append(f"Status: {status}")
    if from_date: parts.append(f"ETA From: {from_date}")
    if to_date:   parts.append(f"ETA To: {to_date}")
    filt = "  |  Filters: " + ", ".join(parts) if parts else ""

    story = _report_header("Shipments Report",
                           f"All shipments for your organisation{filt}")
    story.append(_kpi_table([
        ("Total Shipments", str(total),      "all statuses"),
        ("In Transit",      str(in_transit), "currently en route"),
        ("Delivered",       str(delivered),  "completed"),
        ("Delayed",         str(delayed),    "past ETA"),
    ]))
    story.append(_sp(0.5))

    headers = ["Shipment No", "Buyer", "Destination", "Carrier", "Status", "ETA", "Departure", "Order No"]
    cws = [72, 65, 75, 70, 65, 60, 60, 60]
    scale = CW / sum(cws)
    cws = [c * scale for c in cws]

    # Build order_no lookup from linked order_ids
    order_ids = [s.order_id for s in ships if s.order_id]
    order_map: dict = {}
    if order_ids:
        ores = await db.execute(
            select(ProductionOrder.id, ProductionOrder.order_no)
            .where(ProductionOrder.id.in_(order_ids))
        )
        order_map = {r.id: r.order_no for r in ores.all()}

    rows = []
    for s in ships:
        rows.append([
            s.shipment_no, s.buyer or "–", s.destination or "–", s.carrier or "–",
            s.status, _fmt_date(s.eta), _fmt_date(s.actual_departure),
            order_map.get(s.order_id, "–") if s.order_id else "–",
        ])
    story.append(_dt(headers, rows, cws, status_col=4))
    return _build_pdf(story, "Shipments Report",
                      datetime.now().strftime("%d %b %Y %H:%M"))


# ══════════════════════════════════════════════════════════════════════════════
# 3. INVENTORY REPORT
# ══════════════════════════════════════════════════════════════════════════════
async def generate_inventory_pdf(
    db: AsyncSession,
    status: Optional[str] = None,
    category: Optional[str] = None,
) -> bytes:
    q = select(Inventory)
    if status:
        q = q.where(Inventory.status == status)
    if category:
        q = q.where(Inventory.category.ilike(f"%{category}%"))
    q = q.order_by(Inventory.status, Inventory.material_name)
    result = await db.execute(q)
    items = result.scalars().all()

    total = len(items)
    in_stock = sum(1 for i in items if i.status == "In Stock")
    low = sum(1 for i in items if i.status == "Low Stock")
    out = sum(1 for i in items if i.status == "Out of Stock")

    parts = []
    if status:   parts.append(f"Status: {status}")
    if category: parts.append(f"Category: {category}")
    filt = "  |  Filters: " + ", ".join(parts) if parts else ""

    story = _report_header("Inventory Report",
                           f"Raw material stock levels{filt}")
    story.append(_kpi_table([
        ("Total Materials", str(total),    "all categories"),
        ("In Stock",        str(in_stock), "sufficient stock"),
        ("Low Stock",       str(low),      "reorder needed"),
        ("Out of Stock",    str(out),      "critical shortage"),
    ]))
    story.append(_sp(0.5))

    headers = ["Code", "Material Name", "Category", "Unit", "Stock Qty", "Reserved", "Available", "Status"]
    cws = [55, 110, 75, 40, 55, 55, 60, 70]
    scale = CW / sum(cws)
    cws = [c * scale for c in cws]

    rows = []
    for i in items:
        rows.append([
            i.material_code, i.material_name, i.category, i.unit,
            str(i.stock_qty), str(i.reserved_qty), str(i.available_qty),
            i.status,
        ])
    story.append(_dt(headers, rows, cws, status_col=7))
    return _build_pdf(story, "Inventory Report",
                      datetime.now().strftime("%d %b %Y %H:%M"))


# ══════════════════════════════════════════════════════════════════════════════
# 4. QUALITY CONTROL REPORT
# ══════════════════════════════════════════════════════════════════════════════
async def generate_quality_pdf(
    db: AsyncSession, org_id: int,
    severity: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> bytes:
    q = select(QualityReport)
    if org_id is not None:
        q = q.where(QualityReport.org_id == org_id)
    if severity:
        q = q.where(QualityReport.severity == severity)
    if from_date:
        q = q.where(QualityReport.inspection_date >= from_date)
    if to_date:
        q = q.where(QualityReport.inspection_date <= to_date)
    q = q.order_by(QualityReport.inspection_date.desc())
    result = await db.execute(q)
    reports = result.scalars().all()

    # Get order_no for each report
    order_ids = [r.order_id for r in reports if r.order_id]
    order_map: dict = {}
    if order_ids:
        ores = await db.execute(
            select(ProductionOrder.id, ProductionOrder.order_no)
            .where(ProductionOrder.id.in_(order_ids))
        )
        order_map = {r.id: r.order_no for r in ores.all()}

    total = len(reports)
    critical = sum(1 for r in reports if r.severity == "critical")
    major = sum(1 for r in reports if r.severity == "major")
    total_defects = sum(r.defect_count or 0 for r in reports)
    avg_rate = round(sum(r.defect_rate or 0 for r in reports) / max(total, 1), 2)

    parts = []
    if severity:  parts.append(f"Severity: {severity}")
    if from_date: parts.append(f"From: {from_date}")
    if to_date:   parts.append(f"To: {to_date}")
    filt = "  |  Filters: " + ", ".join(parts) if parts else ""

    story = _report_header("Quality Control Report",
                           f"Defect inspection records{filt}")
    story.append(_kpi_table([
        ("Total Reports",  str(total),         "all inspections"),
        ("Critical Issues",str(critical),       "urgent action needed"),
        ("Major Issues",   str(major),          "high priority"),
        ("Avg Defect Rate",f"{avg_rate}%",      f"{total_defects} total defects"),
    ]))
    story.append(_sp(0.5))

    headers = ["Date", "Order No", "Defect Type", "Defects", "Checked", "Rate %", "Severity", "Notes"]
    cws = [60, 60, 90, 45, 50, 45, 60, 115]
    scale = CW / sum(cws)
    cws = [c * scale for c in cws]

    rows = []
    for r in reports:
        rows.append([
            _fmt_date(r.inspection_date),
            order_map.get(r.order_id, "–") if r.order_id else "–",
            r.defect_type or "–",
            str(r.defect_count or 0),
            str(r.total_checked or 0),
            f"{round(r.defect_rate or 0, 1)}%",
            r.severity or "minor",
            (r.notes or "")[:60],
        ])
    story.append(_dt(headers, rows, cws, status_col=6))
    return _build_pdf(story, "Quality Control Report",
                      datetime.now().strftime("%d %b %Y %H:%M"))


# ══════════════════════════════════════════════════════════════════════════════
# 5. PRODUCTION LINES REPORT
# ══════════════════════════════════════════════════════════════════════════════
async def generate_lines_pdf(db: AsyncSession) -> bytes:
    result = await db.execute(select(ProductionLine).order_by(ProductionLine.line_name))
    lines = result.scalars().all()

    total = len(lines)
    running = sum(1 for l in lines if l.status == "Running" or l.status == "Active")
    idle = sum(1 for l in lines if l.status == "Idle")
    avg_eff = round(sum(l.efficiency or 0 for l in lines) / max(total, 1))

    story = _report_header("Production Lines Report",
                           "Current status and efficiency of all production lines")
    story.append(_kpi_table([
        ("Total Lines",    str(total),    "configured"),
        ("Running",        str(running),  "currently active"),
        ("Idle",           str(idle),     "available"),
        ("Avg Efficiency", f"{avg_eff}%", "across all lines"),
    ]))
    story.append(_sp(0.5))

    headers = ["Line", "Supervisor", "Status", "Target Output", "Actual Output", "Efficiency %", "Defects", "Operators"]
    cws = [55, 80, 60, 72, 72, 65, 55, 60]
    scale = CW / sum(cws)
    cws = [c * scale for c in cws]

    rows = []
    for l in lines:
        rows.append([
            l.line_name, l.supervisor or "–", l.status or "–",
            str(l.target_output or 0), str(l.actual_output or 0),
            f"{l.efficiency or 0}%", str(l.defects or 0), str(l.operators or 0),
        ])
    story.append(_dt(headers, rows, cws, status_col=2))
    return _build_pdf(story, "Production Lines Report",
                      datetime.now().strftime("%d %b %Y %H:%M"))


# ══════════════════════════════════════════════════════════════════════════════
# 6. FACTORY SUMMARY REPORT (Full overview on one document)
# ══════════════════════════════════════════════════════════════════════════════
async def generate_summary_pdf(db: AsyncSession, org_id: int) -> bytes:
    # Fetch all data concurrently (sequential for simplicity)
    oq = select(ProductionOrder)
    if org_id is not None:
        oq = oq.where(ProductionOrder.org_id == org_id)
    orders = (await db.execute(oq.order_by(ProductionOrder.id.desc()))).scalars().all()

    sq = select(Shipment)
    if org_id is not None:
        sq = sq.where(Shipment.org_id == org_id)
    ships = (await db.execute(sq.order_by(Shipment.id.desc()))).scalars().all()

    inv_items = (await db.execute(select(Inventory).order_by(Inventory.status, Inventory.material_name))).scalars().all()
    lines = (await db.execute(select(ProductionLine).order_by(ProductionLine.line_name))).scalars().all()

    story = _report_header(
        "Factory Summary Report",
        f"Complete operational overview  |  {datetime.now().strftime('%d %B %Y')}"
    )
    story.append(_sp(0.3))

    # ── Order KPIs ──
    total_o = len(orders)
    active_o = sum(1 for o in orders if o.status not in ("Completed", "Cancelled", "Shipped"))
    completed_o = sum(1 for o in orders if o.status in ("Completed", "Shipped"))
    avg_prog = round(sum((o.produced_qty or 0) / max(o.quantity, 1) * 100 for o in orders) / max(total_o, 1))

    story.append(_p("Production Orders", _SEC_HDR))
    story.append(_kpi_table([
        ("Total Orders", str(total_o),      "all time"),
        ("Active",       str(active_o),     "in production"),
        ("Completed",    str(completed_o),  "shipped / done"),
        ("Avg Progress", f"{avg_prog}%",    "across active"),
    ]))
    story.append(_sp(0.25))

    # Orders top-10 table
    o_headers = ["Order No", "Buyer", "Style", "Qty", "Progress", "Status", "Delivery"]
    o_cws_raw = [62, 70, 80, 42, 52, 65, 60]
    scale = CW / sum(o_cws_raw)
    o_cws = [c * scale for c in o_cws_raw]
    o_rows = []
    for o in orders[:10]:
        pct = round((o.produced_qty or 0) / max(o.quantity, 1) * 100)
        o_rows.append([o.order_no, o.buyer or "–", o.style or "–",
                       str(o.quantity), f"{pct}%", o.status, _fmt_date(o.delivery_date)])
    story.append(_dt(o_headers, o_rows, o_cws, status_col=5))
    if total_o > 10:
        story.append(_p(f"  … and {total_o - 10} more orders", _s("nm", fontName=_f(False), fontSize=8, textColor=MGREY, spaceAfter=4)))
    story.append(_sp(0.4))

    # ── Shipment KPIs ──
    total_s = len(ships)
    in_transit = sum(1 for s in ships if s.status == "In Transit")
    delivered  = sum(1 for s in ships if s.status == "Delivered")
    delayed    = sum(1 for s in ships if s.status == "Delayed")

    story.append(_p("Shipments", _SEC_HDR))
    story.append(_kpi_table([
        ("Total Shipments", str(total_s),    "all time"),
        ("In Transit",      str(in_transit), "en route"),
        ("Delivered",       str(delivered),  "completed"),
        ("Delayed",         str(delayed),    "past ETA"),
    ]))
    story.append(_sp(0.25))

    s_headers = ["Shipment No", "Buyer", "Destination", "Carrier", "Status", "ETA"]
    s_cws_raw = [75, 75, 85, 80, 70, 65]
    scale = CW / sum(s_cws_raw)
    s_cws = [c * scale for c in s_cws_raw]
    s_rows = []
    for s in ships[:8]:
        s_rows.append([s.shipment_no, s.buyer or "–", s.destination or "–",
                       s.carrier or "–", s.status, _fmt_date(s.eta)])
    story.append(_dt(s_headers, s_rows, s_cws, status_col=4))
    story.append(_sp(0.4))

    # ── Inventory KPIs ──
    total_i = len(inv_items)
    low_items = [i for i in inv_items if i.status in ("Low Stock", "Out of Stock")]
    story.append(_p("Inventory — Low Stock Alert", _SEC_HDR))
    story.append(_kpi_table([
        ("Total Materials", str(total_i),        "tracked"),
        ("In Stock",        str(sum(1 for i in inv_items if i.status == "In Stock")), "healthy"),
        ("Low Stock",       str(sum(1 for i in inv_items if i.status == "Low Stock")), "reorder"),
        ("Out of Stock",    str(sum(1 for i in inv_items if i.status == "Out of Stock")), "critical"),
    ]))
    if low_items:
        story.append(_sp(0.25))
        i_headers = ["Code", "Material Name", "Category", "Available", "Status"]
        i_cws_raw = [65, 130, 90, 70, 80]
        scale = CW / sum(i_cws_raw)
        i_cws = [c * scale for c in i_cws_raw]
        i_rows = [[i.material_code, i.material_name, i.category,
                   str(i.available_qty), i.status] for i in low_items[:10]]
        story.append(_dt(i_headers, i_rows, i_cws, status_col=4))
    story.append(_sp(0.4))

    # ── Production Lines ──
    if lines:
        avg_eff = round(sum(l.efficiency or 0 for l in lines) / len(lines))
        story.append(_p("Production Lines", _SEC_HDR))
        story.append(_kpi_table([
            ("Total Lines",    str(len(lines)), "configured"),
            ("Running",        str(sum(1 for l in lines if l.status in ("Running", "Active"))), "active"),
            ("Avg Efficiency", f"{avg_eff}%",   "overall"),
            ("Total Defects",  str(sum(l.defects or 0 for l in lines)), "on floor today"),
        ]))
        story.append(_sp(0.25))
        l_headers = ["Line", "Supervisor", "Status", "Target", "Actual", "Efficiency"]
        l_cws_raw = [60, 100, 70, 65, 65, 70]
        scale = CW / sum(l_cws_raw)
        l_cws = [c * scale for c in l_cws_raw]
        l_rows = [[l.line_name, l.supervisor or "–", l.status or "–",
                   str(l.target_output or 0), str(l.actual_output or 0),
                   f"{l.efficiency or 0}%"] for l in lines]
        story.append(_dt(l_headers, l_rows, l_cws, status_col=2))

    return _build_pdf(story, "Factory Summary Report",
                      datetime.now().strftime("%d %b %Y %H:%M"))
