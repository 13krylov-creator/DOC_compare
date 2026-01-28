from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any
import uuid

from database import get_db
from models.document import Document, DocumentVersion
from models.comparison import DocumentComparison
from services.diff_engine import DiffEngine
from services.ai_service import ai_service

router = APIRouter()

# Only 2 comparison modes
COMPARISON_MODES = ["line-by-line", "semantic"]

class CompareRequest(BaseModel):
    custom_prompt: Optional[str] = None

class ChangeItem(BaseModel):
    id: str
    type: str
    classification: str
    severity: str
    location: Optional[str] = None
    original_text: Optional[str] = None
    new_text: Optional[str] = None
    original_html: Optional[str] = None
    new_html: Optional[str] = None
    ai_summary: Optional[str] = None
    impact_score: int = 0
    business_context: Optional[str] = None

class ComparisonSummary(BaseModel):
    total_changes: int
    critical_changes: int
    major_changes: int
    minor_changes: int
    similarity_score: float

@router.post("/{id1}/vs/{id2}")
async def compare_documents(
    id1: str,
    id2: str,
    mode: str = Query("line-by-line", enum=COMPARISON_MODES),
    show_full: bool = Query(False, description="Show full document with highlighted differences"),
    request_body: Optional[CompareRequest] = Body(None),
    db: Session = Depends(get_db)
):
    """Compare two documents with optional AI enhancement for semantic mode"""
    # Get documents
    doc1 = db.query(Document).filter(Document.id == id1).first()
    doc2 = db.query(Document).filter(Document.id == id2).first()
    
    version1 = None
    version2 = None
    
    if doc1:
        version1 = db.query(DocumentVersion).filter(
            DocumentVersion.document_id == doc1.id
        ).order_by(DocumentVersion.version_number.desc()).first()
        text1 = doc1.extracted_text or ""
    else:
        version1 = db.query(DocumentVersion).filter(DocumentVersion.id == id1).first()
        if version1:
            text1 = version1.content or ""
        else:
            raise HTTPException(status_code=404, detail=f"Document/version {id1} not found")
    
    if doc2:
        version2 = db.query(DocumentVersion).filter(
            DocumentVersion.document_id == doc2.id
        ).order_by(DocumentVersion.version_number.desc()).first()
        text2 = doc2.extracted_text or ""
    else:
        version2 = db.query(DocumentVersion).filter(DocumentVersion.id == id2).first()
        if version2:
            text2 = version2.content or ""
        else:
            raise HTTPException(status_code=404, detail=f"Document/version {id2} not found")
    
    # Perform diff comparison
    diff_engine = DiffEngine()
    comparison_result = diff_engine.compare(text1, text2, mode, show_full=show_full)
    
    # For semantic mode - call AI for summary
    ai_enhanced = False
    ai_summary = None
    
    if mode == "semantic":
        custom_prompt = request_body.custom_prompt if request_body else None
        try:
            ai_result = await ai_service.generate_semantic_summary(
                text1, text2, 
                comparison_result.get("changes", []),
                custom_prompt
            )
            ai_summary = ai_result.get("summary")
            ai_enhanced = ai_result.get("ai_used", False)  # Use actual flag
            comparison_result["ai_summary"] = ai_summary
        except Exception as e:
            print(f"AI analysis failed: {e}")
            # Use rule-based fallback
            ai_summary = ai_service.generate_fallback_summary(comparison_result.get("changes", []))
            comparison_result["ai_summary"] = ai_summary
            ai_enhanced = False
    
    comparison_result["ai_enhanced"] = ai_enhanced
    comparison_id = str(uuid.uuid4())
    
    # Save comparison
    db_comparison = DocumentComparison(
        id=comparison_id,
        tenant_id="default",
        version1_id=version1.id if version1 else id1,
        version2_id=version2.id if version2 else id2,
        comparison_mode=mode,
        result=comparison_result,
        summary={
            "total_changes": comparison_result["summary"]["total_changes"],
            "critical_changes": comparison_result["summary"]["critical_changes"],
            "major_changes": comparison_result["summary"]["major_changes"],
            "minor_changes": comparison_result["summary"]["minor_changes"],
            "similarity_score": comparison_result["summary"]["similarity_score"]
        },
        total_changes=comparison_result["summary"]["total_changes"],
        critical_changes=comparison_result["summary"]["critical_changes"],
        major_changes=comparison_result["summary"]["major_changes"],
        minor_changes=comparison_result["summary"]["minor_changes"],
        similarity_score=str(comparison_result["summary"]["similarity_score"]),
        created_at=datetime.utcnow()
    )
    db.add(db_comparison)
    db.commit()
    
    # Build response
    response = {
        "id": comparison_id,
        "document_id_v1": id1,
        "document_id_v2": id2,
        "comparison_mode": mode,
        "generated_at": datetime.utcnow().isoformat(),
        "summary": comparison_result["summary"],
        "changes": comparison_result["changes"],
        "ai_enhanced": ai_enhanced
    }
    
    if ai_summary:
        response["ai_summary"] = ai_summary
    
    if "diff_lines" in comparison_result:
        response["diff_lines"] = comparison_result["diff_lines"]
    
    if "mode_info" in comparison_result:
        response["mode_info"] = comparison_result["mode_info"]
    
    return response

@router.get("/history")
async def get_comparison_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get comparison history"""
    query = db.query(DocumentComparison)
    total = query.count()
    comparisons = query.order_by(DocumentComparison.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    return {
        "comparisons": [
            {
                "id": c.id,
                "version1_id": c.version1_id,
                "version2_id": c.version2_id,
                "comparison_mode": c.comparison_mode,
                "total_changes": c.total_changes,
                "critical_changes": c.critical_changes,
                "created_at": c.created_at
            }
            for c in comparisons
        ],
        "total": total,
        "page": page,
        "page_size": page_size
    }

@router.get("/{comparison_id}")
async def get_comparison(comparison_id: str, db: Session = Depends(get_db)):
    """Get a specific comparison result"""
    comparison = db.query(DocumentComparison).filter(DocumentComparison.id == comparison_id).first()
    if not comparison:
        raise HTTPException(status_code=404, detail="Comparison not found")
    
    return {
        "id": comparison.id,
        "version1_id": comparison.version1_id,
        "version2_id": comparison.version2_id,
        "comparison_mode": comparison.comparison_mode,
        "result": comparison.result,
        "summary": comparison.summary,
        "created_at": comparison.created_at
    }
