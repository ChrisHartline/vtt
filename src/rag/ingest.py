import os
import glob
import re
from docling.document_converter import DocumentConverter
from langchain_text_splitters import MarkdownTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

# These TSR modules render (via Docling) with '## ' markdown headers for every
# room/entry/section -- e.g. "## 12. OAKEN CABINET", "## ENTRY 5.",
# "## PART 4: SECOND DUNGEON LEVEL" (verified against real Docling output).
# Splitting on these instead of blind character counts means every chunk can
# be tagged with the room it actually came from, so retrieval can be scoped
# to "only what's in the current room" instead of the whole module.
_SECTION_HEADER_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)


def split_by_section(markdown: str):
    """Split module markdown into (text, section_label) pairs on '## ' headers.

    Falls back to a single ("unknown"-labeled) section if no headers are
    found, so ingestion never silently drops content for a module that
    doesn't follow the same header convention.
    """
    matches = list(_SECTION_HEADER_RE.finditer(markdown))
    if not matches:
        return [(markdown, "unknown")]

    sections = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
        label = m.group(1).strip()
        text = markdown[start:end].strip()
        if text:
            sections.append((text, label))
    return sections


def ingest_pdfs(source_dir: str = "knowledge_base/dnd", persist_dir: str = "data/chroma"):
    print(f"Starting ingestion from {source_dir}...")
    converter = DocumentConverter()

    # 1. Parse PDFs with Docling
    pdf_files = glob.glob(os.path.join(source_dir, "*.pdf"))
    if not pdf_files:
        print(f"No PDFs found in {source_dir}")
        return

    # Sub-splitter for sections still too long for one chunk -- keeps the
    # section tag attached to every resulting piece.
    sub_splitter = MarkdownTextSplitter(chunk_size=1000, chunk_overlap=200)

    all_chunks = []
    for pdf_path in pdf_files:
        source = os.path.basename(pdf_path)
        print(f"Parsing: {pdf_path} using Docling (Layout Preserving)...")
        result = converter.convert(pdf_path)
        markdown_content = result.document.export_to_markdown()

        sections = split_by_section(markdown_content)
        print(f"  {source}: {len(sections)} sections found")

        for section_text, section_label in sections:
            pieces = (
                sub_splitter.split_text(section_text)
                if len(section_text) > 1000
                else [section_text]
            )
            for piece in pieces:
                all_chunks.append(Document(
                    page_content=piece,
                    metadata={"source": source, "section": section_label},
                ))

    # 2. Embed and store
    print(f"Embedding {len(all_chunks)} section-tagged chunks locally using HuggingFace...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    print(f"Saving to Chroma DB at {persist_dir}...")
    # Chroma.from_documents() ADDS to whatever's already at persist_dir rather
    # than replacing it -- re-running ingestion (e.g. after a chunking-scheme
    # change, or just adding a new module) silently doubles up on old data
    # instead of rebuilding clean. Reset the collection first so re-running
    # this is idempotent.
    vector_store = Chroma(persist_directory=persist_dir, embedding_function=embeddings)
    existing_ids = vector_store.get(limit=1_000_000)["ids"]
    if existing_ids:
        print(f"Clearing {len(existing_ids)} existing chunks before re-ingesting...")
        vector_store.delete(ids=existing_ids)

    vector_store.add_documents(all_chunks)
    print("Ingestion complete!")

if __name__ == "__main__":
    ingest_pdfs()
