#!/bin/bash
# PFA Planning System Setup Script

set -e  # Exit on any error

echo "🚀 Setting up PFA Planning System..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "⚡ Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "📈 Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📚 Installing dependencies..."
pip install pyyaml

# Make scripts executable
echo "🔧 Making scripts executable..."
chmod +x generate_pfa_plan.py
chmod +x run_pfa_plan.sh

echo "✅ Setup complete!"
echo ""
echo "🎯 Next steps:"
echo "  1. Run: ./run_pfa_plan.sh --template configs/personal/my_plan.yml"
echo "  2. Edit configs/personal/my_plan.yml with your parameters"
echo "  3. Run: ./run_pfa_plan.sh configs/personal/my_plan.yml"
echo ""
echo "Or use templates:"
echo "  ./run_pfa_plan.sh configs/templates/beginner.yml"
echo "  ./run_pfa_plan.sh configs/templates/intermediate.yml"
echo "  ./run_pfa_plan.sh configs/templates/advanced.yml"