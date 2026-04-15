import os
import json
import uuid
from pathlib import Path
from difflib import SequenceMatcher
from typing import List, Tuple
import tempfile

import boto3
from langchain_text_splitters import RecursiveCharacterTextSplitter

from models import ChunkExtractionResult, QuestionItem, ContextItem, UsageLog


class DocumentLoader:
    def __init__(self):
        try:
            self.s3_client = boto3.client('s3', region_name='ap-southeast-1')
            self.bucket_name = os.environ.get('S3_BUCKET_NAME')

        except Exception as e:
            raise Exception(f"Failed to initialize S3 client: {e}")

    def load_from_s3(self, s3_key: str, file_extension: str):
        """Download file from S3 and load as LangChain documents"""
        with tempfile.NamedTemporaryFile(suffix=f".{file_extension}", delete=False) as tmp_file:
            local_path = tmp_file.name
            try:
                self.s3_client.download_file(self.bucket_name, s3_key, local_path)
            except Exception as e:
                raise Exception(f"Failed to download file from S3: {e}")

        try:
            return self._load_local_file(local_path, file_extension)
        except Exception as e:
            print(f"Error loading file from S3: {e}")
            raise Exception(f"Failed to load file from S3: {e}")
        finally:
            os.unlink(local_path)
            print(f"Deleted temporary file: {local_path}")

    def _load_local_file(self, file_path: str, file_extension: str):
        ext = file_extension.lower()
        path = Path(file_path)

        if ext == "pdf":
            from langchain_community.document_loaders import PDFPlumberLoader
            loader = PDFPlumberLoader(str(path))
        elif ext in ("xlsx", "xls"):
            from langchain_community.document_loaders import UnstructuredExcelLoader
            loader = UnstructuredExcelLoader(str(path), mode="elements")
        elif ext == "csv":
            from langchain_community.document_loaders import CSVLoader
            loader = CSVLoader(str(path))
        elif ext == "docx":
            from langchain_community.document_loaders import Docx2txtLoader
            loader = Docx2txtLoader(str(path))
        else:
            raise ValueError(f"Unsupported file type: {ext}")

        docs = loader.load()
        for i, doc in enumerate(docs):
            doc.metadata["source_file"] = path.name
            doc.metadata["segment_index"] = i
            doc.metadata["file_extension"] = ext

        return docs


class Chunker:
    def __init__(self, chunk_size=6000, chunk_overlap=500):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=[
                "\n--- Page", "\n--- Sheet", "\nSECTION", "\nSection",
                "\nPart ", "\nPART ", "\n\n\n", "\n\n", "\n", ". ", " "
            ],
            length_function=len,
            keep_separator=True,
        )

    def split(self, docs):
        chunks = self.splitter.split_documents(docs)
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = i
            chunk.metadata["chunk_total"] = len(chunks)
        return chunks


