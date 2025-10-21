from http.server import HTTPServer, SimpleHTTPRequestHandler
import subprocess
import sys
import os

def handler(*args):
    """Start Streamlit server"""
    try:
        # Change to app directory
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        
        # Start streamlit
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            "streamlit_app.py", 
            "--server.port=8080",
            "--server.address=0.0.0.0",
            "--server.headless=true",
            "--server.fileWatcherType=none",
            "--browser.gatherUsageStats=false"
        ])
    except Exception as e:
        print(f"Error starting Streamlit: {e}")

if __name__ == "__main__":
    handler()