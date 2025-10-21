import streamlit as st
import sqlite3
import json
import os
from datetime import datetime
import numpy as np
from sentence_transformers import SentenceTransformer
import requests
from dotenv import load_dotenv
import uuid
from auth_improved import (
    authenticate_drive,
    is_authenticated,
    init_drive_service,
    sign_out
)
from gdrive_auth_streamlit import (
    list_all_pdfs, 
    download_pdf_content
)

# Load environment variables
load_dotenv()

# Create credentials.json from Streamlit secrets if it doesn't exist
# This is needed for Streamlit Cloud deployment
try:
    if not os.path.exists('credentials.json'):
        if hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
            credentials_data = {
                "installed": {
                    "client_id": st.secrets["gcp_service_account"]["client_id"],
                    "project_id": st.secrets["gcp_service_account"]["project_id"],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_secret": st.secrets["gcp_service_account"]["client_secret"],
                    "redirect_uris": ["http://localhost:8501", "http://localhost"]
                }
            }
            with open('credentials.json', 'w') as f:
                json.dump(credentials_data, f)
except Exception as e:
    print(f"Warning: Could not create credentials.json: {e}")
    pass  # Continue anyway, credentials.json might exist locally

# Configure Streamlit page
st.set_page_config(
    page_title="IMOS - Intelligent Memory OS",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'user_id' not in st.session_state:
    # Use a consistent user_id for this session
    st.session_state.user_id = "default_user"

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = is_authenticated()

if 'drive_service' not in st.session_state:
    st.session_state.drive_service = None

if 'embed_model' not in st.session_state:
    st.session_state.embed_model = None

if 'current_page' not in st.session_state:
    st.session_state.current_page = 'landing'

if 'drive_pdfs_cache' not in st.session_state:
    st.session_state.drive_pdfs_cache = None

if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []

if 'import_complete' not in st.session_state:
    st.session_state.import_complete = False

# Initialize database
def setup_db():
    """Initialize SQLite database"""
    conn = sqlite3.connect('memoryos.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS pdf_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            file_id TEXT UNIQUE NOT NULL,
            name TEXT,
            drive_link TEXT,
            modified_time TEXT,
            size INTEGER,
            parent TEXT,
            text_content TEXT,
            embedding BLOB,
            last_indexed TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def get_embed_model():
    """Lazy loading of the embedding model with error handling"""
    if st.session_state.embed_model is None:
        try:
            with st.spinner("Loading AI model..."):
                st.session_state.embed_model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as e:
            st.error(f"Error loading embedding model: {e}")
            # Try a smaller model as fallback
            try:
                st.session_state.embed_model = SentenceTransformer("paraphrase-MiniLM-L3-v2")
            except Exception as e2:
                st.error(f"Failed to load fallback model: {e2}")
                raise
    return st.session_state.embed_model

def compute_embedding(text):
    """Compute text embedding"""
    if len(text) > 4000:
        text = text[:4000]
    model = get_embed_model()
    emb = model.encode(text, convert_to_numpy=True).tolist()
    return json.dumps(emb)

def cosine_sim(a, b):
    """Compute cosine similarity"""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def save_pdf_to_db(user_id, file_id, name, drive_link, modified_time, size, parent, text_content, embedding=None):
    """Save PDF data to database"""
    conn = sqlite3.connect('memoryos.db')
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO pdf_documents
        (user_id, file_id, name, drive_link, modified_time, size, parent, text_content, embedding, last_indexed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id, file_id, name, drive_link, modified_time, size, parent, 
        text_content, embedding, datetime.utcnow()
    ))
    conn.commit()
    conn.close()

def semantic_search(query, top_k=5, user_id=None):
    """Perform semantic search on documents"""
    if not query:
        return []
    
    # Compute query embedding
    model = get_embed_model()
    query_emb = model.encode(query, convert_to_numpy=True)
    
    conn = sqlite3.connect('memoryos.db')
    c = conn.cursor()
    
    if user_id:
        c.execute('''
            SELECT file_id, name, drive_link, modified_time, size, parent, text_content, embedding 
            FROM pdf_documents 
            WHERE user_id = ? AND embedding IS NOT NULL
        ''', (user_id,))
    else:
        c.execute('''
            SELECT file_id, name, drive_link, modified_time, size, parent, text_content, embedding 
            FROM pdf_documents
            WHERE embedding IS NOT NULL
        ''')
    
    results = []
    for row in c.fetchall():
        try:
            if row[7]:  # Check if embedding exists
                pdf_emb = np.array(json.loads(row[7]))
                score = cosine_sim(query_emb, pdf_emb)
                if score > 0.1:  # threshold
                    results.append({
                        'file_id': row[0],
                        'name': row[1],
                        'drive_link': row[2],
                        'modified_time': row[3],
                        'size': row[4],
                        'parent': row[5],
                        'snippet': row[6][:400] if row[6] else '',
                        'score': float(score)
                    })
        except Exception as e:
            continue
    
    conn.close()
    results = sorted(results, key=lambda x: x['score'], reverse=True)[:top_k]
    return results

def answer_query_with_groq(conversation_history, top_matches, groq_api_key):
    """Generate answer using Groq API"""
    # Build context from top docs
    context = "\n---\n".join([f"{doc['name']}:\n{doc['snippet']}" for doc in top_matches])
    
    # System message
    system_message = {
        "role": "system",
        "content": (
            f"You are IMOS, an intelligent memory OS for professionals and solopreneurs. "
            f"You help users understand and analyze their documents through natural conversation. "
            f"\nRELEVANT DOCUMENT CONTEXT:\n{context}\n\n"
            f"Guidelines:\n"
            f"- Use the provided context to answer questions accurately\n"
            f"- Reference specific documents when citing information\n"
            f"- If the context doesn't contain relevant information, say so politely\n"
            f"- Maintain conversation flow and refer to previous exchanges when relevant\n"
            f"- Be concise but thorough in your responses"
        )
    }
    
    # Clean conversation history
    cleaned_messages = []
    for msg in conversation_history:
        if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
            cleaned_msg = {
                "role": msg['role'],
                "content": str(msg['content'])
            }
            if cleaned_msg['role'] in ['user', 'assistant']:
                cleaned_messages.append(cleaned_msg)
    
    # Limit to last 10 messages
    if len(cleaned_messages) > 10:
        cleaned_messages = cleaned_messages[-10:]
    
    messages = [system_message] + cleaned_messages
    
    groq_api_url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {groq_api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "messages": messages,
        "model": "llama-3.1-8b-instant",
        "max_tokens": 1500,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(groq_api_url, headers=headers, json=payload)
        response.raise_for_status()
        answer = response.json()['choices'][0]['message']['content'].strip()
        return answer, top_matches
    except Exception as e:
        st.error(f"Error calling Groq API: {str(e)}")
        return "Sorry, I encountered an error while processing your request.", []

# Page functions
def landing_page():
    """Landing page"""
    st.markdown("""
    <div style="text-align: center; padding: 2rem;">
        <h1>🧠 Welcome to IMOS</h1>
        <h2 style="color: #1f77b4;">Your Intelligent Memory OS</h2>
        <div style="margin: 2rem 0;">
            <p>– Instantly recall, connect, and reason across your Google Drive knowledge</p>
            <p>– 100% private. Your data never leaves your control.</p>
            <p>– No mindless file search. Experience true cognitive AI.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Show authentication interface
    authenticate_drive()

def import_page():
    """PDF import page"""
    st.title("📁 Import PDFs from Google Drive")
    
    if not is_authenticated():
        st.error("Please authenticate with Google Drive first.")
        if st.button("🔙 Go to Landing"):
            st.session_state.current_page = 'landing'
            st.rerun()
        return
    
    # Show success buttons if import was completed
    if st.session_state.import_complete:
        st.success("✅ Import completed successfully!")
        
        # Verify documents count
        conn = sqlite3.connect('memoryos.db')
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM pdf_documents WHERE user_id = ?', (st.session_state.user_id,))
        saved_count = c.fetchone()[0]
        conn.close()
        
        st.info(f"📊 Documents now in database: {saved_count}")
        st.success("🎉 Ready to chat with your documents!")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💬 Continue to Chat", type="primary", key="continue_chat_final"):
                st.session_state.import_complete = False  # Reset flag
                st.session_state.current_page = 'chat'
                st.rerun()
        
        with col2:
            if st.button("📥 Import More PDFs", key="import_more_final"):
                st.session_state.import_complete = False  # Reset flag
                st.rerun()
        
        return  # Don't show the import interface again
    
    # Cache management
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write("Select PDFs to import for AI analysis")
    with col2:
        if st.button("🔄 Refresh from Drive"):
            st.session_state.drive_pdfs_cache = None
    
    # Load PDFs from cache or fetch new
    if st.session_state.drive_pdfs_cache is None:
        with st.spinner("Loading PDFs from Google Drive..."):
            try:
                drive_service = init_drive_service()
                if drive_service:
                    pdfs = list_all_pdfs(drive_service)
                    st.session_state.drive_pdfs_cache = pdfs
                else:
                    st.error("Failed to initialize Google Drive service")
                    return
            except Exception as e:
                st.error(f"Error loading PDFs: {str(e)}")
                return
    
    pdfs = st.session_state.drive_pdfs_cache
    
    if not pdfs:
        st.warning("No PDFs found in your Google Drive")
        return
    
    # Display PDFs with selection
    st.write(f"Found {len(pdfs)} PDFs in your Google Drive")
    
    # Search and filter
    search_term = st.text_input("🔍 Search PDFs...", placeholder="Enter filename or folder name")
    
    # Filter PDFs based on search
    filtered_pdfs = pdfs
    if search_term:
        filtered_pdfs = [
            pdf for pdf in pdfs 
            if search_term.lower() in pdf['name'].lower() or 
               search_term.lower() in pdf.get('parent', '').lower()
        ]
    
    if not filtered_pdfs:
        st.warning(f"No PDFs found matching '{search_term}'")
        return
    
    # Selection interface
    st.write(f"Showing {len(filtered_pdfs)} PDFs")
    
    selected_pdfs = []
    for pdf in filtered_pdfs[:50]:  # Limit to first 50 for performance
        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
        
        with col1:
            selected = st.checkbox(
                pdf['name'], 
                key=f"pdf_{pdf['id']}"
            )
            if selected:
                selected_pdfs.append(pdf)
        
        with col2:
            st.write(f"📁 {pdf.get('parent', 'Drive')}")
        
        with col3:
            size_mb = pdf.get('size', 0) / 1024 / 1024
            st.write(f"📄 {size_mb:.1f} MB")
        
        with col4:
            st.markdown(f"[Open]({pdf.get('drive_link', '#')})")
    
    # Import selected PDFs
    if selected_pdfs:
        st.write(f"Selected {len(selected_pdfs)} PDFs")
        
        if st.button("📥 Import Selected PDFs", type="primary"):
            import_pdfs(selected_pdfs)

def import_pdfs(selected_pdfs):
    """Import and process selected PDFs"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_pdfs = len(selected_pdfs)
    successful_imports = 0
    
    # Debug: Show user_id being used for import
    st.info(f"Importing {total_pdfs} PDFs for user: {st.session_state.user_id}")
    
    for i, pdf in enumerate(selected_pdfs):
        try:
            status_text.text(f"Processing {pdf['name']} ({i+1}/{total_pdfs})")
            
            # Download PDF content
            drive_service = init_drive_service()
            text_content = download_pdf_content(drive_service, pdf['id'])
            
            if text_content:
                # Compute embedding
                embedding = compute_embedding(text_content)
                
                # Save to database
                drive_link = f"https://drive.google.com/file/d/{pdf['id']}/view"
                save_pdf_to_db(
                    user_id=st.session_state.user_id,
                    file_id=pdf['id'],
                    name=pdf['name'],
                    drive_link=drive_link,
                    modified_time=pdf.get('modifiedTime', ''),
                    size=pdf.get('size', 0),
                    parent=pdf.get('parent', ''),
                    text_content=text_content,
                    embedding=embedding
                )
                successful_imports += 1
                st.success(f"✅ Imported: {pdf['name']}")
            else:
                st.warning(f"⚠️ No text content extracted from: {pdf['name']}")
                
            progress_bar.progress((i + 1) / total_pdfs)
            
        except Exception as e:
            st.error(f"Error processing {pdf['name']}: {str(e)}")
            continue
    
    status_text.text("✅ Import completed!")
    st.success(f"Successfully imported {successful_imports} out of {total_pdfs} PDFs")
    
    # Set import complete flag
    if successful_imports > 0:
        st.session_state.import_complete = True
        st.info("✅ Import successful! The page will refresh to show navigation options.")
        st.rerun()
    else:
        st.error("No documents were successfully saved. Please try importing again.")

def chat_page():
    """AI Chat interface"""
    st.title("🤖 AI Chat - Query Your Documents")
    
    # Get Groq API key from environment
    groq_api_key = os.getenv('GROQ_API_KEY')
    
    # Debug: Show current user_id
    st.sidebar.info(f"User ID: {st.session_state.user_id}")
    
    # Check if user has imported documents
    conn = sqlite3.connect('memoryos.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM pdf_documents WHERE user_id = ?', (st.session_state.user_id,))
    doc_count = c.fetchone()[0]
    
    # Debug: Show all documents in database
    c.execute('SELECT COUNT(*) FROM pdf_documents')
    total_docs = c.fetchone()[0]
    
    # Debug: Show documents for this user
    c.execute('SELECT name FROM pdf_documents WHERE user_id = ? LIMIT 5', (st.session_state.user_id,))
    user_docs = c.fetchall()
    
    conn.close()
    
    # Debug information
    st.sidebar.write(f"Total documents in DB: {total_docs}")
    st.sidebar.write(f"Documents for user: {doc_count}")
    if user_docs:
        st.sidebar.write("User's documents:")
        for doc in user_docs:
            st.sidebar.write(f"- {doc[0]}")
    
    if doc_count == 0:
        st.warning("No documents imported yet. Please import some PDFs first.")
        st.info("💡 Debug: Check sidebar for user ID and document count information.")
        if st.button("Go to Import"):
            st.session_state.current_page = 'import'
            st.rerun()
        return
    
    st.write(f"💾 You have {doc_count} documents available for search")
    
    # Check Groq API key
    if not groq_api_key:
        st.error("Groq API key not found in environment variables.")
        st.info("Please make sure GROQ_API_KEY is set in your .env file")
        
        # Fallback: allow manual entry
        groq_api_key = st.text_input(
            "🔑 Enter your Groq API Key", 
            type="password",
            help="Get your free API key from https://console.groq.com/"
        )
        
        if not groq_api_key:
            st.warning("Please enter your Groq API key to start chatting")
            return
    else:
        st.success("✅ Groq API key loaded from environment")
    
    # Chat interface
    st.markdown("---")
    
    # Display conversation history
    if st.session_state.conversation_history:
        for message in st.session_state.conversation_history:
            if message['role'] == 'user':
                with st.chat_message("user"):
                    st.write(message['content'])
            else:
                with st.chat_message("assistant"):
                    st.write(message['content'])
                    if 'sources' in message:
                        with st.expander("📚 Sources"):
                            for source in message['sources']:
                                st.markdown(f"- [{source['name']}]({source['drive_link']}) (Score: {source['score']:.3f})")
    
    # Chat input
    user_query = st.chat_input("Ask about your documents...")
    
    if user_query:
        # Add user message to conversation
        st.session_state.conversation_history.append({
            'role': 'user',
            'content': user_query
        })
        
        # Display user message
        with st.chat_message("user"):
            st.write(user_query)
        
        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # Perform semantic search
                top_matches = semantic_search(user_query, top_k=5, user_id=st.session_state.user_id)
                
                # Generate answer
                answer, sources = answer_query_with_groq(
                    st.session_state.conversation_history, 
                    top_matches, 
                    groq_api_key
                )
                
                # Display answer
                st.write(answer)
                
                # Display sources
                if sources:
                    with st.expander("📚 Sources"):
                        for source in sources:
                            st.markdown(f"- [{source['name']}]({source['drive_link']}) (Score: {source['score']:.3f})")
                
                # Add assistant message to conversation
                st.session_state.conversation_history.append({
                    'role': 'assistant',
                    'content': answer,
                    'sources': sources
                })
    
    # Clear conversation button
    if st.session_state.conversation_history:
        if st.button("🗑️ Clear Conversation"):
            st.session_state.conversation_history = []
            st.rerun()

# Sidebar navigation
def sidebar():
    """Sidebar navigation"""
    with st.sidebar:
        st.title("🧠 IMOS")
        st.markdown("---")
        
        # Debug information
        st.write(f"**Current page:** {st.session_state.current_page}")
        st.write(f"**User ID:** {st.session_state.user_id}")
        st.write(f"**Authenticated:** {is_authenticated()}")
        
        st.markdown("---")
        
        # Navigation
        if st.button("🏠 Home", use_container_width=True):
            st.session_state.current_page = 'landing'
            st.rerun()
        
        if is_authenticated():
            if st.button("📁 Import PDFs", use_container_width=True):
                st.session_state.current_page = 'import'
                st.rerun()
            
            if st.button("🤖 AI Chat", use_container_width=True):
                st.session_state.current_page = 'chat'
                st.rerun()
            
            st.markdown("---")
            
            # User info
            conn = sqlite3.connect('memoryos.db')
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM pdf_documents WHERE user_id = ?', (st.session_state.user_id,))
            doc_count = c.fetchone()[0]
            conn.close()
            
            st.metric("Documents", doc_count)
            st.metric("Conversations", len(st.session_state.conversation_history))
            
            if st.button("🚪 Sign Out", use_container_width=True):
                # Clear authentication and session state
                sign_out()
                # Clear other session state
                keys_to_clear = ['current_page', 'authenticated', 'drive_pdfs_cache', 'conversation_history']
                for key in keys_to_clear:
                    if key in st.session_state:
                        del st.session_state[key]
                st.session_state.current_page = 'landing'
                st.rerun()

# Main app
def main():
    """Main application"""
    try:
        # Initialize database
        setup_db()
        
        # Debug: Show current page in main area
        st.caption(f"Debug: Current page = {st.session_state.current_page}")
        
        # Sidebar
        sidebar()
        
        # Main content based on current page
        if st.session_state.current_page == 'landing':
            landing_page()
        elif st.session_state.current_page == 'import':
            import_page()
        elif st.session_state.current_page == 'chat':
            chat_page()
        else:
            st.error(f"Unknown page: {st.session_state.current_page}")
            st.session_state.current_page = 'landing'
            st.rerun()
    except Exception as e:
        st.error(f"Application Error: {str(e)}")
        st.exception(e)

if __name__ == "__main__":
    main()