import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_openai import OpenAIEmbeddings

# Configuration - These should ideally be in a .env file
os.environ["GOOGLE_API_KEY"] = "API Key"
os.environ["OPENAI_API_KEY"] = "API Key"

class EmbeddingManager:
    def __init__(self, provider="gemini", project_id=None, location=None):

        if provider == "gemini":
            self.model = GoogleGenerativeAIEmbeddings(model="models/embedding-001",
            project=project_id,
            location=location,
            vertexai=True)

        elif provider == "openai":
            self.model = OpenAIEmbeddings(model="text-embedding-3-small")

        else:
            raise ValueError("Invalid provider.")

    def embed_documents(self, text_chunks):

        return self.model.embed_documents(text_chunks)

    def embed_query(self, user_query):

        return self.model.embed_query(user_query)