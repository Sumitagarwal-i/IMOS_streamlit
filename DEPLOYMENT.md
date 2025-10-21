# IMOS - Intelligent Memory OS 🧠

AI-powered document chat system with Google Drive integration.

## Features

- 📁 Import PDFs from Google Drive
- 🔍 Semantic search across documents
- 💬 AI-powered chat using Groq API (Llama 3.1)
- 🔐 Secure Google OAuth authentication
- 💾 Local document storage and embeddings

## Deployment to Streamlit Cloud

### Step 1: Push to GitHub

```bash
cd streamlit-app
git init
git add .
git commit -m "Initial commit - IMOS Streamlit App"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/imos-streamlit.git
git push -u origin main
```

### Step 2: Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io/)
2. Sign in with GitHub
3. Click **"New app"**
4. Select your repository
5. Set the following:
   - **Branch:** `main`
   - **Main file path:** `streamlit_app.py`
6. Click **"Advanced settings"**
7. In the **Secrets** section, paste:

```toml
GROQ_API_KEY = "your_groq_api_key_here"
```

8. Click **"Deploy!"**

### Step 3: Configure Google OAuth

After your app is deployed, you'll get a URL like: `https://your-app-name.streamlit.app`

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project
3. Navigate to **APIs & Services** > **Credentials**
4. Edit your **OAuth 2.0 Client ID**
5. Add these **Authorized redirect URIs**:
   - `https://your-app-name.streamlit.app`
   - `https://your-app-name.streamlit.app/oauth2callback`
   - `http://localhost:8501` (for local testing)
6. Click **Save**

### Step 4: Test Your Deployment

Visit your app URL and verify:
- ✅ Google Drive authentication works
- ✅ PDFs can be imported
- ✅ AI chat responds correctly

## Local Development

### Prerequisites

- Python 3.9 or higher
- Google Cloud Project with Drive API enabled
- Groq API key

### Setup

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/imos-streamlit.git
cd imos-streamlit
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file:
```env
GROQ_API_KEY=your_groq_api_key_here
```

4. Run the app:
```bash
streamlit run streamlit_app.py
```

5. Open your browser to: `http://localhost:8501`

## Configuration

### Google Drive API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable **Google Drive API**
4. Create **OAuth 2.0 Client ID** credentials
5. Download as `credentials.json` and place in project root

### Environment Variables

Create a `.env` file (for local) or use Streamlit Secrets (for deployment):

```env
GROQ_API_KEY=your_groq_api_key_here
```

## Project Structure

```
streamlit-app/
├── streamlit_app.py          # Main application
├── auth_improved.py          # Google Drive authentication
├── gdrive_auth_streamlit.py  # Google Drive API functions
├── requirements.txt          # Python dependencies
├── credentials.json          # Google OAuth credentials (not in git)
├── .env                      # Environment variables (not in git)
├── .streamlit/
│   ├── config.toml          # Streamlit configuration
│   └── secrets.toml         # Secrets for deployment (not in git)
└── memoryos.db              # SQLite database (created at runtime)
```

## Tech Stack

- **Frontend:** Streamlit
- **AI Model:** Groq API (Llama 3.1 70B)
- **Embeddings:** Sentence Transformers (all-MiniLM-L6-v2)
- **Database:** SQLite
- **Cloud Storage:** Google Drive API
- **Deployment:** Streamlit Cloud

## Troubleshooting

### Google Auth Fails

- Verify redirect URIs in Google Console match your deployment URL
- Check `credentials.json` is present
- Clear browser cookies and try again

### Groq API Errors

- Verify `GROQ_API_KEY` is set in secrets
- Check API key is valid at [console.groq.com](https://console.groq.com/)
- Ensure you have API credits remaining

### Import Issues

- Check Google Drive permissions are granted
- Verify PDFs are accessible in your Drive
- Check file size limits (large PDFs may timeout)

## Support

For issues and questions:
- Check [Streamlit Documentation](https://docs.streamlit.io/)
- Review [Groq API Docs](https://console.groq.com/docs)
- Google Drive API [Reference](https://developers.google.com/drive/api/v3/reference)

## License

MIT License - See LICENSE file for details