class QuestionExtractor:
    def __init__(self, db_session=None, user_id: str = None, rfp_id: str = None):
        # Load system prompt from external file
        self.system_prompt = self._load_system_prompt()
        self.db_session = db_session
        self.user_id = user_id
        self.rfp_id = rfp_id

        self.model_name = os.environ.get("EXTRACTION_MODEL_NAME", "gemini-2.0-flash-exp")

        from langchain_google_genai import ChatGoogleGenerativeAI
        from cloud_kit.gcp.vertex_handler import GoogleCloud

        self.llm = ChatGoogleGenerativeAI(
            model=self.model_name,
            temperature=float(os.environ.get("EXTRACTION_TEMPERATURE", "0.1")),
            max_output_tokens=4096,
            project=os.environ.get("GCP_PROJECT_ID"),
            location=os.environ.get("GCP_REGION", "us-central1"),
            credentials=GoogleCloud.get_gcp_credentials(),
            vertexai=True
        )

        from langchain_core.output_parsers import PydanticOutputParser
        self.parser = PydanticOutputParser(pydantic_object=ChunkExtractionResult)
        from langchain_core.prompts import ChatPromptTemplate
        self.prompt = self._create_prompt(ChatPromptTemplate)

    def _load_system_prompt(self) -> str:
        """Load system prompt from external file"""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_paths = [
            os.path.join(base_dir, "prompt.txt"),
            "prompt.txt"
        ]

        for path in prompt_paths:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    prompt = f.read()
                    print(f"Loaded system prompt from: {path}")
                    return prompt
            except FileNotFoundError:
                continue

        # Fallback prompt if file not found
        print("Warning: prompt.txt not found, using default prompt")
        return self._get_default_prompt()

    def _get_default_prompt(self) -> str:
        """Default system prompt as fallback"""
        return """
You are a document analyst. Separate text into QUESTIONS and CONTEXT.

QUESTION: Any item expecting an answer (direct questions ending in "?",
directives like "Explain...", "Describe...", numbered items, multiple-choice)

CONTEXT: Everything else (instructions, background, headers, metadata)

Preserve exact wording. Treat sub-parts (a, b, c) as separate questions.

{format_instructions}
"""

    def _create_prompt(self, ChatPromptTemplate):
        return ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", "DOCUMENT TEXT:\n---\n{chunk_text}\n---")
        ])

    def _log_usage(self, response):
        """Log LLM usage information to the database"""
        if not self.db_session or not self.user_id:
            return
        try:
            usage_metadata = response.usage_metadata if hasattr(response, 'usage_metadata') else {}
            token_count = 0
            metadata_dict = {}
            if isinstance(usage_metadata, dict):
                token_count = usage_metadata.get('total_tokens', 0)
                metadata_dict = usage_metadata
            elif usage_metadata:
                token_count = getattr(usage_metadata, 'total_tokens', 0) or 0
                metadata_dict = {
                    'input_tokens': getattr(usage_metadata, 'input_tokens', 0),
                    'output_tokens': getattr(usage_metadata, 'output_tokens', 0),
                    'total_tokens': getattr(usage_metadata, 'total_tokens', 0),
                }

            usage_log = UsageLog(
                user_id=uuid.UUID(self.user_id),
                rfp_id=uuid.UUID(self.rfp_id) if self.rfp_id else None,
                action_type='QUESTION_EXTRACTION',
                ai_tokens_used=token_count,
                ai_model_used=self.model_name,
                status='SUCCESS',
                usage_metadata=metadata_dict,
            )
            self.db_session.add(usage_log)
            self.db_session.commit()
            print(f"Logged usage: model={self.model_name}, tokens={token_count}")
        except Exception as e:
            self.db_session.rollback()
            print(f"Failed to log usage: {e}")

    def extract(self, chunk_text: str, chunk_index: int, max_retries: int = 3) -> ChunkExtractionResult:
        """Extract questions and context from a chunk with retries"""
        for attempt in range(max_retries):
            try:
                chain_without_parser = self.prompt | self.llm
                response = chain_without_parser.invoke({
                    "chunk_text": chunk_text,
                    "format_instructions": self.parser.get_format_instructions()
                })
                self._log_usage(response)
                result = self.parser.parse(response.content)
                return result
            except Exception as e:
                print(f"Attempt {attempt + 1} failed for chunk {chunk_index}: {e}")
                if attempt == max_retries - 1:
                    print(f"All retries exhausted for chunk {chunk_index}")

        return ChunkExtractionResult()


class PostProcessor:
    @staticmethod
    def similarity(a: str, b: str) -> float:
        """Compute string similarity ratio"""
        return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()

    @staticmethod
    def deduplicate_questions(questions: List[QuestionItem], threshold: float = 0.85) -> List[QuestionItem]:
        """Remove near-duplicate questions"""
        unique = []
        for q in questions:
            is_dup = any(
                PostProcessor.similarity(q.text, existing.text) >= threshold
                for existing in unique
            )
            if not is_dup:
                unique.append(q)

        removed = len(questions) - len(unique)
        if removed > 0:
            print(f"Dedup: removed {removed} duplicate(s)")
        return unique

    @staticmethod
    def validate_questions(questions: List[QuestionItem], source_text: str, min_similarity: float = 0.6) -> List[
        QuestionItem]:
        """Validate that extracted questions exist in source text"""
        validated = []
        source_lower = source_text.lower()

        for q in questions:
            q_lower = q.text.lower().strip()

            # Exact substring match
            if q_lower in source_lower:
                validated.append(q)
                continue

            # Partial prefix match (first 50 chars)
            if q_lower[:50] in source_lower:
                validated.append(q)
                continue

            # Fuzzy sliding window
            window_size = len(q_lower)
            found = False
            for i in range(0, max(1, len(source_lower) - window_size), max(1, window_size // 4)):
                if PostProcessor.similarity(q_lower, source_lower[i:i + window_size]) >= min_similarity:
                    validated.append(q)
                    found = True
                    break

            if not found:
                print(f"Removed hallucinated: {q.text[:80]}...")

        return validated

    @staticmethod
    def assign_ids(questions: List[QuestionItem], context_blocks: List[ContextItem]) -> Tuple[
        List[QuestionItem], List[ContextItem]]:
        """Assign UUIDs to questions and context blocks"""
        for q in questions:
            if not q.id:
                q.id = str(uuid.uuid4())
        for c in context_blocks:
            if not c.id:
                c.id = str(uuid.uuid4())
        return questions, context_blocks