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
    print(f"[INFO] Starting file download for file_id: {file_id}")
    url = f'https://drive.google.com/uc?id={file_id}&export=download'
    try:
        response = requests.get(url, stream=True)
        print(f"[INFO] Download status code: {response.status_code}")
        if response.status_code == 200:
            with open(destination_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
            print(f"[INFO] File successfully saved to {destination_path}")
            return True
        else:
            print(f"[ERROR] Failed to download file, status code: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] Exception during file download: {e}")
    return False

def extract_text_from_pdf(pdf_path):
    print(f"[INFO] Extracting text from {pdf_path}")
    try:
        text = extract_text(pdf_path)
        print(f"[INFO] Text extraction completed. Length: {len(text)} characters")
        return text
    except Exception as e:
        print(f"[PDF ERROR] {e}")
        return ""

def chunk_text(text, chunk_size=100):
    print(f"[INFO] Chunking text into {chunk_size}-word chunks")
    words = text.split()
    chunks = [' '.join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
    print(f"[INFO] Created {len(chunks)} chunks")
    return chunks

# ========== API Routes ==========

@app.route("/store", methods=["POST"])
def store_chunks():
    print("[ROUTE] /store triggered")
    try:
        data = request.json
        print(f"[DEBUG] Received data: {data}")
    except Exception as e:
        print(f"[ERROR] Failed to parse JSON: {e}")
        return jsonify({"error": "Invalid JSON format"}), 400

    file_id = data.get("file_id")
    collection_name = data.get("collection")

    if not file_id or not collection_name:
        print("[ERROR] Missing 'file_id' or 'collection' in request")
        return jsonify({"error": "file_id and collection are required"}), 400

    pdf_path = "temp.pdf"

    if not download_file(file_id, pdf_path):
        print("[ERROR] download_file() returned False")
        return jsonify({"error": "Failed to download file"}), 500

    text = extract_text_from_pdf(pdf_path)
    os.remove(pdf_path)

    if not text.strip():
        print("[ERROR] No text found after PDF extraction")
        return jsonify({"error": "No text found in PDF"}), 400

    chunks = chunk_text(text, chunk_size=100)
    ids = [str(uuid.uuid4()) for _ in chunks]
    metadatas = [{"source": f"gdrive:{file_id}"}] * len(chunks)

    try:
        print(f"[INFO] Storing chunks to collection: {collection_name}")
        collection = chroma_client.get_or_create_collection(
            name=collection_name,
            embedding_function=embedding_fn
        )
        collection.add(
            documents=chunks,
            ids=ids,
            metadatas=metadatas
        )
        print(f"[SUCCESS] Stored {len(chunks)} chunks in collection '{collection_name}'")
        return jsonify({
            "message": f"{len(chunks)} chunks stored in '{collection_name}'"
        })
    except Exception as e:
        print(f"[ERROR] ChromaDB error: {e}")
        return jsonify({"error": f"ChromaDB error: {str(e)}"}), 500

@app.route("/query", methods=["GET"])
def query():
    print("[ROUTE] /query triggered")
    query_text = request.args.get("query")
    collection_name = request.args.get("collection")
    print(f"[DEBUG] Query text: '{query_text}', Collection: '{collection_name}'")

    if not query_text or not collection_name:
        print("[ERROR] Missing query or collection in params")
        return jsonify({"error": "Both 'query' and 'collection' are required"}), 400

    try:
        collection = chroma_client.get_collection(
            name=collection_name,
            embedding_function=embedding_fn
        )
        print(f"[INFO] Querying ChromaDB collection '{collection_name}'")
        results = collection.query(
            query_texts=[query_text],
            n_results=1
        )
        if not results['documents'][0]:
            print("[INFO] No match found")
            return jsonify({"result": None, "message": "No match found"}), 200

        print(f"[SUCCESS] Match found: {results['documents'][0][0]}")
        return jsonify({
            "result": results['documents'][0][0],
            "metadata": results['metadatas'][0][0]
        })
    except Exception as e:
        print(f"[ERROR] ChromaDB query error: {e}")
        return jsonify({"error": f"ChromaDB error: {str(e)}"}), 500

@app.route("/home")
def home():
    return "<h1>Welcome to RAG GPT API (PDF + GDrive)</h1>"

if __name__ == "__main__":
    print("[INFO] Starting Flask app on port 5000 with SSL")
    app.run(debug=True, port=5000, ssl_context=("cert.pem", "key.pem"))
