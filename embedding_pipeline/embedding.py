from cloud_kit.gcp.vertex_handler import GoogleCloud
from google import genai
from google.genai.types import EmbedContentConfig


class EmbeddingManager:
    def __init__(self, provider, project_id, location):
        credentials = GoogleCloud.get_gcp_credentials()

        if provider == "gemini":
            self.model_name = "text-embedding-005"
            self.client = genai.Client(
                vertexai=True,
                project=project_id,
                location=location,
                credentials=credentials,
            )
        else:
            raise ValueError("Invalid provider.")


    def embed_documents(self, text_chunks):
        batch_size = 250
        all_embeddings = []

        for i in range(0, len(text_chunks), batch_size):
            batch = text_chunks[i:i + batch_size]
            response = self.client.models.embed_content(
                model=self.model_name,
                contents=batch,
                config=EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT",
                ),
            )
            all_embeddings.extend([e.values for e in response.embeddings])

        return all_embeddings


    def embed_query(self, user_query):
        response = self.client.models.embed_content(
            model=self.model_name,
            contents=user_query,
            config=EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
            ),
        )
        return response.embeddings[0].values