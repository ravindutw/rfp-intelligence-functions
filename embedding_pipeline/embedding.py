# embedding_pipeline/embedding.py

import os
import json
from cloud_kit.aws_sm_handler import AWSSecretsManager
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_openai import OpenAIEmbeddings


class EmbeddingManager:
    def __init__(self, provider="gemini"):
        provider = provider.lower().strip()

        if provider == "gemini":
            #  read the SECRET NAME from env
            secret_name = os.environ.get("GEMINI_SECRET_NAME")
            if not secret_name:
                raise ValueError("GEMINI_SECRET_NAME env variable is missing. (ex: RFP_GEMINI_API_KEY)")

            secret_string = AWSSecretsManager.get_secret(secret_name)
            secret_dict = json.loads(secret_string)

            api_key = secret_dict.get("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("Secret must contain key: GOOGLE_API_KEY")

            #  required by langchain_google_genai
            os.environ["GOOGLE_API_KEY"] = api_key


            self.model = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

        elif provider == "openai":
            secret_name = os.environ.get("OPENAI_SECRET_NAME")
            if not secret_name:
                raise ValueError("OPENAI_SECRET_NAME env variable is missing. (ex: RFP_OPENAI_API_KEY)")

            secret_string = AWSSecretsManager.get_secret(secret_name)
            secret_dict = json.loads(secret_string)

            api_key = secret_dict.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("Secret must contain key: OPENAI_API_KEY")

            os.environ["OPENAI_API_KEY"] = api_key
            self.model = OpenAIEmbeddings(model="text-embedding-3-small")

        else:
            raise ValueError("Invalid provider. Use 'gemini' or 'openai'.")

    def embed_documents(self, text_chunks):
        return self.model.embed_documents(text_chunks)

    def embed_query(self, user_query):
        return self.model.embed_query(user_query)