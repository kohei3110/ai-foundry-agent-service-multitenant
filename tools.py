from typing import Annotated
from semantic_kernel.functions import kernel_function
from azure.storage.blob import BlobServiceClient
import glob
import os
from azure.identity import DefaultAzureCredential
from azure.ai.projects.aio import AIProjectClient
from azure.identity import WorkloadIdentityCredential

openai = None

async def initialize_openai():

    project_client = AIProjectClient(
        endpoint="https://jianshn-eastus2-foundry.services.ai.azure.com/api/projects/firstProject",
        credential=DefaultAzureCredential()
    )
    global openai
    openai = await project_client.inference.get_azure_openai_client(api_version="2024-05-01-preview")

class confirm_booking:
    @staticmethod
    @kernel_function(
        name="upload_blob",
        description="uploads finalized booking details to Azure Blob Storage"
    )
    async def upload_blob(details: str, tenant_id) -> str:
        try:
            with open("/tmp/booking_details.txt", "w") as file:
                file.write(f"file uploaded for {details}")

                blob_service_client = BlobServiceClient(
                    account_url="https://ngjasonmultistorage.blob.core.windows.net/",
                    credential=WorkloadIdentityCredential()
                )
                container_client = blob_service_client.get_container_client(tenant_id)

                booking_files = glob.glob(os.path.join("/tmp/", '*.txt'))
                state=""
                if not booking_files:
                    return "\033[31m❌ No .txt files found to upload.\033[0m"
                for file in booking_files:
                    with open(file, "rb") as data:
                        name = os.path.basename(file)
                        if not container_client.get_blob_client(name).exists():
                            container_client.upload_blob(name=name, data=data)
                            state = f"\033[32m✅ Successfully Uploaded {name}"
                        else:
                            state=f"\033[31m❌ Failed to upload {name}.\033[0m"
                return state
        except Exception as e:
            return f"\033[31m❌ Error uploading blob: {str(e)}\033[0m"

class get_travel:
    @staticmethod
    @kernel_function(
        name="get_travel",
        description="Gets the travel details for the tenant",
    )
    async def plan_travel(city: str, days:str) -> str:
        """Plan itinerary for a given city."""
        if openai is None:
            await initialize_openai()
        response = await openai.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "user", "content": f"Plan an itinerary for a trip to {city} for {days} days."},
            ]
    )
        return response.choices[0].message.content