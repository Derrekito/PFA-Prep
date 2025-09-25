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

# Check if venv exists
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Virtual environment not found!${NC}"
    echo -e "${YELLOW}💡 Run './setup.sh' first to set up the environment${NC}"
    exit 1
fi

# Activate virtual environment
echo -e "${BLUE}⚡ Activating virtual environment...${NC}"
source venv/bin/activate

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