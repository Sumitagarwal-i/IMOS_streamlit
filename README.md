# IMOS Streamlit App

A Streamlit-based intelligent memory OS for analyzing PDFs from Google Drive using AI.

## Features

- 🔗 Google Drive integration for PDF import
- 🧠 AI-powered document analysis using Groq API
- 🔍 Semantic search across your documents
- 💬 Multi-turn conversation with your knowledge base
- 🔒 Privacy-first design - your data stays local

## Setup

### 1. Google Drive API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Google Drive API
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
5. Configure OAuth consent screen
6. Download the credentials JSON file
7. Replace the content in `credentials.json`

### 2. Groq API Setup

1. Get your free API key from [Groq Console](https://console.groq.com/)
2. Update the `.env` file with your API key

### 3. Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run streamlit_app.py
```

### 4. Vercel Deployment

1. Install Vercel CLI: `npm i -g vercel`
2. Deploy: `vercel`
3. Set environment variables in Vercel dashboard:
   - `GROQ_API_KEY`: Your Groq API key

## File Structure

```
streamlit-app/
├── streamlit_app.py              # Main Streamlit application
├── gdrive_auth_streamlit.py      # Google Drive authentication
├── credentials.json              # Google Drive API credentials
├── requirements.txt              # Python dependencies
├── vercel.json                  # Vercel deployment config
├── .env                         # Environment variables
└── README.md                    # This file
```

## How to Use

1. **Landing Page**: Start by connecting your Google Drive
2. **Import PDFs**: Select and import PDFs from your Drive
3. **AI Chat**: Ask questions about your documents using natural language

## Deployment on Vercel

1. Push your code to GitHub
2. Connect your repository to Vercel
3. Set environment variables in Vercel dashboard
4. Deploy!

## Privacy & Security

- Your PDF content is processed locally
- No data is sent to third parties except for AI processing
- Google Drive integration uses read-only access
- SQLite database stores embeddings locally

## Troubleshooting

### Authentication Issues
- Ensure `credentials.json` has correct OAuth client configuration
- Check that redirect URI includes your domain/localhost
- Verify Google Drive API is enabled

### Vercel Deployment Issues
- Check that all dependencies are in `requirements.txt`
- Ensure environment variables are set in Vercel dashboard
- Verify Python version compatibility

## Tech Stack

- **Frontend**: Streamlit
- **Backend**: Python
- **Database**: SQLite
- **AI**: Sentence Transformers + Groq API
- **Cloud**: Google Drive API
- **Deployment**: Vercel

## License

MIT License