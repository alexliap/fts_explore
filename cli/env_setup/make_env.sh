#!/bin/bash

# in order to be able to run the script first run "chmod +x make_env.sh"

curl -LsSf https://astral.sh/uv/install.sh | sh

source $HOME/.local/bin/env

uv venv -p 3.11

source .venv/bin/activate

uv pip install -e '.[dev]'

echo "Install pre-commit ..."
pre-commit install


echo "Configure Git User email ..."
git config --global user.email "alexandrosliapates@gmail.com"
