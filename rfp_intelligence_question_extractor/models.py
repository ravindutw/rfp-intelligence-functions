import uuid
from sqlalchemy import (
    Column, String, Text, Integer, Boolean,
    TIMESTAMP, ForeignKey, CheckConstraint, BigInteger, Numeric, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from typing import Optional, List

Base = declarative_base()

# ============================================================================
# SQLAlchemy ORM Models
# ============================================================================

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    role = Column(String(100), nullable=False)
    phone_number = Column(String(20))
    is_deleted = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint(r"email ~* '^\[?[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\]?$'", name="email_format"),
    )


class RFPDocument(Base):
    __tablename__ = "rfp_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    client_name = Column(String(255))
    client_industry = Column(String(100))
    submission_deadline = Column(TIMESTAMP(timezone=True))
    document_type = Column(String(10), nullable=False)
    original_file_path = Column(String(1000))
    file_name = Column(String(100))
    rfp_doc_url = Column(String(200))
    status = Column(String, server_default="PENDING")
    total_questions = Column(Integer, server_default="0")
    context = Column(Text)
    # completion_percentage is a GENERATED ALWAYS AS column — not mapped as a writable column
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

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
    sequence_number = Column(Integer)
    status = Column(String, server_default="Pending")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class RFPAnswer(Base):
    __tablename__ = "rfp_answers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id = Column(UUID(as_uuid=True), ForeignKey("rfp_questions.id", ondelete="CASCADE"), nullable=False)
    answer_text = Column(Text)
    generated_by_ai = Column(Boolean, server_default="false")
    confidence_score = Column(Numeric(3, 2))
    answer_status = Column(String(20))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("question_id", name="unique_question_answer"),
        CheckConstraint("confidence_score BETWEEN 0 AND 1", name="rfp_answers_confidence_score_check"),
    )


class AnswerVersion(Base):
    __tablename__ = "answer_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    answer_id = Column(UUID(as_uuid=True), ForeignKey("rfp_answers.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    answer_text_snapshot = Column(Text, nullable=False)
    change_type = Column(String(50), nullable=False)
    changed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    changed_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    change_reason = Column(Text)
    is_current = Column(Boolean, server_default="false")

    __table_args__ = (
        UniqueConstraint("answer_id", "version_number", name="unique_answer_version"),
    )




class UsageLog(Base):
    __tablename__ = "usage_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    rfp_id = Column(UUID(as_uuid=True), ForeignKey("rfp_documents.id", ondelete="SET NULL"), nullable=True)
    action_type = Column(String(50), nullable=False)
    ai_tokens_used = Column(Integer, server_default="0")
    ai_model_used = Column(String(100))
    status = Column(String(20), nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), server_default=func.now())
    usage_metadata = Column("metadata", JSONB)


class RFPStatusHistory(Base):
    __tablename__ = "rfp_status_history"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    rfp_id = Column(UUID(as_uuid=True), ForeignKey("rfp_documents.id"))
    status = Column(String(50))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())



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
    user_id: uuid.UUID
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