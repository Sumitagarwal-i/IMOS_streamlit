@echo off
echo 🧠 IMOS Streamlit App Setup
echo ==========================

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed. Please install Python 3.8+ and try again.
    pause
    exit /b 1
)

echo ✅ Python found: 
python --version

REM Create virtual environment
echo 📦 Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate

REM Install dependencies
echo 📚 Installing dependencies...
pip install -r requirements.txt

echo.
echo 🎉 Setup complete!
echo.
echo To run the app:
echo 1. Activate virtual environment: venv\Scripts\activate
echo 2. Start the app: streamlit run streamlit_app.py
echo.
echo 📝 Don't forget to:
echo    - Update credentials.json with your Google Drive API credentials
echo    - Update .env with your Groq API key
echo.
pause