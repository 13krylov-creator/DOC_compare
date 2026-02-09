"""
Enterprise Merge Router
Multi-way document merge with conflict resolution
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
import uuid

from database import get_db
from models.document import Document, DocumentVersion
from models.user import User
from models.comparison import DocumentMerge, MergeStatus
from services.merge_engine import MergeEngine
from services.audit_service import get_audit_service
from services.auth_service import get_current_user

router = APIRouter()

MERGE_STRATEGIES = ["MOST_RECENT", "MANUAL"]


class MergeRequest(BaseModel):
    document_ids: List[str]
    merge_strategy: str = "MOST_RECENT"
    base_version_id: Optional[str] = None


class ConflictVariant(BaseModel):
    source: str
    content: str
    line_count: int = 0
    votes: Optional[int] = None


class ConflictItem(BaseModel):
    index: int
    location: str
    type: str = "REPLACE"
    variants: List[ConflictVariant]
    consensus_variant: Optional[int] = None
    similarity: Optional[float] = None
    analysis: Optional[dict] = None


class MergeResponse(BaseModel):
    id: str
    status: str
    conflicts: List[ConflictItem]
    conflicts_count: int
    auto_resolved: int = 0
    merged_content_preview: Optional[str] = None
    merge_stats: Optional[dict] = None
    recommendation: Optional[str] = None


class ResolveConflictRequest(BaseModel):
    conflict_index: int
    chosen_variant_index: int


class BulkResolveRequest(BaseModel):
    resolutions: List[ResolveConflictRequest]


@router.post("/", response_model=MergeResponse)
async def create_merge(
    request: MergeRequest, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start a merge operation (auth required, validates document ownership)"""
    if request.merge_strategy not in MERGE_STRATEGIES:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid merge strategy. Allowed: {MERGE_STRATEGIES}"
        )
    
    if len(request.document_ids) < 2:
        raise HTTPException(
            status_code=400, 
            detail="At least 2 documents required for merge"
        )
    
    if len(request.document_ids) > 10:
        raise HTTPException(
            status_code=400, 
            detail="Maximum 10 documents can be merged at once"
        )
    
    # Collect document contents (validate ownership)
    contents = []
    for doc_id in request.document_ids:
        doc = db.query(Document).filter(
            Document.id == doc_id,
            Document.uploaded_by == current_user.id
        ).first()
        if doc:
            contents.append({
                "id": doc_id, 
                "content": doc.extracted_text or "", 
                "name": doc.name
            })
        else:
            version = db.query(DocumentVersion).filter(DocumentVersion.id == doc_id).first()
            if version:
                # Check ownership via parent document
                parent_doc = db.query(Document).filter(
                    Document.id == version.document_id,
                    Document.uploaded_by == current_user.id
                ).first()
                if parent_doc:
                    contents.append({
                        "id": doc_id, 
                        "content": version.content or "", 
                        "name": f"Version {version.version_number}"
                    })
                else:
                    raise HTTPException(status_code=404, detail=f"Document {doc_id} not found or access denied")
            else:
                raise HTTPException(status_code=404, detail=f"Document {doc_id} not found or access denied")
    
    # Perform merge
    merge_engine = MergeEngine()
    merge_result = merge_engine.merge(
        contents, 
        request.merge_strategy,
        request.base_version_id
    )
    
    merge_id = str(uuid.uuid4())
    
    # Determine status
    has_conflicts = len([c for c in merge_result["conflicts"] if c.get("consensus_variant") is None]) > 0
    status = MergeStatus.IN_PROGRESS.value if has_conflicts else MergeStatus.COMPLETED.value
    
    # Save merge to database
    db_merge = DocumentMerge(
        id=merge_id,
        tenant_id="default",
        source_version_ids=request.document_ids,
        base_version_id=request.base_version_id,
        merge_strategy=request.merge_strategy,
        status=status,
        conflicts=merge_result["conflicts"],
        conflicts_count=len(merge_result["conflicts"]),
        merged_content=merge_result["merged_content"],
        created_at=datetime.utcnow()
    )
    db.add(db_merge)
    db.commit()
    
    # Log audit
    audit = get_audit_service(db)
    audit.log_merge(
        merge_id=merge_id,
        action="merge_started",
        document_ids=request.document_ids,
        conflicts_count=len(merge_result["conflicts"])
    )
    
    # Build response
    conflicts_response = []
    for c in merge_result["conflicts"]:
        variants = [
            ConflictVariant(
                source=v.get("source", "Unknown"),
                content=v.get("content", ""),
                line_count=v.get("line_count", 0),
                votes=v.get("votes")
            )
            for v in c.get("variants", [])
        ]
        conflicts_response.append(ConflictItem(
            index=c["index"],
            location=c.get("location", ""),
            type=c.get("type", "REPLACE"),
            variants=variants,
            consensus_variant=c.get("consensus_variant"),
            similarity=c.get("similarity"),
            analysis=c.get("analysis")
        ))
    
    return MergeResponse(
        id=merge_id,
        status=status,
        conflicts=conflicts_response,
        conflicts_count=len(merge_result["conflicts"]),
        auto_resolved=merge_result.get("auto_resolved", 0),
        merged_content_preview=merge_result["merged_content"][:1000] if merge_result["merged_content"] else None,
        merge_stats=merge_result.get("merge_stats"),
        recommendation=merge_engine._get_merge_recommendation(merge_result)
    )


