"""
Enterprise Risk Analysis Router
Comprehensive risk assessment for legal documents
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
import json
import csv
import io

from database import get_db
from models.document import Document, DocumentVersion
from models.extraction import RiskAssessment, RiskLevel
from services.risk_analyzer import RiskAnalyzer
from services.audit_service import get_audit_service

router = APIRouter()


class RiskItem(BaseModel):
    id: str
    dimension: str
    risk_type: str
    score: int
    level: str
    description: str
    business_context: Optional[str] = None
    recommendation: Optional[str] = None
    acknowledged: bool = False
    acknowledged_action: Optional[str] = None


class RiskAnalysisResult(BaseModel):
    document_id: str
    document_name: str
    overall_score: int
    overall_level: str
    risks: List[RiskItem]
    risk_by_dimension: dict
    risk_count: dict


class RiskComparisonResult(BaseModel):
    document1_id: str
    document2_id: str
    score_before: int
    score_after: int
    score_change: int
    level_before: str
    level_after: str
    trend: str
    new_risks: List[RiskItem]
    resolved_risks: List[RiskItem]
    changed_risks: List[dict]


class AcknowledgeRequest(BaseModel):
    risk_id: str
    action: str  # accept, mitigate, escalate
    notes: Optional[str] = None


@router.get("/documents/{document_id}", response_model=RiskAnalysisResult)
async def analyze_risk(
    document_id: str, 
    force_refresh: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Perform comprehensive risk analysis on a document"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    version = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == document_id
    ).order_by(DocumentVersion.version_number.desc()).first()
    
    if not version:
        raise HTTPException(status_code=404, detail="No version found")
    
    # Check for existing analysis
    existing = db.query(RiskAssessment).filter(
        RiskAssessment.document_version_id == version.id
    ).all()
    
    if not existing or force_refresh:
        # Delete old if refreshing
        if force_refresh and existing:
            for old in existing:
                db.delete(old)
            db.commit()
        
        # Perform new analysis
        analyzer = RiskAnalyzer()
        risks = analyzer.analyze(doc.extracted_text or "")
        
        for risk in risks:
            db_risk = RiskAssessment(
                document_version_id=version.id,
                risk_dimension=risk["dimension"],
                risk_type=risk["type"],
                risk_score=risk["score"],
                risk_level=risk["level"],
                description=risk["description"],
                business_context=risk.get("business_context"),
                recommendation=risk.get("recommendation"),
                assessed_at=datetime.utcnow()
            )
            db.add(db_risk)
        db.commit()
        
        existing = db.query(RiskAssessment).filter(
            RiskAssessment.document_version_id == version.id
        ).all()
        
        # Log audit
        audit = get_audit_service(db)
        overall = analyzer.calculate_overall_score(risks)
        audit.log_risk_action(
            action="risk_analyzed",
            document_id=document_id,
            risk_score=overall["score"],
            risk_level=overall["level"]
        )
    
    # Calculate overall score
    analyzer = RiskAnalyzer()
    risks_data = [
        {"dimension": r.risk_dimension, "type": r.risk_type, "score": r.risk_score, "level": r.risk_level}
        for r in existing
    ]
    overall = analyzer.calculate_overall_score(risks_data)
    
    # Group by dimension
    risk_by_dimension = {}
    for risk in existing:
        if risk.risk_dimension not in risk_by_dimension:
            risk_by_dimension[risk.risk_dimension] = []
        risk_by_dimension[risk.risk_dimension].append({
            "type": risk.risk_type,
            "score": risk.risk_score,
            "level": risk.risk_level,
            "description": risk.description
        })
    
    return RiskAnalysisResult(
        document_id=document_id,
        document_name=doc.name,
        overall_score=overall["score"],
        overall_level=overall["level"],
        risks=[
            RiskItem(
                id=r.id,
                dimension=r.risk_dimension,
                risk_type=r.risk_type,
                score=r.risk_score,
                level=r.risk_level,
                description=r.description,
                business_context=r.business_context,
                recommendation=r.recommendation,
                acknowledged=r.acknowledged == "true",
                acknowledged_action=r.acknowledged_action
            )
            for r in existing
        ],
        risk_by_dimension=risk_by_dimension,
        risk_count=overall.get("risk_count", {"total": len(existing), "red": 0, "yellow": 0, "green": 0})
    )


@router.get("/compare/{id1}/{id2}", response_model=RiskComparisonResult)
async def compare_risks(id1: str, id2: str, db: Session = Depends(get_db)):
    """Compare risks between two document versions"""
    doc1 = db.query(Document).filter(Document.id == id1).first()
    doc2 = db.query(Document).filter(Document.id == id2).first()
    
    if not doc1 or not doc2:
        raise HTTPException(status_code=404, detail="Document not found")
    
    version1 = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == id1
    ).order_by(DocumentVersion.version_number.desc()).first()
    
    version2 = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == id2
    ).order_by(DocumentVersion.version_number.desc()).first()
    
    # Get or create risk assessments
    risks1 = db.query(RiskAssessment).filter(
        RiskAssessment.document_version_id == version1.id
    ).all() if version1 else []
    
    risks2 = db.query(RiskAssessment).filter(
        RiskAssessment.document_version_id == version2.id
    ).all() if version2 else []
    
    # If no risks, run analysis
    analyzer = RiskAnalyzer()
    
    if not risks1 and version1:
        risk_data = analyzer.analyze(doc1.extracted_text or "")
        for risk in risk_data:
            db_risk = RiskAssessment(
                document_version_id=version1.id,
                risk_dimension=risk["dimension"],
                risk_type=risk["type"],
                risk_score=risk["score"],
                risk_level=risk["level"],
                description=risk["description"],
                business_context=risk.get("business_context"),
                recommendation=risk.get("recommendation"),
                assessed_at=datetime.utcnow()
            )
            db.add(db_risk)
        db.commit()
        risks1 = db.query(RiskAssessment).filter(
            RiskAssessment.document_version_id == version1.id
        ).all()
    
    if not risks2 and version2:
        risk_data = analyzer.analyze(doc2.extracted_text or "")
        for risk in risk_data:
            db_risk = RiskAssessment(
                document_version_id=version2.id,
                risk_dimension=risk["dimension"],
                risk_type=risk["type"],
                risk_score=risk["score"],
                risk_level=risk["level"],
                description=risk["description"],
                business_context=risk.get("business_context"),
                recommendation=risk.get("recommendation"),
                assessed_at=datetime.utcnow()
            )
            db.add(db_risk)
        db.commit()
        risks2 = db.query(RiskAssessment).filter(
            RiskAssessment.document_version_id == version2.id
        ).all()
    
    # Compare
    risks1_data = [{"dimension": r.risk_dimension, "type": r.risk_type, "score": r.risk_score, "level": r.risk_level} for r in risks1]
    risks2_data = [{"dimension": r.risk_dimension, "type": r.risk_type, "score": r.risk_score, "level": r.risk_level} for r in risks2]
    
    comparison = analyzer.compare_risks(risks1_data, risks2_data)
    
    # Build response
    risks1_types = {r.risk_type for r in risks1}
    risks2_types = {r.risk_type for r in risks2}
    
    new_risk_types = risks2_types - risks1_types
    resolved_risk_types = risks1_types - risks2_types
    
    new_risks = [
        RiskItem(
            id=r.id, dimension=r.risk_dimension, risk_type=r.risk_type,
            score=r.risk_score, level=r.risk_level, description=r.description,
            business_context=r.business_context, recommendation=r.recommendation
        )
        for r in risks2 if r.risk_type in new_risk_types
    ]
    
    resolved_risks = [
        RiskItem(
            id=r.id, dimension=r.risk_dimension, risk_type=r.risk_type,
            score=r.risk_score, level=r.risk_level, description=r.description,
            business_context=r.business_context, recommendation=r.recommendation
        )
        for r in risks1 if r.risk_type in resolved_risk_types
    ]
    
    # Find changed risks
    changed_risks = []
    for r2 in risks2:
        for r1 in risks1:
            if r1.risk_type == r2.risk_type and r1.risk_score != r2.risk_score:
                changed_risks.append({
                    "risk_type": r2.risk_type,
                    "dimension": r2.risk_dimension,
                    "old_score": r1.risk_score,
                    "new_score": r2.risk_score,
                    "change": r2.risk_score - r1.risk_score,
                    "old_level": r1.risk_level,
                    "new_level": r2.risk_level
                })
    
    return RiskComparisonResult(
        document1_id=id1,
        document2_id=id2,
        score_before=comparison["score_before"],
        score_after=comparison["score_after"],
        score_change=comparison["score_change"],
        level_before=comparison["level_before"],
        level_after=comparison["level_after"],
        trend=comparison["trend"],
        new_risks=new_risks,
        resolved_risks=resolved_risks,
        changed_risks=changed_risks
    )


@router.post("/acknowledge")
async def acknowledge_risk(request: AcknowledgeRequest, db: Session = Depends(get_db)):
    """Acknowledge a risk with action"""
    risk = db.query(RiskAssessment).filter(RiskAssessment.id == request.risk_id).first()
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")
    
    if request.action not in ["accept", "mitigate", "escalate"]:
        raise HTTPException(status_code=400, detail="Invalid action. Use: accept, mitigate, escalate")
    
    risk.acknowledged = "true"
    risk.acknowledged_action = request.action
    db.commit()
    
    # Log audit
    audit = get_audit_service(db)
    audit.log_risk_action(
        action="risk_acknowledged",
        document_id=risk.document_version_id,
        risk_score=risk.risk_score,
        risk_level=risk.risk_level
    )
    
    return {
        "message": "Risk acknowledged",
        "risk_id": request.risk_id,
        "action": request.action
    }


@router.get("/documents/{document_id}/summary")
async def get_risk_summary(document_id: str, db: Session = Depends(get_db)):
    """Get risk summary for dashboard"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    version = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == document_id
    ).order_by(DocumentVersion.version_number.desc()).first()
    
    if not version:
        return {"document_id": document_id, "has_analysis": False}
    
    risks = db.query(RiskAssessment).filter(
        RiskAssessment.document_version_id == version.id
    ).all()
    
    if not risks:
        return {"document_id": document_id, "has_analysis": False}
    
    analyzer = RiskAnalyzer()
    risks_data = [{"dimension": r.risk_dimension, "type": r.risk_type, "score": r.risk_score, "level": r.risk_level} for r in risks]
    overall = analyzer.calculate_overall_score(risks_data)
    
    # Top risks
    top_risks = sorted(risks, key=lambda r: r.risk_score, reverse=True)[:5]
    
    return {
        "document_id": document_id,
        "document_name": doc.name,
        "has_analysis": True,
        "overall_score": overall["score"],
        "overall_level": overall["level"],
        "total_risks": len(risks),
        "red_count": sum(1 for r in risks if r.risk_level == "RED"),
        "yellow_count": sum(1 for r in risks if r.risk_level == "YELLOW"),
        "green_count": sum(1 for r in risks if r.risk_level == "GREEN"),
        "acknowledged_count": sum(1 for r in risks if r.acknowledged == "true"),
        "top_risks": [
            {
                "type": r.risk_type,
                "score": r.risk_score,
                "level": r.risk_level,
                "description": r.description
            }
            for r in top_risks
        ],
        "dimension_breakdown": overall.get("dimension_breakdown", {})
    }


