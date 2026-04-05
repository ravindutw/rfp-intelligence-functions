import uuid
from sqlalchemy import (
    Column, String, Text, Integer, BigInteger, Boolean,
    TIMESTAMP, ForeignKey, UniqueConstraint, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

Base = declarative_base()

# ============================================================================
# SQLAlchemy ORM Models
# ============================================================================

class RFPDocument(Base):
    __tablename__ = "rfp_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    client_name = Column(String(255))
    client_industry = Column(String(100))
    submission_deadline = Column(TIMESTAMP(timezone=True))
    document_type = Column(String(10), nullable=False)
    original_file_path = Column(String(1000), nullable=False)
    file_size = Column(BigInteger)
    file_format = Column(String(50))
    status = Column(String, server_default="Uploaded")
    total_questions = Column(Integer, server_default="0")
    answered_questions = Column(Integer, server_default="0")
    created_by = Column(UUID(as_uuid=True), nullable=False)
    assigned_to = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    last_accessed_at = Column(TIMESTAMP(timezone=True))

    __table_args__ = (
        CheckConstraint("document_type IN ('RFP', 'RFI', 'RFQ')", name="document_type_check"),
        CheckConstraint("answered_questions <= total_questions", name="valid_completion"),
    )


class RFPQuestion(Base):
    __tablename__ = "rfp_questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rfp_id = Column(UUID(as_uuid=True), ForeignKey("rfp_documents.id", ondelete="CASCADE"), nullable=False)
    question_text = Column(Text, nullable=False)
    question_category = Column(String(50))
    section_heading = Column(String(500))
    page_number = Column(Integer)
    sequence_number = Column(Integer)
    status = Column(String, server_default="Pending")
    difficulty_level = Column(Integer)
    is_mandatory = Column(Boolean, server_default="false")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("rfp_id", "sequence_number", name="unique_rfp_question_sequence"),
        CheckConstraint("difficulty_level BETWEEN 1 AND 5", name="rfp_questions_difficulty_level_check"),
    )


# ============================================================================
# Pydantic Models for API/Validation
# ============================================================================

class QuestionItem(BaseModel):
    """Extracted question from document"""
    id: Optional[str] = None
    text: str = Field(description="The exact question text")
    question_category: Optional[str] = None
    section_heading: Optional[str] = None
    page_number: Optional[int] = None
    sequence_number: Optional[int] = None
    difficulty_level: Optional[int] = Field(default=3, ge=1, le=5)
    is_mandatory: bool = Field(default=False)


class ContextItem(BaseModel):
    """Non-question content block"""
    id: Optional[str] = None
    text: str = Field(description="Context text")
    section_heading: Optional[str] = None
    page_number: Optional[int] = None


class ChunkExtractionResult(BaseModel):
    """Extraction result for a single chunk"""
    questions: List[QuestionItem] = Field(default_factory=list)
    context_blocks: List[ContextItem] = Field(default_factory=list)


class ExtractionEvent(BaseModel):
    """Event payload from SQS/S3"""
    event: str
    rfp_id: str
    s3_path: str
    timestamp: str


class ExtractionResult(BaseModel):
    """Final extraction result"""
    rfp_id: str
    filename: str
    total_questions: int
    total_context_blocks: int
    questions: List[QuestionItem]
    context_blocks: List[ContextItem]