# RFP Intelligence Project
# Question Extractor - Lambda Handler
# © 2026-Y2-S2-KU-DS-15
# Version: 1.0

import os
import json
import traceback
from datetime import datetime

from models import ExtractionEvent, ExtractionResult, QuestionItem, ContextItem
from extractor import DocumentLoader, Chunker, QuestionExtractor, PostProcessor
from db_manager import DatabaseManager

VERSION = "1.0"
ALLOWED_EXTENSIONS = json.loads(
    os.environ.get("ALLOWED_FILE_EXTENSIONS", '{"ext_list": ["pdf", "xlsx", "csv", "docx"]}'))
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", "6000"))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", "500"))


def lambda_handler(event, context):
    """AWS Lambda handler for question extraction"""
    print(f"RFP Question Extractor - Version {VERSION}")
    print(f"Event received: {json.dumps(event)}")

    db_manager = None

    # Parse event body
    if 'Records' in event:
        body = json.loads(event['Records'][0]['body'])
    else:
        body = event

    # Extract event data using Pydantic model
    extraction_event = ExtractionEvent(**body)

    rfp_id = extraction_event.rfp_id
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

            # Run extraction pipeline
            result = run_extraction_pipeline(s3_path, file_ext, rfp_id)

            # Save questions to database
            saved_count = db_manager.save_questions(session, rfp_id, result.questions)

            db_manager.save_context(session, rfp_id, result.context_blocks)

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
                db_manager.update_document_status(session, rfp_id, "Failed")
                session.close()
            except:
                pass
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }


def run_extraction_pipeline(s3_path: str, file_ext: str, rfp_id: str) -> ExtractionResult:
    """Main extraction pipeline"""
    filename = s3_path.split('/')[-1]
    print(f"\n{'=' * 60}")
    print(f"Processing: {filename}")
    print(f"RFP ID: {rfp_id}")
    print(f"{'=' * 60}")

    # Step 1: Load document from S3
    print("\n[1/5] Loading document from S3...")
    loader = DocumentLoader()
    docs = loader.load_from_s3(s3_path, file_ext)
    raw_text = "\n\n".join(doc.page_content for doc in docs)
    print(f"  Loaded {len(docs)} document segments, {len(raw_text)} characters")

    # Step 2: Split into chunks
    print("\n[2/5] Splitting document into chunks...")
    chunker = Chunker(CHUNK_SIZE, CHUNK_OVERLAP)
    chunks = chunker.split(docs)
    print(f"  Split into {len(chunks)} chunks")

    # Step 3: Extract questions and context
    print("\n[3/5] Extracting questions using LLM...")
    extractor = QuestionExtractor()
    all_questions = []
    all_context = []

    for i, chunk in enumerate(chunks):
        print(f"  Processing chunk {i + 1}/{len(chunks)}...", end=" ")
        result = extractor.extract(chunk.page_content, i)
        all_questions.extend(result.questions)
        all_context.extend(result.context_blocks)
        print(f"found {len(result.questions)} questions")

    print(f"  Raw extraction: {len(all_questions)} questions, {len(all_context)} context blocks")

    # Step 4: Post-process
    print("\n[4/5] Post-processing...")
    print(f"  Before dedup: {len(all_questions)}")
    all_questions = PostProcessor.deduplicate_questions(all_questions)
    print(f"  After dedup: {len(all_questions)}")

    all_questions = PostProcessor.validate_questions(all_questions, raw_text)
    print(f"  After validation: {len(all_questions)}")

    all_questions, all_context = PostProcessor.assign_ids(all_questions, all_context)

    # Step 5: Prepare result
    print("\n[5/5] Preparing result...")

    result = ExtractionResult(
        rfp_id=rfp_id,
        filename=filename,
        total_questions=len(all_questions),
        total_context_blocks=len(all_context),
        questions=all_questions,
        context_blocks=all_context
    )

    print(f"\n{'=' * 60}")
    print(f"EXTRACTION SUMMARY")
    print(f"{'=' * 60}")
    print(f"Filename         : {result.filename}")
    print(f"Questions found  : {result.total_questions}")
    print(f"Context blocks   : {result.total_context_blocks}")
    print(f"{'=' * 60}\n")

    return result