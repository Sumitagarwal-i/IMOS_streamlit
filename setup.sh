#!/bin/bash

echo "🧠 IMOS Streamlit App Setup"
echo "=========================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ and try again."
    exit 1
fi

echo "✅ Python found: $(python3 --version)"

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "🎉 Setup complete!"
echo ""
echo "To run the app:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Start the app: streamlit run streamlit_app.py"
echo ""
echo "📝 Don't forget to:"
echo "   - Update credentials.json with your Google Drive API credentials"
echo "   - Update .env with your Groq API key"
echo ""