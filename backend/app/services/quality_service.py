from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.quality import QualityReport


async def log_defect(
    db: AsyncSession, org_id: int, user_id: int,
    order_id: int | None, line_id: int | None,
    defect_type: str, defect_count: int,
    total_checked: int, severity: str, notes: str = ""
) -> dict:
    rate = round(defect_count / total_checked, 4) if total_checked > 0 else 0.0
    report = QualityReport(
        org_id=org_id, inspector_id=user_id,
        order_id=order_id, line_id=line_id,
        defect_type=defect_type, defect_count=defect_count,
        total_checked=total_checked, defect_rate=rate,
        severity=severity, notes=notes,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return {"id": report.id, "defect_rate": rate, "severity": severity, "message": "Quality report logged."}


async def get_quality_reports(db: AsyncSession, org_id: int, limit: int = 50) -> list:
    result = await db.execute(
        select(QualityReport)
        .where(QualityReport.org_id == org_id)
        .order_by(QualityReport.inspection_date.desc())
        .limit(limit)
    )
    reports = result.scalars().all()
    return [
        {
            "id": r.id, "order_id": r.order_id, "line_id": r.line_id,
            "defect_type": r.defect_type, "defect_count": r.defect_count,
            "total_checked": r.total_checked, "defect_rate": r.defect_rate,
            "severity": r.severity, "notes": r.notes,
            "inspection_date": str(r.inspection_date),
        }
        for r in reports
    ]
