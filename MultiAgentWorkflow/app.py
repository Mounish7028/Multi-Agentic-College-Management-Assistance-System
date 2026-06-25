import os
import sqlite3
import uuid
import streamlit as st
from db.database import get_connection
from agents.graph import compiled_graph, run_agent_workflow
from memory_store.memory_manager import load_conversation

# Page Config
st.set_page_config(
    page_title="AI College Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Dark Futuristic 2026 SaaS style)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700&display=swap');

    /* Base structure overrides */
    .stApp {
        background: radial-gradient(circle at 90% 10%, rgba(99, 102, 241, 0.07), transparent 600px),
                    radial-gradient(circle at 10% 90%, rgba(168, 85, 247, 0.07), transparent 600px),
                    #090D16 !important;
        color: #E2E8F0 !important;
        font-family: 'Inter', sans-serif !important;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: rgba(9, 13, 22, 0.95) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(20px) !important;
    }

    [data-testid="stSidebar"] .stMarkdown {
        color: #E2E8F0 !important;
    }

    /* Hide default header/footer */
    header {
        background: transparent !important;
    }
    footer {
        visibility: hidden;
        height: 0;
    }
    #MainMenu {
        visibility: hidden;
    }

    /* Form Styling - Glass Card */
    div[data-testid="stForm"] {
        background: rgba(255, 255, 255, 0.02) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 24px !important;
        padding: 35px !important;
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.4) !important;
        backdrop-filter: blur(20px) !important;
        margin-top: 30px !important;
        transition: all 0.3s ease;
    }

    div[data-testid="stForm"]:hover {
        border-color: rgba(99, 102, 241, 0.15) !important;
        box-shadow: 0 20px 50px rgba(99, 102, 241, 0.03) !important;
    }

    /* Headings */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Outfit', sans-serif !important;
        font-weight: 600 !important;
        color: #FFF !important;
    }

    /* Custom UI cards */
    .glass-card {
        background: rgba(255, 255, 255, 0.02) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 16px !important;
        padding: 20px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3) !important;
        backdrop-filter: blur(12px) !important;
        margin-bottom: 20px !important;
        transition: all 0.3s ease;
    }

    .glass-card:hover {
        border-color: rgba(99, 102, 241, 0.2) !important;
        box-shadow: 0 8px 32px 0 rgba(99, 102, 241, 0.05) !important;
    }

    /* User initials avatar */
    .avatar-circle {
        width: 44px;
        height: 44px;
        border-radius: 50%;
        background: linear-gradient(135deg, #6366F1, #A855F7);
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        color: white;
        font-family: 'Outfit', sans-serif;
        font-size: 1.1em;
        box-shadow: 0 0 15px rgba(99, 102, 241, 0.3);
    }

    .user-badge {
        background: rgba(99, 102, 241, 0.08) !important;
        color: #818CF8 !important;
        padding: 6px 14px !important;
        border-radius: 20px !important;
        font-weight: 500 !important;
        font-size: 0.85em !important;
        border: 1px solid rgba(99, 102, 241, 0.15) !important;
        display: inline-block !important;
        margin-bottom: 15px !important;
        font-family: 'Outfit', sans-serif !important;
    }

    .faculty-badge {
        background: rgba(244, 63, 94, 0.08) !important;
        color: #FB7185 !important;
        padding: 6px 14px !important;
        border-radius: 20px !important;
        font-weight: 500 !important;
        font-size: 0.85em !important;
        border: 1px solid rgba(244, 63, 94, 0.15) !important;
        display: inline-block !important;
        margin-bottom: 15px !important;
        font-family: 'Outfit', sans-serif !important;
    }

    /* Chat Input styling */
    div[data-testid="stChatInput"] {
        background-color: rgba(9, 13, 22, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 24px !important;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5) !important;
        backdrop-filter: blur(20px) !important;
        padding: 4px !important;
    }

    div[data-testid="stChatInput"] textarea {
        background-color: transparent !important;
        color: #FFF !important;
        border: none !important;
        font-size: 0.95em !important;
    }

    /* Chat Message Overrides */
    [data-testid="stChatMessage"] {
        background-color: rgba(255, 255, 255, 0.02) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 16px !important;
        padding: 16px 20px !important;
        margin-bottom: 16px !important;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2) !important;
        backdrop-filter: blur(8px) !important;
    }

    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatar"] [class*="user"]),
    [data-testid="stChatMessage"]:has([class*="avatarIcon-user"]),
    [data-testid="stChatMessage"]:has([alt="user avatar"]) {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.04), rgba(168, 85, 247, 0.04)) !important;
        border-color: rgba(99, 102, 241, 0.12) !important;
        box-shadow: 0 4px 30px rgba(99, 102, 241, 0.02) !important;
    }

    /* Base buttons style */
    div.stButton button {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        color: #FFF !important;
        border-radius: 10px !important;
        padding: 8px 16px !important;
        font-weight: 500 !important;
        transition: all 0.3s ease !important;
    }

    div.stButton button:hover {
        background: rgba(255, 255, 255, 0.08) !important;
        border-color: rgba(255, 255, 255, 0.2) !important;
        color: #FFF !important;
    }

    /* Text inputs */
    div[data-baseweb="input"] {
        background-color: rgba(255, 255, 255, 0.02) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 10px !important;
        color: #FFF !important;
    }

    div[data-baseweb="input"]:focus-within {
        border-color: #6366F1 !important;
        box-shadow: 0 0 0 1px #6366F1 !important;
    }

    /* Processing Timeline Styling */
    .timeline-wrapper {
        background: rgba(9, 13, 22, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 16px;
        padding: 22px;
        margin: 15px 0 25px 0;
        backdrop-filter: blur(15px);
        box-shadow: 0 15px 40px rgba(0, 0, 0, 0.4);
    }

    .timeline-title {
        color: rgba(255, 255, 255, 0.85);
        font-family: 'Outfit', sans-serif;
        margin-bottom: 18px;
        font-size: 1.05em;
        font-weight: 600;
        letter-spacing: 0.5px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .timeline-step-card {
        display: flex;
        align-items: center;
        gap: 15px;
        padding: 12px 18px;
        margin-bottom: 8px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.03);
        background: rgba(255, 255, 255, 0.01);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .timeline-step-card.active {
        background: rgba(99, 102, 241, 0.05);
        border-color: rgba(99, 102, 241, 0.2);
        box-shadow: 0 0 15px rgba(99, 102, 241, 0.1);
    }

    .timeline-step-card.completed {
        background: rgba(16, 185, 129, 0.03);
        border-color: rgba(16, 185, 129, 0.1);
    }

    .step-icon {
        font-size: 1.3em;
    }

    .step-info {
        flex: 1;
    }

    .step-name {
        font-weight: 500;
        color: #FFF;
        font-size: 0.9em;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .step-desc {
        font-size: 0.75em;
        color: rgba(255, 255, 255, 0.45);
        margin-top: 2px;
    }

    .step-status {
        font-size: 0.85em;
    }

    /* Warning/Error banners */
    div[data-testid="stAlert"] {
        background: rgba(239, 68, 68, 0.05) !important;
        border: 1px solid rgba(239, 68, 68, 0.15) !important;
        color: #FCA5A5 !important;
        border-radius: 12px !important;
    }
</style>
""", unsafe_allow_html=True)

# Session State Initialization
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "role" not in st.session_state:
    st.session_state.role = None
if "user_details" not in st.session_state:
    st.session_state.user_details = {}
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

def authenticate(email, password):
    """Verifies credentials against Student and Faculty tables."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Check Student Table
    cursor.execute(
        "SELECT student_id, name, email, department, semester FROM Students WHERE email = ? AND password = ?",
        (email.strip(), password.strip())
    )
    student = cursor.fetchone()
    if student:
        conn.close()
        return {
            "user_id": student["student_id"],
            "name": student["name"],
            "email": student["email"],
            "role": "student",
            "details": {
                "Department": student["department"],
                "Semester": student["semester"]
            }
        }
        
    # 2. Check Faculty Table
    cursor.execute(
        "SELECT faculty_id, name, email, designation FROM Faculty WHERE email = ? AND password = ?",
        (email.strip(), password.strip())
    )
    faculty = cursor.fetchone()
    if faculty:
        conn.close()
        return {
            "user_id": faculty["faculty_id"],
            "name": faculty["name"],
            "email": faculty["email"],
            "role": "faculty",
            "details": {
                "Designation": faculty["designation"]
            }
        }
        
    conn.close()
    return None

# Login Page
if not st.session_state.authenticated:
    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        # Form widget is customized to look like a glass card using CSS overrides
        with st.form("login_form"):
            st.markdown("<h1 style='text-align: center; margin-bottom: 0px;'>🎓 AI College Assistant</h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: rgba(255,255,255,0.4); font-size: 0.9em; margin-bottom: 25px;'>Sign in with your institutional credentials</p>", unsafe_allow_html=True)
            
            email = st.text_input("Institutional Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)
            
            if submitted:
                if not email or not password:
                    st.error("Please fill in both email and password fields.")
                else:
                    user_data = authenticate(email, password)
                    if user_data:
                        st.session_state.authenticated = True
                        st.session_state.user_id = user_data["user_id"]
                        st.session_state.username = user_data["name"]
                        st.session_state.user_email = user_data["email"]
                        st.session_state.role = user_data["role"]
                        st.session_state.user_details = user_data["details"]
                        st.session_state.session_id = str(uuid.uuid4())
                        
                        st.session_state.chat_history = []
                        st.rerun()
                    else:
                        st.error("Invalid email or password. Please try again.")

# Main Interface
else:
    # Sidebar
    with st.sidebar:
        # Custom profile avatar widget
        initials = "".join([p[0].upper() for p in st.session_state.username.split()[:2]]) if st.session_state.username else "?"
        st.markdown(f"""
        <div class="glass-card" style="padding: 18px !important; border-radius: 16px !important; background: rgba(255,255,255,0.01) !important; margin-top: 10px;">
            <div style="display: flex; align-items: center; gap: 14px;">
                <div class="avatar-circle">{initials}</div>
                <div style="overflow: hidden;">
                    <div style="font-weight: 600; color: #FFF; font-size: 0.95em; white-space: nowrap; text-overflow: ellipsis; overflow: hidden;">{st.session_state.username}</div>
                    <div style="font-size: 0.78em; color: rgba(255,255,255,0.4); white-space: nowrap; text-overflow: ellipsis; overflow: hidden;">{st.session_state.user_email}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # User badges & details
        if st.session_state.role == "student":
            st.markdown(f"<span class='user-badge'>🎓 Student ID: {st.session_state.user_id}</span>", unsafe_allow_html=True)
        else:
            st.markdown(f"<span class='faculty-badge'>💼 Faculty ID: {st.session_state.user_id}</span>", unsafe_allow_html=True)
            
        st.markdown("<div class='glass-card' style='padding: 15px !important;'>", unsafe_allow_html=True)
        for k, v in st.session_state.user_details.items():
            st.markdown(f"**{k}:** {v}")
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<div style='margin-top: 40px;'></div>", unsafe_allow_html=True)
        
        # Actions in sidebar
        if st.button("🗑️ Clear Conversation", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.session_id = str(uuid.uuid4())
            st.rerun()
            
        if st.button("🚪 Log Out", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user_id = None
            st.session_state.username = None
            st.session_state.user_email = None
            st.session_state.role = None
            st.session_state.user_details = {}
            st.session_state.session_id = None
            st.session_state.chat_history = []
            st.rerun()
            
    # Main Chat Area
    st.markdown(f"<h2>🎓 Institutional Agent</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='color: rgba(255,255,255,0.5); margin-bottom: 25px;'>Inquire about academic courses, grading results, class attendance, campus policies, or submit request forms.</p>", unsafe_allow_html=True)
    
    # Display Chat History
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    # Chat Input
    if user_query := st.chat_input("How can I help you today?"):
        # Display user bubble
        with st.chat_message("user"):
            st.markdown(user_query)
        st.session_state.chat_history.append({"role": "user", "content": user_query})
        
        # Real-time processing timeline containers
        timeline_placeholder = st.empty()
        
        # Initial workflow state
        initial_state = {
            "query": user_query,
            "user_role": st.session_state.role,
            "user_id": st.session_state.user_id,
            "user_name": st.session_state.username,
            "session_id": st.session_state.session_id,
            "guardrail_allowed": True,
            "guardrail_reason": "",
            "route": "PENDING",
            "sql_query": "",
            "sql_valid": False,
            "sql_feedback": "",
            "sql_attempts": 0,
            "db_results": "",
            "rag_context": "",
            "response": ""
        }
        
        node_display = {
            "guardrail": ("🛡️", "Safety Guardrail", "Checking prompt and user role safety..."),
            "router": ("🔀", "Supervisor Router", "Analyzing query intent and routing path..."),
            "decision_gate": ("⚖️", "Decision Gate", "Synchronizing routing and guardrail verdicts..."),
            "sql_generation": ("💾", "SQL Generator", "Writing optimized database query..."),
            "sql_validation": ("🔍", "SQL Validator", "Checking database query syntax and rules..."),
            "db_execution": ("🗄️", "Database Engine", "Executing query and fetching records..."),
            "rag_retrieval": ("📚", "Regulations Finder", "Searching knowledge base context (RAG)..."),
            "response_generation": ("✍️", "Response Builder", "Formulating natural language response...")
        }
        
        progress_steps = []
        final_state = {}
        active_node = None
        response = ""
        
        try:
            # Stream compilation events from LangGraph to update timeline dynamically
            # This provides a visual representation of agent workflow execution
            for event in compiled_graph.stream(initial_state):
                for node_name, state_update in event.items():
                    final_state.update(state_update)
                    active_node = node_name
                    
                    if node_name in node_display:
                        if node_name not in progress_steps:
                            # Insert in correct workflow order for visualization
                            progress_steps.append(node_name)
                    
                    # Update live timeline HTML representation
                    timeline_html = "<div class='timeline-wrapper'>"
                    timeline_html += "<div class='timeline-title'>⚙️ Pipeline Processing</div>"
                    for step_node in progress_steps:
                        icon, name, desc = node_display[step_node]
                        is_active = (step_node == active_node)
                        status_class = "active" if is_active else "completed"
                        status_icon = "🔵" if is_active else "✅"
                        timeline_html += f"""
                        <div class='timeline-step-card {status_class}'>
                            <div class='step-icon'>{icon}</div>
                            <div class='step-info'>
                                <div class='step-name'>{name} <span class='step-status'>{status_icon}</span></div>
                                <div class='step-desc'>{desc}</div>
                            </div>
                        </div>
                        """
                    timeline_html += "</div>"
                    timeline_placeholder.markdown(timeline_html, unsafe_allow_html=True)
            
            response = final_state.get("response", "No response generated.")
            
            # Clear timeline on success
            timeline_placeholder.empty()
            
        except Exception as e:
            # If streaming execution fails, attempt fallback compile invoke
            try:
                response = run_agent_workflow(
                    query=user_query,
                    user_role=st.session_state.role,
                    user_id=st.session_state.user_id,
                    user_name=st.session_state.username,
                    session_id=st.session_state.session_id
                )
            except Exception as stream_e:
                response = f"Workflow Error: {e}"
            timeline_placeholder.empty()
            
        # Display warning if local Ollama model is missing
        if "model 'qwen3:8b' not found" in response or "404" in response or "connection refused" in response.lower():
            st.error("⚠️ Local LLM Connection Error: Could not connect to the model `qwen3:1.7b` via Ollama.")
            st.info("💡 **Fix instructions:**\n1. Ensure Ollama is running on your machine.\n2. Run the command **`ollama pull qwen3:1.7b`** in your command line to install the model.\n3. Alternatively, update the `OLLAMA_MODEL` in your `.env` file to an existing model (e.g. `llama3`, `qwen2.5`).")
            response = "I was unable to connect to the local Ollama service or the model `qwen3:1.7b` is not installed. Please follow the instructions in the sidebar or warning banner."
            
        # Display assistant bubble
        with st.chat_message("assistant"):
            st.markdown(response)
        st.session_state.chat_history.append({"role": "assistant", "content": response})
