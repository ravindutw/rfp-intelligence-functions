import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_openai import OpenAIEmbeddings
from cloud_kit.gcp.vertex_handler import GoogleCloud
from dotenv import load_dotenv

load_dotenv()


class EmbeddingManager:
    def __init__(self, provider, project_id, location):
        credentials = GoogleCloud.get_gcp_credentials()

        if provider == "gemini":
            self.model = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001",
            project=project_id,
            location=location,
            credentials=credentials,
            vertexai=True)

        elif provider == "openai":
            self.model = OpenAIEmbeddings(model="text-embedding-3-small")

        else:
            raise ValueError("Invalid provider.")

    def embed_documents(self, text_chunks):

        return self.model.embed_documents(text_chunks)

    def embed_query(self, user_query):

        return self.model.embed_query(user_query)

    def get_embedding_model(self):
        return self.model
