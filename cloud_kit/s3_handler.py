# cloud_kit/s3_handler.py

import os
import tempfile
import boto3
from langchain_community.document_loaders import PyPDFLoader


class S3Handler:
    def __init__(self):
        self.s3 = boto3.client("s3")
        self.bucket_name = os.environ["S3_BUCKET_NAME"]

    def get_file(self, file_name: str, file_extension: str):
        """
        Downloads a file from S3 into a temp file and loads it as LangChain Documents.
        Currently, supports PDF (PyPDFLoader).
        """
        ext = file_extension.lower().strip()

        if not ext.startswith("."):
            ext = "." + ext

        if ext != ".pdf":
            raise ValueError("Only PDF is supported for now. Use .pdf")

        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            local_path = tmp.name

        try:

            self.s3.download_file(self.bucket_name, file_name, local_path)

            loader = PyPDFLoader(local_path)
            docs = loader.load()
            return docs
        finally:
            try:
                os.remove(local_path)
            except OSError:
                pass