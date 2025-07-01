from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from azure.identity import WorkloadIdentityCredential


blob_service_client = BlobServiceClient(
    account_url="https://ngjasonmultistorage.blob.core.windows.net/",
    credential=WorkloadIdentityCredential()
)

print("Connecting to Azure Blob Storage for Tenant A")
try:
    container_client = blob_service_client.get_container_client("tenanta")

    blobs = container_client.list_blobs()

    for blob in blobs:
        print(blob.name)
        print("\033[32m✅ Successfully connected to tenant A container\033[0m")
except Exception as e:
    print(f"An error occurred: {e}")
    print("\033[31m❌ Failed to connect to tenant A container\033[0m")

print("Connecting to Azure Blob Storage for Tenant B")
try:
    container_client = blob_service_client.get_container_client("tenantb")

    blobs = container_client.list_blobs()

    for blob in blobs:
        print(blob.name)
        print("\033[32m✅ Successfully connected to tenant B container\033[0m")
except Exception as e:
    print(f"An error occurred: {e}")
    print("\033[31m❌ Failed to connect to tenant B container\033[0m")
