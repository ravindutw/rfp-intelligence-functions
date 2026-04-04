# RFP Intelligence Project
# Question Extractor - Single File Version
# © 2026-Y2-S2-KU-DS-15
# Version: 1.0

import os
import json
import uuid
import tempfile
from pathlib import Path
from difflib import SequenceMatcher
from typing import List
from dataclasses import dataclass, field, asdict

import boto3
from botocore.exceptions import ClientError

# LangChain imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PDFPlumberLoader,
    UnstructuredExcelLoader,
    CSVLoader,
    Docx2txtLoader
)

# SQLAlchemy for database
from sqlalchemy import create_engine, Column, String, Text, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

# Pydantic for output parsing
from pydantic import BaseModel, Field


# ============================================================================
# SECTION 1: Pydantic Models for LLM Output
# ============================================================================

class QuestionItem(BaseModel):
    id: str = Field(default="", description="Unique identifier for the question")
    text: str = Field(description="The exact question text, preserved verbatim")


class ContextItem(BaseModel):
    id: str = Field(default="", description="Unique identifier for the context block")
    text: str = Field(description="The context text")


class ChunkExtractionResult(BaseModel):
    questions: List[QuestionItem] = Field(default_factory=list)
    context_blocks: List[ContextItem] = Field(default_factory=list)


# ============================================================================
# SECTION 2: Database Models
# ============================================================================

Base = declarative_base()


class RFPDocument(Base):
    __tablename__ = "rfp_documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=False)
    s3_path = Column(String(500), nullable=False)
    total_questions = Column(Integer, default=0)
    total_context_blocks = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    context_blocks = Column(JSON, default=list)


class RFPQuestion(Base):
    __tablename__ = "rfp_questions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("rfp_documents.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("RFPDocument", back_populates="questions")


RFPDocument.questions = relationship("RFPQuestion", back_populates="document", cascade="all, delete-orphan")


# ============================================================================
# SECTION 3: AWS Secrets Manager
# ============================================================================

class AWSSecretsManager:
    @staticmethod
    def get_secret(secret_name: str):
        aws_region = os.environ.get('AWS_REGION_NAME', 'ap-southeast-1')
        session = boto3.session.Session()
        client = session.client(service_name='secretsmanager', region_name=aws_region)

        try:
            response = client.get_secret_value(SecretId=secret_name)
            return response['SecretString']
        except ClientError as e:
            print(f"Secrets Manager error: {e}")
            raise e


# ============================================================================
# SECTION 4: Database Manager
# ============================================================================

class DatabaseManager:
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._init_db()

    def _init_db(self):
        db_secret_name = os.environ.get("DB_SECRET_NAME")
        if db_secret_name:
            db_secret = AWSSecretsManager.get_secret(db_secret_name)
            db_config = json.loads(db_secret)
            db_url = f"postgresql://{db_config['username']}:{db_config['password']}@{db_config['host']}:{db_config.get('port', 5432)}/{db_config['database']}"
        else:
            db_url = f"postgresql://{os.environ.get('DB_USER')}:{os.environ.get('DB_PASSWORD')}@{os.environ.get('DB_HOST')}:{os.environ.get('DB_PORT', 5432)}/{os.environ.get('DB_NAME')}"

        self.engine = create_engine(db_url, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        print("Database initialized")

    def get_session(self):
        return self.SessionLocal()

    def save_results(self, session, filename: str, s3_path: str, questions: list, context_blocks: list):
        document = RFPDocument(
            filename=filename,
            s3_path=s3_path,
            total_questions=len(questions),
            total_context_blocks=len(context_blocks),
            processed_at=datetime.utcnow(),
            context_blocks=context_blocks
        )
        session.add(document)
        session.flush()

        for q in questions:
            question_text = q.get('text') if isinstance(q, dict) else q.text
            question = RFPQuestion(document_id=document.id, question_text=question_text)
            session.add(question)

        session.commit()
        return document.id


# ============================================================================
# SECTION 5: Document Loader (with DOCX support)
# ============================================================================

class DocumentLoader:
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.bucket_name = os.environ.get('S3_BUCKET_NAME')

    def load_from_s3(self, s3_key: str, file_extension: str):
        with tempfile.NamedTemporaryFile(suffix=f".{file_extension}", delete=False) as tmp_file:
            local_path = tmp_file.name
            self.s3_client.download_file(self.bucket_name, s3_key, local_path)

        try:
            return self._load_local_file(local_path, file_extension)
        finally:
            os.unlink(local_path)

    def _load_local_file(self, file_path: str, file_extension: str):
        ext = file_extension.lower()
        path = Path(file_path)

        if ext == "pdf":
            loader = PDFPlumberLoader(str(path))
        elif ext in ("xlsx", "xls"):
            loader = UnstructuredExcelLoader(str(path), mode="elements")
        elif ext == "csv":
            loader = CSVLoader(str(path))
        elif ext == "docx":
            loader = Docx2txtLoader(str(path))
        else:
            raise ValueError(f"Unsupported file type: {ext}")

        docs = loader.load()
        for i, doc in enumerate(docs):
            doc.metadata["source_file"] = path.name
            doc.metadata["segment_index"] = i

        return docs


# ============================================================================
# SECTION 6: Chunker
# ============================================================================

class Chunker:
    def __init__(self, chunk_size=6000, chunk_overlap=500):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n--- Page", "\n--- Sheet", "\nSECTION", "\nSection",
                        "\nPart ", "\nPART ", "\n\n\n", "\n\n", "\n", ". ", " "],
            length_function=len,
            keep_separator=True,
        )

    def split(self, docs):
        chunks = self.splitter.split_documents(docs)
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = i
            chunk.metadata["chunk_total"] = len(chunks)
        return chunks


