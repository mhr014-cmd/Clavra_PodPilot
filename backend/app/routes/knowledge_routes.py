import os, uuid
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.dependencies import get_db, get_current_user
from app.schemas.auth import UserRead
from app.models.knowledge_document import KnowledgeDocument

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads", "docs")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx", ".xlsx"}


@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    doc_type: str = "policy",
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only PDF, TXT, DOCX, and XLSX files are accepted")

    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 20MB)")

    fname = f"{uuid.uuid4().hex}{ext}"
    fpath = os.path.join(UPLOAD_DIR, fname)
    with open(fpath, "wb") as f:
        f.write(content)

    doc = KnowledgeDocument(
        org_id=current_user.org_id,
        filename=fname,
        original_name=file.filename,
        doc_type=doc_type,
        uploaded_by=current_user.id,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    background_tasks.add_task(_embed_document, fpath, doc.id, current_user.org_id, ext)

    return {"message": "Document uploaded. Embedding in progress.", "doc_id": doc.id}


async def _embed_document(fpath: str, doc_id: int, org_id: int, ext: str):
    from app.database import AsyncSessionLocal
    from app.ai.rag_service import ingest_pdf, ingest_txt, ingest_docx, ingest_xlsx
    from app.models.knowledge_document import KnowledgeDocument
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        if ext == ".pdf":
            chunks = await ingest_pdf(fpath, doc_id, org_id, db)
        elif ext == ".txt":
            chunks = await ingest_txt(fpath, doc_id, org_id, db)
        elif ext == ".docx":
            chunks = await ingest_docx(fpath, doc_id, org_id, db)
        elif ext == ".xlsx":
            chunks = await ingest_xlsx(fpath, doc_id, org_id, db)
        else:
            chunks = 0

        result = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id))
        doc = result.scalar_one_or_none()
        if doc:
            doc.chunk_count = chunks
            await db.commit()


@router.get("/documents")
async def list_documents(
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(KnowledgeDocument)
        .where(KnowledgeDocument.org_id == current_user.org_id)
        .order_by(KnowledgeDocument.uploaded_at.desc())
    )
    docs = result.scalars().all()
    return [{"id": d.id, "name": d.original_name, "type": d.doc_type,
             "chunks": d.chunk_count, "uploaded_at": str(d.uploaded_at)} for d in docs]


@router.post("/documents/{doc_id}/reindex")
async def reindex_document(
    doc_id: int,
    background_tasks: BackgroundTasks,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete existing chunks and re-embed the document (useful after embedding failures)."""
    from sqlalchemy import delete as sql_delete
    from app.models.document_chunk import DocumentChunk

    result = await db.execute(
        select(KnowledgeDocument).where(
            KnowledgeDocument.id == doc_id,
            KnowledgeDocument.org_id == current_user.org_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    fpath = os.path.join(UPLOAD_DIR, doc.filename)
    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail="Source file not found on disk")

    ext = os.path.splitext(doc.filename)[1].lower()

    # Wipe old chunks so count resets visibly
    await db.execute(sql_delete(DocumentChunk).where(DocumentChunk.document_id == doc_id))
    doc.chunk_count = 0
    await db.commit()

    background_tasks.add_task(_embed_document, fpath, doc_id, current_user.org_id, ext)
    return {"message": "Re-indexing started. Refresh in a few seconds."}


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: int,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(KnowledgeDocument).where(
            KnowledgeDocument.id == doc_id,
            KnowledgeDocument.org_id == current_user.org_id
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    await db.execute(delete(KnowledgeDocument).where(KnowledgeDocument.id == doc_id))
    await db.commit()

    try:
        fpath = os.path.join(UPLOAD_DIR, doc.filename)
        if os.path.exists(fpath):
            os.remove(fpath)
    except:
        pass

    return {"message": "Document deleted"}
