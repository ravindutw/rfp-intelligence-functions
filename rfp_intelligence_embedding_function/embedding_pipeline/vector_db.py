from langchain_milvus import Milvus, BM25BuiltInFunction
from langchain_postgres import PGVector
import psycopg
import os
import json
import re


class _BaseVectorDB:

    METADATA_SCHEMA = {
        "source": "", "page": 0, "total_pages": 0, "page_label": "",
        "title": "", "author": "", "creator": "", "producer": "",
        "creationdate": "", "moddate": "", "start_index": 0,
    }

    def sanitize_metadata_keys(self, documents):
        for doc in documents:
            cleaned = {
                re.sub(r'[^a-zA-Z0-9_]', '_', k): v
                for k, v in doc.metadata.items()
            }
            doc.metadata = {
                k: cleaned.get(k, default)
                for k, default in self.METADATA_SCHEMA.items()
            }
        return documents


class MilvusDB(_BaseVectorDB):

    @staticmethod
    def init_vector_db(embeddings, milvus_secret: str):
        milvus_collection_name = os.getenv("MILVUS_COLLECTION_NAME")
        s = json.loads(milvus_secret)
        return Milvus(
            embedding_function=embeddings,
            collection_name=milvus_collection_name,
            builtin_function=BM25BuiltInFunction(),
            vector_field=["dense", "sparse"],
            consistency_level="Bounded",
            auto_id=True,
            drop_old=False,
            connection_args={
                "uri": s["MILVUS_HOST"], "user": s["MILVUS_UNAME"],
                "password": s["MILVUS_PWD"], "secure": True,
            },
        )


class PgVectorDB(_BaseVectorDB):

    TS_CONFIG = os.getenv("PGVECTOR_TS_CONFIG", "english")

    @staticmethod
    def init_vector_db(embeddings, pgvector_secret: str):
        collection_name = os.getenv("PGVECTOR_COLLECTION_NAME")
        db_environment = os.environ.get("DB_ENVIRONMENT")

        db_cert_path: str

        if db_environment == "DGO":
            db_cert_path = "./certs/dgo-ca-certificate.crt"
        elif db_environment == "AWS":
            db_cert_path = "./certs/ap-southeast-1-bundle.pem"
        else:
            raise Exception("DB_ENVIRONMENT not set")

        pgvector_secret_json = json.loads(pgvector_secret)
        pg_host = pgvector_secret_json["host"]
        pg_port = pgvector_secret_json["port"]
        pg_db = pgvector_secret_json["dbname"]
        pg_user = pgvector_secret_json["username"]
        pg_pwd = pgvector_secret_json["password"]

        ssl_params = f"?sslmode=verify-full&sslrootcert={db_cert_path}"

        connection_string = (
            f"postgresql+psycopg://{pg_user}:{pg_pwd}"
            f"@{pg_host}:{pg_port}/{pg_db}{ssl_params}"
        )
        psycopg_conn_string = (
            f"postgresql://{pg_user}:{pg_pwd}"
            f"@{pg_host}:{pg_port}/{pg_db}{ssl_params}"
        )

        vector_store = PGVector(
            embeddings=embeddings,
            collection_name=collection_name,
            connection=connection_string,
            use_jsonb=True,
            create_extension=True,
        )

        # Ensure the FTS column + GIN index exist (idempotent)
        PgVectorDB._ensure_hybrid_schema(psycopg_conn_string)

        return vector_store


    @staticmethod
    def _ensure_hybrid_schema(psycopg_conn_string: str):
        ddl = f"""
        ALTER TABLE langchain_pg_embedding
            ADD COLUMN IF NOT EXISTS content_tsv tsvector
            GENERATED ALWAYS AS (
                to_tsvector('{PgVectorDB.TS_CONFIG}', coalesce(document, ''))
            ) STORED;

        CREATE INDEX IF NOT EXISTS idx_lpe_content_tsv
            ON langchain_pg_embedding USING GIN (content_tsv);
        """
        with psycopg.connect(psycopg_conn_string, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(ddl)
        print("pgvector hybrid schema ensured (tsvector column + GIN index)")


def get_vector_db(provider: str):
    provider = (provider or "").lower()
    if provider == "milvus":
        return MilvusDB
    if provider == "pgvector":
        return PgVectorDB
    raise ValueError(f"Invalid vector DB provider: {provider}")