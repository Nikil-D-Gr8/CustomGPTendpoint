from flask import Flask, request, jsonify
import chromadb
from chromadb.utils import embedding_functions
import uuid

app = Flask(__name__)

# Initialize ChromaDB in-memory
chroma_client = chromadb.Client()
collection = chroma_client.create_collection(name="text_chunks")

# Default embedding function (OpenAI-like)
embedding_fn = embedding_functions.DefaultEmbeddingFunction()

# Helper: Chunk text into 20-word pieces
def chunk_text(text, chunk_size=20):
    words = text.split()
    return [
        ' '.join(words[i:i + chunk_size])
        for i in range(0, len(words), chunk_size)
    ]

@app.route("/home")
def home():
    return "<h1>Welcome Home</h1>"


@app.route("/store", methods=["POST"])
def store_chunks():
    data = request.json
    text = data.get("text")
    tags = data.get("tags")  # Don't default to {}

    if not text:
        return jsonify({"error": "Text is required"}), 400

    chunks = chunk_text(text)
    ids = [str(uuid.uuid4()) for _ in chunks]
    embeddings = embedding_fn(chunks)

    if tags and isinstance(tags, dict) and tags:
        # ✅ Tags provided
        metadatas = [tags] * len(chunks)
    else:
        # ✅ Provide dummy metadata (Chroma requires non-empty)
        metadatas = [{"source": "default"}] * len(chunks)

    collection.add(
        documents=chunks,
        ids=ids,
        metadatas=metadatas,
        embeddings=embeddings
    )

    return jsonify({"message": "Chunks stored", "chunk_count": len(chunks)})

@app.route("/query", methods=["GET"])
def query():
    query_text = request.args.get("query")
    if not query_text:
        return jsonify({"error": "Query parameter is required"}), 400

    results = collection.query(
        query_texts=[query_text],
        n_results=1,
        embeddings=embedding_fn([query_text])
    )

    if not results['documents'][0]:
        return jsonify({"result": None, "message": "No match found"}), 200

    return jsonify({
        "result": results['documents'][0][0],
        "metadata": results['metadatas'][0][0]
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)
