
import streamlit as st
import tempfile
import os
from api import ask_url, ask_file

# Define custom styles
def local_css(file_name):
    with open(file_name, "r") as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

def remote_css(url):
    st.markdown(f'<link href="{url}" rel="stylesheet">', unsafe_allow_html=True)

def icon(icon_name):
    st.markdown(f'<i class="material-icons">{icon_name}</i>', unsafe_allow_html=True)

# Apply custom CSS
#local_css("./style.css")  # Assuming you have a CSS file named 'style.css' in the same directory
# Alternatively, you can define CSS directly here

st.markdown("""
<style>
.primaryColor {
    color: #0e76a8;
}
.secondaryColor {
    color: #0e76a8;
}
div.stButton > button:first-child {
    background-color: #0e76a8;
    color: white;
}
</style>
""", unsafe_allow_html=True)

st.title('PDF-GPT', anchor=None)

st.write('''
This application allows you to ask questions about the content of PDF files. You can provide a PDF either by entering a URL or by uploading a file directly.
''', anchor=None)

api_key = st.text_input("Enter your API key:", type="password")  # Use type="password" to hide the API key input

if api_key:
    os.environ['API_KEY'] = api_key  # Set the API key in the environment

# Create a form for user inputs
with st.form("Query Form"):
    # Using columns to organize the input fields
    col1, col2 = st.columns(2)
    
    with col1:
        form_type = st.radio("Choose your input type:", ("URL", "Upload PDF"), index=0, horizontal=True)
    
    #if form_type == "URL":
    url = st.text_input("Enter the URL of the PDF:", max_chars=250)
    #uploaded_file = None  # Ensure file is None when URL is chosen
    #else:
    #url = None  # Ensure URL is None when file is chosen
    uploaded_file = st.file_uploader("Upload your PDF file", type=["pdf"], accept_multiple_files=False)
    
    question = st.text_input("Enter your question:", max_chars=500)
    submitted = st.form_submit_button("Submit", on_click=None, args=None, kwargs=None, help=None)

if submitted:
    if form_type == "URL" and url:
        with st.spinner("Downloading and processing PDF from URL..."):
            try:
                response = ask_url(url, question)
                st.markdown(f"<div class='primaryColor'><h1>Answer</h1>{response['result']}</div>", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"An error occurred: {e}")
    elif form_type == "Upload PDF" and uploaded_file:
        with st.spinner("Processing uploaded PDF..."):
            try:
                # Using a context manager to automatically clean up the temporary file
                with tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp.seek(0)  # Move read cursor to the start of the file
                    response = ask_file(tmp.name, question)
                
                st.markdown(f"<div class='secondaryColor'><h1>Answer</h1>{response['result']}</div>", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"An error occurred while processing the file: {e}")
    else:
        st.error("Please provide a URL or upload a file and enter a question.")
