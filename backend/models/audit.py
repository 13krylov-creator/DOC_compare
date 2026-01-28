from sqlalchemy import Column, String, DateTime, ForeignKey
from datetime import datetime
import uuid

from database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    resource_type = Column(String(100), nullable=False)  # document, comparison, merge, etc.
    resource_id = Column(String, nullable=True)
    action = Column(String(100), nullable=False)  # created, updated, deleted, compared, merged
    details = Column(String, nullable=True)  # JSON string with additional details
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
