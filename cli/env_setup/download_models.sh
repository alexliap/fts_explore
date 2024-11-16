#!/bin/bash

# in order to be able to run the script first run "chmod +x download_data.sh"

echo "Downloading all models from Azure ..."
python -m cli.download_models
