#!/bin/bash

# Pull the latest updates from the repository
read -p "Do you want to pull the latest updates from the repository? (y/n): " pull_choice
if [[ "$pull_choice" == "y" || "$pull_choice" == "Y" ]]; then
    echo "Pulling latest updates from the repository..."
    git pull --quiet || { echo "Failed to pull updates. Ensure git is installed and configured."; exit 1; }
else
    echo "Skipping git pull."
fi

# Check if .venv exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv || { echo "Failed to create virtual environment. Install python3-venv."; exit 1; }
fi

echo "Activating virtual environment..."
source .venv/bin/activate || { echo "Failed to activate virtual environment."; exit 1; }

# Install missing dependencies from requirements.txt
if [ -f "requirements.txt" ]; then
    echo "Installing missing dependencies..."
    pip install -r requirements.txt --disable-pip-version-check --quiet || { echo "Failed to install dependencies."; exit 1; }
    echo "All dependencies are up to date."
else
    echo "requirements.txt not found. Skipping dependency installation."
fi

# Check for .env file
if [ ! -f ".env" ]; then
    echo "Copying configuration file..."
    cp .env-example .env || { echo "Failed to copy .env file."; exit 1; }
else
    echo "Skipping .env copying."
fi

echo "Starting the bot..."
python3 main.py || { echo "Failed to start the bot."; exit 1; }

echo "Done."
echo "PLEASE EDIT .ENV FILE IF REQUIRED."
