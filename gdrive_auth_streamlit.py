import streamlit as st
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import PyPDF2
import json
import os
import base64
import pickle
from datetime import datetime
from urllib.parse import urlencode

# Google Drive API scopes
SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'openid'
]

def get_credentials_path():
    """Get the path to credentials.json"""
    return os.path.join(os.path.dirname(__file__), 'credentials.json')

def get_auth_url():
    """Generate Google OAuth URL"""
    try:
        creds_path = get_credentials_path()
        if not os.path.exists(creds_path):
            return None, "credentials.json not found"
        
        # Load client configuration
        with open(creds_path, 'r') as f:
            client_config = json.load(f)
        
        # Use the installed app configuration but modify for web
        if 'installed' in client_config:
            # Convert installed app config to web app config
            config = {
                "web": {
                    "client_id": client_config['installed']['client_id'],
                    "client_secret": client_config['installed']['client_secret'],
                    "auth_uri": client_config['installed']['auth_uri'],
                    "token_uri": client_config['installed']['token_uri'],
                    "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob"]
                }
            }
        else:
            config = client_config
        
        # Create flow for out-of-band (manual code entry)
        flow = Flow.from_client_config(
            config,
            scopes=SCOPES,
            redirect_uri='urn:ietf:wg:oauth:2.0:oob'
        )
        
        # Generate auth URL
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        return auth_url, None
        
    except Exception as e:
        return None, str(e)

def exchange_code_for_token(auth_code):
    """Exchange authorization code for access token"""
    try:
        creds_path = get_credentials_path()
        
        # Load client configuration
        with open(creds_path, 'r') as f:
            client_config = json.load(f)
        
        # Convert to web config if needed
        if 'installed' in client_config:
            config = {
                "web": {
                    "client_id": client_config['installed']['client_id'],
                    "client_secret": client_config['installed']['client_secret'],
                    "auth_uri": client_config['installed']['auth_uri'],
                    "token_uri": client_config['installed']['token_uri'],
                    "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob"]
                }
            }
        else:
            config = client_config
        
        # Create flow
        flow = Flow.from_client_config(
            config,
            scopes=SCOPES,
            redirect_uri='urn:ietf:wg:oauth:2.0:oob'
        )
        
        # Exchange code for token
        flow.fetch_token(code=auth_code.strip())
        
        # Store credentials
        st.session_state.google_credentials = flow.credentials
        
        # Also store in a more persistent way
        creds_dict = {
            'token': flow.credentials.token,
            'refresh_token': flow.credentials.refresh_token,
            'token_uri': flow.credentials.token_uri,
            'client_id': flow.credentials.client_id,
            'client_secret': flow.credentials.client_secret,
            'scopes': flow.credentials.scopes
        }
        st.session_state.google_creds_dict = creds_dict
        
        return True, "Authentication successful!"
        
    except Exception as e:
        return False, f"Authentication failed: {str(e)}"

def load_stored_credentials():
    """Load stored credentials if available"""
    try:
        if 'google_creds_dict' in st.session_state:
            creds_dict = st.session_state.google_creds_dict
            
            # Recreate credentials object
            credentials = Credentials(
                token=creds_dict.get('token'),
                refresh_token=creds_dict.get('refresh_token'),
                token_uri=creds_dict.get('token_uri'),
                client_id=creds_dict.get('client_id'),
                client_secret=creds_dict.get('client_secret'),
                scopes=creds_dict.get('scopes')
            )
            
            # Check if credentials are valid and refresh if needed
            if credentials.valid:
                st.session_state.google_credentials = credentials
                return True
            elif credentials.refresh_token:
                try:
                    credentials.refresh(Request())
                    st.session_state.google_credentials = credentials
                    # Update stored dict
                    st.session_state.google_creds_dict['token'] = credentials.token
                    return True
                except:
                    # Refresh failed, need to re-authenticate
                    return False
        
        return False
        
    except Exception:
        return False

