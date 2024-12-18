# After syncing the vast.ai machine with the GDrive upload everything to Azure Blob Storage
import os

from azure.storage.blob import BlobServiceClient

# TODO: Replace <storage-account-name> with your actual storage account name
account_name = ""
blob_key = ""

account_url = f"https://{account_name}.blob.core.windows.net"

# Create the BlobServiceClient object
blob_service_client = BlobServiceClient(account_url, credential=blob_key)

container_client = blob_service_client.get_container_client(
    container="model-checkpoints"
)

directory = ""
for root, dirs, files in os.walk("outputs"):
    for file in files:
        file_path = os.path.join(root, file)
        with open(file=file_path, mode="rb") as data:
            name = "/".join(file_path.split("/")[2:])
            name = os.path.join(directory, name)
            print(name)
            container_client.upload_blob(name=name, data=data, overwrite=True)
