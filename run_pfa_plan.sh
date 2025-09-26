#!/bin/bash
# PFA Planning System Runner Script
# Automatically activates venv and runs the planning system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Setup virtual environment if it doesn't exist
if [ ! -d "venvs/main" ]; then
    echo -e "${BLUE}🚀 Setting up PFA Planning System for first time...${NC}"

    # Create venvs directory structure
    mkdir -p venvs

    # Create virtual environment
    echo -e "${BLUE}📦 Creating main virtual environment at venvs/main/...${NC}"
    python3 -m venv venvs/main

    # Activate and setup environment
    source venvs/main/bin/activate

    # Upgrade pip
    echo -e "${BLUE}📈 Upgrading pip...${NC}"
    pip install --upgrade pip

    # Install requirements
    echo -e "${BLUE}📚 Installing dependencies...${NC}"
    pip install pyyaml

    # Make scripts executable
    echo -e "${BLUE}🔧 Making scripts executable...${NC}"
    chmod +x generate_pfa_plan.py
    chmod +x run_pfa_plan.sh

    echo -e "${GREEN}✅ Setup complete!${NC}"
    echo ""
    echo -e "${BLUE}📊 Virtual environments:${NC}"
    echo -e "${BLUE}  Main app: venvs/main/${NC}"
    echo -e "${BLUE}  Graph API: venvs/graph/ (created by ./scripts/run-graph.sh)${NC}"
    echo ""
else
    # Activate existing virtual environment
    echo -e "${BLUE}⚡ Activating virtual environment...${NC}"
    source venvs/main/bin/activate
fi

# Load environment variables from .env file
if [ -f ".env" ]; then
    echo -e "${BLUE}🔧 Loading environment variables from .env...${NC}"
    set -a
    source .env
    set +a
else
    echo -e "${YELLOW}⚠️  No .env file found - API credentials may not be available${NC}"
fi

# Check if Python script exists
if [ ! -f "generate_pfa_plan.py" ]; then
    echo -e "${RED}❌ generate_pfa_plan.py not found!${NC}"
    exit 1
fi

# Run the PFA planning system with all arguments passed through
echo -e "${GREEN}🏃‍♂️ Running PFA Planning System...${NC}"
python generate_pfa_plan.py "$@"

# Check exit code
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ PFA Plan generation completed successfully!${NC}"
else
    echo -e "${RED}❌ PFA Plan generation failed${NC}"
    exit 1
fi