#!/bin/bash
# Kavita SafeUploader - Development Runner Script

set -e

# Color output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Kavita SafeUploader - Dev Runner     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Check if virtual environment exists
if [ ! -d "backend/venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Run install.sh first.${NC}"
    exit 1
fi

# Check if config exists
if [ ! -f "config.yaml" ]; then
    echo -e "${YELLOW}Config file not found. Copying from example...${NC}"
    cp config.example.yaml config.yaml
    echo -e "${YELLOW}Please edit config.yaml with your settings.${NC}"
    exit 1
fi

# Function to run backend
run_backend() {
    echo -e "${GREEN}Starting backend server...${NC}"
    cd backend
    source venv/bin/activate
    uvicorn app.main:app --reload --host 0.0.0.0 --port 5050
}

# Function to run frontend
run_frontend() {
    echo -e "${GREEN}Starting frontend dev server...${NC}"
    cd frontend
    npm run dev
}

# Function to run tests
run_tests() {
    echo -e "${GREEN}Running tests...${NC}"
    cd backend
    source venv/bin/activate
    pytest
}

# Function to build frontend
build_frontend() {
    echo -e "${GREEN}Building frontend...${NC}"
    cd frontend
    npm run build
}

# Parse command
case "${1:-dev}" in
    dev|backend)
        run_backend
        ;;
    frontend)
        run_frontend
        ;;
    test)
        run_tests
        ;;
    build)
        build_frontend
        ;;
    prod)
        echo -e "${GREEN}Starting production server...${NC}"
        cd backend
        source venv/bin/activate
        uvicorn app.main:app --host 0.0.0.0 --port 5050
        ;;
    *)
        echo "Usage: $0 {dev|frontend|test|build|prod}"
        echo ""
        echo "  dev       - Run backend in development mode (default)"
        echo "  frontend  - Run frontend dev server"
        echo "  test      - Run test suite"
        echo "  build     - Build frontend for production"
        echo "  prod      - Run backend in production mode"
        echo ""
        echo "For development, run backend and frontend in separate terminals:"
        echo "  Terminal 1: ./run.sh dev"
        echo "  Terminal 2: ./run.sh frontend"
        exit 1
        ;;
esac



