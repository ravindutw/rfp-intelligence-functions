import os
import json
import uuid
from typing import List, Optional
from datetime import datetime
from sqlalchemy import create_engine, update
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from models import Base, RFPDocument, RFPQuestion, QuestionItem
from cloud_kit.aws.sm_handler import AWSSecretsManager


class DatabaseManager:
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._init_db()
        self.db_cert_path: str

        db_environment = os.environ.get("DB_ENVIRONMENT")

        if db_environment == "DGO":
            self.db_cert_path = "./certs/dgo-ca-certificate.crt"
        elif db_environment == "AWS":
            self.db_cert_path = "./certs/ap-southeast-1-bundle.pem"
        else:
            raise Exception("DB_ENVIRONMENT not set")


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
                connect_args={"sslmode": "verify-full", "sslrootcert": self.db_cert_path},
                pool_pre_ping=True,
                echo=False
            )
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

            # Create tables if they don't exist
            Base.metadata.create_all(bind=self.engine)
            print("Database initialized successfully")

        except Exception as e:
            print(f"Database initialization failed: {e}")
            raise

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
            print(f"Updated document {rfp_id} status to {status}")
        except Exception as e:
            session.rollback()
            print(f"Failed to update document status: {e}")
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