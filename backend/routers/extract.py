"""
Enterprise Entity Extraction Router
Extract structured data from documents
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any
import csv
import io
import re

from database import get_db
from models.document import Document, DocumentVersion
from models.extraction import ExtractedEntity
from services.llm_client import LLMClient
from services.audit_service import get_audit_service

router = APIRouter()


class EntityData(BaseModel):
    entity_type: str
    entity_data: dict
    confidence: float
    is_verified: bool = False


class ExtractionResult(BaseModel):
    document_id: str
    document_name: str
    extraction_timestamp: datetime
    confidence_overall: float
    entities: List[EntityData]
    summary: Optional[Dict[str, Any]] = None


class UpdateEntityRequest(BaseModel):
    entity_data: dict


def generate_summary(entities) -> Dict[str, Any]:
    """Generate extraction summary"""
    summary = {
        "total_entities": len(entities),
        "verified_count": sum(1 for e in entities if e.is_verified == "true"),
        "entity_types": [e.entity_type for e in entities]
    }
    
    for entity in entities:
        if entity.entity_type == "payment_terms" and entity.entity_data:
            if "total_amount" in entity.entity_data:
                summary["total_amount"] = entity.entity_data["total_amount"]
                summary["currency"] = entity.entity_data.get("currency", "RUB")
        
        if entity.entity_type == "dates" and entity.entity_data:
            if "effective_date" in entity.entity_data:
                summary["effective_date"] = entity.entity_data["effective_date"]
            if "expiration_date" in entity.entity_data:
                summary["expiration_date"] = entity.entity_data["expiration_date"]
        
        if entity.entity_type == "parties" and entity.entity_data:
            if isinstance(entity.entity_data, list):
                summary["parties_count"] = len(entity.entity_data)
    
    return summary


def flatten_dict(d: dict, parent_key: str = '', sep: str = '.') -> dict:
    """Flatten nested dictionary"""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            for i, item in enumerate(v):
                if isinstance(item, dict):
                    items.extend(flatten_dict(item, f"{new_key}[{i}]", sep=sep).items())
                else:
                    items.append((f"{new_key}[{i}]", item))
        else:
            items.append((new_key, v))
    return dict(items)


def create_ical_event(summary: str, date_str: str, description: str) -> List[str]:
    """Create iCal event lines"""
    match = re.match(r'(\d{1,2})[./](\d{1,2})[./](\d{2,4})', date_str)
    if not match:
        return []
    
    day, month, year = match.groups()
    if len(year) == 2:
        year = "20" + year
    
    date_formatted = f"{year}{month.zfill(2)}{day.zfill(2)}"
    
    return [
        "BEGIN:VEVENT",
        f"DTSTART;VALUE=DATE:{date_formatted}",
        f"DTEND;VALUE=DATE:{date_formatted}",
        f"SUMMARY:{summary}",
        f"DESCRIPTION:{description}",
        f"UID:{date_formatted}-{hash(summary)}@documentcompare",
        "END:VEVENT"
    ]


def find_changes(data1: Any, data2: Any) -> List[Dict]:
    """Find changes between two data structures"""
    changes = []
    
    if isinstance(data1, dict) and isinstance(data2, dict):
        all_keys = set(data1.keys()) | set(data2.keys())
        for key in all_keys:
            val1 = data1.get(key)
            val2 = data2.get(key)
            if val1 != val2:
                changes.append({
                    "field": key,
                    "old_value": val1,
                    "new_value": val2
                })
    elif data1 != data2:
        changes.append({
            "field": "value",
            "old_value": data1,
            "new_value": data2
        })
    
    return changes


@router.get("/documents/{document_id}", response_model=ExtractionResult)
async def extract_entities(
    document_id: str,
    force_refresh: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Extract structured entities from document"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    version = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == document_id
    ).order_by(DocumentVersion.version_number.desc()).first()
    
    if not version:
        raise HTTPException(status_code=404, detail="No version found")
    
    existing = db.query(ExtractedEntity).filter(
        ExtractedEntity.document_version_id == version.id
    ).all()
    
    if existing and not force_refresh:
        avg_confidence = sum(e.confidence for e in existing) / len(existing) if existing else 0
        
        return ExtractionResult(
            document_id=document_id,
            document_name=doc.name,
            extraction_timestamp=existing[0].extracted_at if existing else datetime.utcnow(),
            confidence_overall=round(avg_confidence, 2),
            entities=[
                EntityData(
                    entity_type=e.entity_type,
                    entity_data=e.entity_data,
                    confidence=e.confidence,
                    is_verified=e.is_verified == "true"
                )
                for e in existing
            ],
            summary=generate_summary(existing)
        )
    
    if force_refresh and existing:
        for old in existing:
            db.delete(old)
        db.commit()
    
    llm_client = LLMClient()
    extracted = llm_client.extract_entities(doc.extracted_text or "")
    
    for entity_type, entity_data in extracted.items():
        if entity_data:
            entity = ExtractedEntity(
                document_version_id=version.id,
                entity_type=entity_type,
                entity_data=entity_data if isinstance(entity_data, dict) else {"data": entity_data},
                confidence=0.85,
                extracted_at=datetime.utcnow()
            )
            db.add(entity)
    
    db.commit()
    
    saved_entities = db.query(ExtractedEntity).filter(
        ExtractedEntity.document_version_id == version.id
    ).all()
    
    audit = get_audit_service(db)
    audit.log(
        action="entities_extracted",
        resource_type="extraction",
        resource_id=document_id,
        details={"entity_types": list(extracted.keys())}
    )
    
    avg_confidence = sum(e.confidence for e in saved_entities) / len(saved_entities) if saved_entities else 0
    
    return ExtractionResult(
        document_id=document_id,
        document_name=doc.name,
        extraction_timestamp=datetime.utcnow(),
        confidence_overall=round(avg_confidence, 2),
        entities=[
            EntityData(
                entity_type=e.entity_type,
                entity_data=e.entity_data,
                confidence=e.confidence,
                is_verified=e.is_verified == "true"
            )
            for e in saved_entities
        ],
        summary=generate_summary(saved_entities)
    )


@router.put("/documents/{document_id}/{entity_type}/{entity_id}")
async def update_entity(
    document_id: str,
    entity_type: str,
    entity_id: str,
    request: UpdateEntityRequest,
    db: Session = Depends(get_db)
):
    """Update extracted entity"""
    entity = db.query(ExtractedEntity).filter(ExtractedEntity.id == entity_id).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    old_data = entity.entity_data
    entity.entity_data = request.entity_data
    entity.is_verified = "true"
    entity.confidence = 1.0
    db.commit()
    
    audit = get_audit_service(db)
    audit.log(
        action="entity_updated",
        resource_type="extraction",
        resource_id=entity_id,
        details={"entity_type": entity_type, "old_data": old_data, "new_data": request.entity_data}
    )
    
    return {"message": "Entity updated", "id": entity_id, "is_verified": True}


@router.get("/documents/{document_id}/export")
async def export_entities(
    document_id: str,
    format: str = Query("json", enum=["json", "csv", "ical"]),
    db: Session = Depends(get_db)
):
    """Export extracted entities"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    version = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == document_id
    ).order_by(DocumentVersion.version_number.desc()).first()
    
    if not version:
        raise HTTPException(status_code=404, detail="No version found")
    
    entities = db.query(ExtractedEntity).filter(
        ExtractedEntity.document_version_id == version.id
    ).all()
    
    audit = get_audit_service(db)
    audit.log(action="entities_exported", resource_type="extraction", resource_id=document_id, details={"format": format})
    
    if format == "json":
        return {
            "document_id": document_id,
            "document_name": doc.name,
            "exported_at": datetime.utcnow().isoformat(),
            "entities": {e.entity_type: e.entity_data for e in entities}
        }
    
    elif format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Entity Type", "Key", "Value", "Confidence", "Verified"])
        
        for entity in entities:
            if isinstance(entity.entity_data, dict):
                for key, value in flatten_dict(entity.entity_data).items():
                    writer.writerow([entity.entity_type, key, str(value), entity.confidence, "Yes" if entity.is_verified == "true" else "No"])
            else:
                writer.writerow([entity.entity_type, "value", str(entity.entity_data), entity.confidence, "Yes" if entity.is_verified == "true" else "No"])
        
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={doc.name}_entities.csv"}
        )
    
    elif format == "ical":
        dates_entity = next((e for e in entities if e.entity_type == "dates"), None)
        
        ical_lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//DocumentCompare//EN",
            f"X-WR-CALNAME:{doc.name} - Key Dates"
        ]
        
        if dates_entity and dates_entity.entity_data:
            dates = dates_entity.entity_data
            if dates.get("effective_date"):
                ical_lines.extend(create_ical_event(f"Contract Start: {doc.name}", dates["effective_date"], "Contract effective date"))
            if dates.get("expiration_date"):
                ical_lines.extend(create_ical_event(f"Contract Expiry: {doc.name}", dates["expiration_date"], "Contract expiration date"))
        
        ical_lines.append("END:VCALENDAR")
        
        output = "\r\n".join(ical_lines)
        return StreamingResponse(
            iter([output]),
            media_type="text/calendar",
            headers={"Content-Disposition": f"attachment; filename={doc.name}_dates.ics"}
        )
