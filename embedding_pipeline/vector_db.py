from langchain_milvus import Milvus
import os

class MilvusDB:

    @staticmethod
    def init_vector_db():
        milvus_host = os.getenv("MILVUS_HOST")
        embeddings = os.getenv("MILVUS_EMBEDDINGS")
        milvus_collection_name = os.getenv("MILVUS_COLLECTION_NAME")
        milvus_un = os.getenv("MILVUS_UN")
        milvus_pwd = os.getenv("MILVUS_PWD")

        vector_store = Milvus(
            embedding_function=embeddings,
            collection_name=milvus_collection_name,
            connection_args = {
                "uri": milvus_host,
                "user": milvus_un,
                "password": milvus_pwd,
                "secure": True
            }
        )

        return vector_store