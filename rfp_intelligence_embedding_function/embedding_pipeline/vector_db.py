from langchain_milvus import Milvus, BM25BuiltInFunction
import os
import json
import re


class MilvusDB:

    METADATA_SCHEMA = {
        "source": "",
        "page": 0,
        "total_pages": 0,
        "page_label": "",
        "title": "",
        "author": "",
        "creator": "",
        "producer": "",
        "creationdate": "",
        "moddate": "",
        "start_index": 0,
    }


    @staticmethod
    def init_vector_db(embeddings, milvus_secret : str):
        milvus_collection_name = os.getenv("MILVUS_COLLECTION_NAME")

        milvus_secret_json = json.loads(milvus_secret)
        milvus_host = milvus_secret_json["MILVUS_HOST"]
        milvus_un = milvus_secret_json["MILVUS_UNAME"]
        milvus_pwd = milvus_secret_json["MILVUS_PWD"]

        #milvus_host = "https://in03-7b88ad21ad4f51c.serverless.aws-eu-central-1.cloud.zilliz.com"
        #milvus_un = "db_7b88ad21ad4f51c"
        #milvus_pwd = "Ju2~<X,zRuE01Yq6"

        vector_store = Milvus(
            embedding_function=embeddings,
            collection_name=milvus_collection_name,
            builtin_function=BM25BuiltInFunction(),
            vector_field=["dense", "sparse"],
            consistency_level="Bounded",
            auto_id=True,
            drop_old=False,
            connection_args = {
                "uri": milvus_host,
                "user": milvus_un,
                "password": milvus_pwd,
                "secure": True
            }
        )

        return vector_store


    def sanitize_metadata_keys(self, documents):
        """Replace invalid characters in metadata keys for Milvus compatibility."""
        for doc in documents:
            # First sanitize key names (replace invalid chars with underscores)
            cleaned = {
                re.sub(r'[^a-zA-Z0-9_]', '_', k): v
                for k, v in doc.metadata.items()
            }
            # Then enforce fixed schema: only keep known fields, fill missing with defaults
            doc.metadata = {
                k: cleaned.get(k, default)
                for k, default in self.METADATA_SCHEMA.items()
            }
        return documents
