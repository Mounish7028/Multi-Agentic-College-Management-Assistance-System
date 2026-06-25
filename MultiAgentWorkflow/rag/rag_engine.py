import os
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# Load environment variables
load_dotenv()

CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "data/chroma_db")
KNOWLEDGE_BASE_DIR = os.getenv("KNOWLEDGE_BASE_DIR", "knowledge_base")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-v1.5")

_embeddings = None

def get_embeddings():
    """Lazy initialization of HuggingFace embeddings."""
    global _embeddings
    if _embeddings is None:
        print(f"Loading embedding model: {EMBEDDING_MODEL} (running on CPU)...")
        # Run on CPU to ensure compatibility across client hardware
        model_kwargs = {'device': 'cpu'}
        encode_kwargs = {'normalize_embeddings': True} # standard for bge models
        _embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs=model_kwargs,
            encode_kwargs=encode_kwargs
        )
    return _embeddings

def init_rag_db(force_rebuild=False):
    """
    Initializes Chroma DB with documents in the KNOWLEDGE_BASE_DIR.
    If the database folder already exists, it loads it, unless force_rebuild is True.
    """
    # Check if DB already exists and contains files
    if os.path.exists(CHROMA_DB_PATH) and len(os.listdir(CHROMA_DB_PATH)) > 0 and not force_rebuild:
        print("Chroma DB already initialized. Loading existing index.")
        return Chroma(persist_directory=CHROMA_DB_PATH, embedding_function=get_embeddings())

    print("Initializing Chroma DB from knowledge base files...")
    if not os.path.exists(KNOWLEDGE_BASE_DIR):
        os.makedirs(KNOWLEDGE_BASE_DIR)
        print(f"Created empty knowledge base directory: {KNOWLEDGE_BASE_DIR}")
        return None

    # Load all txt/md files from knowledge base
    documents = []
    for filename in os.listdir(KNOWLEDGE_BASE_DIR):
        if filename.endswith(".txt") or filename.endswith(".md"):
            filepath = os.path.join(KNOWLEDGE_BASE_DIR, filename)
            try:
                loader = TextLoader(filepath, encoding="utf-8")
                documents.extend(loader.load())
                print(f"Loaded: {filename}")
            except Exception as e:
                print(f"Error loading {filename}: {e}")

    if not documents:
        print("No documents found in knowledge base. Vector store not created.")
        return None

    # Chunk the documents
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        length_function=len
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Split documents into {len(chunks)} chunks.")

    # Create Chroma DB
    db = Chroma.from_documents(
        documents=chunks,
        embedding=get_embeddings(),
        persist_directory=CHROMA_DB_PATH
    )
    db.persist()
    print("Chroma DB created and persisted successfully.")
    return db

def query_rag(query_text: str, k: int = 3) -> str:
    """
    Performs similarity search against Chroma DB and returns structured context block.
    """
    db = init_rag_db()
    if db is None:
        return "Knowledge base is currently empty."
    
    docs = db.similarity_search(query_text, k=k)
    
    # Format document contents
    context_list = []
    for i, doc in enumerate(docs):
        source = os.path.basename(doc.metadata.get('source', 'unknown'))
        context_list.append(f"[Source: {source}]\n{doc.page_content}")
        
    return "\n\n---\n\n".join(context_list)

if __name__ == "__main__":
    # Test initialization
    db = init_rag_db(force_rebuild=True)
    if db:
        test_query = "How many leaves are allowed per semester?"
        print(f"\nTest Query: {test_query}")
        result = query_rag(test_query)
        print(f"Result:\n{result}")