@router.post("/preview")
async def preview_merge(
    request: MergeRequest, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Preview merge without saving (auth required)"""
    if len(request.document_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 documents required")
    
    contents = []
    for doc_id in request.document_ids:
        doc = db.query(Document).filter(
            Document.id == doc_id,
            Document.uploaded_by == current_user.id
        ).first()
        if doc:
            contents.append({"id": doc_id, "content": doc.extracted_text or "", "name": doc.name})
        else:
            version = db.query(DocumentVersion).filter(DocumentVersion.id == doc_id).first()
            if version:
                parent_doc = db.query(Document).filter(
                    Document.id == version.document_id,
                    Document.uploaded_by == current_user.id
                ).first()
                if parent_doc:
                    contents.append({"id": doc_id, "content": version.content or "", "name": f"Version {version.version_number}"})
                else:
                    raise HTTPException(status_code=404, detail=f"Document {doc_id} not found or access denied")
            else:
                raise HTTPException(status_code=404, detail=f"Document {doc_id} not found or access denied")
    
    merge_engine = MergeEngine()
    result = merge_engine.preview_merge(contents, request.merge_strategy)
    
    return {
        "preview": True,
        "can_auto_merge": result.get("can_auto_merge", False),
        "estimated_conflicts": result.get("estimated_conflicts", 0),
        "auto_resolved": result.get("auto_resolved", 0),
        "recommendation": result.get("recommendation"),
        "merge_stats": result.get("merge_stats")
    }


@router.get("/{merge_id}/status")
async def get_merge_status(merge_id: str, db: Session = Depends(get_db)):
    """Get merge operation status"""
    merge = db.query(DocumentMerge).filter(DocumentMerge.id == merge_id).first()
    if not merge:
        raise HTTPException(status_code=404, detail="Merge not found")
    
    resolved_count = len(merge.resolved_conflicts or [])
    unresolved_count = merge.conflicts_count - resolved_count
    
    return {
        "id": merge.id,
        "status": merge.status,
        "conflicts_count": merge.conflicts_count,
        "resolved_count": resolved_count,
        "unresolved_count": unresolved_count,
        "progress_percent": int((resolved_count / merge.conflicts_count * 100) if merge.conflicts_count > 0 else 100),
        "created_at": merge.created_at,
        "completed_at": merge.completed_at
    }


@router.get("/{merge_id}/conflicts")
async def get_merge_conflicts(merge_id: str, db: Session = Depends(get_db)):
    """Get all conflicts for a merge"""
    merge = db.query(DocumentMerge).filter(DocumentMerge.id == merge_id).first()
    if not merge:
        raise HTTPException(status_code=404, detail="Merge not found")
    
    resolved_indices = {r["conflict_index"] for r in (merge.resolved_conflicts or [])}
    
    conflicts_with_status = []
    for c in (merge.conflicts or []):
        c_copy = dict(c)
        c_copy["is_resolved"] = c["index"] in resolved_indices
        if c_copy["is_resolved"]:
            resolution = next((r for r in merge.resolved_conflicts if r["conflict_index"] == c["index"]), None)
            if resolution:
                c_copy["chosen_variant_index"] = resolution["chosen_variant_index"]
        conflicts_with_status.append(c_copy)
    
    return {
        "merge_id": merge.id,
        "conflicts": conflicts_with_status,
        "resolved_conflicts": merge.resolved_conflicts or [],
        "status": merge.status,
        "total_conflicts": merge.conflicts_count,
        "resolved_count": len(resolved_indices)
    }


@router.post("/{merge_id}/resolve-conflict")
async def resolve_conflict(
    merge_id: str, 
    request: ResolveConflictRequest, 
    db: Session = Depends(get_db)
):
    """Resolve a specific conflict"""
    merge = db.query(DocumentMerge).filter(DocumentMerge.id == merge_id).first()
    if not merge:
        raise HTTPException(status_code=404, detail="Merge not found")
    
    if merge.status == MergeStatus.COMPLETED.value:
        raise HTTPException(status_code=400, detail="Merge already completed")
    
    # Validate conflict index
    if request.conflict_index >= merge.conflicts_count:
        raise HTTPException(status_code=400, detail="Invalid conflict index")
    
    # Check if already resolved
    resolved = merge.resolved_conflicts or []
    if any(r["conflict_index"] == request.conflict_index for r in resolved):
        # Update existing resolution
        for r in resolved:
            if r["conflict_index"] == request.conflict_index:
                r["chosen_variant_index"] = request.chosen_variant_index
                break
    else:
        resolved.append({
            "conflict_index": request.conflict_index, 
            "chosen_variant_index": request.chosen_variant_index
        })
    
    merge.resolved_conflicts = resolved
    
    # Check if all conflicts resolved
    unresolved = [c for c in merge.conflicts if c.get("consensus_variant") is None]
    if len(resolved) >= len(unresolved):
        # Apply resolutions
        merge_engine = MergeEngine()
        final_content = merge_engine.apply_resolutions(
            merge.merged_content, 
            merge.conflicts, 
            resolved
        )
        merge.merged_content = final_content
        merge.status = MergeStatus.COMPLETED.value
        merge.completed_at = datetime.utcnow()
        
        # Log completion
        audit = get_audit_service(db)
        audit.log_merge(
            merge_id=merge_id,
            action="merge_completed",
            document_ids=merge.source_version_ids,
            conflicts_count=merge.conflicts_count
        )
    
    db.commit()
    
    remaining = len(unresolved) - len(resolved)
    return {
        "message": "Conflict resolved",
        "conflict_index": request.conflict_index,
        "remaining_conflicts": max(0, remaining),
        "status": merge.status,
        "is_complete": merge.status == MergeStatus.COMPLETED.value
    }


@router.post("/{merge_id}/resolve-bulk")
async def resolve_conflicts_bulk(
    merge_id: str, 
    request: BulkResolveRequest, 
    db: Session = Depends(get_db)
):
    """Resolve multiple conflicts at once"""
    merge = db.query(DocumentMerge).filter(DocumentMerge.id == merge_id).first()
    if not merge:
        raise HTTPException(status_code=404, detail="Merge not found")
    
    if merge.status == MergeStatus.COMPLETED.value:
        raise HTTPException(status_code=400, detail="Merge already completed")
    
    resolved = merge.resolved_conflicts or []
    
    for resolution in request.resolutions:
        # Update or add resolution
        existing = next((r for r in resolved if r["conflict_index"] == resolution.conflict_index), None)
        if existing:
            existing["chosen_variant_index"] = resolution.chosen_variant_index
        else:
            resolved.append({
                "conflict_index": resolution.conflict_index,
                "chosen_variant_index": resolution.chosen_variant_index
            })
    
    merge.resolved_conflicts = resolved
    
    # Check completion
    unresolved = [c for c in merge.conflicts if c.get("consensus_variant") is None]
    if len(resolved) >= len(unresolved):
        merge_engine = MergeEngine()
        final_content = merge_engine.apply_resolutions(
            merge.merged_content, 
            merge.conflicts, 
            resolved
        )
        merge.merged_content = final_content
        merge.status = MergeStatus.COMPLETED.value
        merge.completed_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "message": f"Resolved {len(request.resolutions)} conflicts",
        "remaining_conflicts": max(0, len(unresolved) - len(resolved)),
        "status": merge.status
    }


@router.post("/{merge_id}/finalize")
async def finalize_merge(
    merge_id: str, 
    name: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Finalize merge and create new document"""
    merge = db.query(DocumentMerge).filter(DocumentMerge.id == merge_id).first()
    if not merge:
        raise HTTPException(status_code=404, detail="Merge not found")
    
    # Count truly unresolved conflicts (those without consensus_variant and not manually resolved)
    resolved_indices = {r["conflict_index"] for r in (merge.resolved_conflicts or [])}
    unresolved = [
        c for c in (merge.conflicts or []) 
        if c.get("consensus_variant") is None and c["index"] not in resolved_indices
    ]
    
    if unresolved:
        raise HTTPException(
            status_code=400, 
            detail=f"Merge not completed. {len(unresolved)} conflicts remaining"
        )
    
    # Apply all resolutions to get final content
    merge_engine = MergeEngine()
    final_content = merge.merged_content or ""
    
    # First apply consensus variants
    for conflict in (merge.conflicts or []):
        if conflict.get("consensus_variant") is not None:
            variant_idx = conflict["consensus_variant"]
            if variant_idx < len(conflict.get("variants", [])):
                replacement = conflict["variants"][variant_idx].get("content", "")
                if replacement in ["(deleted)", "(absent)"]:
                    replacement = ""
                final_content = final_content.replace(f"<<<CONFLICT_{conflict['index']}>>>", replacement)
    
    # Then apply manual resolutions
    if merge.resolved_conflicts:
        final_content = merge_engine.apply_resolutions(
            final_content, 
            merge.conflicts or [], 
            merge.resolved_conflicts
        )
    
    # Create merged document
    doc_name = name or f"Merged Document {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    new_doc = Document(
        id=str(uuid.uuid4()),
        tenant_id="default",
        name=doc_name,
        description=f"Merged from {len(merge.source_version_ids)} documents using {merge.merge_strategy} strategy",
        file_path="",
        original_filename="merged.txt",
        uploaded_at=datetime.utcnow(),
        status="READY",
        extracted_text=final_content,
        file_size=len(final_content.encode('utf-8')) if final_content else 0
    )
    db.add(new_doc)
    
    # Create version
    new_version = DocumentVersion(
        id=str(uuid.uuid4()),
        document_id=new_doc.id,
        version_number=1,
        content=final_content,
        created_at=datetime.utcnow(),
        change_summary=f"Created by merging {len(merge.source_version_ids)} documents"
    )
    db.add(new_version)
    
    merge.result_version_id = new_version.id
    merge.merged_content = final_content
    merge.status = MergeStatus.COMPLETED.value
    merge.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(new_doc)
    
    # Log audit
    audit = get_audit_service(db)
    audit.log_document_action(
        action="document_uploaded",
        document_id=new_doc.id,
        document_name=doc_name,
        details={"source": "merge", "merge_id": merge_id}
    )
    
    return {
        "message": "Merge finalized",
        "new_document_id": new_doc.id,
        "new_version_id": new_version.id,
        "document_name": doc_name,
        "content_size": len(final_content) if final_content else 0
    }


