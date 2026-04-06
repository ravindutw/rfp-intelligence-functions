import requests
import os

class InvokeInference:

    api_url: str

    def __init__(self):
        self.api_url = os.environ.get("AI_BACKEND_URL")

    def run_process_rfp(self, rfp_id: str):
        api_call_url = f"{self.api_url}/api/process-rfp/{rfp_id}"

        try:
            response = requests.get(api_call_url)

            if response.status_code != 200:
                raise Exception(f"Failed to fetch data from API: {response.status_code}")

        except Exception as e:
            print(e)
            raise