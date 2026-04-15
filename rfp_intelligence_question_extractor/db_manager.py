import os
import json
import uuid
from typing import List, Optional
from datetime import datetime
from sqlalchemy import create_engine, update
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from models import Base, RFPDocument, RFPQuestion, RFPAnswer, AnswerVersion, QuestionItem, RFPStatusHistory
from cloud_kit.aws.sm_handler import AWSSecretsManager


class DatabaseManager:
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self.db_cert_path: str

        db_environment = os.environ.get("DB_ENVIRONMENT")
        base_dir = os.path.dirname(os.path.abspath(__file__))

        if db_environment == "AWS":
            self.db_cert_path = os.path.join(base_dir, "certs/ap-southeast-1-bundle.pem")
        elif db_environment == "DGO":
            self.db_cert_path = os.path.join(base_dir, "certs/dgo-ca-certificate.crt")
        else:
            raise Exception("DB_ENVIRONMENT not set")

        self._init_db()


    def _init_db(self):
        """Initialize database connection from Secrets Manager"""
        try:
            db_secret_name = os.environ.get("DB_SECRET_NAME")
            if db_secret_name:
                db_secret = AWSSecretsManager.get_secret(db_secret_name)
                db_config = json.loads(db_secret)
                db_url = f"postgresql://{db_config['username']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['dbname']}"
            else:
                raise Exception("DB_SECRET_NAME not set")

            self.engine = create_engine(
                db_url,
                connect_args={
                    "sslmode": "verify-full",
                    "sslrootcert": self.db_cert_path,
                    "connect_timeout": 60,
                    "options": "-c statement_timeout=30000"
                },
                pool_pre_ping=True,
                echo=False,
                pool_timeout = 30,  # Seconds to wait for a connection from the pool
                pool_recycle = 1800,
            )
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

            # Create tables if they don't exist
            Base.metadata.create_all(bind=self.engine)
            print("Database initialized successfully")

        except Exception as e:
            print(f"Database initialization failed: {e}")
            raise Exception("Database initialization failed")


    def get_session(self):
        """Get database session"""
        return self.SessionLocal()


    def get_document_by_id(self, session, rfp_id: str) -> Optional[RFPDocument]:
        """Get RFP document by UUID"""
        try:
            rfp_uuid = uuid.UUID(rfp_id)
            return session.query(RFPDocument).filter(RFPDocument.id == rfp_uuid).first()
        except ValueError:
            print(f"Invalid UUID format: {rfp_id}")
            raise


    def update_document_status(self, session, rfp_id: str, status: str, total_questions: int = None):
        """Update document status and question count"""
        try:
            rfp_uuid = uuid.UUID(rfp_id)
            update_data = {"status": status, "updated_at": datetime.utcnow()}
            if total_questions is not None:
                update_data["total_questions"] = total_questions

            session.execute(
                update(RFPDocument)
                .where(RFPDocument.id == rfp_uuid)
                .values(**update_data)
            )
            session.commit()

            session.add(RFPStatusHistory(rfp_id=rfp_uuid, status=status))
            session.commit()

            print(f"Updated document {rfp_id} status to {status}")
        except Exception as e:
            session.rollback()
            print(f"Failed to update document status: {e}")
            raise


    def delete_existing_questions(self, session, rfp_id: str):
        """Delete existing questions and their related answers/answer versions for an RFP document (for re-try scenarios)"""
        try:
            rfp_uuid = uuid.UUID(rfp_id)

            # Get question IDs for this RFP
            question_ids = [q.id for q in session.query(RFPQuestion.id).filter(RFPQuestion.rfp_id == rfp_uuid).all()]

            if question_ids:
                # Get answer IDs for these questions
                answer_ids = [a.id for a in session.query(RFPAnswer.id).filter(RFPAnswer.question_id.in_(question_ids)).all()]

                if answer_ids:
                    # Delete answer versions first
                    deleted_versions = session.query(AnswerVersion).filter(AnswerVersion.answer_id.in_(answer_ids)).delete(synchronize_session='fetch')
                    print(f"Deleted {deleted_versions} answer versions for RFP {rfp_id}")

                # Delete answers
                deleted_answers = session.query(RFPAnswer).filter(RFPAnswer.question_id.in_(question_ids)).delete(synchronize_session='fetch')
                print(f"Deleted {deleted_answers} answers for RFP {rfp_id}")

            # Delete questions
            deleted_count = session.query(RFPQuestion).filter(RFPQuestion.rfp_id == rfp_uuid).delete(synchronize_session='fetch')
            session.commit()
            print(f"Deleted {deleted_count} existing questions for RFP {rfp_id}")
            return deleted_count
        except SQLAlchemyError as e:
            session.rollback()
            print(f"Database error deleting existing questions: {e}")
            raise


    def save_questions(self, session, rfp_id: str, questions: List[QuestionItem]):
        """Save extracted questions to database"""
        try:
            rfp_uuid = uuid.UUID(rfp_id)
            saved_count = 0

            for seq, q in enumerate(questions, start=1):
                question = RFPQuestion(
                    rfp_id=rfp_uuid,
                    question_text=q.text,
                    question_category=getattr(q, 'question_category', None),
                    sequence_number=seq,
                    status="Pending"
                )
                session.add(question)
                saved_count += 1

            # Update total questions count
            #self.update_document_status(session, rfp_id, "Questions_Extracted", saved_count)
            session.commit()
            print(f"Saved {saved_count} questions for RFP {rfp_id}")
            return saved_count

        except SQLAlchemyError as e:
            session.rollback()
            print(f"Database error saving questions: {e}")
            raise

        except Exception as e:
            session.rollback()
            print(f"Failed to save questions: {e}")
            raise


    def save_context(self, session, rfp_id: str, context):
        """Save context to database"""
        try:
            rfp_uuid = uuid.UUID(rfp_id)
            all_context = []

            for c in context:
                all_context.append(c.text)

            all_context = "\n".join(all_context)

            session.query(RFPDocument).filter(RFPDocument.id == rfp_uuid).update({"context": all_context})
            session.commit()
            print(f"Saved context for RFP {rfp_id}")
        except SQLAlchemyError as e:
            session.rollback()
            print(f"Database error saving context: {e}")
            raise


    def document_exists(self, session, rfp_id: str) -> bool:
        """Check if document exists in database"""
        try:
            rfp_uuid = uuid.UUID(rfp_id)
            return session.query(RFPDocument).filter(RFPDocument.id == rfp_uuid).count() > 0
        except ValueError:
            raise