#!/bin/bash
# Setup script for Shaggy Dog Web Application

echo "Setting up Shaggy Dog Web Application..."

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cat > .env << EOF
OPENAI_API_KEY=your-openai-api-key-here
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
DATABASE_URL=sqlite:///shaggydog.db
EOF
    echo ".env file created. Please update OPENAI_API_KEY with your actual API key."
fi

# Create upload directories
mkdir -p uploads/originals
mkdir -p uploads/generated

echo "Setup complete!"
echo "To run the application:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Update .env file with your OpenAI API key"
echo "3. Run: python app.py"
