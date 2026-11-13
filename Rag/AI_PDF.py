import hashlib  # Makes repeatable chunk IDs.
from pathlib import Path  # Builds paths beside this script.

import chromadb  # Local vector database.
import requests  # Calls Ollama's local API.
from langchain_community.document_loaders import PyPDFDirectoryLoader  # Reads PDF pages.
from langchain_core.documents import Document  # Holds text and metadata.
from langchain_text_splitters import RecursiveCharacterTextSplitter  # Splits page text.

# Paths, models, and chunk settings.
DATA_PATH = Path(__file__).resolve().parent / "data"  # Folder containing PDFs.
DB_PATH = Path(__file__).resolve().parent / "chroma_db"  # Persistent Chroma folder.
OLLAMA_URL = "http://localhost:11434"  # Local Ollama address.
EMBED_MODEL = "nomic-embed-text"  # Creates text vectors.
CHAT_MODEL = "mistral"  # Writes answers.
CHUNK_SIZE, CHUNK_OVERLAP = 800, 80  # Chunk length and repeated context.

# Load every PDF page from data.
def load_pages() -> list[Document]:  # Returns one document per page.
    if not DATA_PATH.is_dir():  # Check the input folder exists.
        raise FileNotFoundError(f"Folder not found: {DATA_PATH}")
    pages = PyPDFDirectoryLoader(str(DATA_PATH)).load()  # Read the PDFs.
    if not pages:  # Stop if no pages were loaded.
        raise FileNotFoundError(f"No PDF pages found in: {DATA_PATH}")
    return pages  # Keep each page's source and page number.

# Split pages and create IDs from source, page, and chunk number.
def split_pages(pages: list[Document]) -> tuple[list[Document], list[str]]:
    splitter = RecursiveCharacterTextSplitter(  # Split at natural boundaries.
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP  # Set chunk sizing.
    )
    chunks, ids = [], []  # Store chunks and their matching IDs.
    for page in pages:  # Process one page at a time.
        source = str(page.metadata["source"])  # Get the PDF path.
        number = int(page.metadata.get("page", 0)) + 1  # Use page numbers starting at 1.
        source_id = hashlib.sha256(source.encode()).hexdigest()  # Stable source part of ID.
        for index, part in enumerate(splitter.split_documents([page])):  # Split this page.
            chunks.append(Document(  # Keep only Chroma-compatible metadata.
                page_content=part.page_content,
                metadata={"source": source, "page": number, "chunk": index},
            ))
            ids.append(f"{source_id}-p{number}-c{index}")  # Unique and repeatable ID.
    return chunks, ids  # Return paired chunk and ID lists.

# Send one request to the local Ollama API.
def ollama(endpoint: str, data: dict) -> dict:
    try:  # Give a clear message if Ollama is not running.
        response = requests.post(f"{OLLAMA_URL}/api/{endpoint}", json=data, timeout=120)
    except (requests.ConnectionError, requests.Timeout) as error:
        raise RuntimeError("Start Ollama before running this app.") from error
    response.raise_for_status()  # Report HTTP and model errors.
    return response.json()  # Return Ollama's response.

# Convert text into vectors in batches.
def embed(texts: list[str]) -> list[list[float]]:
    vectors = []  # Keep vectors in the same order as the text.
    for start in range(0, len(texts), 32):  # Send at most 32 chunks per request.
        batch = texts[start : start + 32]  # Select the next batch.
        vectors.extend(ollama("embed", {"model": EMBED_MODEL, "input": batch})["embeddings"])
    if len(vectors) != len(texts):  # Check every text got a vector.
        raise ValueError("Ollama returned the wrong number of embeddings.")
    return vectors  # Give vectors to Chroma.

# Build or update the persistent Chroma database.
def build_database() -> chromadb.Collection:
    pages = load_pages()  # Read source PDFs.
    chunks, ids = split_pages(pages)  # Make chunks and stable IDs.
    if not chunks:  # Stop instead of creating an empty database.
        raise ValueError("No text was extracted from the PDFs.")
    vectors = embed([chunk.page_content for chunk in chunks])  # Embed every chunk.
    client = chromadb.PersistentClient(path=str(DB_PATH))  # Open local Chroma.
    collection = client.get_or_create_collection(  # Reuse this collection on reruns.
        "pdf_pages", metadata={"hnsw:space": "cosine"}
    )
    old_ids = collection.get(include=[])["ids"]  # Remember previously indexed IDs.
    collection.upsert(  # Add new chunks or replace chunks with matching IDs.
        ids=ids,
        documents=[chunk.page_content for chunk in chunks],
        metadatas=[chunk.metadata for chunk in chunks],
        embeddings=vectors,
    )
    stale_ids = list(set(old_ids) - set(ids))  # Find chunks no longer in the PDFs.
    if stale_ids:  # Remove old chunks after the new chunks are saved.
        collection.delete(ids=stale_ids)
    print(f"Indexed {len(chunks)} chunks from {len(pages)} pages.")
    return collection  # Return the database for searching.

# Retrieve relevant chunks and ask Mistral to answer.
def answer(collection: chromadb.Collection, question: str) -> str:
    count = collection.count()  # Check how many chunks are searchable.
    if not count:  # Avoid querying an empty database.
        raise ValueError("The vector database is empty.")
    result = collection.query(  # Find the four closest chunks.
        query_embeddings=embed([question]), n_results=min(4, count)
    )
    context = "\n\n".join(  # Attach source and page to each result.
        f"{meta['source']} (page {meta['page']}):\n{text}"
        for text, meta in zip(result["documents"][0], result["metadatas"][0])
    )
    response = ollama("chat", {  # Send the question and context to Mistral.
        "model": CHAT_MODEL, "stream": False, "options": {"temperature": 0},
        "messages": [
            {"role": "system", "content": "Answer only from the context; say if it is insufficient."},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
        ],
    })
    return response["message"]["content"]  # Return Mistral's answer.

# Build once, then answer questions until the user exits.
def main() -> None:
    collection = build_database()  # Load, chunk, embed, and save the PDFs.
    while True:  # Keep the RAG application interactive.
        question = input("Ask a question (or type exit): ").strip()
        if question.lower() in {"exit", "quit"}:  # Stop on the exit command.
            break
        if question:  # Ignore blank input.
            print(answer(collection, question))  # Retrieve context and print the answer.

if __name__ == "__main__":  # Run only when called as a script.
    main()
