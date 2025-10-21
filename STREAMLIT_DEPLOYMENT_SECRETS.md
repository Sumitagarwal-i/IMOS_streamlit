# 🚀 Streamlit Cloud Deployment - Secrets Configuration

## Step 1: Go to Streamlit Cloud

1. Visit: **https://share.streamlit.io/**
2. Sign in with your GitHub account
3. Click **"New app"**

## Step 2: Configure Your App

- **Repository:** `Sumitagarwal-i/IMOS_streamlit`
- **Branch:** `main`
- **Main file path:** `streamlit_app.py`

## Step 3: Add Secrets

Click **"Advanced settings"** and paste the following into the **Secrets** box:

**⚠️ IMPORTANT:** Replace the placeholder values below with your actual credentials!

```toml
GROQ_API_KEY = "your_groq_api_key_from_console.groq.com"

[gcp_service_account]
client_id = "your_client_id.apps.googleusercontent.com"
project_id = "your-gcp-project-id"
client_secret = "your_gcp_client_secret"
```

**Where to find these values:**
- **GROQ_API_KEY**: Get from `.env` file or https://console.groq.com/
- **client_id, project_id, client_secret**: Get from your `credentials.json` file

## Step 4: Deploy

Click **"Deploy!"** and wait 2-3 minutes for your app to build and start.

## Step 5: Get Your App URL

After deployment, you'll get a URL like:
- `https://imos-streamlit-xxxxx.streamlit.app`

**Copy this URL** - you'll need it for Google OAuth setup.

## Step 6: Update Google OAuth Settings

1. Go to: **https://console.cloud.google.com/**
2. Select project: **linkmage-42**
3. Navigate to: **APIs & Services** → **Credentials**
4. Click on your OAuth 2.0 Client ID
5. Under **"Authorized redirect URIs"**, add:
   - `https://YOUR-APP-URL.streamlit.app`
   - `https://YOUR-APP-URL.streamlit.app/oauth2callback`
   - Keep existing: `http://localhost:8501`
6. Click **Save**

## Step 7: Update credentials.json in Streamlit

Since `credentials.json` is not in the repository, we need to create it dynamically from secrets.

The app will automatically create `credentials.json` from the secrets at runtime.

## Step 8: Test Your App

1. Visit your Streamlit app URL
2. Click "Authenticate with Google Drive"
3. Sign in and grant permissions
4. Import PDFs
5. Chat with your documents!

## Troubleshooting

### "credentials.json not found"
- Make sure you added the `[gcp_service_account]` section to Streamlit secrets
- Check the app logs for errors

### "OAuth Error: redirect_uri_mismatch"
- Verify you added the correct app URL to Google Console
- Make sure there are no trailing slashes
- Wait a few minutes for Google to propagate changes

### "Groq API Error"
- Verify GROQ_API_KEY is correct in secrets
- Check you have API credits at console.groq.com

---

🎉 **That's it! Your app should be live!**

Your app URL will be something like:
**https://imos-streamlit.streamlit.app**
