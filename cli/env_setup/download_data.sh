#!/bin/bash

# in order to be able to run the script first run "chmod +x download_data.sh"

echo "Downloading Load data ..."

# Define the URLs for the files to download
FILE_URL_1="https://eepublicdownloads.blob.core.windows.net/public-cdn-container/clean-documents/Publications/Statistics/2023/monthly_hourly_load_values_2023.csv"
FILE_URL_2="https://eepublicdownloads.blob.core.windows.net/public-cdn-container/clean-documents/Publications/Statistics/2024/monthly_hourly_load_values_2024.csv"

# Define the directory to save the files
DEST_DIR="data/"

# Check if the destination directory exists, if not, create it
if [ ! -d "$DEST_DIR" ]; then
  mkdir -p "$DEST_DIR"
fi

# Download the files using curl
curl -o "$DEST_DIR/load_values_23.csv" "$FILE_URL_1"
curl -o "$DEST_DIR/load_values_24.csv" "$FILE_URL_2"

# Inform the user that the download is complete
echo "Files have been downloaded to $DEST_DIR"

echo "Merge data ..."
source .venv/bin/activate
python -m merge_data

echo "Downloading Crypto data ..."
python -m cli.download_crypto_data --dir $DEST_DIR
