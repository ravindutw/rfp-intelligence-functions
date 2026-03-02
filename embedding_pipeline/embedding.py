from langchain_google_genai import GoogleGenerativeAIEmbeddings
from cloud_kit.gcp.vertex_handler import GoogleCloud


class EmbeddingManager:
    def __init__(self, provider, project_id, location, model_name):
        credentials = GoogleCloud.get_gcp_credentials()

        if provider == "gemini":
            self.model = GoogleGenerativeAIEmbeddings(model=model_name,
            project=project_id,
            location=location,
            credentials=credentials,
            vertexai=True)

        else:
            raise ValueError("Invalid provider.")

    def embed_documents(self, text_chunks):

        return self.model.embed_documents(text_chunks)

    def embed_query(self, user_query):

        return self.model.embed_query(user_query)

    def get_embedding_model(self):
        return self.model
