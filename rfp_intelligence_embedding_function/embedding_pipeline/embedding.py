from langchain_aws import BedrockEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from cloud_kit.gcp.vertex_handler import GoogleCloud


class EmbeddingManager:
    def __init__(
        self,
        provider,
        model_name,
        project_id=None,
        location=None,
        region=None,
        output_dimensionality=1536,
    ):

        self.provider = provider

        if provider == "gemini":
            credentials = GoogleCloud.get_gcp_credentials()
            self.model = GoogleGenerativeAIEmbeddings(
                model=model_name,
                project=project_id,
                location=location,
                credentials=credentials,
                vertexai=True,
                output_dimensionality=output_dimensionality,
            )

        elif provider == "cohere":
            self.model = BedrockEmbeddings(
                model_id=model_name,
                region_name=region or "us-east-1",
                dimensions=output_dimensionality,
            )

        else:
            raise ValueError("Invalid provider.")

    def embed_documents(self, text_chunks):
        return self.model.embed_documents(text_chunks)

    def embed_query(self, user_query):
        return self.model.embed_query(user_query)

    def get_embedding_model(self):
        return self.model