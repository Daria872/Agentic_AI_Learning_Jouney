import json
from pathlib import Path
from typing import Literal

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_experimental.text_splitter import SemanticChunker
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)


BASE_DIR = Path(__file__).resolve().parent
DOCUMENTS_DIR = BASE_DIR / "documents"
VECTOR_DB_DIR = BASE_DIR / "chroma_db"
COLLECTION_NAME = "rag_documents"
EMBEDDING_MODEL = "nomic-embed-text"
CHAT_MODEL = "mistral"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
SPLIT_METHOD: Literal[
    "manual", "recursive", "format_aware", "semantic", "agentic"
] = "format_aware"
AGENT_ATOM_SIZE = 300
AGENT_MAX_UNITS_PER_REQUEST = 12

#It loads .txt and .md files from a documents folder, chunks and stores them in persistent Chroma, then answers questions using retrieved context and Ollama’s Mistral model

def load_documents() -> list[Document]: #Returns a lost
    """Load UTF-8 text and Markdown files from the documents directory."""
    if not DOCUMENTS_DIR.is_dir(): #If DOCUMENTS_DIR is not found in the hard drive
        raise FileNotFoundError(
            f"Create a documents directory and add .txt or .md files: {DOCUMENTS_DIR}"
        )

    documents = [
        Document(
            #Reads the entire content of the text file
            page_content=file_path.read_text(encoding="utf-8"),
            #Records the relative path
            metadata={"source": str(file_path.relative_to(BASE_DIR))},
        )
        for pattern in ("*.txt", "*.md")
        #rglob-> scans all the subfolders in .txt and .md files
        for file_path in DOCUMENTS_DIR.rglob(pattern)
    ]
    #Removes all the whitespaces and ensure there are no empty files
    documents = [document for document in documents if document.page_content.strip()]
    #If the document becomes empty after removing white spaces, raise error otherwise return it
    if not documents:
        raise FileNotFoundError(
            f"No non-empty .txt or .md documents found in {DOCUMENTS_DIR}"
        )
    return documents

