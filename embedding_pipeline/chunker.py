# embedding_pipeline/chunker.py

from langchain_text_splitters import RecursiveCharacterTextSplitter


class Chunker:
    @staticmethod
    def chunk_documents(docs, chunk_size, chunk_overlap):
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            add_start_index=True
        )
        return splitter.split_documents(docs)