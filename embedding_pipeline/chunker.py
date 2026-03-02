# embedding_pipeline/chunker.py

# Use the classic langchain import which is most commonly available.
# Keep a fallback in case you have the newer separate package installed.
try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
except Exception:
    # fallback: some versions publish a separate package
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    except Exception:
        # Let runtime raise the proper error if neither is available.
        raise ImportError(
            "Cannot import RecursiveCharacterTextSplitter. "
            "Install 'langchain' (and optionally 'langchain-text-splitters' if needed)."
        )


class Chunker:
    @staticmethod
    def chunk_documents(docs, chunk_size=1000, chunk_overlap=150):
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        # returns a list of LangChain Document objects
        return splitter.split_documents(docs)