import os
from db.database import execute_query, execute_write
from rag.rag_engine import query_rag
from memory_store.memory_manager import load_conversation, save_conversation, append_message
from agents.guardrail_agent import validate_query
from agents.sql_agent import generate_sql
from agents.validator_agent import validate_sql
from agents.llm_provider import get_llm

ROUTER_PROMPT = """You are the routing hub for a College Multi-Agent Assistant.
Analyze the user's query and classify it into exactly one of three categories:
1. DATABASE: Query is about specific structured student/faculty data, grades, marks, attendance, specific course registrations, prerequisites, classroom bookings, classroom availability, submitting leave requests, approving/rejecting leave requests, or finding faculty advisor.
2. KNOWLEDGE: Query asks about general college policies, leave rules/allowances, academic regulations, examination policies, library timings, bus routes, or general college infrastructure.
3. CONVERSATIONAL: Query is a greeting (hello/hi), general chat, or relates to conversation history (e.g., "thank you", "who are you").

Respond with exactly one word: DATABASE, KNOWLEDGE, or CONVERSATIONAL.
User Query: {query}
Category:"""

DB_RESPONSE_PROMPT = """You are the College Multi-Agent Assistant.
Formulate a friendly, natural language answer for the user based on their query and the database query results.

User Query: {query}
Database SQL Query: {sql}
Database Query Results: {results}

If the results are empty or none, explain that politely.
Answer:"""

KNOWLEDGE_RESPONSE_PROMPT = """You are the College Multi-Agent Assistant.
Formulate an answer for the user based strictly on the retrieved knowledge base context. Do not invent any facts not mentioned in the context.

User Query: {query}
Retrieved Context:
{context}

Answer:"""

CONVERSATIONAL_RESPONSE_PROMPT = """You are the College Multi-Agent Assistant.
Have a polite conversation with the user. Answer their query using the conversation history context.

User Query: {query}
History: {history}

Answer:"""

def route_query(query: str) -> str:
    """Classifies the query into DATABASE, KNOWLEDGE, or CONVERSATIONAL using LLM."""
    llm = get_llm()
    try:
        response = llm.invoke([{"role": "user", "content": ROUTER_PROMPT.format(query=query)}])
        category = response.content.strip().upper()
        # Clean response in case LLM added extra words
        if "DATABASE" in category:
            return "DATABASE"
        elif "KNOWLEDGE" in category:
            return "KNOWLEDGE"
        else:
            return "CONVERSATIONAL"
    except Exception as e:
        print(f"[Supervisor Agent] Error in query classification: {e}")
        # Default fallback
        return "CONVERSATIONAL"

def process_database_query(query: str, user_role: str, user_id: str, user_name: str) -> tuple:
    """
    Executes the loop: SQL Agent -> Validator Agent -> SQL Agent (if needed) -> DB Execution.
    Returns: (sql_query, results_summary)
    """
    error_feedback = None
    max_attempts = 3
    sql = ""
    
    for attempt in range(max_attempts):
        print(f"[Supervisor Agent] SQL Generation Attempt {attempt + 1}/{max_attempts}")
        sql = generate_sql(query, user_role, user_id, user_name, error_feedback)
        
        # Validate the SQL
        validation = validate_sql(sql, user_role, user_id)
        if validation["valid"]:
            print(f"[Supervisor Agent] SQL Query validated successfully: {sql}")
            break
        else:
            print(f"[Supervisor Agent] SQL Validation failed: {validation['feedback']}")
            error_feedback = validation["feedback"]
            sql = "" # Reset
            
    if not sql:
        return "None", f"Failed to generate a secure, valid SQL query after {max_attempts} attempts. Error: {error_feedback}"
        
    # Run the query
    try:
        sql_upper = sql.strip().upper()
        if sql_upper.startswith("SELECT"):
            results = execute_query(sql)
            return sql, str(results)
        else:
            # Write query (INSERT/UPDATE)
            row_id_or_count = execute_write(sql)
            if sql_upper.startswith("INSERT"):
                return sql, f"Operation successful. Inserted record with ID: {row_id_or_count}."
            else:
                return sql, f"Operation successful. Affected rows: {row_id_or_count}."
    except Exception as e:
        print(f"[Supervisor Agent] Database execution error: {e}")
        return sql, f"Database execution error: {e}"

def run_agent_assistant(query: str, user_role: str, user_id: str, user_name: str, session_id: str) -> dict:
    """
    Main orchestrator logic.
    1. Guardrails check.
    2. Route.
    3. Execute path (DB, RAG, Conversational).
    4. Compile response.
    5. Save in memory.
    """
    # 1. Guardrails check
    guardrail_res = validate_query(query, user_role, user_id, user_name)
    if not guardrail_res["allowed"]:
        response_text = guardrail_res["reason"]
        # Save blocked interaction to memory
        append_message(user_id, user_name, user_role, session_id, {"role": "user", "content": query})
        append_message(user_id, user_name, user_role, session_id, {"role": "assistant", "content": response_text})
        return {
            "category": "BLOCKED",
            "sql": "None",
            "results": "Blocked by Guardrails",
            "response": response_text
        }
        
    # Load conversation history for context
    memory_data = load_conversation(user_id)
    history_str = ""
    # Find current session messages
    session_messages = []
    for session in memory_data.get("sessions", []):
        if session["session_id"] == session_id:
            session_messages = session["messages"]
            break
            
    if session_messages:
        # Build history string (last 5 messages for brevity)
        history_str = "\n".join([f"{m['role']}: {m['content']}" for m in session_messages[-5:]])
        
    # Append the user query to memory
    append_message(user_id, user_name, user_role, session_id, {"role": "user", "content": query})
    
    # 2. Route the query
    category = route_query(query)
    print(f"[Supervisor Agent] Route decision: {category}")
    
    sql = "None"
    results = "None"
    response_text = ""
    llm = get_llm()
    
    # 3. Execute appropriate path
    if category == "DATABASE":
        sql, results = process_database_query(query, user_role, user_id, user_name)
        # Synthesize DB response
        try:
            resp = llm.invoke([{"role": "user", "content": DB_RESPONSE_PROMPT.format(query=query, sql=sql, results=results)}])
            response_text = resp.content.strip()
        except Exception as e:
            response_text = f"Here is the database information: {results}"
            
    elif category == "KNOWLEDGE":
        # Run RAG
        context = query_rag(query)
        results = context
        try:
            resp = llm.invoke([{"role": "user", "content": KNOWLEDGE_RESPONSE_PROMPT.format(query=query, context=context)}])
            response_text = resp.content.strip()
        except Exception as e:
            response_text = f"Based on college guidelines:\n{context}"
            
    else: # CONVERSATIONAL
        try:
            resp = llm.invoke([{"role": "user", "content": CONVERSATIONAL_RESPONSE_PROMPT.format(query=query, history=history_str)}])
            response_text = resp.content.strip()
        except Exception as e:
            response_text = "Hello! How can I assist you with your college activities today?"
            
    # Append assistant response to memory
    append_message(user_id, user_name, user_role, session_id, {"role": "assistant", "content": response_text})
    
    return {
        "category": category,
        "sql": sql,
        "results": results,
        "response": response_text
    }

if __name__ == "__main__":
    # Test DB path run
    print("Test running Supervisor...")
    res = run_agent_assistant("What is my attendance percentage?", "student", "S101", "Alice Smith", "test_session_123")
    print(f"Final Output:\n{res}")