# ============================================================================
# SECTION 7: Question Extractor (LLM)
# ============================================================================

class QuestionExtractor:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model=os.environ.get("EXTRACTION_MODEL_NAME", "gemini-2.0-flash-exp"),
            temperature=float(os.environ.get("EXTRACTION_TEMPERATURE", "0.1")),
            max_output_tokens=4096,
        )
        self.parser = PydanticOutputParser(pydantic_object=ChunkExtractionResult)
        self.chain = self._create_prompt() | self.llm | self.parser

    def _create_prompt(self):
        return ChatPromptTemplate.from_messages([
            ("system", """
You are a document analyst. Separate text into QUESTIONS and CONTEXT.

QUESTION: Any item expecting an answer (direct questions ending in "?", 
directives like "Explain...", "Describe...", numbered items, multiple-choice)

CONTEXT: Everything else (instructions, background, headers, metadata)

Preserve exact wording. Treat sub-parts (a, b, c) as separate questions.

{format_instructions}
"""),
            ("human", "DOCUMENT TEXT:\n---\n{chunk_text}\n---")
        ])

    def extract(self, chunk_text: str, chunk_index: int):
        for attempt in range(3):
            try:
                return self.chain.invoke({
                    "chunk_text": chunk_text,
                    "format_instructions": self.parser.get_format_instructions()
                })
            except Exception as e:
                print(f"Attempt {attempt + 1} failed for chunk {chunk_index}: {e}")
        return ChunkExtractionResult()


# ============================================================================
# SECTION 8: Post Processor
# ============================================================================

class PostProcessor:
    @staticmethod
    def similarity(a: str, b: str) -> float:
        return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()

    @staticmethod
    def deduplicate(questions: list, threshold=0.85) -> list:
        unique = []
        for q in questions:
            q_text = q.get('text') if isinstance(q, dict) else q.text
            if not any(PostProcessor.similarity(q_text, existing.get('text') if isinstance(existing,
                                                                                           dict) else existing.text) >= threshold
                       for existing in unique):
                unique.append(q)
        return unique

    @staticmethod
    def validate(questions: list, source_text: str, min_sim=0.6) -> list:
        validated = []
        source_lower = source_text.lower()

        for q in questions:
            q_text = q.get('text') if isinstance(q, dict) else q.text
            q_lower = q_text.lower().strip()

            if q_lower in source_lower or q_lower[:50] in source_lower:
                validated.append(q)
                continue

            window_size = len(q_lower)
            found = False
            for i in range(0, max(1, len(source_lower) - window_size), max(1, window_size // 4)):
                if PostProcessor.similarity(q_lower, source_lower[i:i + window_size]) >= min_sim:
                    validated.append(q)
                    found = True
                    break

            if not found:
                print(f"  Removed hallucinated: {q_text[:80]}...")

        return validated

    @staticmethod
    def assign_ids(questions: list, context: list):
        for q in questions:
            if isinstance(q, dict):
                q['id'] = str(uuid.uuid4())
        for c in context:
            if isinstance(c, dict):
                c['id'] = str(uuid.uuid4())
        return questions, context


# ============================================================================
# SECTION 9: Main Lambda Handler
# ============================================================================

VERSION = "1.0"
ALLOWED_EXTENSIONS = json.loads(
    os.environ.get("ALLOWED_FILE_EXTENSIONS", '{"ext_list": ["pdf", "xlsx", "csv", "docx"]}'))
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", "6000"))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", "500"))


def lambda_handler(event, context):
    print(f"RFP Question Extractor - Version {VERSION}")

    try:
        body = json.loads(event['Records'][0]['body'])
        s3_path = body["detail"]["object"]["key"]
        file_ext = s3_path.split('.')[-1].lower()

        if file_ext not in ALLOWED_EXTENSIONS["ext_list"]:
            raise ValueError(f"Invalid extension: {file_ext}")

        # Run pipeline
        result = run_pipeline(s3_path, file_ext)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Success",
                "filename": result["filename"],
                "questions": result["total_questions"],
                "document_id": result["document_id"]
            })
        }

    except Exception as e:
        print(f"Error: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


def run_pipeline(s3_path: str, file_ext: str) -> dict:
    filename = s3_path.split('/')[-1]
    print(f"Processing: {filename}")

    # Load
    loader = DocumentLoader()
    docs = loader.load_from_s3(s3_path, file_ext)
    raw_text = "\n\n".join(doc.page_content for doc in docs)

    # Chunk
    chunker = Chunker(CHUNK_SIZE, CHUNK_OVERLAP)
    chunks = chunker.split(docs)

    # Extract
    extractor = QuestionExtractor()
    all_questions = []
    all_context = []

    for i, chunk in enumerate(chunks):
        print(f"Chunk {i + 1}/{len(chunks)}")
        result = extractor.extract(chunk.page_content, i)
        all_questions.extend([{"id": q.id, "text": q.text} for q in result.questions])
        all_context.extend([{"id": c.id, "text": c.text} for c in result.context_blocks])

    # Post-process
    print(f"Raw questions: {len(all_questions)}")
    all_questions = PostProcessor.deduplicate(all_questions)
    all_questions = PostProcessor.validate(all_questions, raw_text)
    all_questions, all_context = PostProcessor.assign_ids(all_questions, all_context)
    print(f"Final questions: {len(all_questions)}")

    # Save to database
    db = DatabaseManager()
    session = db.get_session()
    try:
        doc_id = db.save_results(session, filename, s3_path, all_questions, all_context)
    finally:
        session.close()

    return {
        "filename": filename,
        "total_questions": len(all_questions),
        "total_context_blocks": len(all_context),
        "document_id": doc_id
    }