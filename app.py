from flask import Flask, render_template, request, jsonify
from sentence_transformers import SentenceTransformer
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.schema import Document
import faiss
import numpy as np
import pandas as pd
import google.generativeai as genai
import re
from datetime import datetime
import os
from dotenv import load_dotenv

app = Flask(__name__)

# Configuration
load_dotenv()

API_KEY = os.getenv('GEMINI_API_KEY')

if not API_KEY or not API_KEY.startswith("AIza"):
    raise ValueError("Invalid or missing Google API Key")

try:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-pro')
    print("✅ Gemini API connected successfully")
except Exception as e:
    raise RuntimeError(f"Failed to configure Gemini API: {str(e)}")

# Load models
def load_models():
    print("Loading models...")
    
    metadata = pd.read_csv("unified_cli_commands.csv")
    metadata['text_data'] = (
        "Command: " + metadata['command'].fillna('') + "\n" +
        "Description: " + metadata['description'].fillna('') + "\n" +
        "OS: " + metadata['os'].fillna('') + "\n" +
        "Generated Command: " + metadata['generated_command'].fillna('')
    )
    
    embedding_model = SentenceTransformer('models/content/all-MiniLM-L6-v2')
    embeddings_model = HuggingFaceEmbeddings(model_name="models/content/all-MiniLM-L6-v2")
    vectorstore = FAISS.load_local(
        "models/content/faiss_vectorstore", 
        embeddings_model,
        allow_dangerous_deserialization=True
    )
    
    return {
        "metadata": metadata,
        "vectorstore": vectorstore,
        "retriever": vectorstore.as_retriever(search_kwargs={"k": 5})
    }

models = load_models()

# Chatbot functions
def retrieval_tool(query, os_pref):
    try:
        all_results = models["retriever"].invoke(query)
        filtered = [doc for doc in all_results if doc.metadata.get("os", "").lower() == os_pref.lower()]

        if len(filtered) < 3:
            general_commands = [doc for doc in all_results if doc.metadata.get("os", "").lower() in ["all", "general"]]
            filtered.extend(general_commands)
            filtered = filtered[:5]

        return filtered if filtered else all_results
    except Exception as e:
        print(f"Retrieval error: {e}")
        return []

def format_command_response(query, retrieved_docs, os_pref, chat_context):
    context = "\n".join([doc.page_content for doc in retrieved_docs])
    
    prompt = f"""You are CLI-Tutor, a {os_pref} command-line expert. The user asks: "{query}"

Relevant commands:
{context}

Respond concisely with:
1. The solution to their problem
2. The command in ```code blocks```
3. Brief explanation
4. Practical example if helpful
"""
    return prompt

def gemini_llm(prompt):
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini API error: {e}")
        return "I'm having trouble connecting right now. Please try again later."

# API Routes
@app.route('/')
def home():
    return render_template('landing.html')

@app.route('/chat')
def chat_interface():
    return render_template('index.html') 

@app.route('/reset', methods=['POST'])
def reset_chat():
    return jsonify({
        "messages": [{
            "role": "assistant",
            "content": "👋 Welcome to CLI-Tutor! I'm ready to help with your command-line questions.",
            "timestamp": datetime.now().isoformat()
        }],
        "os": "Windows"
    })

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data['message']
    os_pref = data.get('os', 'Windows')  # Default to Windows
    messages = data.get('messages', [])
    
    # Add user message to history
    messages.append({
        "role": "user",
        "content": user_message,
        "timestamp": datetime.now().isoformat()
    })

    # Process query
    retrieved_docs = retrieval_tool(user_message, os_pref)
    prompt = format_command_response(user_message, retrieved_docs, os_pref, "")
    llm_response = gemini_llm(prompt)

    # Add assistant response
    messages.append({
        "role": "assistant",
        "content": llm_response,
        "timestamp": datetime.now().isoformat()
    })
    
    return jsonify({
        "response": llm_response,
        "os": os_pref,
        "messages": messages
    })

if __name__ == '__main__':
    app.run(debug=True)