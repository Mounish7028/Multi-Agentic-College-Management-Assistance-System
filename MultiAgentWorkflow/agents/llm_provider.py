import os
from dotenv import load_dotenv
from langchain_ollama import ChatOllama

# Load env variables
load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")

def get_llm():
    """Initializes and returns the ChatOllama model with temperature 0 for deterministic outputs."""
    print(f"Connecting to Ollama model '{OLLAMA_MODEL}' at {OLLAMA_BASE_URL}...")
    return ChatOllama(
        base_url=OLLAMA_BASE_URL,
        model=OLLAMA_MODEL,
        temperature=0.0
    )
