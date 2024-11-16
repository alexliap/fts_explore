#!/bin/bash

# in order to be able to run the script first run "chmod +x download_data.sh"

./cli/env_setup/make_env.sh
./cli/env_setup/download_data.sh &
./cli/env_setup/download_models.sh &
