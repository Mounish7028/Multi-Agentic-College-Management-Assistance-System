from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END

# Define AgentState
class AgentState(TypedDict):
    query: str
    user_role: str
    user_id: str
    user_name: str
    session_id: str
    
    # Guardrail results
    guardrail_allowed: bool
    guardrail_reason: str
    
    # Route category
    route: str  # BLOCKED, DATABASE, KNOWLEDGE, CONVERSATIONAL
    
    # SQL generation & validation loop
    sql_query: str
    sql_valid: bool
    sql_feedback: str
    sql_attempts: int
    
    # Query execution results
    db_results: str
    rag_context: str
    
    # Final response
    response: str

# Import our helper functions
from db.database import execute_query, execute_write
from rag.rag_engine import query_rag
from memory_store.memory_manager import load_conversation, append_message
from agents.guardrail_agent import validate_query
from agents.sql_agent import generate_sql
from agents.validator_agent import validate_sql
from agents.llm_provider import get_llm
from agents.supervisor_agent import (
    route_query, 
    DB_RESPONSE_PROMPT, 
    KNOWLEDGE_RESPONSE_PROMPT, 
    CONVERSATIONAL_RESPONSE_PROMPT
)

# 0. Entry Node (Diverges execution to Guardrail and Router concurrently)
def entry_node(state: AgentState) -> Dict[str, Any]:
    return {}

# 1. Guardrail Node
def guardrail_node(state: AgentState) -> Dict[str, Any]:
    print("[Graph Node] Running Guardrails...")
    validation = validate_query(
        state["query"], 
        state["user_role"], 
        state["user_id"], 
        state["user_name"]
    )
    return {
        "guardrail_allowed": validation["allowed"],
        "guardrail_reason": validation["reason"]
    }

# 2. Router Node
def router_node(state: AgentState) -> Dict[str, Any]:
    print("[Graph Node] Running Router...")
    category = route_query(state["query"])
    return {
        "route": category,
        "sql_attempts": 0,
        "sql_feedback": ""
    }

# 2b. Decision Gate Node (Synchronizes Guardrail and Router outcomes)
def decision_gate_node(state: AgentState) -> Dict[str, Any]:
    print("[Graph Node] Running Decision Gate...")
    if not state.get("guardrail_allowed", True):
        return {"route": "BLOCKED"}
    return {}

# 3. SQL Generation Node
def sql_generation_node(state: AgentState) -> Dict[str, Any]:
    attempts = state.get("sql_attempts", 0) + 1
    print(f"[Graph Node] Generating SQL (Attempt {attempts})...")
    sql = generate_sql(
        state["query"],
        state["user_role"],
        state["user_id"],
        state["user_name"],
        state.get("sql_feedback")
    )
    return {
        "sql_query": sql,
        "sql_attempts": attempts
    }

# 4. SQL Validation Node
def sql_validation_node(state: AgentState) -> Dict[str, Any]:
    print("[Graph Node] Validating SQL...")
    validation = validate_sql(
        state["sql_query"],
        state["user_role"],
        state["user_id"]
    )
    return {
        "sql_valid": validation["valid"],
        "sql_feedback": validation["feedback"] if not validation["valid"] else ""
    }

# 5. Database Execution Node
def db_execution_node(state: AgentState) -> Dict[str, Any]:
    print("[Graph Node] Executing Database Query...")
    sql = state["sql_query"]
    try:
        sql_upper = sql.strip().upper()
        if sql_upper.startswith("SELECT"):
            results = execute_query(sql)
            results_str = str(results)
        else:
            row_id_or_count = execute_write(sql)
            if sql_upper.startswith("INSERT"):
                results_str = f"Operation successful. Inserted record with ID: {row_id_or_count}."
            else:
                results_str = f"Operation successful. Affected rows: {row_id_or_count}."
    except Exception as e:
        results_str = f"Database execution error: {e}"
        
    return {"db_results": results_str}

# 6. RAG Retrieval Node
def rag_retrieval_node(state: AgentState) -> Dict[str, Any]:
    print("[Graph Node] Retrieving from Knowledge Base (RAG)...")
    context = query_rag(state["query"])
    return {"rag_context": context}

