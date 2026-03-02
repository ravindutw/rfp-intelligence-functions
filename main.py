# main.py

from cloud_kit.s3_handler import S3Handler
from embedding_pipeline.chunker import Chunker
from embedding_pipeline.embedding import EmbeddingManager


def lambda_handler(event, context):
    file_name = event.get("file_name")
    file_extension = event.get("file_extension") or (("." + file_name.split(".")[-1]) if "." in file_name else ".pdf")

    if not file_name:
        return {"status": "error", "message": "file_name is required", "file_name": "file_name"}


    # 1) Load document from S3
    s3 = S3Handler()
    docs = s3.get_file(file_name, file_extension)

    # 2) Chunk
    chunks = Chunker.chunk_documents(docs)

    # 3) Embed
    embedder = EmbeddingManager(provider="gemini")
    texts = [c.page_content for c in chunks]
    embeddings = embedder.embed_documents(texts)

    return {
        "status": "success",
        "pages_loaded": len(docs),
        "chunks_created": len(chunks),
        "embeddings_created": len(embeddings),
    }


if __name__ == "__main__":
    test_event = {
        "file_name": "2-IT2021_PP1-Instructions (3).pdf",
        "file_extension": ".pdf",
    }
    print(lambda_handler(test_event, None))