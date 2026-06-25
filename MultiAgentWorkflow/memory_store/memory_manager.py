import os
import json
from datetime import datetime
from dotenv import load_dotenv

# Load env variables
load_dotenv()

MEMORY_DIR = os.getenv("MEMORY_DIR", "memory")

def get_memory_file_path(user_id: str) -> str:
    """Returns the file path for a user's memory JSON."""
    if not os.path.exists(MEMORY_DIR):
        os.makedirs(MEMORY_DIR)
    # Sanitize user_id for file systems
    safe_user_id = "".join(c for c in user_id if c.isalnum() or c in ("-", "_")).rstrip()
    return os.path.join(MEMORY_DIR, f"{safe_user_id}.json")

def load_conversation(user_id: str) -> dict:
    """
    Loads conversation memory for a user.
    If no file exists, returns a default structure.
    """
    file_path = get_memory_file_path(user_id)
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading memory for user {user_id}: {e}")
            
    # Default structure
    return {
        "user_id": user_id,
        "username": "",
        "role": "",
        "sessions": []
    }

def save_conversation(user_id: str, username: str, role: str, session_id: str, messages: list):
    """
    Saves or updates a conversation session for a user.
    """
    memory_data = load_conversation(user_id)
    memory_data["username"] = username
    memory_data["role"] = role
    
    # Check if session already exists
    session_found = False
    for session in memory_data["sessions"]:
        if session["session_id"] == session_id:
            session["messages"] = messages
            session["updated_at"] = datetime.now().isoformat()
            session_found = True
            break
            
    if not session_found:
        memory_data["sessions"].append({
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "messages": messages
        })
        
    file_path = get_memory_file_path(user_id)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(memory_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving memory for user {user_id}: {e}")

def append_message(user_id: str, username: str, role: str, session_id: str, message: dict):
    """
    Appends a single message (e.g. {"role": "user", "content": "..."}) to the specified session.
    """
    memory_data = load_conversation(user_id)
    
    target_session = None
    for session in memory_data["sessions"]:
        if session["session_id"] == session_id:
            target_session = session
            break
            
    if target_session is None:
        target_session = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "messages": []
        }
        memory_data["sessions"].append(target_session)
        
    target_session["messages"].append(message)
    target_session["updated_at"] = datetime.now().isoformat()
    
    memory_data["username"] = username
    memory_data["role"] = role
    
    file_path = get_memory_file_path(user_id)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(memory_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error appending message for user {user_id}: {e}")

if __name__ == "__main__":
    # Test functions
    test_user = "S101"
    test_session = "session_abc"
    append_message(test_user, "Alice Smith", "student", test_session, {"role": "user", "content": "Hello world"})
    append_message(test_user, "Alice Smith", "student", test_session, {"role": "assistant", "content": "Hello! How can I help you?"})
    print(load_conversation(test_user))