#Chunking->manually
def split_documents_manually(
    documents: list[Document],  #Stores the list of documents containing .txt or .md files
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[Document]: #Returns a list of split chunks
    """Split text into fixed-size character windows, preserving source metadata."""
    if chunk_size <= 0 or not 0 <= chunk_overlap < chunk_size:
        raise ValueError("Require chunk_size > 0 and 0 <= chunk_overlap < chunk_size")

    chunks: list[Document] = []
    step = chunk_size - chunk_overlap #Sliding window to specify the number of chunks 
    for document in documents:
        text = document.page_content
        for start in range(0, len(text), step):
            chunk_text = text[start : start + chunk_size].strip()
            if chunk_text:
                chunks.append(
                    Document(
                        page_content=chunk_text,
                        metadata=document.metadata.copy(), #Every chunks remembers which original file it came from
                    )
                )
    return chunks

#By using langchain's built in function
def split_documents_recursively(
    documents: list[Document],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[Document]:
    """Use LangChain's recursive splitter to prefer natural text boundaries."""
    splitter = RecursiveCharacterTextSplitter( #Langchain's built in function
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""],  #Based on separators
    )
    return splitter.split_documents(documents)

#Document specific chunking
def split_documents_by_format(documents: list[Document]) -> list[Document]:
    """Split Markdown at headings, then apply recursive chunk-size limits."""
    markdown_splitter = MarkdownHeaderTextSplitter( #Core function offered by langchain to break markdown files based on '#', '##' , '###'
        headers_to_split_on=[
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ], # As it splits, it saves the heading text into metadata keys named "Header 1", "Header 2", and "Header 3".
        strip_headers=False, #inside page_content, leaves # heading lines 
    )
    chunks: list[Document] = []

    #Traverses all the indidual documents
    for document in documents:
        #fetches the relative path
        source = document.metadata.get("source", "")
        #Gets the extension .txt or .md and converts it to lower case for matching 
        extension = Path(source).suffix.lower()
        if extension == ".md": #If the extension is .md
            sections = markdown_splitter.split_text(document.page_content) #divides the Markdown document into logical sections based on headings.
            sections_with_source = [
                Document(
                    page_content=section.page_content,
                    metadata={**document.metadata, **section.metadata}, #Combines original file with new heading 
                )
                for section in sections
            ]#• Passes those sections into split_documents_recursively(). If a single Markdown section is still longer than CHUNK_SIZE, it gets broken down further while keeping both the file source and header metadata attached.
            chunks.extend(split_documents_recursively(sections_with_source))
        elif extension == ".txt": #Since .txt files do not have Markdown headings, they skip header splitting and go straight to split_documents_recursively()
            chunks.extend(split_documents_recursively([document]))
        else:
            raise ValueError(f"Unsupported document format for splitting: {source}")

    return chunks

#Semantic based search
def split_documents_semantically_by_format(
    documents: list[Document],
    embeddings: Embeddings,
) -> list[Document]: #Takes the documents as input and embeddings from vector db
    """Split Markdown by headings, then group semantically similar text."""
    markdown_splitter = MarkdownHeaderTextSplitter( #Splits the markdown file based on # into different sections
        headers_to_split_on=[
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ],
        strip_headers=False, #exclude the headers and focus on content alone
    )
    #Langchain's default SemanticChunker and groups text until there's a significant drop in significant drop in semantic similarity (determined by percentile threshold)
    semantic_splitter = SemanticChunker(
        embeddings,
        breakpoint_threshold_type="percentile",
    )
    chunks: list[Document] = []

    for document in documents:
        source = document.metadata.get("source", "")
        extension = Path(source).suffix.lower()
        #It runs the semantic chunks through a custom split_documents_recursively() function. This acts as a safety net to break down any oversized semantic chunks so they fit within your model's token limits
        if extension == ".md":
            sections = markdown_splitter.split_text(document.page_content)
            documents_to_split = [
                Document(
                    page_content=section.page_content,
                    metadata={**document.metadata, **section.metadata},
                )
                for section in sections
            ]
        elif extension == ".txt":
            documents_to_split = [document]
        else:
            raise ValueError(f"Unsupported document format for splitting: {source}")

        semantic_chunks = semantic_splitter.split_documents(documents_to_split)
        chunks.extend(split_documents_recursively(semantic_chunks))

    return chunks

#Agenic chunking for optimised chunking
def group_units_with_agent(
    units: list[Document],
    agent: ChatOllama,
) -> list[Document]: 
    """Ask the local model to group adjacent text units without rewriting them."""
    #Assigns each small text unit with an index (0,1,..) instead of long paragraphs
    indexed_units = [
        {"index": index, "text": unit.page_content}
        for index, unit in enumerate(units)
    ]
    #Prompting for JSON: Instructs the model to group consecutive indices together until the topic changes or the combined length approaches CHUNK_SIZE, outputting strictly {"groups": [[0, 1], [2]]}.
    prompt = (
        f"Group these ordered text units into coherent chunks. Each group should "
        f"stay within {CHUNK_SIZE} characters when its unit text is joined with "
        "newlines. Make a new group when the topic changes. Do not rewrite or "
        "reorder text. Return only a JSON object in this form: "
        '{"groups": [[0, 1], [2]]}. Every supplied index must appear exactly '
        "once, in its original order, and groups must contain consecutive indices.\n\n"
        f"Text units:\n{json.dumps(indexed_units, ensure_ascii=False)}"
    )
    response = agent.invoke(prompt)
    if not isinstance(response.content, str):
        raise TypeError("The chunking model must return a text JSON response")

    try:
        result = json.loads(response.content)
    except json.JSONDecodeError as error:
        raise ValueError("The chunking model returned invalid JSON") from error

    #Guardrails 
    #Confirms result is a dictionary and contains only the "groups" key (rejecting responses with extra chatter or missing keys).
    if not isinstance(result, dict) or set(result) != {"groups"}:
        raise ValueError("The chunking model response must contain only 'groups'")
    raw_groups = result["groups"]
    #Verifies that the value inside "groups" is a list.
    if not isinstance(raw_groups, list):
        raise ValueError("The chunking model 'groups' value must be a list")

    groups: list[list[int]] = []
    for raw_group in raw_groups:
        if (
            #Loops over every inner group to ensure it is a list, is not empty ([]), and contains only pure integers.
            not isinstance(raw_group, list)
            or not raw_group
            or any(type(index) is not int for index in raw_group)
        ):
            raise ValueError("Each chunk group must be a non-empty list of indices")
        groups.append(raw_group)

    #Flattening: Unpacks nested lists like [[0, 1], [2]] into a flat list [0, 1, 2].
    #Exact sequence check: Compares the flattened list against [0, 1, 2, ...]. If Mistral skipped a paragraph, duplicated an index, or swapped two paragraphs out of order, it immediately raises an error.
    expected_indices = list(range(len(units)))
    flattened_indices = [index for group in groups for index in group]
    if flattened_indices != expected_indices:
        raise ValueError(
            "The chunking model must assign every text unit once and preserve order"
        )
    #Contiguity rule: Ensures there are no gaps inside a single group. For example, [1, 2, 3] matches list(range(1, 4)), whereas [1, 3] fails because unit 2 was skipped.
    if any(
        group != list(range(group[0], group[-1] + 1))
        for group in groups
    ):
        raise ValueError("The chunking model can only group adjacent text units")

    return [
        Document(
            page_content="\n".join(units[index].page_content for index in group),
            metadata=units[group[0]].metadata.copy(),
        )
        for group in groups
    ]

def split_documents_agentically_by_format(
    documents: list[Document],
    agent: ChatOllama,
) -> list[Document]:
    """Use Mistral to group coherent text units within each source document."""
    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ],
        strip_headers=False,
    )
    atom_splitter = RecursiveCharacterTextSplitter(
        chunk_size=AGENT_ATOM_SIZE,
        chunk_overlap=0,
        separators=["\n\n", "\n", " ", ""],
    )
    chunks: list[Document] = []

    for document in documents:
        source = document.metadata.get("source", "")
        extension = Path(source).suffix.lower()
        if extension == ".md":
            sections = markdown_splitter.split_text(document.page_content)
            sections_to_split = [
                Document(
                    page_content=section.page_content,
                    metadata={**document.metadata, **section.metadata},
                )
                for section in sections
            ]
        elif extension == ".txt":
            sections_to_split = [document]
        else:
            raise ValueError(f"Unsupported document format for splitting: {source}")

        for section in sections_to_split:
            #Slicing into batches: Breaks units into smaller batches of size AGENT_MAX_UNITS_PER_REQUEST so Mistral doesn't lose accuracy on massive documents
            units = atom_splitter.split_documents([section])
            for start in range(0, len(units), AGENT_MAX_UNITS_PER_REQUEST):
                unit_batch = units[start : start + AGENT_MAX_UNITS_PER_REQUEST]
                if len(unit_batch) == 1: #If a batch only contains 1 unit, it skips calling Mistral to save time.
                    grouped_chunks = unit_batch
                else:
                    grouped_chunks = group_units_with_agent(unit_batch, agent)
                chunks.extend(split_documents_recursively(grouped_chunks))
                #

    return chunks