# 7. Response Generation Node
def response_generation_node(state: AgentState) -> Dict[str, Any]:
    print("[Graph Node] Generating Final Response & Saving Memory...")
    route = state["route"]
    query = state["query"]
    user_id = state["user_id"]
    user_name = state["user_name"]
    user_role = state["user_role"]
    session_id = state["session_id"]
    llm = get_llm()
    
    response_text = ""
    
    # Check if blocked by guardrails
    if route == "BLOCKED":
        response_text = state["guardrail_reason"]
    elif route == "DATABASE":
        db_res = state.get("db_results", "No results found.")
        sql = state.get("sql_query", "")
        # If generation failed completely
        if "Failed to generate" in db_res:
            response_text = db_res
        else:
            try:
                resp = llm.invoke([{"role": "user", "content": DB_RESPONSE_PROMPT.format(query=query, sql=sql, results=db_res)}])
                response_text = resp.content.strip()
            except Exception:
                response_text = f"Here is the database information: {db_res}"
    elif route == "KNOWLEDGE":
        context = state.get("rag_context", "No context found.")
        try:
            resp = llm.invoke([{"role": "user", "content": KNOWLEDGE_RESPONSE_PROMPT.format(query=query, context=context)}])
            response_text = resp.content.strip()
        except Exception:
            response_text = f"Based on college guidelines:\n{context}"
    else: # CONVERSATIONAL / memory fallback
        # Load conversation history for context
        memory_data = load_conversation(user_id)
        history_str = ""
        session_messages = []
        for session in memory_data.get("sessions", []):
            if session["session_id"] == session_id:
                session_messages = session["messages"]
                break
        if session_messages:
            history_str = "\n".join([f"{m['role']}: {m['content']}" for m in session_messages[-5:]])
            
        try:
            resp = llm.invoke([{"role": "user", "content": CONVERSATIONAL_RESPONSE_PROMPT.format(query=query, history=history_str)}])
            response_text = resp.content.strip()
        except Exception:
            response_text = "Hello! How can I assist you with your college activities today?"

    # Append exchange to JSON conversation memory
    append_message(user_id, user_name, user_role, session_id, {"role": "user", "content": query})
    append_message(user_id, user_name, user_role, session_id, {"role": "assistant", "content": response_text})

    return {"response": response_text}

# Build the Graph
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("entry", entry_node)
workflow.add_node("guardrail", guardrail_node)
workflow.add_node("router", router_node)
workflow.add_node("decision_gate", decision_gate_node)
workflow.add_node("sql_generation", sql_generation_node)
workflow.add_node("sql_validation", sql_validation_node)
workflow.add_node("db_execution", db_execution_node)
workflow.add_node("rag_retrieval", rag_retrieval_node)
workflow.add_node("response_generation", response_generation_node)

# Set Entry Point
workflow.set_entry_point("entry")

# Define Routing Edges
def route_after_decision_gate(state: AgentState) -> str:
    r = state["route"]
    if r == "BLOCKED":
        return "response_generation"
    elif r == "DATABASE":
        return "sql_generation"
    elif r == "KNOWLEDGE":
        return "rag_retrieval"
    else:
        return "response_generation"

def route_after_validation(state: AgentState) -> str:
    if state["sql_valid"]:
        return "db_execution"
    # If invalid, check attempt count
    if state["sql_attempts"] < 3:
        print(f"[Graph Edge] SQL invalid. Retrying generation (Attempt {state['sql_attempts'] + 1})...")
        return "sql_generation"
    else:
        print("[Graph Edge] SQL invalid. Max attempts reached. Routing to response generation...")
        return "response_generation"

# Add Conditional Edges
workflow.add_conditional_edges(
    "decision_gate",
    route_after_decision_gate,
    {
        "sql_generation": "sql_generation",
        "rag_retrieval": "rag_retrieval",
        "response_generation": "response_generation"
    }
)

workflow.add_conditional_edges(
    "sql_validation",
    route_after_validation,
    {
        "db_execution": "db_execution",
        "sql_generation": "sql_generation",
        "response_generation": "response_generation"
    }
)

# Add Normal Edges (Parallel fan-out from entry, fan-in to decision_gate)
workflow.add_edge("entry", "guardrail")
workflow.add_edge("entry", "router")
workflow.add_edge("guardrail", "decision_gate")
workflow.add_edge("router", "decision_gate")

workflow.add_edge("sql_generation", "sql_validation")
workflow.add_edge("db_execution", "response_generation")
workflow.add_edge("rag_retrieval", "response_generation")
workflow.add_edge("response_generation", END)

# Compile Graph
compiled_graph = workflow.compile()

def run_agent_workflow(query: str, user_role: str, user_id: str, user_name: str, session_id: str) -> str:
    """Executes the compiled LangGraph workflow and returns the final response string."""
    initial_state = {
        "query": query,
        "user_role": user_role,
        "user_id": user_id,
        "user_name": user_name,
        "session_id": session_id,
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
    
    try:
        final_state = compiled_graph.invoke(initial_state)
        return final_state["response"]
    except Exception as e:
        print(f"Error in LangGraph workflow execution: {e}")
        return f"Workflow Error: {e}"

if __name__ == "__main__":
    print("Testing LangGraph compiled workflow...")
    # Test conversational query
    res = run_agent_workflow("Hello there!", "student", "S101", "Alice Smith", "test_graph_session")
    print(f"Response: {res}")
