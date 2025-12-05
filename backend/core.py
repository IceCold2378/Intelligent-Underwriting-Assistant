import os
import io
from PyPDF2 import PdfReader

# LangChain components
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_ollama import OllamaLLM
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains.retrieval import create_retrieval_chain 

# Define paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
GUIDELINES_PATH = os.path.join(DATA_DIR, 'guidelines.txt')
APPLICATION_PATH = os.path.join(DATA_DIR, 'sample_app.pdf')

def create_vector_db(file_path):
    """
    Creates a vector database from the underwriting guidelines.
    """
    print("Loading guidelines...")
    # 1. Load the document
    loader = TextLoader(file_path)
    documents = loader.load()

    # 2. Split the document into chunks
    # This is crucial for RAG. It breaks the long text into smaller
    # pieces that can be embedded and retrieved individually.
    print("Splitting documents into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=200
    )
    chunks = text_splitter.split_documents(documents)

    # 3. Create embeddings
    # This uses Ollama (running Mistral locally) to turn
    # the text chunks into numerical vectors.
    print("Creating embeddings...")
    embeddings = OllamaEmbeddings(model="mistral")

    # 4. Create the vector database (ChromaDB)
    # This stores the vectors and allows for fast similarity search.
    # We are using an in-memory database (persist_directory=None).
    print("Creating vector database...")
    vector_db = Chroma.from_documents(
        documents=chunks, 
        embedding=embeddings
    )

    # 5. Create the retriever
    # This is the "search engine" interface for our vector DB.
    # k=3 means it will retrieve the top 3 most relevant chunks.
    return vector_db.as_retriever(search_kwargs={"k": 3})

def load_application_text_from_bytes(pdf_bytes):
    """
    Extracts text from an in-memory PDF file bytes.
    """
    print(f"Loading application from bytes...")
    try:
        pdf_file_in_memory=io.BytesIO(pdf_bytes)
        reader = PdfReader(pdf_file_in_memory)
        application_text = ""
        for page in reader.pages:
            application_text += page.extract_text()
        if not application_text:
            print("Warning: Extracted no text from PDF.")
            return "Error: Could not read text from PDF."
        
        return application_text
    except Exception as e:
        print(f"Error reading PDF bytes:{e}")
        return "Error: Could not read text from PDF."

def create_rag_chain(retriever):
    """
    Creates the RAG (Retrieval-Augmented Generation) chain.
    """
    print("Creating RAG chain...")
    
    # 1. Define the LLM
    # We are using the Mistral model we downloaded via Ollama.
    llm = OllamaLLM(model="mistral")

    # 2. Define the Prompt Template
    # This is the *most important part* for getting good results.
    # We instruct the LLM on its role, what to do, and how to use
    # the 'context' (from the retriever) and 'input' (from the user).
    
    system_prompt = """
    You are an expert underwriting assistant. Your task is to analyze a
    loan application based *only* on the provided 'Underwriting Guidelines'.
    
    Do not use any external knowledge.
    
    Analyze the following 'Loan Application' against the 'Underwriting Guidelines'.
    
    Guidelines:
    {context}
    
    Loan Application:
    {input}
    
    Please provide your analysis in the following format:
    
    **Summary:**
    [Provide a brief summary of the loan application.]
    
    **Flagged Risks:**
    [List all violations or risks found in the application based on the guidelines. 
    For each risk, state the guideline that was violated and why. 
    If no risks are found, state "No risks flagged." ]
    """

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt)
    ])

    # 3. Create the "Stuff Documents" Chain
    # This chain will "stuff" the retrieved documents (our guidelines)
    # into the 'context' variable of the prompt.
    question_answer_chain = create_stuff_documents_chain(llm, prompt)

    # 4. Create the final Retrieval Chain
    # This chain does two things:
    # 1. Takes the user 'input' (application) and finds relevant 'context' (guidelines) using the retriever.
    # 2. Passes the 'input' and 'context' to the 'question_answer_chain' to get a final answer.
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)

    return rag_chain