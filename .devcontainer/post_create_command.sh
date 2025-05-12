#!/bin/bash

cd frontend && npm install
pipx install poetry

echo 'alias start-backend="cd /workspaces/twilio-openai && python3 main.py "' >> ~/.bashrc

source /home/vscode/.bashrc
