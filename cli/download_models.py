import argparse
import os

from azure.storage.blob import BlobServiceClient

account_name = ""
blob_key = ""

account_url = f"https://{account_name}.blob.core.windows.net"

# Create the BlobServiceClient object
blob_service_client = BlobServiceClient(account_url, credential=blob_key)

container_client = blob_service_client.get_container_client(
    container="model-checkpoints"
)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--download_dir", required=False, default="model_checkpoints")

    args = parser.parse_args()

    os.makedirs(args.download_dir, exist_ok=True)

    for blob in container_client.list_blobs():
        blob_name = blob.name
        if "crypto_data/stage_one" in blob_name:
            blob_path = "/".join(blob_name.split("/")[:-1])

            os.makedirs(os.path.join(args.download_dir, blob_path), exist_ok=True)

            with open(
                file=os.path.join(args.download_dir, blob_name), mode="wb"
            ) as download_file:
                download_file.write(container_client.download_blob(blob_name).readall())
