from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.dependencies import get_db, get_current_user
from app.schemas.auth import UserRead
from app.services.quality_service import log_defect, get_quality_reports

router = APIRouter(prefix="/quality", tags=["Quality"])


@router.get("/reports")
async def list_reports(
    limit: int = Query(50, le=200),
    current_user: UserRead    = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    return await get_quality_reports(db, current_user.org_id, limit)


@router.post("/reports", status_code=201)
async def create_report(
    payload: dict,
    current_user: UserRead    = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    return await log_defect(
        db=db, org_id=current_user.org_id, user_id=current_user.id,
        order_id=payload.get("order_id"), line_id=payload.get("line_id"),
        defect_type=payload.get("defect_type", "Unknown"),
        defect_count=int(payload.get("defect_count", 0)),
        total_checked=int(payload.get("total_checked", 0)),
        severity=payload.get("severity", "minor"),
        notes=payload.get("notes", ""),
    )
