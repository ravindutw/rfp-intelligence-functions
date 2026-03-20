import os
from google.oauth2 import service_account
from rfp_intelligence_embedding_function.cloud_kit.aws.sm_handler import AWSSecretsManager
import json


class GoogleCloud:

    @staticmethod
    def get_gcp_credentials():
        gcp_service_account_key = AWSSecretsManager.get_secret(os.environ['GCP_KEY_SECRET_NAME'])
        gcp_credentials_dict = json.loads(gcp_service_account_key)

        credentials = service_account.Credentials.from_service_account_info(
            gcp_credentials_dict,
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        return credentials