def authenticate_drive():
    """Main authentication function with improved UX"""
    # Try to load existing credentials first
    if load_stored_credentials():
        return True
    
    # Show authentication UI
    st.subheader("🔐 Google Drive Authentication")
    st.info("To access your PDFs, we need permission to read your Google Drive files.")
    
    # Step 1: Generate auth URL
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.button("🚀 Start Authentication", type="primary", use_container_width=True):
            auth_url, error = get_auth_url()
            
            if auth_url:
                st.session_state.auth_url = auth_url
                st.session_state.show_auth_step = True
            else:
                st.error(f"Failed to generate auth URL: {error}")
    
    # Show authentication steps if URL is generated
    if st.session_state.get('show_auth_step', False) and st.session_state.get('auth_url'):
        st.markdown("---")
        
        # Step 1: Auth URL
        st.markdown("**Step 1:** Click the link below to authenticate:")
        auth_url = st.session_state.auth_url
        
        # Create a more prominent link
        st.markdown(f"""
        <div style="padding: 10px; background-color: #e1f5fe; border-radius: 5px; margin: 10px 0;">
            <a href="{auth_url}" target="_blank" style="color: #0277bd; font-weight: bold; text-decoration: none;">
                🔗 Open Google Authentication Page
            </a>
        </div>
        """, unsafe_allow_html=True)
        
        # Step 2: Code input
        st.markdown("**Step 2:** Copy the authorization code and paste it here:")
        
        with st.form("auth_form", clear_on_submit=False):
            auth_code = st.text_input(
                "Authorization Code:",
                placeholder="Paste the code you received from Google here...",
                type="password"
            )
            submit_button = st.form_submit_button("🔑 Complete Authentication")
            
            if submit_button and auth_code:
                with st.spinner("Verifying authorization code..."):
                    success, message = exchange_code_for_token(auth_code)
                    
                    if success:
                        st.success(message)
                        # Clear the auth step
                        st.session_state.show_auth_step = False
                        st.session_state.auth_url = None
                        # Rerun to refresh the page
                        st.rerun()
                    else:
                        st.error(message)
        
        # Add helpful instructions
        st.markdown("""
        **Instructions:**
        1. Click the authentication link above (opens in new tab)
        2. Choose your Google account and grant permissions
        3. Copy the authorization code shown on the screen
        4. Paste the code in the input box above and click "Complete Authentication"
        """)
    
    return 'google_credentials' in st.session_state

def init_drive_service():
    """Initialize Google Drive service"""
    try:
        if 'google_credentials' not in st.session_state:
            return None
        
        service = build('drive', 'v3', credentials=st.session_state.google_credentials)
        return service
        
    except Exception as e:
        st.error(f"Failed to initialize Drive service: {str(e)}")
        return None

def is_authenticated():
    """Check if user is authenticated"""
    return 'google_credentials' in st.session_state

def sign_out():
    """Sign out and clear credentials"""
    keys_to_remove = ['google_credentials', 'google_creds_dict', 'auth_url', 'show_auth_step']
    for key in keys_to_remove:
        if key in st.session_state:
            del st.session_state[key]

def list_all_pdfs(service, max_results=1000):
    """List all PDF files from Google Drive"""
    try:
        query = "mimeType='application/pdf' and trashed=false"
        
        results = service.files().list(
            q=query,
            pageSize=min(max_results, 1000),
            fields="nextPageToken, files(id, name, size, modifiedTime, parents)"
        ).execute()
        
        items = results.get('files', [])
        
        # Get parent folder names
        pdfs = []
        for item in items:
            # Get parent folder name
            parent_name = "Drive"
            if item.get('parents'):
                try:
                    parent_id = item['parents'][0]
                    parent_info = service.files().get(fileId=parent_id, fields='name').execute()
                    parent_name = parent_info.get('name', 'Drive')
                except:
                    parent_name = "Drive"
            
            # Format modified time
            modified_time = item.get('modifiedTime', '')
            if modified_time:
                try:
                    dt = datetime.fromisoformat(modified_time.replace('Z', '+00:00'))
                    modified_time = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    pass
            
            pdfs.append({
                'id': item['id'],
                'name': item['name'],
                'size': int(item.get('size', 0)),
                'modifiedTime': modified_time,
                'parent': parent_name,
                'drive_link': f"https://drive.google.com/file/d/{item['id']}/view"
            })
        
        return pdfs
        
    except Exception as e:
        st.error(f"Error listing PDFs: {str(e)}")
        return []

def download_pdf_content(service, file_id):
    """Download and extract text content from PDF"""
    try:
        # Download file
        request = service.files().get_media(fileId=file_id)
        file_buffer = io.BytesIO()
        
        downloader = MediaIoBaseDownload(file_buffer, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        
        file_buffer.seek(0)
        
        # Extract text from PDF
        pdf_reader = PyPDF2.PdfReader(file_buffer)
        text_content = ""
        
        for page in pdf_reader.pages:
            try:
                text_content += page.extract_text() + "\n"
            except:
                continue
        
        return text_content.strip()
        
    except Exception as e:
        st.error(f"Error downloading PDF content: {str(e)}")
        return ""