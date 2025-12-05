import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from contextlib import asynccontextmanager
import uvicorn

# Import the functions from our "brain"
from core import (
    create_vector_db, 
    create_rag_chain, 
    load_application_text_from_bytes
)

# --- Global State ---
# This dictionary will hold our RAG chain
# It's populated only once during the 'startup' event
app_state = {}

# --- Lifespan Event Handler ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    This function runs once when the app starts.
    It builds the RAG chain and stores it in app_state.
    """
    print("Server starting up...")
    print("Building knowledge base... (This may take a moment)")
    
    # Get the path to the guidelines file
    base_dir = os.path.dirname(os.path.abspath(__file__))
    guidelines_path = os.path.join(base_dir, 'data', 'guidelines.txt')
    
    # 1. Build the Vector DB
    retriever = create_vector_db(guidelines_path)
    
    # 2. Create the RAG chain
    rag_chain = create_rag_chain(retriever)
    
    # 3. Store the chain in our app state
    app_state["rag_chain"] = rag_chain
    
    print("Knowledge base and RAG chain are ready.")
    
    yield  # The app is now running
    
    # --- Shutdown ---
    print("Server shutting down...")
    app_state.clear()

# --- Initialize FastAPI ---
# We pass in our 'lifespan' function
app = FastAPI(
    title="Intelligent Underwriting Assistant API",
    description="Analyzes loan applications against underwriting guidelines.",
    lifespan=lifespan
)

# --- API Endpoints ---
@app.get("/", tags=["General"])
def read_root():
    """A simple root endpoint to check if the server is running."""
    return {"message": "Welcome to the Underwriting Assistant API!"}

@app.post("/analyze", tags=["Analysis"])
async def analyze_application(
    file: UploadFile = File(..., description="The PDF loan application to analyze.")
):
    """
    Analyzes a loan application PDF against the stored guidelines.
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF.")

    print(f"Received file: {file.filename}")

    # 1. Read the uploaded file into memory
    contents = await file.read()

    # 2. Extract text from the PDF bytes
    application_text = load_application_text_from_bytes(contents)
    
    if "Error:" in application_text:
        raise HTTPException(status_code=400, detail=application_text)

    # 3. Get the RAG chain from our app state
    rag_chain = app_state.get("rag_chain")
    if not rag_chain:
        raise HTTPException(status_code=500, detail="RAG chain not initialized.")

    # 4. Run the analysis
    try:
        print("Analyzing document...")
        response = rag_chain.invoke({"input": application_text})
        
        # 5. Return the result
        return {"analysis": response["answer"]}
    
    except Exception as e:
        print(f"Error during analysis: {e}")
        raise HTTPException(status_code=500, detail="An error occurred during analysis.")

# --- Main execution ---
if __name__ == "__main__":
    """
    This allows you to run the server directly with 'python main.py'
    (But we will use 'uvicorn' for better control)
    """
    uvicorn.run(app, host="127.0.0.1", port=8000)