@router.get("/{merge_id}/content")
async def get_merged_content(merge_id: str, db: Session = Depends(get_db)):
    """Get the merged content"""
    merge = db.query(DocumentMerge).filter(DocumentMerge.id == merge_id).first()
    if not merge:
        raise HTTPException(status_code=404, detail="Merge not found")
    
    return {
        "merge_id": merge.id,
        "status": merge.status,
        "content": merge.merged_content,
        "has_unresolved_conflicts": "<<<CONFLICT_" in (merge.merged_content or "")
    }


@router.delete("/{merge_id}")
async def cancel_merge(merge_id: str, db: Session = Depends(get_db)):
    """Cancel a merge operation"""
    merge = db.query(DocumentMerge).filter(DocumentMerge.id == merge_id).first()
    if not merge:
        raise HTTPException(status_code=404, detail="Merge not found")
    
    if merge.status == MergeStatus.COMPLETED.value and merge.result_version_id:
        raise HTTPException(
            status_code=400, 
            detail="Cannot cancel completed and finalized merge"
        )
    
    merge.status = MergeStatus.FAILED.value
    db.commit()
    
    # Log audit
    audit = get_audit_service(db)
    audit.log_merge(
        merge_id=merge_id,
        action="merge_cancelled",
        document_ids=merge.source_version_ids,
        conflicts_count=merge.conflicts_count
    )
    
    return {"message": "Merge cancelled", "id": merge_id}
