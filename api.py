
import os
import re
import shutil
import urllib.request
from pathlib import Path
from tempfile import NamedTemporaryFile

from litellm import completion

import PyPDF2  # Use PyMuPDF instead of fitz
import numpy as np

import json
from tempfile import _TemporaryFileWrapper

import gradio as gr
import requests

import openai


import tensorflow_hub as hub

import tensorflow as tf

from fastapi import UploadFile
from sklearn.neighbors import NearestNeighbors
import json

recommender = None

def download_pdf(url, output_path):
    
    urllib.request.urlretrieve(url, output_path)


def preprocess(text):
    
    text = text.replace('\n', ' ')  # Replace newlines with spaces
    text = re.sub('\s+', ' ', text)  # Replace multiple spaces with single spaces
    return text


def pdf_to_text(path, start_page=1, end_page=None):

    pdf_file = open(path, 'rb')  # Open as a binary file
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    total_pages = len(pdf_reader.pages)

    if end_page is None:
        end_page = total_pages

    text_list = []

    for page_num in range(start_page - 1, end_page):
        page = pdf_reader.pages[page_num]
        text = page.extract_text()
        text = preprocess(text)
        text_list.append(text)

    pdf_file.close()
    return text_list 


def text_to_chunks(texts, word_length=150, start_page=1):
    
    text_toks = [t.split(' ') for t in texts]
    chunks = []

    for idx, words in enumerate(text_toks):
        for i in range(0, len(words), word_length):
            chunk = words[i : i + word_length]
            if (
                (i + word_length) > len(words)
                and (len(chunk) < word_length)
                and (len(text_toks) != (idx + 1))
            ):
                text_toks[idx + 1] = chunk + text_toks[idx + 1]
                continue
            chunk = ' '.join(chunk).strip()
            chunk = f'[Page no. {idx+start_page}]' + ' ' + '"' + chunk + '"'
            chunks.append(chunk)
    return chunks



class SemanticSearch:

    def __init__(self):
        
        #model_path = "./saved_model.pb"  # Update with your download path
        #self.use = tf.saved_model.load(model_path)       
        self.use = hub.load('https://tfhub.dev/google/universal-sentence-encoder/4')          
        self.fitted = False

    def fit(self, data, batch=1000, n_neighbors=5):
        
        self.data = data
        self.embeddings = self.get_text_embedding(data, batch=batch)
        n_neighbors = min(n_neighbors, len(self.embeddings))
        self.nn = NearestNeighbors(n_neighbors=n_neighbors)
        self.nn.fit(self.embeddings)
        self.fitted = True

    def __call__(self, text, return_data=True):
        
        inp_emb = self.use([text])
        neighbors = self.nn.kneighbors(inp_emb, return_distance=False)[0]

        if return_data:
            return [self.data[i] for i in neighbors]
        else:
            return neighbors

    def get_text_embedding(self, texts, batch=1000):
        
        embeddings = []
        for i in range(0, len(texts), batch):
            text_batch = texts[i : (i + batch)]
            emb_batch = self.use(text_batch)
            embeddings.append(emb_batch)
        embeddings = np.vstack(embeddings)
        return embeddings


def load_recommender(path, start_page=1):
    
    global recommender
    if recommender is None:
        recommender = SemanticSearch()

    texts = pdf_to_text(path, start_page=start_page)
    chunks = text_to_chunks(texts, start_page=start_page)
    recommender.fit(chunks)
    return 'Corpus Loaded.'

def generate_text(openAI_key, messages, engine="gpt-3.5-turbo-0125"):
    """Generates text using the OpenAI API with error handling.

    Args:
        openAI_key (str): Your OpenAI API key.
        messages (list): A list of dictionaries containing message content and role (user or system).
        engine (str, optional): The OpenAI engine to use. Defaults to "gpt-3.5-turbo-0125".

    Returns:
        str: The generated text response.
    """

    openai.api_key = openAI_key
    try:
        # Construct a single prompt string 
 
        response = openai.chat.completions.create(
            model='gpt-3.5-turbo-0125',
            messages=messages,
            max_tokens=512,
            temperature=0.7,
            n=1,  # Generate a single response
        )
        message = response.choices[0].message.content.strip() 
    except Exception as e:
        message = f'API Error: {str(e)}'
    return message

def generate_answer(question, openAI_key):
    """Generates an answer to a question based on the loaded corpus.

    Args:
        question (str): The question to answer.
        openAI_key (str): Your OpenAI API key.

    Returns:
        dict: A dictionary containing the generated answer under the key "result".
    """

    # Providing a more detailed context
    topn_chunks = recommender(question)
    context = ""

    for c in topn_chunks:
        context += c + '\n\n'

    # Cite sources using square brackets with page number
    ##context = 'Anupam Poddar is known for his extensive art collection and contributions to contemporary art in India. He co-founded the Devi Art Foundation, a non-profit organization dedicated to promoting contemporary art from the Indian subcontinent [1].'

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": context},
        {"role": "user", "content": question}
    ]

    prompt = (
        "Instructions: Compose a comprehensive reply to the query using the search results given. "
        "Cite each reference using square brackets with page number [X] notation (each result has this number at the beginning). "
        "Citation should be done at the end of each sentence. If the search results mention multiple subjects "
        "with the same name, create separate answers for each. Only include information found in the results and "
        "don't add any additional information. Make sure the answer is correct and don't output false content. "
        "If the text does not relate to the query, simply state 'Data Not Available'. Ignore outlier "
        "search results which has nothing to do with the question. Only answer what is asked. The "
        "answer should be short and concise. Answer step-by-step. \n\nQuery: {question}\nAnswer: "
    )
    messages.append({"role": "system", "content": prompt})

    answer = generate_text(openAI_key, messages)
    #if answer == 'Data Not Available':
    #    return {"result": topn_chunks[0]}

    return {"result": answer}


def load_openai_key() -> str:
    """Loads the OpenAI API key from the environment variable.

    Raises:
        ValueError: If the OPENAI_API_KEY environment variable is not set.

    Returns:
        str: The OpenAI API key.
    """

    key = os.environ.get("API_KEY")
    print(key)
    if key is None:
        raise ValueError(
            "[ERROR]: Please set your OPENAI_API_KEY environment variable. Get your key here: https://platform.openai.com/account/api-keys"
        )
    return key

def ask_url(url: str, question: str):
    """Synchronously processes a URL, downloads the PDF, and generates an answer to a question."""
    try:
        print("Downloading PDF...")
        download_pdf(url, './corpus.pdf')
        print("Loading recommender...")
        load_recommender('./corpus.pdf')
        openAI_key = load_openai_key()
        print("Generating answer...")
        return generate_answer(question, openAI_key)
    except Exception as e:
        return f"An error occurred: {str(e)}"

def ask_file(file_path: str, question: str):
    """Synchronously processes a file path, extracts text, and generates an answer to a question."""
    try:
        print("Loading recommender...")
        load_recommender(file_path)
        openAI_key = load_openai_key()
        print("Generating answer...")
        answer = generate_answer(question, openAI_key)
        return answer
    except Exception as e:
        return f"An error occurred: {str('Data Not Available')}"

