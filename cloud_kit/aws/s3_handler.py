import boto3
import os
import tempfile
from langchain_community.document_loaders import PyPDFLoader
import json
from dotenv import load_dotenv

load_dotenv()

class S3Handler:

    S3 = boto3.client('s3')
    BUCKET_NAME = os.environ.get('S3_BUCKET_NAME')
    ALLOWED_FILE_EXTENSIONS = os.environ.get("ALLOWED_FILE_EXTENSIONS")


    def get_file(self, file_name, file_extension):

        # Pass the file name and extension (pdf, xlsx, docx) to the function

        allowed_ext_json = json.loads(self.ALLOWED_FILE_EXTENSIONS)
        file_ext_ : str
        file_extension = file_extension.lower()

        if file_extension not in allowed_ext_json["ext_list"]:
            raise ValueError("Invalid file extension")

        if not file_extension.startswith('.'):
            file_ext_ = '.' + file_extension
        else:
            file_ext_ = file_extension

        with tempfile.NamedTemporaryFile(suffix=file_ext_, delete=False) as tmp_file:
            local_path = tmp_file.name
            self.S3.download_file(self.BUCKET_NAME, file_name, local_path)
        try:
            loader = PyPDFLoader(local_path)
            docs = loader.load()
            return docs
        finally:
            os.remove(local_path)

