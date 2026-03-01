from langchain_milvus import Milvus
import os
import json

class MilvusDB:

    @staticmethod
    def init_vector_db(embeddings, milvus_secret : str):
        milvus_collection_name = os.getenv("MILVUS_COLLECTION_NAME")

        milvus_secret_json = json.loads(milvus_secret)
        milvus_host = milvus_secret_json["MILVUS_HOST"]
        milvus_un = milvus_secret_json["MILVUS_UNAME"]
        milvus_pwd = milvus_secret_json["MILVUS_PWD"]

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