@router.get("/documents/{document_id}/export")
async def export_risk_report(
    document_id: str,
    format: str = Query("json", enum=["json", "csv"]),
    db: Session = Depends(get_db)
):
    """Export risk analysis report"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    version = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == document_id
    ).order_by(DocumentVersion.version_number.desc()).first()
    
    if not version:
        raise HTTPException(status_code=404, detail="No version found")
    
    risks = db.query(RiskAssessment).filter(
        RiskAssessment.document_version_id == version.id
    ).all()
    
    # Log audit
    audit = get_audit_service(db)
    audit.log_risk_action(
        action="risk_exported",
        document_id=document_id,
        risk_score=sum(r.risk_score for r in risks) // len(risks) if risks else 0,
        risk_level="N/A"
    )
    
    if format == "json":
        analyzer = RiskAnalyzer()
        risks_data = [{"dimension": r.risk_dimension, "type": r.risk_type, "score": r.risk_score, "level": r.risk_level} for r in risks]
        overall = analyzer.calculate_overall_score(risks_data)
        
        return {
            "document_id": document_id,
            "document_name": doc.name,
            "exported_at": datetime.utcnow().isoformat(),
            "overall_score": overall["score"],
            "overall_level": overall["level"],
            "risks": [
                {
                    "dimension": r.risk_dimension,
                    "type": r.risk_type,
                    "score": r.risk_score,
                    "level": r.risk_level,
                    "description": r.description,
                    "business_context": r.business_context,
                    "recommendation": r.recommendation,
                    "acknowledged": r.acknowledged == "true",
                    "acknowledged_action": r.acknowledged_action
                }
                for r in risks
            ]
        }
    
    elif format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Dimension", "Type", "Score", "Level", 
            "Description", "Business Context", "Recommendation",
            "Acknowledged", "Action"
        ])
        
        for risk in risks:
            writer.writerow([
                risk.risk_dimension,
                risk.risk_type,
                risk.risk_score,
                risk.risk_level,
                risk.description,
                risk.business_context or "",
                risk.recommendation or "",
                "Yes" if risk.acknowledged == "true" else "No",
                risk.acknowledged_action or ""
            ])
        
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={doc.name}_risk_report.csv"}
        )
