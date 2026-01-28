from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Float, JSON
from datetime import datetime
import uuid
import enum

from database import Base

class RiskLevel(str, enum.Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"

class ExtractedEntity(Base):
    __tablename__ = "extracted_entities"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_version_id = Column(String, ForeignKey("document_versions.id"), nullable=False)
    entity_type = Column(String(100), nullable=False)  # parties, dates, payment_terms, penalties, etc.
    entity_data = Column(JSON, nullable=False)  # Structured data for the entity
    confidence = Column(Float, default=0.0)  # 0.0 - 1.0
    extracted_at = Column(DateTime, default=datetime.utcnow)
    is_verified = Column(String(10), default="false")  # User verified

class RiskAssessment(Base):
    __tablename__ = "risk_assessments"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_version_id = Column(String, ForeignKey("document_versions.id"), nullable=False)
    risk_dimension = Column(String(100), nullable=False)  # financial, temporal, legal, operational
    risk_type = Column(String(100), nullable=False)  # payment_days, liability_cap, etc.
    risk_score = Column(Integer, default=0)  # 0-100
    risk_level = Column(String(20), default=RiskLevel.GREEN.value)
    description = Column(Text, nullable=True)
    business_context = Column(Text, nullable=True)  # Why this matters
    recommendation = Column(Text, nullable=True)  # How to mitigate
    assessed_at = Column(DateTime, default=datetime.utcnow)
    acknowledged = Column(String(10), default="false")
    acknowledged_action = Column(String(50), nullable=True)  # accept, mitigate, escalate
