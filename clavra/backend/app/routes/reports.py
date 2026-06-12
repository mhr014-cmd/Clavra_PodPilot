"""Report download endpoints — returns branded PDF via StreamingResponse."""
import io
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.schemas.auth import UserRead
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["Reports"])


def _pdf_response(pdf_bytes: bytes, filename: str) -> StreamingResponse:
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/orders")
async def download_orders(
    status:    Optional[str] = Query(None, description="Filter by order status"),
    buyer:     Optional[str] = Query(None, description="Filter by buyer name (partial match)"),
    from_date: Optional[str] = Query(None, description="Delivery date from (YYYY-MM-DD)"),
    to_date:   Optional[str] = Query(None, description="Delivery date to (YYYY-MM-DD)"),
    current_user: UserRead    = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    """Download Production Orders as PDF."""
    pdf = await report_service.generate_orders_pdf(
        db, current_user.org_id, status=status, buyer=buyer,
        from_date=from_date, to_date=to_date,
    )
    return _pdf_response(pdf, "clavra_orders_report.pdf")


@router.get("/shipments")
async def download_shipments(
    status:    Optional[str] = Query(None, description="Filter by shipment status"),
    from_date: Optional[str] = Query(None, description="ETA from (YYYY-MM-DD)"),
    to_date:   Optional[str] = Query(None, description="ETA to (YYYY-MM-DD)"),
    current_user: UserRead    = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    """Download Shipments as PDF."""
    pdf = await report_service.generate_shipments_pdf(
        db, current_user.org_id, status=status,
        from_date=from_date, to_date=to_date,
    )
    return _pdf_response(pdf, "clavra_shipments_report.pdf")


@router.get("/inventory")
async def download_inventory(
    status:   Optional[str] = Query(None, description="Filter by stock status"),
    category: Optional[str] = Query(None, description="Filter by material category"),
    current_user: UserRead    = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    """Download Inventory as PDF."""
    pdf = await report_service.generate_inventory_pdf(
        db, status=status, category=category,
    )
    return _pdf_response(pdf, "clavra_inventory_report.pdf")


@router.get("/quality")
async def download_quality(
    severity:  Optional[str] = Query(None, description="Filter by severity: critical|major|minor"),
    from_date: Optional[str] = Query(None, description="Inspection date from (YYYY-MM-DD)"),
    to_date:   Optional[str] = Query(None, description="Inspection date to (YYYY-MM-DD)"),
    current_user: UserRead    = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    """Download Quality Control report as PDF."""
    pdf = await report_service.generate_quality_pdf(
        db, current_user.org_id, severity=severity,
        from_date=from_date, to_date=to_date,
    )
    return _pdf_response(pdf, "clavra_quality_report.pdf")


@router.get("/production-lines")
async def download_lines(
    current_user: UserRead    = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    """Download Production Lines report as PDF."""
    pdf = await report_service.generate_lines_pdf(db)
    return _pdf_response(pdf, "clavra_lines_report.pdf")


@router.get("/summary")
async def download_summary(
    current_user: UserRead    = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    """Download full Factory Summary report as PDF."""
    pdf = await report_service.generate_summary_pdf(db, current_user.org_id)
    return _pdf_response(pdf, "clavra_factory_summary.pdf")
