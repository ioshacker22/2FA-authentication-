#!/bin/bash

# 2FA Authentication App Setup Script
# This script automates the setup process

set -e

echo " Starting 2FA Authentication App Setup..."
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then 
    echo "Python $python_version detected"
else
    echo "Python 3.8 or higher is required. You have $python_version"
    exit 1
fi

# Create virtual environment
echo ""
echo "📦 Creating virtual environment..."
if [ -d "venv" ]; then
    echo "⚠️  Virtual environment already exists. Skipping..."
else
    python3 -m venv venv
    echo "Virtual environment created"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate
echo "Virtual environment activated"

# Upgrade pip
echo ""
echo "  Upgrading pip..."
pip install --upgrade pip --quiet
echo "Pip upgraded"

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt --quiet
echo " Dependencies installed"

# Create .env file if it doesn't exist
echo ""
if [ -f ".env" ]; then
    echo "  .env file already exists. Skipping..."
else
    echo "Creating .env file..."
    cp .env.example .env
    
    # Generate a random secret key
    secret_key=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    
    # Update .env file with generated secret key
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/your-super-secret-key-change-this-in-production/$secret_key/" .env
    else
        # Linux
        sed -i "s/your-super-secret-key-change-this-in-production/$secret_key/" .env
    fi
    
    echo " .env file created with generated SECRET_KEY"
fi

# Create instance directory
echo ""
echo " Creating instance directory..."
mkdir -p instance
mkdir -p logs
echo "Directories created"

# Initialize database
echo ""
echo "  Initializing database..."
python3 -c "from app import app, db; app.app_context().push(); db.create_all()" 2>/dev/null || true
echo " Database initialized"

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " Setup Complete! "
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo " Next Steps:"
echo ""
echo "1. Review your .env file and update settings if needed"
echo "2. Start the application:"
echo "   source venv/bin/activate"
echo "   python3 app.py"
echo ""
echo "3. Open your browser to:"
echo "   http://127.0.0.1:5000"
echo ""
echo " For more information, check the README.md"
echo ""
echo " Docker Alternative:"
echo "   docker-compose up -d"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"