"""
Enterprise Audit Service for Compliance Logging
Tracks all significant actions for audit trail
"""
import json
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from models.audit import AuditLog


class AuditService:
    """Service for logging audit events"""
    
    # Action types
    ACTIONS = {
        # Document actions
        "document_uploaded": "Document uploaded",
        "document_deleted": "Document deleted",
        "document_archived": "Document archived",
        "document_restored": "Document restored",
        "document_viewed": "Document viewed",
        
        # Comparison actions
        "comparison_created": "Comparison performed",
        "comparison_viewed": "Comparison viewed",
        "comparison_exported": "Comparison exported",
        
        # Merge actions
        "merge_started": "Merge operation started",
        "merge_conflict_resolved": "Merge conflict resolved",
        "merge_completed": "Merge completed",
        "merge_cancelled": "Merge cancelled",
        
        # Risk actions
        "risk_analyzed": "Risk analysis performed",
        "risk_acknowledged": "Risk acknowledged",
        "risk_exported": "Risk report exported",
        
        # Extraction actions
        "entities_extracted": "Entities extracted",
        "entity_updated": "Entity manually updated",
        "entities_exported": "Entities exported",
        
        # System actions
        "system_error": "System error occurred",
        "api_rate_limited": "API rate limit reached",
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def log(
        self,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        tenant_id: str = "default",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """Log an audit event"""
        
        audit_entry = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=json.dumps(details, ensure_ascii=False) if details else None,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=datetime.utcnow()
        )
        
        self.db.add(audit_entry)
        self.db.commit()
        
        return audit_entry
    
    def log_document_action(
        self,
        action: str,
        document_id: str,
        document_name: str,
        details: Optional[Dict] = None,
        **kwargs
    ) -> AuditLog:
        """Log a document-related action"""
        full_details = {"document_name": document_name}
        if details:
            full_details.update(details)
        
        return self.log(
            action=action,
            resource_type="document",
            resource_id=document_id,
            details=full_details,
            **kwargs
        )
    
    def log_comparison(
        self,
        doc1_id: str,
        doc2_id: str,
        mode: str,
        changes_count: int,
        **kwargs
    ) -> AuditLog:
        """Log a comparison action"""
        return self.log(
            action="comparison_created",
            resource_type="comparison",
            resource_id=f"{doc1_id}:{doc2_id}",
            details={
                "document1_id": doc1_id,
                "document2_id": doc2_id,
                "mode": mode,
                "changes_count": changes_count
            },
            **kwargs
        )
    
    def log_merge(
        self,
        merge_id: str,
        action: str,
        document_ids: list,
        conflicts_count: int = 0,
        **kwargs
    ) -> AuditLog:
        """Log a merge action"""
        return self.log(
            action=action,
            resource_type="merge",
            resource_id=merge_id,
            details={
                "document_ids": document_ids,
                "conflicts_count": conflicts_count
            },
            **kwargs
        )
    
    def log_risk_action(
        self,
        action: str,
        document_id: str,
        risk_score: int,
        risk_level: str,
        **kwargs
    ) -> AuditLog:
        """Log a risk-related action"""
        return self.log(
            action=action,
            resource_type="risk",
            resource_id=document_id,
            details={
                "risk_score": risk_score,
                "risk_level": risk_level
            },
            **kwargs
        )
    
    def get_audit_trail(
        self,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        action: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list:
        """Get audit trail with filters"""
        query = self.db.query(AuditLog)
        
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if resource_id:
            query = query.filter(AuditLog.resource_id == resource_id)
        if action:
            query = query.filter(AuditLog.action == action)
        if from_date:
            query = query.filter(AuditLog.created_at >= from_date)
        if to_date:
            query = query.filter(AuditLog.created_at <= to_date)
        
        total = query.count()
        entries = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
        
        return {
            "entries": [self._serialize_entry(e) for e in entries],
            "total": total,
            "limit": limit,
            "offset": offset
        }
    
    def get_document_history(self, document_id: str) -> list:
        """Get complete history for a document"""
        entries = self.db.query(AuditLog).filter(
            AuditLog.resource_id == document_id
        ).order_by(AuditLog.created_at.desc()).all()
        
        return [self._serialize_entry(e) for e in entries]
    
    def _serialize_entry(self, entry: AuditLog) -> Dict:
        """Serialize audit entry to dict"""
        return {
            "id": entry.id,
            "action": entry.action,
            "action_description": self.ACTIONS.get(entry.action, entry.action),
            "resource_type": entry.resource_type,
            "resource_id": entry.resource_id,
            "details": json.loads(entry.details) if entry.details else None,
            "user_id": entry.user_id,
            "ip_address": entry.ip_address,
            "created_at": entry.created_at.isoformat() if entry.created_at else None
        }


def get_audit_service(db: Session) -> AuditService:
    """Factory function to get audit service"""
    return AuditService(db)
