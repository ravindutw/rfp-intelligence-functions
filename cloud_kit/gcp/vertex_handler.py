import os
from google.oauth2 import service_account
import vertexai
from cloud_kit.aws.sm_handler import AWSSecretsManager
import json

class VertexAI:

    @staticmethod
    def init_vertex_ai(gcp_project_id: str, gcp_location: str):
        gcp_service_account_key = AWSSecretsManager.get_secret(os.environ['GCP_KEY_SECRET_NAME'])

        gcp_credentials_dict = json.loads(gcp_service_account_key)

        credentials = service_account.Credentials.from_service_account_info(
            gcp_credentials_dict,
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        vertexai.init(
            project=gcp_project_id,
            location=gcp_location,
            credentials=credentials
        )

