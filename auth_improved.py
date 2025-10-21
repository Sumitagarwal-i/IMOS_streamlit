"""
Improved Google Drive Authentication for Streamlit
This version provides a better UX with clearer instructions and state management
"""

import streamlit as st
import json
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# Google Drive API scopes
SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'openid'
]

class GoogleDriveAuth:
    def __init__(self):
        self.credentials_path = os.path.join(os.path.dirname(__file__), 'credentials.json')
    
    def load_credentials_config(self):
        """Load Google OAuth credentials configuration"""
        try:
            with open(self.credentials_path, 'r') as f:
                config = json.load(f)
            
            # Always use installed app flow for desktop/streamlit apps
            if 'installed' in config:
                # Keep the installed configuration but ensure it has the right redirect URI
                config['installed']['redirect_uris'] = ['urn:ietf:wg:oauth:2.0:oob']
                return config
            elif 'web' in config:
                # Convert web config to installed for better compatibility
                web_config = config['web']
                return {
                    "installed": {
                        "client_id": web_config['client_id'],
                        "client_secret": web_config['client_secret'],
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                        "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob"]
                    }
                }
            else:
                st.error("Invalid credentials format. Please check your credentials.json file.")
                return None
                
        except Exception as e:
            st.error(f"Error loading credentials: {e}")
            return None
    
    def is_authenticated(self):
        """Check if user is currently authenticated"""
        if 'google_credentials' not in st.session_state:
            return False
        
        credentials = st.session_state.google_credentials
        if not credentials.valid:
            if credentials.refresh_token:
                try:
                    credentials.refresh(Request())
                    return True
                except:
                    return False
            return False
        return True
    
    def get_auth_url(self):
        """Generate Google OAuth authorization URL"""
        try:
            config = self.load_credentials_config()
            if not config:
                return None
            
            # Use installed app flow
            flow = Flow.from_client_config(
                config,
                scopes=SCOPES
            )
            flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
            
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'
            )
            
            # Store flow in session for later use
            st.session_state.oauth_flow = flow
            
            return auth_url
        except Exception as e:
            st.error(f"Error generating auth URL: {e}")
            return None
    
    def exchange_code(self, auth_code):
        """Exchange authorization code for access token"""
        try:
            if 'oauth_flow' not in st.session_state:
                # Create a new flow if needed
                config = self.load_credentials_config()
                if not config:
                    return False, "Configuration error"
                
                flow = Flow.from_client_config(
                    config,
                    scopes=SCOPES
                )
                flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
            else:
                flow = st.session_state.oauth_flow
            
            # Exchange code for token
            flow.fetch_token(code=auth_code.strip())
            
            # Store credentials
            st.session_state.google_credentials = flow.credentials
            
            # Clean up
            if 'oauth_flow' in st.session_state:
                del st.session_state.oauth_flow
            
            return True, "Authentication successful!"
            
        except Exception as e:
            error_msg = str(e)
            if "Scope has changed" in error_msg:
                return False, "Authentication scope mismatch. Please try the authentication process again."
            elif "invalid_grant" in error_msg:
                return False, "Authorization code expired or invalid. Please get a new code."
            else:
                return False, f"Authentication failed: {error_msg}"
    
    def sign_out(self):
        """Sign out and clear all authentication data"""
        keys_to_remove = ['google_credentials', 'oauth_flow', 'auth_step', 'auth_url']
        for key in keys_to_remove:
            if key in st.session_state:
                del st.session_state[key]
    
    def reset_auth_flow(self):
        """Reset the authentication flow"""
        keys_to_remove = ['oauth_flow', 'auth_step', 'auth_url']
        for key in keys_to_remove:
            if key in st.session_state:
                del st.session_state[key]
        st.session_state.auth_step = 1
    
    def get_drive_service(self):
        """Get authenticated Google Drive service"""
        if not self.is_authenticated():
            return None
        
        try:
            return build('drive', 'v3', credentials=st.session_state.google_credentials)
        except Exception as e:
            st.error(f"Error creating Drive service: {e}")
            return None
    
    def show_auth_interface(self):
        """Display the authentication interface"""
        st.subheader("🔐 Connect to Google Drive")
        
        # Check if already authenticated
        if self.is_authenticated():
            st.success("✅ Connected to Google Drive!")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📁 Continue to Import", type="primary"):
                    st.session_state.current_page = 'import'
                    st.rerun()
            
            with col2:
                if st.button("🚪 Sign Out"):
                    self.sign_out()
                    st.rerun()
            
            return True
        
        # Show authentication steps
        st.info("🔒 We need read-only access to your Google Drive to import PDF files.")
        
        # Authentication state management
        if 'auth_step' not in st.session_state:
            st.session_state.auth_step = 1
        
        if st.session_state.auth_step == 1:
            # Step 1: Generate auth URL
            st.markdown("### Step 1: Authorize Access")
            st.write("Click the button below to open Google's authorization page:")
            
            if st.button("🚀 Open Google Authorization", type="primary"):
                auth_url = self.get_auth_url()
                if auth_url:
                    st.session_state.auth_url = auth_url
                    st.session_state.auth_step = 2
                    st.rerun()
        
        elif st.session_state.auth_step == 2:
            # Step 2: Show auth URL and get code
            st.markdown("### Step 2: Complete Authorization")
            
            # Show the auth URL prominently
            if 'auth_url' in st.session_state:
                st.markdown(f"""
                <div style="padding: 15px; background-color: #e3f2fd; border-left: 4px solid #2196f3; border-radius: 4px; margin: 15px 0;">
                    <p><strong>🔗 Authorization Link:</strong></p>
                    <a href="{st.session_state.auth_url}" target="_blank" style="color: #1976d2; font-weight: bold; text-decoration: none;">
                        Click here to authorize IMOS to access your Google Drive
                    </a>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("**Instructions:**")
                st.markdown("1. Click the authorization link above (opens in new tab)")
                st.markdown("2. Sign in to your Google account")
                st.markdown("3. Grant permission to read your Drive files")
                st.markdown("4. Copy the authorization code shown")
                st.markdown("5. Paste the code below and click 'Complete Setup'")
                
                # Code input form
                with st.form("auth_code_form"):
                    auth_code = st.text_input(
                        "Authorization Code:",
                        placeholder="Paste the code from Google here...",
                        help="Copy the entire code from the Google authorization page"
                    )
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        submit = st.form_submit_button("✅ Complete Setup", type="primary")
                    with col2:
                        restart = st.form_submit_button("🔄 Start Over")
                    
                    if restart:
                        st.session_state.auth_step = 1
                        if 'auth_url' in st.session_state:
                            del st.session_state.auth_url
                        st.rerun()
                    
                    if submit and auth_code:
                        with st.spinner("Verifying authorization..."):
                            success, message = self.exchange_code(auth_code)
                            
                            if success:
                                st.success(message)
                                st.session_state.auth_step = 1  # Reset for next time
                                if 'auth_url' in st.session_state:
                                    del st.session_state.auth_url
                                st.balloons()
                                st.rerun()
                            else:
                                st.error(message)
                                if "scope mismatch" in message.lower() or "scope has changed" in message.lower():
                                    st.warning("⚠️ Scope mismatch detected. Restarting authentication process...")
                                    self.reset_auth_flow()
                                    st.rerun()
                                else:
                                    st.info("💡 Make sure you copied the entire authorization code. If the problem persists, click 'Start Over'.")
        
        return False

# Create global instance
auth_manager = GoogleDriveAuth()

# Export functions for compatibility
def authenticate_drive():
    return auth_manager.show_auth_interface()

def is_authenticated():
    return auth_manager.is_authenticated()

def init_drive_service():
    return auth_manager.get_drive_service()

def sign_out():
    auth_manager.sign_out()