#Routing function to identify what type of split, calls the corresponding splitting function and return the result
def split_documents(
    documents: list[Document],
    method: Literal[
        "manual", "recursive", "format_aware", "semantic", "agentic"
    ] = SPLIT_METHOD,
    embeddings: Embeddings | None = None,
    agent: ChatOllama | None = None,
) -> list[Document]:
    if method == "manual":
        return split_documents_manually(documents) 
    if method == "recursive":
        return split_documents_recursively(documents)
    if method == "format_aware":
        return split_documents_by_format(documents)
    if method == "semantic":
        if embeddings is None:
            raise ValueError("Semantic splitting requires an embeddings model")
        return split_documents_semantically_by_format(documents, embeddings)
    if method == "agentic":
        if agent is None:
            raise ValueError("Agentic splitting requires a chat model")
        return split_documents_agentically_by_format(documents, agent)
    raise ValueError(f"Unknown splitting method: {method}")


# Use nomic-embed-text for embeddings and split documents before storing them.
#Connects to your local nomic-embed-text model via OllamaEmbeddings
def build_vector_store() -> Chroma:
    """Split source documents and persist their embeddings in Chroma."""
    #The chunks are now converted into embeddings
    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
    chunking_agent = (
        ChatOllama(model=CHAT_MODEL, temperature=0, format="json")
        if SPLIT_METHOD == "agentic"
        else None
    )
    vector_store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(VECTOR_DB_DIR),
    )
    documents_by_source: dict[str, list[Document]] = {}
    for document in load_documents():
        source = document.metadata["source"] #Organises the documents based on file path
        documents_by_source.setdefault(source, []).append(document)

    for source, source_documents in documents_by_source.items():
        chunks = split_documents(
            source_documents,
            embeddings=embeddings,
            agent=chunking_agent,
        ) #Split based on source
        vector_store.delete(where={"source": source}) #Deletes duplicate files
        vector_store.add_documents(chunks) #This prevents duplicate entries if you edit a document and re-run the script.


    return vector_store

#Connects to your local chat model (like mistral) with temperature=0 to keep answers strictly factual. 
def main() -> None:
    vector_store = build_vector_store() #Build the vector database
    llm = ChatOllama(model=CHAT_MODEL, temperature=0) #For the LLM use Ollama
    prompt = ChatPromptTemplate.from_template(
        """Answer the question using only the supplied context.
If the context does not contain the answer, say you do not know.
Include the source names of the relevant context when possible.

Context:
{context}

Question: {question}
"""
    )
    rag_chain = prompt | llm

    print("RAG is ready. Type 'exit' to quit.")
    while True:
        question = input("\nAsk a question: ").strip()
        if question.lower() in {"exit", "quit"}:
            break
        if not question:
            continue

        #Checks match between content in vector db and user's prompt
        matches = vector_store.similarity_search(question, k=4) #fetches 4 most relavant chunks
        if not matches: #No matches found
            print("No relevant documents were found.")
            continue

        context = "\n\n".join( #Source and content is joined
            f"Source: {document.metadata['source']}\n{document.page_content}"
            for document in matches
        )#Provides to context to llm using invoke
        response = rag_chain.invoke({"context": context, "question": question})
        print(f"\n{response.content}")


if __name__ == "__main__":
    main()