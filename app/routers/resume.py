from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, status
from datetime import datetime
from bson import ObjectId

from app.database import get_db
from app.auth.dependencies import get_current_admin
from app.services.resume_parser import extract_text_from_pdf, parse_resume_sections
from app.models.schemas import ResumeOut, ResumeListResponse

router = APIRouter(prefix="/api/resume", tags=["Resume"])


@router.post("/upload", response_model=ResumeOut)
async def upload_resume(
    file: UploadFile = File(...),
    admin=Depends(get_current_admin),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported",
        )

    # Read file
    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size must be under 10MB",
        )

    # Extract text
    try:
        raw_text = extract_text_from_pdf(file_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not parse PDF: {str(e)}",
        )

    if not raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No text content found in the PDF",
        )

    # Parse sections
    sections = parse_resume_sections(raw_text)

    db = get_db()

    # Deactivate all existing resumes
    await db.resumes.update_many({}, {"$set": {"is_active": False}})

    # Store resume
    resume_doc = {
        "filename": file.filename,
        "raw_text": raw_text,
        "sections": sections,
        "is_active": True,
        "uploaded_at": datetime.utcnow(),
        "uploaded_by": admin["email"],
    }
    result = await db.resumes.insert_one(resume_doc)

    return ResumeOut(
        id=str(result.inserted_id),
        filename=file.filename,
        uploaded_at=resume_doc["uploaded_at"],
        is_active=True,
        sections=sections,
    )


@router.get("/active")
async def get_active_resume():
    db = get_db()
    resume = await db.resumes.find_one({"is_active": True})
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active resume found",
        )
    return ResumeOut(
        id=str(resume["_id"]),
        filename=resume["filename"],
        uploaded_at=resume["uploaded_at"],
        is_active=True,
        sections=resume.get("sections"),
    )


@router.get("/list", response_model=ResumeListResponse)
async def list_resumes(admin=Depends(get_current_admin)):
    db = get_db()
    resumes = []
    async for r in db.resumes.find().sort("uploaded_at", -1):
        resumes.append(
            ResumeOut(
                id=str(r["_id"]),
                filename=r["filename"],
                uploaded_at=r["uploaded_at"],
                is_active=r.get("is_active", False),
                sections=r.get("sections"),
            )
        )
    return ResumeListResponse(resumes=resumes, total=len(resumes))


@router.put("/{resume_id}/activate")
async def activate_resume(resume_id: str, admin=Depends(get_current_admin)):
    db = get_db()

    try:
        obj_id = ObjectId(resume_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid resume ID")

    resume = await db.resumes.find_one({"_id": obj_id})
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # Deactivate all, then activate the selected one
    await db.resumes.update_many({}, {"$set": {"is_active": False}})
    await db.resumes.update_one({"_id": obj_id}, {"$set": {"is_active": True}})

    return {"message": "Resume activated", "id": resume_id}


@router.delete("/{resume_id}")
async def delete_resume(resume_id: str, admin=Depends(get_current_admin)):
    db = get_db()

    try:
        obj_id = ObjectId(resume_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid resume ID")

    result = await db.resumes.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Resume not found")

    return {"message": "Resume deleted", "id": resume_id}
