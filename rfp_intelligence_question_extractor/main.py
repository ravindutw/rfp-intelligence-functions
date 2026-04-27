# RFP Intelligence Project
# Question Extractor - Lambda Handler
# © 2026-Y2-S2-KU-DS-15
# Version: 1.2.2

import os
import json
import traceback
from datetime import datetime

# Heavy modules are imported lazily inside lambda_handler to reduce
# peak memory during Lambda cold-start.  With ~190 transitive
# dependencies (langchain, spacy, google-cloud, numpy, pandas …)
# eager module-level imports can exhaust a low-memory Lambda
# (e.g. 128 MB) before the handler even runs, causing the process
# to hang on the first boto3 / network call.

_modules_loaded = False
ExtractionEvent = None
ExtractionResult = None
QuestionItem = None
ContextItem = None
DocumentLoader = None
Chunker = None
QuestionExtractor = None
PostProcessor = None
DatabaseManager = None
InvokeInference = None


def _load_modules():
    """Lazy-load all heavy dependencies on first invocation."""
    global _modules_loaded
    global ExtractionEvent, ExtractionResult, QuestionItem, ContextItem
    global DocumentLoader, Chunker, QuestionExtractor, PostProcessor
    global DatabaseManager, InvokeInference

    if _modules_loaded:
        return

    try:
        from models import (
            ExtractionEvent as _ExtractionEvent,
            ExtractionResult as _ExtractionResult,
            QuestionItem as _QuestionItem,
            ContextItem as _ContextItem,
        )
        ExtractionEvent = _ExtractionEvent
        ExtractionResult = _ExtractionResult
        QuestionItem = _QuestionItem
        ContextItem = _ContextItem

        from extractor import (
            DocumentLoader as _DocumentLoader,
            Chunker as _Chunker,
            QuestionExtractor as _QuestionExtractor,
            PostProcessor as _PostProcessor,
        )
        DocumentLoader = _DocumentLoader
        Chunker = _Chunker
        QuestionExtractor = _QuestionExtractor
        PostProcessor = _PostProcessor

        from db_manager import DatabaseManager as _DatabaseManager
        DatabaseManager = _DatabaseManager

        from invoke_inference import InvokeInference as _InvokeInference
        InvokeInference = _InvokeInference

        _modules_loaded = True
    except Exception as e:
        print(f"CRITICAL: Module import failed: {e}")
        traceback.print_exc()
        raise

VERSION = "1.2.2"
ALLOWED_EXTENSIONS = json.loads(
    os.environ.get("ALLOWED_FILE_EXTENSIONS", '{"ext_list": ["pdf", "xlsx", "csv", "docx"]}'))
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", "6000"))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", "500"))


def lambda_handler(event, context):
    """AWS Lambda handler for question extraction"""
    print(f"RFP Question Extractor - Version {VERSION}")
    print(f"Event received: {json.dumps(event)}")

    # Lazy-load heavy modules on first invocation
    _load_modules()

    db_manager = None

    # Parse event body
    if 'Records' in event:
        body = json.loads(event['Records'][0]['body'])
    else:
        body = event

    # Extract event data using Pydantic model
    extraction_event = ExtractionEvent(**body)

    rfp_id = extraction_event.rfp_id
    user_id = str(extraction_event.user_id)
    s3_path = extraction_event.s3_path
    file_ext = s3_path.split('.')[-1].lower()

    try:

        print(f"Processing RFP ID: {rfp_id}")
        print(f"S3 Path: {s3_path}")
        print(f"File extension: {file_ext}")

        # Validate file extension
        if file_ext not in ALLOWED_EXTENSIONS["ext_list"]:
            raise ValueError(f"Invalid extension: {file_ext}. Allowed: {ALLOWED_EXTENSIONS['ext_list']}")

        # Initialize database manager
        db_manager = DatabaseManager()
        session = db_manager.get_session()

        try:
            # Verify document exists in database
            if not db_manager.document_exists(session, rfp_id):
                raise ValueError(f"RFP document with ID {rfp_id} not found in database")

            # Update status to processing
            #db_manager.update_document_status(session, rfp_id, "Processing")

            # Delete any existing questions for this RFP (handles re-try scenarios)
            db_manager.delete_existing_questions(session, rfp_id)

            # Run extraction pipeline
            result = run_extraction_pipeline(s3_path, file_ext, rfp_id, db_session=session, user_id=user_id)

            # Save questions to database
            saved_count = db_manager.save_questions(session, rfp_id, result.questions)

            db_manager.save_context(session, rfp_id, result.context_blocks)

            invoke_inference = InvokeInference()
            invoke_inference.run_process_rfp(rfp_id, user_id)

            print(f"Successfully extracted and saved {saved_count} questions")

            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "Question extraction completed",
                    "rfp_id": rfp_id,
                    "filename": result.filename,
                    "total_questions": result.total_questions,
                    "saved_questions": saved_count,
                    "timestamp": datetime.utcnow().isoformat()
                }, default=str)
            }

        finally:
            session.close()

    except ValueError as e:
        print(f"Validation error: {e}")
        if db_manager and rfp_id:
            try:
                session = db_manager.get_session()
                db_manager.update_document_status(session, rfp_id, "FAILED")
                session.close()
            except:
                pass
        return {
            "statusCode": 400,
            "body": json.dumps({"error": str(e)})
        }

    except Exception as e:
        print(f"Error in lambda_handler: {e}")
        traceback.print_exc()
        if db_manager and 'rfp_id' in locals():
            try:
                session = db_manager.get_session()
                db_manager.update_document_status(session, rfp_id, "FAILED")
                session.close()
            except:
                pass
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }


def run_extraction_pipeline(s3_path: str, file_ext: str, rfp_id: str, db_session=None, user_id: str = None) -> ExtractionResult:
    """Main extraction pipeline"""
    filename = s3_path.split('/')[-1]
    print(f"Processing: {filename}")
    print(f"RFP ID: {rfp_id}")

    # Step 1: Load document from S3
    loader = DocumentLoader()
    docs = loader.load_from_s3(s3_path, file_ext)
    raw_text = "\n\n".join(doc.page_content for doc in docs)

    # Step 2: Split into chunks
    chunker = Chunker(CHUNK_SIZE, CHUNK_OVERLAP)
    chunks = chunker.split(docs)

    # Step 3: Extract questions and context
    extractor = QuestionExtractor(db_session=db_session, user_id=user_id, rfp_id=rfp_id)
    all_questions = []
    all_context = []

    for i, chunk in enumerate(chunks):
        result = extractor.extract(chunk.page_content, i)
        all_questions.extend(result.questions)
        all_context.extend(result.context_blocks)

    # Step 4: Post-process
    all_questions = PostProcessor.deduplicate_questions(all_questions)

    all_questions = PostProcessor.validate_questions(all_questions, raw_text)

    all_questions, all_context = PostProcessor.assign_ids(all_questions, all_context)

    # Step 5: Prepare result

    result = ExtractionResult(
        rfp_id=rfp_id,
        filename=filename,
        total_questions=len(all_questions),
        total_context_blocks=len(all_context),
        questions=all_questions,
        context_blocks=all_context
    )

    print(f"Total questions: {result.total_questions}")

    return result