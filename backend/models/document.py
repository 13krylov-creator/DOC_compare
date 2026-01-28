from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from database import Base

class DocumentStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PROCESSING = "PROCESSING"
    READY = "READY"
    ERROR = "ERROR"

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    file_path = Column(String(512), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=True)
    page_count = Column(Integer, nullable=True)
    uploaded_by = Column(String, ForeignKey("users.id"), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default=DocumentStatus.DRAFT.value)
    content_hash = Column(String(256), nullable=True)
    extracted_text = Column(Text, nullable=True)
    folder = Column(String(255), nullable=True)  # Virtual folder for grouping
    is_archived = Column(String(10), default="false")
    
    # Relationships
    tenant = relationship("Tenant", back_populates="documents")
    uploaded_by_user = relationship("User", back_populates="documents")
    versions = relationship("DocumentVersion", back_populates="document", order_by="DocumentVersion.version_number")

class DocumentVersion(Base):
    __tablename__ = "document_versions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    version_number = Column(Integer, nullable=False, default=1)
    content = Column(Text, nullable=True)
    file_path = Column(String(512), nullable=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    parent_version_id = Column(String, ForeignKey("document_versions.id"), nullable=True)
    change_summary = Column(Text, nullable=True)
    change_count = Column(Integer, default=0)
    critical_changes = Column(Integer, default=0)
    major_changes = Column(Integer, default=0)
    minor_changes = Column(Integer, default=0)
    
    # Relationships
    document = relationship("Document", back_populates="versions")
    parent_version = relationship("DocumentVersion", remote_side=[id])
    comparisons_as_v1 = relationship("DocumentComparison", foreign_keys="DocumentComparison.version1_id")
    comparisons_as_v2 = relationship("DocumentComparison", foreign_keys="DocumentComparison.version2_id")
