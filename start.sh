#!/bin/bash

# Web Automation Assistant Startup Script
# Starts both backend and frontend servers

echo "======================================================================"
echo "Starting Web Automation Assistant"
echo "======================================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}Virtual environment not found${NC}"
    echo "Please run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}.env file not found${NC}"
    echo "Please run: cp .env.example .env"
    echo "Then add your OPENAI_API_KEY to .env"
    exit 1
fi

# Check if frontend dependencies are installed
if [ ! -d "frontend/node_modules" ]; then
    echo -e "${YELLOW}Frontend dependencies not found${NC}"
    echo "Installing frontend dependencies..."
    cd frontend && npm install && cd ..
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "======================================================================"
    echo "Shutting down servers..."
    echo "======================================================================"
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "Cleanup complete"
    exit 0
}

# Set trap to cleanup on CTRL+C
trap cleanup INT TERM

echo -e "${BLUE}Starting Backend API Server...${NC}"
echo "----------------------------------------------------------------------"

# Activate virtual environment and start backend
source venv/bin/activate
python api_server.py > backend.log 2>&1 &
BACKEND_PID=$!

echo -e "${GREEN}Backend started (PID: $BACKEND_PID)${NC}"
echo "  API: http://localhost:8000"
echo "  Docs: http://localhost:8000/docs"
echo "  Logs: tail -f backend.log"
echo ""

# Wait for backend to start
sleep 3

echo -e "${BLUE}Starting Frontend Dev Server...${NC}"
echo "----------------------------------------------------------------------"

# Start frontend
cd frontend
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

echo -e "${GREEN}Frontend started (PID: $FRONTEND_PID)${NC}"
echo "  UI: http://localhost:3000"
echo "  Logs: tail -f frontend.log"
echo ""

echo "======================================================================"
echo -e "${GREEN}Both servers are running!${NC}"
echo "======================================================================"
echo ""
echo "Open your browser to: http://localhost:3000"
echo ""
echo "Logs:"
echo "  Backend: tail -f backend.log"
echo "  Frontend: tail -f frontend.log"
echo ""
echo "Press CTRL+C to stop all servers"
echo "======================================================================"
echo ""

# Wait for processes
wait
