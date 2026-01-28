from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import ARRAY
from datetime import datetime
import uuid
import enum

from database import Base

class MergeStatus(str, enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class DocumentComparison(Base):
    __tablename__ = "document_comparisons"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True)
    version1_id = Column(String, ForeignKey("document_versions.id"), nullable=False)
    version2_id = Column(String, ForeignKey("document_versions.id"), nullable=False)
    comparison_mode = Column(String(50), nullable=False)  # line-by-line, semantic, impact, clause, legal, timeline
    result = Column(JSON, nullable=True)  # Full comparison result
    summary = Column(JSON, nullable=True)  # Quick summary stats
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    
    # Stats
    total_changes = Column(Integer, default=0)
    critical_changes = Column(Integer, default=0)
    major_changes = Column(Integer, default=0)
    minor_changes = Column(Integer, default=0)
    similarity_score = Column(String(10), nullable=True)  # 0.0 - 1.0

class DocumentMerge(Base):
    __tablename__ = "document_merges"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True)
    source_version_ids = Column(JSON, nullable=False)  # List of version IDs
    base_version_id = Column(String, ForeignKey("document_versions.id"), nullable=True)
    merge_strategy = Column(String(50), nullable=False)  # CONSENSUS, MOST_RECENT, MANUAL
    status = Column(String(20), default=MergeStatus.IN_PROGRESS.value)
    result_version_id = Column(String, ForeignKey("document_versions.id"), nullable=True)
    conflicts = Column(JSON, nullable=True)  # List of conflicts
    conflicts_count = Column(Integer, default=0)
    resolved_conflicts = Column(JSON, nullable=True)  # Resolved decisions
    merged_content = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
