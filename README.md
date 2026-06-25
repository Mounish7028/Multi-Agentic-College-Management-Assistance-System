# 🎓 AI-Powered College Multi-Agent Assistant System

A production-ready multi-agent system designed using LangGraph, LangChain, SQLite, and ChromaDB. It provides role-based academic access control and lets Students and Faculty interact with institutional data through natural language.

---

# Preview:-
<img width="1600" height="901" alt="WhatsApp Image 2026-06-25 at 3 38 38 PM" src="https://github.com/user-attachments/assets/df6d312f-cf22-48fd-95ad-b540e421220e" />


## 🌟 Features

1. **Role-Based Access Control (RBAC)**: Enforces access rules using rule-based guardrails.
   - **Students** can only view their own attendance, grades, results, pending courses, prerequisites, and submit leave requests or book courses. They cannot view other students' records or modify attendance.
   - **Faculty** can view assigned classes, student rosters, courses, grades, approve/reject leave requests, check classroom availability, and book classrooms.
2. **Multi-Agent Orchestration**:
   - **Guardrail Agent**: Pure Python rule-based safety validation for role enforcement, prompt injection, and SQL injection blocking.
   - **Supervisor Agent**: Routes requests to the appropriate processing stream (Database, RAG, or Conversational).
   - **SQL Query Agent**: Generates SQL using the local Ollama LLM (`qwen3:8b`).
   - **Validator Agent**: Exercises a dry-run (`EXPLAIN`) of the query to verify SQLite syntax and checks table boundaries to guarantee safety. Iteratively prompts the SQL agent for correction if invalid.
3. **Retrieval Augmented Generation (RAG)**: Uses ChromaDB and `BAAI/bge-large-en-v1.5` embeddings to answer general policy questions (handbook, exam rules, leave policies, bus routes).
4. **JSON-based Conversation Memory**: Keeps a persistent history of conversations in the `/memory` folder per user.

---

## 📁 Project Structure

```
MultiAgentWorkflow/
├── data/                      # SQLite DB and ChromaDB files
├── knowledge_base/            # RAG documents (Markdown/TXT)
├── memory/                    # JSON memory files per user
├── db/                        # Database schemas and seed files
│   ├── __init__.py
│   ├── database.py            # SQLite connection and helper functions
│   └── seed_data.py           # Populates mock data
├── rag/                       # RAG index and search scripts
│   ├── __init__.py
│   └── rag_engine.py          # Document chunking and Chroma search
├── memory_store/              # Persistent memory manager
│   ├── __init__.py
│   └── memory_manager.py      # Conversation log saving/loading
├── agents/                    # Multi-Agent LangGraph implementations
│   ├── __init__.py
│   ├── llm_provider.py        # Instantiates ChatOllama (Qwen-3 8B)
│   ├── guardrail_agent.py     # Rule-based guardrails
│   ├── sql_agent.py           # Text-to-SQL agent
│   ├── validator_agent.py     # SQL dry-run syntax validator
│   ├── supervisor_agent.py    # Orchestration and response prompts
│   └── graph.py               # Compiled LangGraph StateGraph
├── app.py                     # Streamlit frontend application
├── requirements.txt           # Package dependencies
├── .env                       # Local environment variables
└── README.md                  # Project instructions
```

---

## 🔑 Test Credentials

Use these credentials on the Streamlit login page:

### Student Login
- **Email**: `alice@college.edu`
- **Password**: `password123`
- *(Permitted: Access own CS attendance, view completed results, submit leaves)*

- **Email**: `bob@college.edu`
- **Password**: `password123`

### Faculty Login
- **Email**: `johndoe@college.edu`
- **Password**: `password123`
- *(Permitted: View AI Fundamentals students, check classroom availability, book classrooms)*

---

## 🚀 Setup Instructions

### 1. Prerequisite: Install Ollama & Pull Model
1. Download and install [Ollama](https://ollama.com).
2. Start the Ollama application.
3. Run the following command in your terminal to download the Qwen3 model:
   ```bash
   ollama pull qwen3:8b
   ```

### 2. Environment Setup
1. Clone or extract this repository into your workspace.
2. Verify that your `.env` contains the correct database and model paths:
   ```ini
   DB_PATH=data/college.db
   CHROMA_DB_PATH=data/chroma_db
   KNOWLEDGE_BASE_DIR=knowledge_base
   MEMORY_DIR=memory
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=qwen3:8b
   EMBEDDING_MODEL=BAAI/bge-large-en-v1.5
   ```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Initialize Database and Seed Data
Run the database seed script to set up schema tables and populate them with sample data:
```bash
python db/seed_data.py
```

### 5. Build RAG Vector Database Index
Initialize Chroma DB by chunking and embedding the college handbook documents:
```bash
python rag/rag_engine.py
```

### 6. Run Streamlit Application
Launch the frontend dashboard:
```bash
streamlit run app.py
```
This will automatically open the login page in your default browser (usually at `http://localhost:8501`).

---

## ❓ Example Queries for Testing

### Logged in as Student (Alice Smith)
* **Personal Data (Database)**: `"What is my attendance percentage?"` or `"Which courses are pending?"`
* **Academic Query (RAG)**: `"How many leaves are allowed per semester?"` or `"What are the library timings on Saturdays?"`
* **Access Violation (Blocked)**: `"Show grades of Bob Jones"` (should be blocked by Guardrails).
* **Write Action (Database)**: `"Submit a leave request for tomorrow."`

### Logged in as Faculty (Dr. John Doe)
* **Classroom Action (Database)**: `"Book Lab-302 for tomorrow."` or `"Which classrooms are available between 2 PM and 4 PM?"`
* **Student Roster (Database)**: `"Show students enrolled in AI Fundamentals."`
* **Administrative (Database)**: `"Reject leave request ID 23."` or `"Approve leave requests submitted today."`
