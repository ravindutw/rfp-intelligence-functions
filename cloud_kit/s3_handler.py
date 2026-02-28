import boto3
import os
import tempfile
from langchain_community.document_loaders import PyPDFLoader

class S3Handler:

    s3 = boto3.client('s3')
    bucket_name = os.environ['S3_BUCKET_NAME']


    def get_file(self, file_name, file_extension):

        # Pass the file name and extension (.pdf, .xlsx, .docx) to the function

        file_ext_ : str
        file_extension = file_extension.lower()

        if file_extension == ".pdf" or file_extension == ".xlsx" or file_extension == ".docx":
            file_ext_ = file_extension
        elif file_extension == "pdf":
            file_ext_ = ".pdf"
        elif file_extension == "xlsx":
            file_ext_ = ".xlsx"
        elif file_extension == "docx":
            file_ext_ = ".docx"
        else:
            raise ValueError("Invalid file extension")

        with tempfile.NamedTemporaryFile(suffix=file_ext_, delete=False) as tmp_file:
            local_path = tmp_file.name
            self.s3.download_fileobj(self.bucket_name, file_name, local_path)
        try:
            loader = PyPDFLoader(local_path)
            docs = loader.load()
            return docs
        finally:
            os.remove(local_path)

