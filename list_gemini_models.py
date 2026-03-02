import os
import json
from cloud_kit.aws_sm_handler import AWSSecretsManager
from google import genai

#  TEMP: hardcode env vars for local testing ONLY (remove later)
os.environ["AWS_REGION"] = "us-east-1"
os.environ["GEMINI_SECRET_NAME"] = "RFP_GEMINI_API_KEY"

# 1) Read secret name from env
secret_name = os.environ.get("GEMINI_SECRET_NAME")
if not secret_name:
    raise ValueError("GEMINI_SECRET_NAME is missing")

# 2) Pull secret from AWS Secrets Manager
secret_string = AWSSecretsManager.get_secret(secret_name)
secret_dict = json.loads(secret_string)

api_key = secret_dict.get("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("AWS Secret must contain GOOGLE_API_KEY")

# 3) List models
client = genai.Client(api_key=api_key)

print("=== AVAILABLE MODELS ===")
for m in client.models.list():
    print(getattr(m, "name", str(m)))