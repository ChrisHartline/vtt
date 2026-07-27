import os
# Bypass network blocks by forcing HuggingFace to use a mirror
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
import glob
from docling.document_converter import DocumentConverter
from langchain_text_splitters import MarkdownTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

def ingest_pdfs(source_dir: str = "knowledge_base/dnd", persist_dir: str = "data/chroma"):
    print(f"Starting ingestion from {source_dir}...")
    converter = DocumentConverter()
    
    # 1. Parse PDFs with Docling
    pdf_files = glob.glob(os.path.join(source_dir, "*.pdf"))
    if not pdf_files:
        print(f"No PDFs found in {source_dir}")
        return
        
    documents = []
    for pdf_path in pdf_files:
        print(f"Parsing: {pdf_path} using Docling (Layout Preserving)...")
        result = converter.convert(pdf_path)
        markdown_content = result.document.export_to_markdown()
        
        # We wrap it in a LangChain Document
        doc = Document(
            page_content=markdown_content,
            metadata={"source": os.path.basename(pdf_path)}
        )
        documents.append(doc)
        
    # 2. Chunk with Markdown Splitter to preserve tables
    print("Chunking documents...")
    splitter = MarkdownTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(documents)
    
    # 3. Embed and store
    print(f"Embedding {len(chunks)} chunks locally using HuggingFace...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    print(f"Saving to Chroma DB at {persist_dir}...")
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=persist_dir
    )
    print("Ingestion complete!")

if __name__ == "__main__":
    ingest_pdfs()
