from flask import Flask, request, jsonify
import chromadb
from chromadb.utils import embedding_functions
import uuid
import requests
import os
from pdfminer.high_level import extract_text

app = Flask(__name__)

# Initialize Chroma client
chroma_client = chromadb.Client()
embedding_fn = embedding_functions.DefaultEmbeddingFunction()

# ========== Utility Functions ==========

def download_file(file_id, destination_path):
    url = f'https://drive.google.com/uc?id={file_id}&export=download'
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(destination_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        return True
    return False

def extract_text_from_pdf(pdf_path):
    try:
        return extract_text(pdf_path)
    except Exception as e:
        print(f"[PDF ERROR] {e}")
        return ""

def chunk_text(text, chunk_size=100):
    words = text.split()
    return [
        ' '.join(words[i:i + chunk_size])
        for i in range(0, len(words), chunk_size)
    ]

# ========== API Routes ==========

@app.route("/store", methods=["POST"])
def store_chunks():
    data = request.json
    file_id = data.get("file_id")
    collection_name = data.get("collection")

    if not file_id or not collection_name:
        return jsonify({"error": "file_id and collection are required"}), 400

    pdf_path = "temp.pdf"

    if not download_file(file_id, pdf_path):
        return jsonify({"error": "Failed to download file"}), 500

    text = extract_text_from_pdf(pdf_path)
    os.remove(pdf_path)

    if not text.strip():
        return jsonify({"error": "No text found in PDF"}), 400

    chunks = chunk_text(text, chunk_size=100)
    ids = [str(uuid.uuid4()) for _ in chunks]
    metadatas = [{"source": f"gdrive:{file_id}"}] * len(chunks)

    try:
        collection = chroma_client.get_or_create_collection(
            name=collection_name,
            embedding_function=embedding_fn
        )
        collection.add(
            documents=chunks,
            ids=ids,
            metadatas=metadatas
        )
        return jsonify({
            "message": f"{len(chunks)} chunks stored in '{collection_name}'"
        })
    except Exception as e:
        return jsonify({"error": f"ChromaDB error: {str(e)}"}), 500

@app.route("/query", methods=["GET"])
def query():
    query_text = request.args.get("query")
    collection_name = request.args.get("collection")

    if not query_text or not collection_name:
        return jsonify({"error": "Both 'query' and 'collection' are required"}), 400

    try:
        collection = chroma_client.get_collection(
            name=collection_name,
            embedding_function=embedding_fn
        )
        results = collection.query(
            query_texts=[query_text],
            n_results=1
        )
        if not results['documents'][0]:
            return jsonify({"result": None, "message": "No match found"}), 200

        return jsonify({
            "result": results['documents'][0][0],
            "metadata": results['metadatas'][0][0]
        })
    except Exception as e:
        return jsonify({"error": f"ChromaDB error: {str(e)}"}), 500

@app.route("/home")
def home():
    return "<h1>Welcome to RAG GPT API (PDF + GDrive)</h1>"

if __name__ == "__main__":
    app.run(debug=True, port=5000)
