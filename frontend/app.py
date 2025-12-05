import streamlit as st
import requests

# --- Page Configuration ---
st.set_page_config(
    page_title="Intelligent Underwriting Assistant",
    page_icon="🤖",
    layout="wide"
)

# --- UI Elements ---
st.title("Intelligent Underwriting Assistant 🤖")
st.write("Upload a loan application PDF to analyze it against internal guidelines.")

# File uploader widget
uploaded_file = st.file_uploader(
    "Upload Loan Application (PDF)", 
    type="pdf",
    help="Please upload the loan application in PDF format."
)

# "Analyze Application" button
if st.button("Analyze Application"):
    # Check if a file has been uploaded
    if uploaded_file is not None:
        # Show a spinner while processing
        with st.spinner("Analyzing document... This may take a moment."):
            
            # --- API Call ---
            # Define the backend API endpoint
            api_url = "http://backend:8000/analyze"

            # Prepare the file for the POST request
            # The key 'file' must match the parameter name in the FastAPI endpoint
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}

            try:
                # Send the request to the backend
                response = requests.post(api_url, files=files, timeout=120) # 120-second timeout

                # Check the response from the server
                if response.status_code == 200:
                    result = response.json()
                    st.subheader("✅ Analysis Complete")
                    
                    # Use st.markdown to render the formatted response from the LLM
                    st.markdown(result['analysis'])
                    
                else:
                    # Show an error message if the API call failed
                    st.error(f"Error from API: {response.status_code} - {response.text}")

            except requests.exceptions.RequestException as e:
                # Handle network-related errors (e.g., connection refused)
                st.error(f"Could not connect to the analysis service. Please ensure the backend is running. Details: {e}")

    else:
        # Show a warning if no file is uploaded
        st.warning("Please upload a PDF file to analyze.")