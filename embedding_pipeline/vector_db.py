from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
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

    DTYPE_MAP = {
        str: DataType.VARCHAR,
        int: DataType.INT64,
        float: DataType.DOUBLE,
    }


    def __init__(self):
        self.collection_name = os.getenv("MILVUS_COLLECTION_NAME")
        self.collection = None


    def connect(self, milvus_secret: str):
        """Establish connection to Milvus using secret credentials."""
        milvus_secret_json = json.loads(milvus_secret)
        milvus_host = milvus_secret_json["MILVUS_HOST"]
        milvus_un = milvus_secret_json["MILVUS_UNAME"]
        milvus_pwd = milvus_secret_json["MILVUS_PWD"]

        connections.connect(
            alias="default",
            uri=milvus_host,
            user=milvus_un,
            password=milvus_pwd,
            secure=True,
        )


    def _get_or_create_collection(self, embedding_dim):
        """Get existing collection or create one with the defined schema."""
        if utility.has_collection(self.collection_name):
            self.collection = Collection(self.collection_name)
            return

        fields = [
            FieldSchema(name="pk", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=embedding_dim),
        ]

        # Add metadata fields based on METADATA_SCHEMA
        for key, default_val in self.METADATA_SCHEMA.items():
            dtype = self.DTYPE_MAP.get(type(default_val), DataType.VARCHAR)
            if dtype == DataType.VARCHAR:
                fields.append(FieldSchema(name=key, dtype=dtype, max_length=65535))
            else:
                fields.append(FieldSchema(name=key, dtype=dtype))

        schema = CollectionSchema(fields=fields, enable_dynamic_field=False)
        self.collection = Collection(name=self.collection_name, schema=schema)

        # Create index on vector field for search
        index_params = {
            "metric_type": "COSINE",
            "index_type": "AUTOINDEX",
        }
        self.collection.create_index(field_name="vector", index_params=index_params)


    def init_collection(self, embedding_dim):
        """Initialize the collection (get or create)."""
        self._get_or_create_collection(embedding_dim)
        return self.collection


    def add_documents(self, texts, embeddings, metadatas):
        """Insert documents with embeddings and metadata into the collection."""
        if self.collection is None:
            raise RuntimeError("Collection not initialized. Call init_collection first.")

        # Build insert data
        insert_data = [
            texts,       # text field
            embeddings,  # vector field
        ]

        # Add metadata fields in schema order
        for key, default_val in self.METADATA_SCHEMA.items():
            field_values = [meta.get(key, default_val) for meta in metadatas]
            insert_data.append(field_values)

        self.collection.insert(insert_data)
        self.collection.flush()


    def sanitize_metadata_keys(self, documents):
        """Replace invalid characters in metadata keys for Milvus compatibility."""
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