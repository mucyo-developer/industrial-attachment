#!/bin/bash

# Production startup script for AI Chatbot

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting AI Chatbot...${NC}"

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found. Copying from .env.example${NC}"
    cp .env.example .env
    echo -e "${YELLOW}Please edit .env file with your configuration${NC}"
fi

# Create necessary directories
mkdir -p logs data

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null; then
    echo -e "${YELLOW}Warning: Ollama is not running. Please start Ollama first.${NC}"
    echo -e "${YELLOW}Run: ollama serve${NC}"
fi

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo -e "${GREEN}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements-prod.txt

# Start the application
echo -e "${GREEN}Starting production server...${NC}"
export FLASK_ENV=production
gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 60 --access-logfile logs/access.log --error-logfile logs/error.log production_chatbot:app
