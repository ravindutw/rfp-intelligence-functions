from langchain_text_splitters import RecursiveCharacterTextSplitter
from cloud_kit.aws.s3_handler import S3Handler
from dotenv import load_dotenv

load_dotenv()

class Docs:

    @staticmethod
    def chunk(obj_path, chunk_size, chunk_overlap, file_ext):
        docs = S3Handler().get_file(obj_path, file_ext)

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,  # chunk size (characters)
            chunk_overlap=chunk_overlap,  # chunk overlap (characters)
            add_start_index=True,  # track index in an original document
        )
        all_splits = text_splitter.split_documents(docs)

        print(f"Split into {len(all_splits)} chunks.")

        return all_splits